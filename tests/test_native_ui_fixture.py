"""Validate the isolated native-layout fixture, never a live identity service."""
import json
import importlib.util
import plistlib
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from scripts.native_ui_fixture import native_ui_fixture


def test_layout_fixture_auth_expiry_and_availability():
    with native_ui_fixture(0) as state:
        def get(path):
            with urlopen(state["origin"] + path, timeout=2) as response:
                return json.load(response)
        assert get("/api/bootstrap")["user"]["consented"]
        assert get("/api/workspace")["packs"] == []
        get("/__qa/expired")
        assert get("/api/bootstrap")["user"] is None
        assert get("/api/bootstrap")["providers"] == ["lazyingart"]
        get("/__qa/unavailable")
        assert get("/api/bootstrap")["providers"] == []
        get("/__qa/providers")
        providers = get("/api/bootstrap")
        assert providers["user"] is None
        assert providers["providers"] == ["google", "apple", "github", "lazyingart", "unknown", "google"]
        assert not state["unexpected"]


def test_layout_fixture_refuses_every_mutation():
    with native_ui_fixture(0) as state:
        with pytest.raises(HTTPError) as caught:
            urlopen(Request(state["origin"] + "/api/native/link", data=b"{}"), timeout=2)
        assert caught.value.code == 405
        assert state["unexpected"] == ["POST /api/native/link"]


def test_explicit_provider_fixture_only_returns_inert_local_urls():
    with native_ui_fixture(0) as state:
        state["mode"] = "providers"
        for provider in ("google", "apple", "github", "lazyingart"):
            request = Request(state["origin"] + "/api/native/link", data=json.dumps({
                "provider": provider, "app_return": True, "challenge": "A" * 43}).encode())
            with urlopen(request, timeout=2) as response:
                result = json.load(response)
            assert result["url"] == state["origin"] + "/auth/" + provider + "/start?native_link=fixture-link"
            with urlopen(result["url"], timeout=2) as response:
                assert b"Native cancellation fixture" in response.read()
            assert "token" not in result
        assert [probe["provider"] for probe in state["link_probes"]] == ["google", "apple", "github", "lazyingart"]
        with pytest.raises(HTTPError) as caught:
            urlopen(Request(state["origin"] + "/api/native/link/fixture-link/exchange", data=b"{}"), timeout=2)
        assert caught.value.code == 405


def test_stopped_simulator_cleanup_preserves_unrelated_preferences(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("apple_release_qa", scripts / "apple_release_qa.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    paths = []
    for name, origin in (("owned", "http://127.0.0.1:18649"), ("public", "https://westicker.lazying.art")):
        path = tmp_path / name / "Library/Preferences/art.lazying.westicker.plist"
        path.parent.mkdir(parents=True)
        path.write_bytes(plistlib.dumps({"studio-origin": origin, "keep": "draft preference"}))
        paths.append(path)
    unrelated = tmp_path / "owned/Library/Preferences/another.app.plist"
    unrelated.write_bytes(plistlib.dumps({"studio-origin": "http://127.0.0.1:18649"}))
    assert module.clear_fixture_origin(tmp_path) == 1
    assert plistlib.loads(paths[0].read_bytes()) == {"keep": "draft preference"}
    assert plistlib.loads(paths[1].read_bytes())["studio-origin"] == "https://westicker.lazying.art"
    assert plistlib.loads(unrelated.read_bytes())["studio-origin"] == "http://127.0.0.1:18649"
    assert module.clear_fixture_origin(tmp_path) == 0
