"""Approve and export an inspected synthetic AgInTi canary; never call a provider."""
import argparse
import io
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.app import create_app
from server.store import database


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', type=Path, required=True)
    p.add_argument('--approve-inspected-image', action='store_true', required=True)
    args = p.parse_args()
    os.umask(0o077)
    os.environ.pop('WESTICKER_CONFIG', None)
    os.environ.pop('WESTICKER_LAZYINGART_CONFIG', None)
    state = args.state.resolve()
    receipt = json.loads((state / 'qualification.json').read_text())
    assert receipt['production_enabled'] is False and receipt['state'] == 'review'
    assert not (state / 'reviewed-export.zip').exists(), 'Inspect the previous export instead'
    app = create_app({'state': str(state), 'origin': 'http://localhost:18642', 'local_accounts': True})
    with database(app.config['WESTICKER']) as db:
        users = db.execute('SELECT id,email FROM users').fetchall()
        assert len(users) == 1 and users[0]['email'] == 'aginti-canary@fixture.invalid'
        user = users[0]['id']
    with app.test_request_context():
        auth = app.extensions['westicker']['login_user'](user, ttl=60, native=True).json
    client = app.test_client()
    headers = {'Authorization': 'Bearer ' + auth['token'], 'X-CSRF-Token': auth['csrf'],
               'Origin': 'http://localhost:18642'}
    try:
        workspace = client.get('/api/workspace', headers=headers).json
        pack = next(row for row in workspace['packs'] if row['id'] == receipt['pack'])
        rows = [dict(row, approved=True) for row in pack['items']]
        result = client.patch(f'/api/packs/{pack["id"]}', json={'items': rows, 'revision': pack['revision']}, headers=headers)
        assert result.status_code == 200, result.json
        result = client.get(f'/api/packs/{pack["id"]}/export', headers=headers)
        assert result.status_code == 200, result.status_code
        with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            assert any(name.endswith('.png') for name in names)
        (state / 'reviewed-export.zip').write_bytes(result.data)
        evidence = {'approved': True, 'export_bytes': len(result.data), 'files': names,
                    'new_provider_requests': 0}
        (state / 'export-review.json').write_text(json.dumps(evidence, indent=2))
        print(json.dumps(evidence))
    finally:
        client.post('/api/auth/logout', headers=headers)


if __name__ == '__main__':
    main()
