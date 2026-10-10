"""Small public edge regression probe: HEAD for artwork, one compressed catalog."""
import gzip
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = 'https://aya.lazying.art'


def probe(path, status=200, headers=None, method='HEAD'):
    request = Request(BASE + path, headers=headers or {}, method=method)
    try:
        response = urlopen(request, timeout=25)
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
    probe('/westicker/')
    direct, _ = probe(path)
    assert 'max-age=86400' in direct.get('Cache-Control', '')
    probe(path, headers={'Sec-Fetch-Site': 'same-site', 'Sec-Fetch-Dest': 'image'})
    cross = {'Sec-Fetch-Site': 'cross-site', 'Sec-Fetch-Dest': 'image'}
    probe(path, 403, cross)
    probe(path, headers={**cross, 'Referer': 'http://127.0.0.1:18642/'})
    probe('/westicker/manifest.webmanifest', 405, method='POST')
    probe('/.env', 404)
    print(json.dumps({'checks': 9, 'catalog_transfer_bytes': len(data),
                      'catalog_decoded_bytes': len(decoded), 'direct_downloads': True,
                      'external_hotlink_blocked': True, 'loopback_preview': True}))


if __name__ == '__main__':
    main()
