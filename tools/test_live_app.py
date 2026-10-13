"""Live end-to-end verification of the unified SireSoft-IKON application.

Requires a RUNNING `python app.py`, real model artifacts and working API.
Does not train or change any artifacts. --require-gpu checks observed backend.
"""
import argparse
import json
import time
import urllib.error
import urllib.request


def get_json(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        assert response.status == 200, (url, response.status)
        return json.loads(response.read().decode('utf-8'))


def post_json(url, payload):
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}, method='POST',
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        assert response.status == 200, (url, response.status)
        return response.read().decode('utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--web-url', default='http://127.0.0.1:5173')
    parser.add_argument('--require-gpu', action='store_true')
    parser.add_argument('--min-context', type=int, default=0,
                        help='Require an actual loaded checkpoint with at least this many context tokens')
    parser.add_argument('--timeout', type=int, default=120)
    args = parser.parse_args()
    base = args.web_url.rstrip('/')
    with urllib.request.urlopen(base + '/', timeout=10) as response:
        html = response.read().decode('utf-8')
        assert response.status == 200 and ('id="root"' in html or 'src="/src/main.tsx"' in html), 'React/Vite index missing'
    print('PASS React frontend via unified URL')
    deadline = time.monotonic() + args.timeout
    while True:
        health = get_json(base + '/api/health')
        if health.get('model_ready'):
            break
        if health.get('model_error'):
            raise RuntimeError('Model failed to initialize: ' + health['model_error'])
        if time.monotonic() >= deadline:
            raise TimeoutError('Timed out waiting for trained model to load')
        time.sleep(2)
    print('PASS Django and trained model loaded:', health['compute'])
    if args.min_context:
        model_health = get_json(base + '/v1/health')
        model_info = (model_health.get('model') or {}).get('model') or {}
        actual = model_info.get('max_seq_len', 0)
        if actual < args.min_context:
            raise RuntimeError(f'Loaded model context {actual} is less than required {args.min_context}')
        print('PASS actual checkpoint context:', actual)
    if args.require_gpu and health['compute'].get('active') != 'cuda':
        raise RuntimeError('GPU is NOT active; refusing to count CPU mode as a CUDA pass')

    # Vite proxies /api and /v1 on the SAME frontend origin. Test the
    # real model, retrieval index and embedding API (not stubs).
    generated = json.loads(post_json(base + '/v1/generate', {
        'prompt': 'Hi', 'max_new_tokens': 8,
    }))
    assert generated.get('generated_count', 0) > 0
    print('PASS real Transformer generation:', generated['generated_count'], 'tokens')

    retrieved = json.loads(post_json(base + '/v1/retrieve', {
        'query': 'SireSoft?', 'top_k': 1,
    }))
    assert retrieved.get('hits'), 'No actual documents returned from the RAG index'
    print('PASS real vector retrieval:', len(retrieved['hits']), 'hits')

    embedding = json.loads(post_json(base + '/v1/embed', {'text': 'SireSoft?'}))
    assert embedding.get('dimension', 0) > 0
    print('PASS real text embedding:', embedding['dimension'], 'dimensions')

    rag_answer = json.loads(post_json(base + '/v1/chat', {
        'query': 'SireSoft?', 'max_new_tokens': 8,
    }))
    assert 'answer' in rag_answer
    print('PASS IKON RAG orchestrator endpoint (v1)')

    # The same-origin React chat endpoint tests both base and RAG without
    # reaching Django through a second URL.
    for rag in (False, True):
        response = post_json(base + '/api/chat/stream', {
            'conversation_id': 'ikon-live-smoke',
            'messages': [{'role': 'user', 'content': 'SireSoft?'}],
            'use_rag': rag,
        })
        events = [json.loads(line) for line in response.splitlines() if line.strip()]
        errors = [event for event in events if event.get('type') == 'error']
        if errors:
            raise RuntimeError(('RAG' if rag else 'Base') + ' failed: ' + str(errors[0]))
        assert events and events[0].get('mode') == ('rag' if rag else 'base')
        assert events[-1].get('done') is True, events
        print('PASS', 'RAG' if rag else 'General chat', 'tokens:',
              len(''.join(e.get('content', '') for e in events if e.get('type') == 'token')),
              'citations:', len(events[0].get('citations', [])))
    after = get_json(base + '/api/health')
    if args.require_gpu and after['compute'].get('calls', 0) <= 0:
        raise RuntimeError('No CUDA kernel operations recorded during live inference')
    print('PASS Unified real UI + Django + LLM + RAG', after.get('compute'))


if __name__ == '__main__':
    main()
