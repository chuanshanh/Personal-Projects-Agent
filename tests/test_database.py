import sqlite3
import subprocess
import sys
import pytest
from database import Database


def test_crud_persistence_and_backup(tmp_path):
    path = tmp_path / 'test.sqlite3'
    db = Database(path)
    p = db.create_project('Agent 实习准备', goal='做一个 MVP')
    t = db.create_task(p['id'], '跑通 Tool Calling', due_date='2026-09-09')
    db.complete_task(t['id'])
    first = db.get('tasks', t['id'])['completed_at']
    assert db.complete_task(t['id'])['completed_at'] == first
    assert db.get_project_status(p['id'])['progress'] == 100
    db.update_task(t['id'], status='todo', due_date='', priority='low')
    assert db.get('tasks', t['id'])['completed_at'] is None
    assert db.get('tasks', t['id'])['due_date'] is None
    subprocess.run([sys.executable, '-c',
        'from database import Database; import sys; assert Database(sys.argv[1]).get_tasks()[0]["priority"] == "low"', str(path)], check=True)
    backup = tmp_path / 'backup.sqlite3'
    backup.write_bytes(db.backup())
    assert Database(backup).get_tasks() == db.get_tasks()
    db.delete_task(t['id'])
    assert not db.get_tasks()
    db.create_task(p['id'], '级联删除')
    db.update_project(p['id'], status='paused')
    db.delete_project(p['id'])
    assert not db.get_projects() and not db.get_tasks()


def test_invalid_data_does_not_write(tmp_path):
    db = Database(tmp_path / 'test.sqlite3')
    with pytest.raises(ValueError):
        db.create_project('  ')
    p = db.create_project('Test')
    for kwargs in ({'title': ' '}, {'title': 'x', 'priority': 'urgent'}, {'title': 'x', 'due_date': '2026-02-30'}):
        with pytest.raises(ValueError):
            db.create_task(p['id'], **kwargs)
    with pytest.raises(ValueError):
        db.create_task(999, 'Missing project')
    assert db.get_tasks() == []


def test_postpone_uses_current_persisted_due_date(tmp_path):
    from datetime import date, timedelta
    from models import today
    db = Database(tmp_path / 'postpone.sqlite3')
    p = db.create_project('Postpone')
    original = today() + timedelta(days=7)
    task = db.create_task(p['id'], 'Future task', due_date=original.isoformat())
    result = db.postpone_task(task['id'])
    assert result['previous_due_date'] == original.isoformat()
    assert result['due_date'] == (original + timedelta(days=1)).isoformat()
    db.update_task(task['id'], due_date='')
    assert db.postpone_task(task['id'])['due_date'] == (today() + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError):
        db.postpone_task(task['id'], 0)


def test_legacy_upgrade_preserves_data_and_never_reuses_ids(tmp_path):
    path = tmp_path / 'legacy.sqlite3'
    db = Database(path)
    p = db.create_project('Original', goal='Keep this')
    task = db.create_task(p['id'], 'Original task')
    # Recreate the exact pre-V0.1 schema to exercise upgrade of existing user files.
    with db.connect() as con:
        schemas = list(con.execute("SELECT name,sql FROM sqlite_master WHERE name IN ('projects','tasks')"))
        con.execute('PRAGMA foreign_keys=OFF')
        for row in schemas:
            table = row['name']
            sql = row['sql'].replace(f'CREATE TABLE {table}', f'CREATE TABLE old_{table}').replace(' AUTOINCREMENT', '')
            con.execute(sql)
            con.execute(f'INSERT INTO old_{table} SELECT * FROM {table}')
        con.execute('DROP TABLE tasks')
        con.execute('DROP TABLE projects')
        con.execute('ALTER TABLE old_projects RENAME TO projects')
        con.execute('ALTER TABLE old_tasks RENAME TO tasks')
    reopened = Database(path)
    assert reopened.get('projects', p['id']) == p
    assert reopened.get('tasks', task['id']) == task
    assert path.with_suffix('.pre-v01.sqlite3').exists()
    reopened.delete_task(task['id'])
    new_task = reopened.create_task(p['id'], 'New task')
    assert new_task['id'] > task['id']
    with pytest.raises(ValueError):
        reopened.complete_task(task['id'])
    reopened.delete_project(p['id'])
    assert reopened.create_project('New')['id'] > p['id']
    assert not reopened.get_tasks()
