"""Django migration regression tests, runnable as a stand-alone script."""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ikon_django.contracts import (
    parse_contract, PayloadError, FrontendChatRequest,
    ChatRequest, GenerateRequest, RetrieveRequest, EmbedRequest,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_request_contracts():
    req = parse_contract(FrontendChatRequest, {
        'conversation_id': 'conv-1',
        'messages': [{'role': 'user', 'content': 'Hello'}],
    })
    check(req.messages[0].content == 'Hello' and req.use_rag is True, 'frontend chat decoding')
    check(parse_contract(ChatRequest, {'query': 'x'}).max_new_tokens == 64, 'chat defaults')
    check(parse_contract(GenerateRequest, {'prompt': 'hello'}).sampler == 'greedy', 'generate defaults')
    check(parse_contract(RetrieveRequest, {'query': 'x'}).top_k == 5, 'retrieve defaults')
    check(parse_contract(EmbedRequest, {'text': 'x'}).text == 'x', 'embed contract')
    bad = (
        (FrontendChatRequest, {'conversation_id': '', 'messages': [{'role': 'user', 'content': 'x'}]}),
        (FrontendChatRequest, {'conversation_id': 'x', 'messages': []}),
        (FrontendChatRequest, {'conversation_id': 'x', 'messages': [{'role': 'admin', 'content': 'x'}]}),
        (ChatRequest, {'query': 'x', 'max_new_tokens': -1}),
        (ChatRequest, {'query': 'x', 'temperature': 0}),
        (ChatRequest, {'query': 'x', 'temperature': float('nan')}),
        (ChatRequest, {'query': 'x', 'use_mmr': 'true'}),
        (RetrieveRequest, {'query': 'x', 'mmr_lambda': 2}),
        (EmbedRequest, {'text': '   '}),
    )
    for model, value in bad:
        try:
            parse_contract(model, value)
        except PayloadError:
            pass
        else:
            raise AssertionError(f'accepted invalid {model.__name__} payload: {value}')


def test_django_files():
    urls = (ROOT / 'ikon_django/urls.py').read_text()
    views = (ROOT / 'ikon_django/views.py').read_text()
    core = (ROOT / 'ikon_django/core.py').read_text()
    app = (ROOT / 'app.py').read_text()
    for path in ('/api/health', '/api/chat/stream', '/v1/health', '/v1/chat', '/v1/generate', '/v1/retrieve', '/v1/embed'):
        check(path.lstrip("/") in urls, f'Django URL mapping missing: {path}')
    check('StreamingHttpResponse' in views and 'application/x-ndjson' in views, 'Django NDJSON stream')
    check('build_stack(args)' in core and 'orchestrator.answer(' in core, 'original RAG and loader logic missing')
    check('inference.generate(' in core, 'original inference logic missing')
    for code in (app, views, core):
        check('from fastapi ' not in code and 'import uvicorn' not in code and 'from pydantic ' not in code,
              'FastAPI runtime still present')
    check('ikon_django.wsgi:application' in (ROOT / 'deploy/start-django.sh').read_text(), 'WSGI deployment guidance')


def test_django_http_if_installed():
    try:
        import django
    except ImportError:
        if os.getenv('SIREIKON_REQUIRE_DJANGO_TESTS') == '1':
            raise RuntimeError('Django HTTP tests require Django: pip install -r requirements.txt')
        print('DJANGO HTTP TEST: SKIPPED (install requirements.txt to run HTTP tests)')
        return
    os.environ['DJANGO_SETTINGS_MODULE'] = 'ikon_django.settings'
    os.environ['SIREIKON_DEBUG'] = '1'
    django.setup()
    from django.test import Client, override_settings
    from django.conf import settings
    from ikon_django import views
    # Django Client uses Host: testserver. Permit it only for this test, never in production.
    allowed = list(settings.ALLOWED_HOSTS) + ['testserver']
    with override_settings(ALLOWED_HOSTS=allowed):
        _test_http_contract(Client(), views)
    print('DJANGO HTTP TEST: PASS')


def _test_http_contract(client, views):
    with patch.object(views.core, 'ensure_stack_loading'):
        health = client.get('/api/health')
        check(health.status_code == 200 and health.json()['backend'] == 'online', 'frontend health')
        check(client.get('/v1/health').status_code == 200, 'v1 health')
    check(client.get('/api/chat/stream').status_code == 405, 'POST-only stream')
    check(client.post('/v1/chat', data='not-json', content_type='application/json').status_code == 400, 'invalid JSON')
    check(client.post('/v1/chat', data=json.dumps({'query':''}), content_type='application/json').status_code == 400, 'schema 400')
    check(client.post('/v1/chat', data=json.dumps({'query':'hello'}), content_type='text/plain').status_code == 400, 'content-type 400')
    with patch.object(views.core, '_run_rag_frontend_chat', return_value={'text':'Hello there', 'citations': []}):
        result = client.post('/api/chat/stream', data=json.dumps({
            'conversation_id':'conv-1','messages':[{'role':'user','content':'hello'}], 'use_rag':True
        }), content_type='application/json')
        check(result.status_code == 200 and result['Content-Type'].startswith('application/x-ndjson'), 'stream status')
        events = [json.loads(chunk) for chunk in result.streaming_content]
        check(events[0]['type']=='meta' and events[-1]['done'] is True, 'stream metadata')
        check(''.join(event['content'] for event in events if event['type']=='token') == 'Hello there', 'stream tokens')
    with patch.object(views.core, '_require_stack', side_effect=views.core.StackUnavailable('not ready')):
        result = client.post('/v1/chat', data=json.dumps({'query':'hi'}), content_type='application/json')
        check(result.status_code == 503, 'stack unavailable 503')


def test_original_llm_rag_bridge_without_framework():
    # Mock only the model objects; exercise the actual migrated IKON adapters.
    from types import SimpleNamespace
    from ikon_django import core
    vocab = SimpleNamespace(special_id=lambda token: 7 if token == '<EOS>' else 0)
    generated = SimpleNamespace(generated_ids=[42], to_dict=lambda: {'generated_ids': [42]})
    tokenizer = SimpleNamespace(encode=lambda text: [1, 2], decode=lambda ids: 'Base answer')
    tokenizer_manager = SimpleNamespace(model=SimpleNamespace(vocabulary=vocab), tokenizer=tokenizer)
    inference = SimpleNamespace(generate=lambda **kwargs: generated)
    rag_result = SimpleNamespace(to_dict=lambda: {
        'answer_text': 'Retrieved answer',
        'citations': [{'document_id': 'doc-A', 'marker': 'S1', 'text': 'source'}],
    })
    orchestrator = SimpleNamespace(answer=lambda **kwargs: rag_result)
    stack = {'tokenizer_manager': tokenizer_manager, 'inference': inference,
             'orchestrator': orchestrator}
    request = parse_contract(FrontendChatRequest, {
        'conversation_id': 'conv-1', 'messages': [{'role': 'user', 'content': 'Question'}]
    })
    with patch.object(core, '_require_stack', return_value=stack):
        base = core._run_base_frontend_chat(request)
        rag = core._run_rag_frontend_chat(request)
    check(base['text'] == 'Base answer', 'original base LLM adapter')
    check(rag['text'] == 'Retrieved answer', 'original RAG adapter')
    check(rag['citations'][0]['title'] == 'doc-A', 'citation normalization')
    check('Question' in core._base_prompt(request.messages), 'existing chat prompt builder')
    check(''.join(core._stream_text_chunks('Hello there')) == 'Hello there', 'stream chunk preservation')
    check(json.loads(core._ndjson_event({'type': 'token', 'content': 'x'}))['content'] == 'x', 'NDJSON format')

def main():
    test_request_contracts()
    test_django_files()
    test_original_llm_rag_bridge_without_framework()
    test_django_http_if_installed()
    print('DJANGO MIGRATION CONTRACT TEST: PASS')


if __name__ == '__main__':
    main()
