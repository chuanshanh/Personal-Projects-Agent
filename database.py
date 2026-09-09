import os
import sqlite3
from contextlib import contextmanager, closing
from datetime import date, timedelta
from pathlib import Path
from models import now, today, nonempty, choice, valid_date, PROJECT_STATUSES, TASK_STATUSES, PRIORITIES


class Database:
    def __init__(self, path=None):
        self.path = Path(path or os.getenv('PROJECT_AGENT_DB', Path(__file__).parent / 'data' / 'project-agent.sqlite3'))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL,
                    goal TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','paused','completed')),
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('todo','done')),
                    priority TEXT NOT NULL CHECK(priority IN ('low','medium','high')),
                    due_date TEXT, created_at TEXT NOT NULL, completed_at TEXT);
                CREATE INDEX IF NOT EXISTS tasks_project ON tasks(project_id);
            ''')
        self._upgrade_ids()

    def _upgrade_ids(self):
        # Old databases reused deleted IDs, allowing stale chat references to hit new data.
        with self.connect() as con:
            schemas = {r['name']: r['sql'] for r in con.execute(
                "SELECT name,sql FROM sqlite_master WHERE name IN ('projects','tasks')")}
            if all('AUTOINCREMENT' in sql.upper() for sql in schemas.values()):
                return
            backup_path = self.path.with_suffix('.pre-v01.sqlite3')
            if not backup_path.exists():
                backup_path.write_bytes(self.backup())
            con.execute('PRAGMA foreign_keys=OFF')
            con.execute('BEGIN IMMEDIATE')
            # Preserve every existing field and ID; all changes roll back on failure.
            for table in ('projects', 'tasks'):
                sql = f'CREATE TABLE new_{table} (' + schemas[table].split('(', 1)[1]
                if 'AUTOINCREMENT' not in sql.upper():
                    sql = sql.replace('INTEGER PRIMARY KEY', 'INTEGER PRIMARY KEY AUTOINCREMENT', 1)
                con.execute(sql)
                con.execute(f'INSERT INTO new_{table} SELECT * FROM {table}')
            con.execute('DROP TABLE tasks')
            con.execute('DROP TABLE projects')
            con.execute('ALTER TABLE new_projects RENAME TO projects')
            con.execute('ALTER TABLE new_tasks RENAME TO tasks')
            con.execute('CREATE INDEX tasks_project ON tasks(project_id)')
            if con.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError('数据库外键校验失败，升级已回滚。')

    @contextmanager
    def connect(self):
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        try:
            with con:
                yield con
        finally:
            con.close()

    def get(self, table, item_id):
        if table not in ('projects', 'tasks'):
            raise ValueError('Invalid table')
        with self.connect() as con:
            row = con.execute(f'SELECT * FROM {table} WHERE id=?', (item_id,)).fetchone()
        if row is None:
            raise ValueError(f'{table} #{item_id} 不存在')
        return dict(row)

    def create_project(self, name, description='', goal=''):
        with self.connect() as con:
            item_id = con.execute('INSERT INTO projects(name,description,goal,status,created_at) VALUES(?,?,?,?,?)',
                                  (nonempty(name), description, goal, 'active', now())).lastrowid
        return self.get('projects', item_id)

    def get_projects(self):
        with self.connect() as con:
            return [dict(r) for r in con.execute('SELECT * FROM projects ORDER BY id')]

    def update_project(self, project_id, name=None, description=None, goal=None, status=None):
        p = self.get('projects', project_id)
        for key, value in dict(name=name, description=description, goal=goal, status=status).items():
            if value is not None:
                p[key] = value
        p['name'] = nonempty(p['name'])
        choice(p['status'], PROJECT_STATUSES)
        with self.connect() as con:
            con.execute('UPDATE projects SET name=?,description=?,goal=?,status=? WHERE id=?',
                        (p['name'], p['description'], p['goal'], p['status'], project_id))
        return self.get('projects', project_id)

    def delete_project(self, project_id):
        self.get('projects', project_id)
        with self.connect() as con:
            con.execute('DELETE FROM projects WHERE id=?', (project_id,))
        return {'deleted_project_id': project_id}

    def create_task(self, project_id, title, priority='medium', due_date=None):
        self.get('projects', project_id)
        with self.connect() as con:
            item_id = con.execute('INSERT INTO tasks(project_id,title,status,priority,due_date,created_at) VALUES(?,?,?,?,?,?)',
                (project_id, nonempty(title), 'todo', choice(priority, PRIORITIES), valid_date(due_date), now())).lastrowid
        return self.get('tasks', item_id)

    def get_tasks(self, project_id=None):
        with self.connect() as con:
            rows = con.execute('SELECT * FROM tasks ORDER BY id' if project_id is None else
                               'SELECT * FROM tasks WHERE project_id=? ORDER BY id',
                               () if project_id is None else (project_id,))
            return [dict(r) for r in rows]

    def update_task(self, task_id, title=None, status=None, priority=None, due_date=None):
        # None leaves a field unchanged; empty due_date explicitly clears it.
        t = self.get('tasks', task_id)
        if title is not None:
            t['title'] = nonempty(title)
        if priority is not None:
            t['priority'] = choice(priority, PRIORITIES)
        if due_date is not None:
            t['due_date'] = valid_date(due_date)
        if status is not None:
            t['status'] = choice(status, TASK_STATUSES)
            t['completed_at'] = (t['completed_at'] or now()) if status == 'done' else None
        with self.connect() as con:
            con.execute('UPDATE tasks SET title=?,status=?,priority=?,due_date=?,completed_at=? WHERE id=?',
                (t['title'], t['status'], t['priority'], t['due_date'], t['completed_at'], task_id))
        return self.get('tasks', task_id)

    def complete_task(self, task_id):
        return self.update_task(task_id, status='done')

    def postpone_task(self, task_id, days=1):
        if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 3650:
            raise ValueError('顺延天数必须是 1 到 3650 的整数')
        task = self.get('tasks', task_id)
        original = date.fromisoformat(task['due_date']) if task['due_date'] else None
        baseline = original if original and original > today() else today()
        updated = self.update_task(task_id, due_date=(baseline + timedelta(days=days)).isoformat())
        return {**updated, 'previous_due_date': original.isoformat() if original else None,
                'postponed_days': days}

    def delete_task(self, task_id):
        self.get('tasks', task_id)
        with self.connect() as con:
            con.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        return {'deleted_task_id': task_id}

    def get_project_status(self, project_id):
        p = self.get('projects', project_id)
        tasks = self.get_tasks(project_id)
        done = sum(t['status'] == 'done' for t in tasks)
        return {**p, 'tasks': tasks, 'completed': done, 'total': len(tasks),
                'progress': round(done / len(tasks) * 100) if tasks else 0}

    def backup(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'backup.sqlite3'
            with self.connect() as source, closing(sqlite3.connect(path)) as destination:
                source.backup(destination)
            return path.read_bytes()
