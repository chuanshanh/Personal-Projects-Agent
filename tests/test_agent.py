import asyncio
import json
from agents import Model, ModelResponse, Usage
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
from agent import run_turn
from database import Database


class ScriptedModel(Model):
    """Offline contract test: real Runner and tools, scripted model decisions."""
    def __init__(self, calls):
        self.calls = iter(calls)

    async def get_response(self, *args, **kwargs):
        name, arguments = next(self.calls, (None, None))
        if name:
            output = [ResponseFunctionToolCall(type='function_call', name=name,
                arguments=json.dumps(arguments), call_id=f'call_{id(arguments)}')]
        else:
            output = [ResponseOutputMessage(id='msg_done', type='message', role='assistant', status='completed',
                content=[ResponseOutputText(type='output_text', text='已保存', annotations=[])])]
        return ModelResponse(output=output, usage=Usage(), response_id=None)

    async def stream_response(self, *args, **kwargs):
        raise NotImplementedError
        yield


def test_sdk_tool_loop(tmp_path):
    db = Database(tmp_path / 'agent.sqlite3')
    calls = [
        ('get_projects', {}),
        ('create_project', {'name': 'Agent Internship Preparation', 'description': '', 'goal': '完成 MVP'}),
        *[('create_task', {'project_id': 1, 'title': title, 'priority': 'medium', 'due_date': None})
          for title in ['定义 Project Agent MVP', '跑通 Agent + Tool Calling', '完成自然语言修改任务']],
        ('get_project_status', {'project_id': 1}),
    ]
    answer, history = asyncio.run(run_turn(db, '帮我建立项目', model=ScriptedModel(calls)))
    assert answer == '已保存'
    assert len(db.get_tasks()) == 3
    db.update_task(3, due_date='2026-09-16')
    second = [('get_projects', {}), ('complete_task', {'task_id': 2}),
              ('postpone_task', {'task_id': 3, 'days': 1}),
              ('get_project_status', {'project_id': 1})]
    asyncio.run(run_turn(db, '第二个完成，第三个推迟', history, ScriptedModel(second)))
    reopened = Database(db.path)
    assert reopened.get('tasks', 2)['status'] == 'done'
    assert reopened.get('tasks', 3)['due_date'] == '2026-09-17'
    assert reopened.get_project_status(1)['progress'] == 33
    asyncio.run(run_turn(db, '删除第三个', model=ScriptedModel([('delete_task', {'task_id': 3})])))
    assert len(db.get_tasks()) == 2
    asyncio.run(run_turn(db, '暂停项目', model=ScriptedModel([('update_project', {
        'project_id': 1, 'name': None, 'description': None, 'goal': None, 'status': 'paused'})])))
    assert db.get('projects', 1)['status'] == 'paused'
    asyncio.run(run_turn(db, '删除整个项目', model=ScriptedModel([('delete_project', {'project_id': 1})])))
    assert not db.get_projects() and not db.get_tasks()
