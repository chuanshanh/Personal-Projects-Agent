from streamlit.testing.v1 import AppTest
from database import Database
from pathlib import Path


def test_manual_flow(tmp_path, monkeypatch):
    path = tmp_path / 'ui.sqlite3'
    monkeypatch.setenv('PROJECT_AGENT_DB', str(path))
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=15).run()
    assert not app.exception
    app.radio[0].set_value('Projects').run()
    app.text_input[0].set_value('我的 MVP')
    app.button[0].click().run()
    assert not app.exception
    db = Database(path)
    assert db.get_projects()[0]['name'] == '我的 MVP'
    task = db.create_task(1, '写测试')
    app.run()
    next(c for c in app.checkbox if c.label == '写测试').check().run()
    assert db.get('tasks', task['id'])['status'] == 'done'
    app.radio[0].set_value('Today').run()
    assert not app.exception
    app.radio[0].set_value('Explore').run()
    assert not app.exception


def open_app(path, monkeypatch):
    monkeypatch.setenv('PROJECT_AGENT_DB', str(path))
    return AppTest.from_file(Path(__file__).resolve().parents[1] / 'app.py', default_timeout=15).run()


def test_external_status_change_is_not_overwritten(tmp_path, monkeypatch):
    path = tmp_path / 'status.sqlite3'
    db = Database(path)
    p = db.create_project('Status')
    task = db.create_task(p['id'], 'Finish me')
    app = open_app(path, monkeypatch)
    app.radio[0].set_value('Projects').run()
    db.complete_task(task['id'])
    app.run()
    assert db.get('tasks', task['id'])['status'] == 'done'
    assert next(c for c in app.checkbox if c.label == 'Finish me').value
    db.update_task(task['id'], status='todo')
    app.run()
    assert not next(c for c in app.checkbox if c.label == 'Finish me').value


def test_task_form_edit_and_delete(tmp_path, monkeypatch):
    path = tmp_path / 'forms.sqlite3'
    db = Database(path)
    p = db.create_project('Forms')
    app = open_app(path, monkeypatch)
    app.radio[0].set_value('Projects').run()
    next(t for t in app.text_input if t.label == '任务名称').set_value('New task')
    next(b for b in app.button if b.label == '新增任务').click().run()
    assert db.get_tasks()[0]['title'] == 'New task'
    # The last task-name input is inside the existing task edit form.
    [t for t in app.text_input if t.label == '任务名称'][-1].set_value('Edited task')
    next(b for b in app.button if b.label == '保存修改').click().run()
    assert db.get_tasks()[0]['title'] == 'Edited task'
    next(b for b in app.button if b.label == '删除任务').click().run()
    assert not db.get_tasks()
    assert not app.exception


def test_today_priority_and_limit(tmp_path, monkeypatch):
    from models import today
    path = tmp_path / 'today.sqlite3'
    db = Database(path)
    p = db.create_project('Focus')
    for i in range(6):
        db.create_task(p['id'], f'Task {i}', priority='high' if i == 5 else 'low', due_date=today().isoformat())
    app = open_app(path, monkeypatch)
    visible = [c for c in app.checkbox if c.key.startswith('today_done_')]
    assert len(visible) == 3
    assert visible[0].label == 'Task 5'
    assert any(e.label == '其他 3 个到期任务' for e in app.expander)


def test_project_edit_and_delete(tmp_path, monkeypatch):
    path = tmp_path / 'project.sqlite3'
    db = Database(path)
    p = db.create_project('Original')
    db.create_task(p['id'], 'Child task')
    app = open_app(path, monkeypatch)
    app.radio[0].set_value('Projects').run()
    next(t for t in app.text_input if t.label == '名称').set_value('Renamed')
    next(s for s in app.selectbox if s.label == '状态').set_value('paused')
    next(b for b in app.button if b.label == '保存项目').click().run()
    assert db.get('projects', p['id'])['name'] == 'Renamed'
    assert db.get('projects', p['id'])['status'] == 'paused'
    assert next(b for b in app.button if b.label == '删除项目').disabled
    next(c for c in app.checkbox if c.label == '同时删除此项目的所有任务').check().run()
    next(b for b in app.button if b.label == '删除项目').click().run()
    assert not db.get_projects() and not db.get_tasks()
    assert not app.exception


def test_chat_refresh_and_partial_failure(tmp_path, monkeypatch):
    import agent
    from models import today
    path = tmp_path / 'chat.sqlite3'
    db = Database(path)
    p = db.create_project('Chat')
    task = db.create_task(p['id'], 'Finish', due_date=today().isoformat())
    monkeypatch.setenv('LLM_PROVIDER', 'openai')
    monkeypatch.setenv('LLM_API_KEY', 'test-only-key')
    app = open_app(path, monkeypatch)
    def fake_chat(database, message, history):
        database.complete_task(task['id'])
        return '已完成', []
    monkeypatch.setattr(agent, 'chat', fake_chat)
    app.chat_input[0].set_value('完成任务').run()
    assert db.get('tasks', task['id'])['status'] == 'done'
    assert not any(c.label == 'Finish' for c in app.checkbox)
    assert not app.exception
    def failing_chat(database, message, history):
        database.update_task(task['id'], status='todo')
        raise RuntimeError('secret should never appear')
    monkeypatch.setattr(agent, 'chat', failing_chat)
    app.chat_input[0].set_value('重新打开任务').run()
    assert any(c.label == 'Finish' for c in app.checkbox)
    assert app.warning
    assert 'secret should never appear' not in str(app)
    assert not app.exception
