"""Two explicit live text checks in disposable accounts; never generate media."""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.app import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:18646')
    parser.add_argument('--token-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--live', action='store_true', help='Authorize exactly two text inferences')
    args = parser.parse_args()
    if not args.live:
        raise SystemExit('Live text verification requires --live')
    if args.output.exists():
        raise SystemExit('Verification receipt already exists; inspect it before another run')
    os.environ.pop('WESTICKER_CONFIG', None)
    evidence = []
    with tempfile.TemporaryDirectory(prefix='westicker-agent-check-') as state:
        app = create_app({'state': state, 'origin': 'http://localhost:18642', 'local_accounts': True,
            'chat_provider': 'aginti', 'chat_agent_qualified': True,
            'chat_agent_url': args.url, 'chat_agent_token_file': str(args.token_file.resolve())})
        for index, text in enumerate([
            'Hello! I want to brainstorm a cheerful sticker. Can you help me? Do not make a table yet.',
            'Please propose exactly one English greeting sticker with the caption Hello and a natural waving action.',
        ]):
            client = app.test_client()
            def post(path, body):
                csrf = client.get('/api/bootstrap').json.get('csrf') or ''
                return client.post(path, json=body, headers={'Origin': 'http://localhost:18642', 'X-CSRF-Token': csrf})
            assert post('/api/auth/register', {'name': 'Agent QA', 'email': f'agent-{index}@example.test',
                'password': 'Disposable-Local-Check-123', 'adult': True, 'terms': True}).status_code == 200
            pack = post('/api/packs', {'title': 'Synthetic greeting check', 'language': 'en'}).json['id']
            payload = {'text': text, 'attempt': f'agent-live-qualification-{index}'}
            start = time.monotonic()
            response = post(f'/api/packs/{pack}/chat', payload)
            assert response.status_code == 200, response.json
            result = response.json['result']
            assert result['engine'] == 'aginti-deepseek' and result['reply'].strip()
            assert (result['items'] is None) if index == 0 else (len(result['items']) == 1 and result['items'][0]['label'].rstrip('!.,') == 'Hello')
            assert post(f'/api/packs/{pack}/chat', payload).json == response.json
            assert not client.get('/api/workspace').json['jobs']
            evidence.append({'case': 'conversation' if index == 0 else 'table', 'elapsed_seconds': round(time.monotonic() - start, 2),
                'engine': result['engine'], 'model': result['model'], 'reply': result['reply'], 'items': result['items'],
                'replay_identical': True, 'media_jobs': 0})
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))


if __name__ == '__main__':
    main()
