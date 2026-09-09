import asyncio
from config import ModelConfig
from database import Database
import agent


def test_provider_config_and_legacy_keys():
    config = ModelConfig.from_settings({'OPENAI_API_KEY': 'secret', 'OPENAI_MODEL': 'old-name'})
    assert config.model == 'old-name' and not config.problem()
    assert 'secret' not in repr(config)
    compatible = ModelConfig.from_settings({'LLM_PROVIDER': 'openai-compatible', 'OPENAI_API_KEY': 'openai-secret',
        'LLM_MODEL': 'local-model', 'LLM_BASE_URL': 'http://localhost:1234/v1'})
    assert compatible.api_key == ''  # Never forward an OpenAI credential to another provider implicitly.
    assert compatible.problem()
    invalid = ModelConfig.from_settings({'LLM_BASE_URL': 'https://api.example.com/v1?api_key=secret', 'LLM_API_KEY': 'x'})
    assert invalid.problem()


def test_compatible_model_adapter_calls_real_tool(tmp_path, monkeypatch):
    from openai import AsyncOpenAI
    import httpx2
    import json
    db = Database(tmp_path / 'compatible.sqlite3')
    p = db.create_project('Provider test')
    task = db.create_task(p['id'], 'Complete via tool')
    requests = []
    def handle(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body['model'] == 'provider-model'
        assert str(request.url) == 'https://provider.example/v1/chat/completions'
        message = {'role': 'assistant', 'content': '已完成'}
        reason = 'stop'
        if len(requests) == 1:
            message = {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'c1', 'type': 'function',
                'function': {'name': 'complete_task', 'arguments': json.dumps({'task_id': task['id']})}}]}
            reason = 'tool_calls'
        return httpx2.Response(200, json={'id': 'chatcmpl-test', 'object': 'chat.completion', 'created': 1,
            'model': 'provider-model', 'choices': [{'index': 0, 'message': message, 'finish_reason': reason}]})
    monkeypatch.setattr(agent, 'load_settings', lambda: {'LLM_PROVIDER': 'openai-compatible',
        'LLM_MODEL': 'provider-model', 'LLM_BASE_URL': 'https://provider.example/v1', 'LLM_API_KEY': 'test-only'})
    def client_factory(**kwargs):
        return AsyncOpenAI(**kwargs, http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handle)))
    monkeypatch.setattr(agent, 'AsyncOpenAI', client_factory)
    answer, _ = asyncio.run(agent.run_turn(db, '完成任务'))
    assert answer == '已完成'
    assert db.get('tasks', task['id'])['status'] == 'done'
    assert any(m['role'] == 'tool' for m in requests[1]['messages'])
