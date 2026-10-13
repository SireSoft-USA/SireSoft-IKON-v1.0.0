"""Run real end-to-end model questions and write a report for human review.

API status != conversational quality. This script does not give an automatic
quality PASS to gibberish. Review answer relevance, truthfulness and citations.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


CASES = [
    ('general', 'Hello! How are you today?'),
    ('general', 'What is the difference between a list and a dictionary?'),
    ('general', 'Explain photosynthesis to a twelve-year-old student.'),
    ('general', 'Can you help me plan a study schedule?'),
    ('rag', 'What services does SireSoft provide?'),
    ('rag', 'Who is the CEO of SireSoft?'),
    ('rag', 'Where does SireSoft operate?'),
    ('rag', 'What is SireSoft IKON?'),
]


def read_events(url, data):
    request = Request(
        url, data=json.dumps(data).encode('utf-8'), method='POST',
        headers={'Content-Type': 'application/json'},
    )
    with urlopen(request, timeout=300) as response:
        return [json.loads(line) for line in response.read().decode('utf-8').splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--web-url', default='http://127.0.0.1:5173')
    parser.add_argument('--output', default='model-quality-evaluation.json')
    args = parser.parse_args()
    base = args.web_url.rstrip('/')
    report = {'timestamp': datetime.now(timezone.utc).isoformat(),
              'endpoint': base, 'status': 'requires_human_review', 'examples': []}
    for mode, question in CASES:
        started = time.monotonic()
        item = {'mode': mode, 'question': question}
        try:
            events = read_events(base + '/api/chat/stream', {
                'conversation_id': 'ikon-eval-' + mode,
                'messages': [{'role': 'user', 'content': question}],
                'use_rag': mode == 'rag',
            })
            errors = [e.get('message', 'unknown') for e in events if e.get('type') == 'error']
            item['error'] = '; '.join(errors) if errors else None
            item['answer'] = ''.join(e.get('content', '') for e in events if e.get('type') == 'token')
            item['citations'] = next((e.get('citations', []) for e in events if e.get('type') == 'meta'), [])
            item['completed'] = any(e.get('done') for e in events)
        except Exception as error:
            item['error'] = str(error)
            item['answer'] = ''
            item['citations'] = []
            item['completed'] = False
        item['seconds'] = round(time.monotonic() - started, 2)
        report['examples'].append(item)
        print(f"[{mode.upper()}] {question}")
        print(f"  Answer: {item['answer'][:240]!r}")
        print(f"  Citations: {len(item['citations'])} | error: {item['error']}")
        print()
    destination = Path(args.output)
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Quality report:', destination.resolve())
    print('Review each answer manually. API success alone is not a quality pass.')


if __name__ == '__main__':
    main()
