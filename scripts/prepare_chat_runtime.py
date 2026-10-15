"""Prepare private AgInTi chat settings; does not restart or change live services."""

import argparse
import json
import os
from pathlib import Path
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.generation import private_key


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--token-file', type=Path, required=True)
    p.add_argument('--agent-url', default='http://127.0.0.1:18646')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    private_key(a.token_file)
    session = requests.Session()
    session.trust_env = False
    response = session.get(a.agent_url.rstrip('/') + '/health', timeout=5, allow_redirects=False)
    response.raise_for_status()
    status = response.json()
    if (status.get('app') != 'westicker-agent' or status.get('engine') != 'aginti-deepseek'
            or status.get('tools') != [] or status.get('codexFallback') is not False):
        raise SystemExit('Agent readiness differs from the qualified contract')
    cfg = json.loads(a.config.read_text())
    cfg.update(chat_provider='aginti', chat_agent_url=a.agent_url.rstrip('/'),
        chat_agent_token_file=str(a.token_file.resolve()), chat_agent_qualified=True)
    with os.fdopen(os.open(a.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as output:
        json.dump(cfg, output, indent=2)
        output.write('\n')
    print(json.dumps({'prepared': True, 'engine': status['engine'], 'model': status['model']}))


if __name__ == '__main__':
    main()
