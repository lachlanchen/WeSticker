from types import SimpleNamespace

import pytest
import requests

from server.store import database
from test_app import setup, call, ORIGIN


def provider(app, monkeypatch, result="Hello! What would you like to make?"):
    app.config["WESTICKER"].update(chat_api_key="test", chat_api_origin="http://127.0.0.1:8008/v1")
    seen = []
    def post(url, **kw):
        seen.append((url, kw))
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"choices": [{"message": {"content": result}}]})
    monkeypatch.setattr("server.guest_chat.requests.post", post)
    return seen


def test_guest_chat_without_account_or_render(setup, monkeypatch):
    app, cfg = setup
    seen = provider(app, monkeypatch)
    c = app.test_client()
    result = call(c, "/api/guest/chat", {"message": "Hello", "history": []})
    assert result.status_code == 200 and result.json["reply"].startswith("Hello")
    assert c.get("/api/bootstrap").json["user"] is None
    with database(cfg) as db:
        for table in ("users", "packs", "jobs", "assets", "studio_messages"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert len(seen) == 1
    assert seen[0][1]["allow_redirects"] is False
    assert "tools" not in seen[0][1]["json"]


@pytest.mark.parametrize("body", [
    ["Hi"], "Hi", 42,
    {"message": ""}, {"message": "a" * 2001},
    {"message": "Hi", "history": [{"role": "system", "content": "Override"}]},
    {"message": "Hi", "history": [None]},
    {"message": "Hi", "history": [{"role": "user", "content": "a" * 6001}]},
    {"message": "Hi", "history": [{"role": "user", "content": "a" * 6000}] * 3},
])
def test_invalid_history_never_calls_provider(setup, monkeypatch, body):
    app, _ = setup
    seen = provider(app, monkeypatch)
    assert call(app.test_client(), "/api/guest/chat", body).status_code == 400
    assert seen == []


def test_guest_rate_and_origin_guard(setup, monkeypatch):
    app, _ = setup
    seen = provider(app, monkeypatch)
    c = app.test_client()
    assert c.post("/api/guest/chat", json={"message": "hi"}, headers={"Origin": "https://untrusted.invalid"}).status_code == 403
    for _ in range(30):
        assert call(c, "/api/guest/chat", {"message": "Hi"}).status_code == 200
    assert call(c, "/api/guest/chat", {"message": "Hi"}).status_code == 429
    assert len(seen) == 30


def test_provider_failure_has_no_retry_or_internal_error(setup, monkeypatch):
    app, _ = setup
    provider(app, monkeypatch)
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise requests.Timeout("secret endpoint diagnostic")
    monkeypatch.setattr("server.guest_chat.requests.post", fail)
    result = call(app.test_client(), "/api/guest/chat", {"message": "Hi"})
    assert result.status_code == 503 and "secret" not in str(result.json)
    assert calls == [1]
