"""Read the public AYA artwork catalog with bounded refresh and offline fallback."""
import copy
import hashlib
import json
import threading
import time
import tempfile
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

ORIGIN = "https://aya.lazying.art"
SOURCE = ORIGIN + "/catalog.json"
MAX_BYTES = 2_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def normalize_catalog(value):
    """Accept artwork only; no upstream account, entitlement or billing state."""
    packs = value.get("packs") if isinstance(value, dict) else None
    if not isinstance(packs, list) or not 1 <= len(packs) <= 200:
        raise ValueError("Invalid public catalog")

    def asset(value):
        if not isinstance(value, str):
            raise ValueError("Invalid asset")
        parsed = urlsplit(value)
        if (parsed.scheme or parsed.netloc) and (parsed.scheme != "https" or parsed.netloc != "aya.lazying.art"):
            raise ValueError("Unapproved artwork host")
        if (not parsed.path.startswith("/media/") or ".." in parsed.path or "%" in parsed.path
                or parsed.query or parsed.fragment or "\\" in parsed.path):
            raise ValueError("Unapproved artwork path")
        return ORIGIN + parsed.path

    output = []
    ids = set()
    for p in packs:
        if not isinstance(p, dict):
            raise ValueError("Invalid pack")
        if not isinstance(p.get("id"), str) or p["id"] in ids:
            raise ValueError("Duplicate pack")
        ids.add(p["id"])
        if type(p.get("count")) is not int or not 1 <= p["count"] <= 64:
            raise ValueError("Invalid sticker count")
        pack = {k: p[k] for k in ("id", "name", "english", "description", "count", "tag")}
        if any(not isinstance(pack[k], str) or len(pack[k]) > 2000 for k in ("id", "name", "english", "description", "tag")):
            raise ValueError("Invalid public text")
        pack.update(banner=asset(p["banner"]), cover=asset(p["cover"]), stickers={})
        reference_ids = None
        for language in ("zh", "en", "ja"):
            rows = p["stickers"][language]
            if not isinstance(rows, list) or any(not isinstance(s, dict) or not isinstance(s.get("id"), str) for s in rows):
                raise ValueError("Invalid stickers")
            if len(rows) != p["count"] or len({s["id"] for s in rows}) != len(rows):
                raise ValueError("Incomplete language edition")
            language_ids = [s["id"] for s in rows]
            if reference_ids is not None and language_ids != reference_ids:
                raise ValueError("Language editions identify different stickers")
            reference_ids = language_ids
            pack["stickers"][language] = []
            for s in rows:
                if not isinstance(s["label"], str) or not 1 <= len(s["label"]) <= 100:
                    raise ValueError("Invalid sticker label")
                row = {"id": s["id"], "label": s["label"], "gif": asset(s["gif"]), "poster": asset(s["poster"])}
                if s.get("motion"):
                    row["motion"] = asset(s["motion"])
                pack["stickers"][language].append(row)
        output.append(pack)
    revision = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return {"packs": output, "default_pack": value.get("default_pack") if value.get("default_pack") in ids else output[0]["id"], "attribution": {"owner": "LazyingArt", "source": ORIGIN,
            "use": "personal-use previews; independent WeSticker subscriptions"}, "source_revision": revision}


class PublicCatalog:
    def __init__(self, fallback, cache, enabled=False, fetch=None, clock=time.monotonic):
        self.fallback = fallback
        self.cache = cache
        self.enabled = enabled
        self.fetch = fetch or build_opener(NoRedirect()).open
        self.clock = clock
        self.lock = threading.Lock()
        self.value = None
        self.etag = None
        self.next_check = 0
        if cache.is_file():
            try:
                raw = json.loads(cache.read_bytes()[:MAX_BYTES + 1])
                self.value = normalize_catalog(raw["catalog"])
                self.etag = raw.get("etag")
            except (ValueError, KeyError, TypeError, OSError):
                pass

    def get(self):
        if self.enabled and self.clock() >= self.next_check and self.lock.acquire(blocking=False):
            try:
                self.next_check = self.clock() + 300
                headers = {"Accept": "application/json", "User-Agent": "WeSticker-Public-Catalog/1"}
                if self.etag:
                    headers["If-None-Match"] = self.etag
                try:
                    with self.fetch(Request(SOURCE, headers=headers), timeout=4) as response:
                        if response.status != 200 or response.geturl() != SOURCE:
                            raise ValueError("Unexpected catalog response")
                        body = response.read(MAX_BYTES + 1)
                        if len(body) > MAX_BYTES:
                            raise ValueError("Catalog too large")
                        raw = json.loads(body)
                        value = normalize_catalog(raw)
                        etag = response.headers.get("ETag")
                    self.cache.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(mode="w", dir=self.cache.parent, delete=False) as handle:
                        handle.write(json.dumps({"catalog": raw, "etag": etag}, ensure_ascii=False))
                        temporary = type(self.cache)(handle.name)
                    try:
                        temporary.replace(self.cache)
                    finally:
                        temporary.unlink(missing_ok=True)
                    self.value, self.etag = value, etag
                except HTTPError as error:
                    if error.code != 304:
                        self.next_check = self.clock() + 60
                except (OSError, ValueError, KeyError, TypeError):
                    self.next_check = self.clock() + 60
            finally:
                self.lock.release()
        return copy.deepcopy(self.value) if self.value else json.loads(self.fallback.read_text())
