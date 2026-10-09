"""Real Django test-client suite for IKON's endpoints, streaming, and failure handling.

Run after: python -m pip install -r requirements.txt
Usage: python tests/test_django_http.py
No checkpoint, RAG index, NVIDIA GPU, or running Django server is needed.
"""
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ikon_django.settings')
os.environ['SIREIKON_DEBUG'] = '1'


def main():
    try:
        import django
    except ImportError as exc:
        if os.getenv('SIREIKON_REQUIRE_DJANGO_TESTS') == '1':
            raise SystemExit('Django must be installed: python -m pip install -r requirements.txt') from exc
        print('DJANGO HTTP INTEGRATION TEST: SKIPPED (Django not installed)')
        return
    django.setup()
    from django.conf import settings
    from django.test import Client, override_settings
    from ikon_django import core, views

    # Do not loosen ALLOWED_HOSTS in production to accommodate Django's test client.
    with override_settings(ALLOWED_HOSTS=[*settings.ALLOWED_HOSTS, 'testserver']):
        client = Client(raise_request_exception=True)
        with patch.object(core, 'ensure_stack_loading'):
            res = client.get('/api/health')
            assert res.status_code == 200, (res.status_code, res.content[:200])
            assert res.json()['backend'] == 'online'
            assert 'model_ready' in res.json()
            assert client.get('/v1/health').status_code == 200

        # Django routing / method, JSON and validation parity.
        assert client.get('/api/chat/stream').status_code == 405
        for path in ('/v1/chat','/v1/generate','/v1/retrieve','/v1/embed'):
            assert client.get(path).status_code == 405, path
            assert client.post(path, data='{not-json}', content_type='application/json').status_code == 400, path
            assert client.post(path, data='{}', content_type='application/json').status_code == 400, path
        assert client.post('/v1/chat', data=json.dumps({'query':'hello'}), content_type='text/plain').status_code == 400

        payload = {
            'conversation_id': 'conv-local',
            'messages': [{'role': 'user', 'content': 'Hello Django'}],
            'use_rag': True,
        }
        with patch.object(core, '_run_rag_frontend_chat', return_value={
            'text': 'Hello there', 'citations': [{'title': 'sample'}],
        }) as rag:
            res = client.post('/api/chat/stream', data=json.dumps(payload), content_type='application/json')
            assert res.status_code == 200
            assert res['Content-Type'].startswith('application/x-ndjson')
            assert res['X-Accel-Buffering'] == 'no'
            events = [json.loads(x) for x in res.streaming_content if x.strip()]
            assert events[0]['type'] == 'meta' and events[0]['mode'] == 'rag'
            assert ''.join(item['content'] for item in events if item['type'] == 'token') == 'Hello there'
            assert events[-1]['done'] is True
            rag.assert_called_once()
        payload['use_rag'] = False
        with patch.object(core, '_run_base_frontend_chat', return_value={'text': 'Base model', 'citations': []}):
            res = client.post('/api/chat/stream', data=json.dumps(payload), content_type='application/json')
            events = [json.loads(x) for x in res.streaming_content if x.strip()]
            assert events[0]['mode'] == 'base'
            assert ''.join(x['content'] for x in events if x['type']=='token') == 'Base model'

        # Simulate precisely the frontend 'Response generation failed' case.
        with patch.object(core, '_run_rag_frontend_chat', side_effect=core.StackUnavailable('Missing checkpoint')):
            payload['use_rag'] = True
            res = client.post('/api/chat/stream', data=json.dumps(payload), content_type='application/json')
            events = [json.loads(x) for x in res.streaming_content if x.strip()]
            assert len(events) == 1 and events[0]['type'] == 'error'
            assert 'Missing checkpoint' in events[0]['message']
        with patch.object(core, '_require_stack', side_effect=core.StackUnavailable('Missing checkpoint')):
            res = client.post('/v1/chat', data=json.dumps({'query':'test'}), content_type='application/json')
            assert res.status_code == 503 and 'Missing checkpoint' in res.json()['detail']

        # Mock only the model stack to verify all four v1 endpoints reach the right core API.
        class Output:
            generated_ids = [1, 2]
            def to_dict(self): return {'generated_count': 2}
        class Answer:
            def to_dict(self): return {'answer_text':'IKON answer', 'citations': []}
        class Retrieve:
            def to_dict(self): return {'results': []}
        manager = SimpleNamespace(
            model=SimpleNamespace(vocabulary=SimpleNamespace(special_id=lambda t: 1)),
            tokenizer=SimpleNamespace(encode=lambda text:[2,3], decode=lambda ids:'Base answer'),
        )
        fake_stack = {
            'tokenizer_manager': manager,
            'inference': SimpleNamespace(generate=lambda **kwargs: Output()),
            'orchestrator': SimpleNamespace(answer=lambda **kwargs: Answer()),
            'retrieval': SimpleNamespace(
                search=lambda **kwargs: Retrieve(),
                embedder=SimpleNamespace(embed_text=lambda text: SimpleNamespace(vector=[0.25,0.5])),
            ),
        }
        with patch.object(core, '_require_stack', return_value=fake_stack):
            def post(path, value):
                response = client.post(path, data=json.dumps(value), content_type='application/json')
                assert response.status_code == 200, (path, response.status_code, response.content[:300])
                return response.json()
            assert post('/v1/chat', {'query':'hello'})['answer'] == 'IKON answer'
            assert post('/v1/generate', {'prompt':'hello'})['generated_text'] == 'Base answer'
            assert post('/v1/retrieve', {'query':'hello'})['results'] == []
            assert post('/v1/embed', {'text':'hello'})['dimension'] == 2

    print('DJANGO HTTP INTEGRATION TEST: PASS')


if __name__ == '__main__':
    main()
