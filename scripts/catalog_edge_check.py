"""Small public edge regression probe: HEAD for artwork, one compressed catalog."""
import gzip
import json
from urllib.error import HTTPError
from urllib.request import Request, HTTPRedirectHandler, build_opener

BASE = 'https://aya.lazying.art'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


OPENER = build_opener(NoRedirect())


def probe(path, status=200, headers=None, method='HEAD'):
    request = Request(BASE + path, headers=headers or {}, method=method)
    try:
        response = OPENER.open(request, timeout=25)
    except HTTPError as error:
        response = error
    with response:
        assert response.status == status, (path, response.status, status)
        return dict(response.headers), response.read() if method == 'GET' else b''


def main():
    headers, data = probe('/catalog.json', headers={'Accept-Encoding': 'gzip'}, method='GET')
    decoded = gzip.decompress(data) if headers.get('Content-Encoding') == 'gzip' else data
    catalog = json.loads(decoded)
    sticker = catalog['packs'][0]['stickers']['en'][0]
    path = sticker['gif']
    if path.startswith(BASE):
        path = path[len(BASE):]
    assert path.startswith('/media/')
    probe('/')
    for old in ['/westicker', '/westicker/', '/westicker/index.html?legacy=1']:
        redirect, _ = probe(old, 308)
        assert redirect['Location'] == 'https://westicker.lazying.art/'
    worker, body = probe('/westicker/sw.js', method='GET')
    assert 'javascript' in worker.get('Content-Type', '')
    assert 'no-store' in worker.get('Cache-Control', '')
    assert b'registration.unregister()' in body
    direct, _ = probe(path)
    assert 'max-age=86400' in direct.get('Cache-Control', '')
    probe(path, headers={'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Dest': 'image'})
    cross = {'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Dest': 'image'}
    probe(path, 403, cross)
    probe(path, headers={**cross, 'Referer': 'http://127.0.0.1:18642/'})
    probe('/westicker/manifest.webmanifest', 405, method='POST')
    probe('/.env', 404)
    print(json.dumps({'checks': 12, 'legacy_entry_retired': True, 'catalog_transfer_bytes': len(data),
                      'catalog_decoded_bytes': len(decoded), 'direct_downloads': True,
                      'external_hotlink_blocked': True, 'loopback_preview': True}))


if __name__ == '__main__':
    main()
