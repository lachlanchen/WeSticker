import io
import json
from urllib.error import HTTPError, URLError

import pytest

from server.public_catalog import PublicCatalog, SOURCE, normalize_catalog


def catalog():
    row = {"id":"hello", "label":"Hello", "gif":"/media/test/hello.gif", "poster":"/media/test/hello.png", "motion":"/media/test/hello.webp"}
    return {"packs":[{"id":"test", "name":"Test", "english":"Test", "description":"Public artwork",
        "tag":"daily", "count":1, "banner":"/media/test/banner.jpg", "cover":"/media/test/cover.png",
        "stickers":{lang:[dict(row)] for lang in ("en","ja","zh")}}]}


class Response(io.BytesIO):
    status = 200
    headers = {"ETag":'"v1"'}
    def geturl(self):
        return SOURCE


def test_normalize_allowlist():
    source = catalog()
    source['private'] = 'must not propagate'
    result = normalize_catalog(source)
    assert 'private' not in result
    assert result['packs'][0]['stickers']['ja'][0]['motion'] == 'https://aya.lazying.art/media/test/hello.webp'
    assert result['default_pack'] == 'test'
    source['default_pack'] = 'private-draft'
    assert normalize_catalog(source)['default_pack'] == 'test'


@pytest.mark.parametrize('url',['https://evil.example/a.gif','//evil.example/a.gif','/media/../secret','/media/%2e%2e/x','/media/x?token=a','file:///media/x','/media/x#token','/media/\\x'])
def test_reject_external_or_ambiguous_assets(url):
    value = catalog()
    value['packs'][0]['cover'] = url
    with pytest.raises(ValueError): normalize_catalog(value)


def test_reject_missing_language_and_duplicate():
    value = catalog()
    value['packs'].append(value['packs'][0])
    with pytest.raises(ValueError): normalize_catalog(value)
    value = catalog()
    value['packs'][0]['stickers']['ja'][0]['id'] = 'different-animation'
    with pytest.raises(ValueError): normalize_catalog(value)
    value = catalog()
    value['packs'][0]['stickers']['ja'] = []
    with pytest.raises(ValueError): normalize_catalog(value)


def test_cache_conditional_refresh_and_offline(tmp_path):
    fallback = tmp_path/'fallback.json'
    fallback.write_text(json.dumps({'packs':[]}))
    now = [0]
    calls = []
    def fetch(req, **kw):
        calls.append(req)
        if len(calls)==1:
            return Response(json.dumps(catalog()).encode())
        raise HTTPError(SOURCE,304,'Not Modified',{},None)
    cache = PublicCatalog(fallback,tmp_path/'cache.json',True,fetch,lambda:now[0])
    first = cache.get()
    assert len(first['packs'])==1
    assert cache.get()==first and len(calls)==1
    now[0]=301
    assert cache.get()==first and len(calls)==2
    assert calls[-1].get_header('If-none-match')=='"v1"'
    first['packs'].clear()
    assert len(cache.get()['packs'])==1
    def fail(*a,**kw): raise URLError('offline')
    restart = PublicCatalog(fallback,tmp_path/'cache.json',True,fail)
    assert len(restart.get()['packs'])==1


def test_failed_refresh_keeps_last_good(tmp_path):
    fallback=tmp_path/'fallback.json';fallback.write_text(json.dumps(catalog()))
    def fetch(*a,**kw): return Response(b'x'*2_000_001)
    cache=PublicCatalog(fallback,tmp_path/'cache.json',True,fetch)
    assert cache.get()==catalog()
    assert not (tmp_path/'cache.json').exists()


def test_sync_disabled_has_no_network(tmp_path):
    fallback=tmp_path/'fallback.json';fallback.write_text(json.dumps(catalog()))
    def fail(*a,**kw): pytest.fail('Unexpected network request')
    assert PublicCatalog(fallback,tmp_path/'cache.json',fetch=fail).get()==catalog()
