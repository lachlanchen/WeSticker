"""Public browsing is allowed; anonymous model access is retired."""

import pytest

from server.store import database
from test_app import setup, call


@pytest.mark.parametrize("body", [{"message": "Hello"}, {"message": "a" * 2001}, ["Hi"], None])
def test_retired_guest_chat_never_calls_model_or_creates_state(setup, monkeypatch, body):
    app, cfg = setup
    def fail(*args, **kwargs):
        pytest.fail("Retired guest route must never contact a model")
    monkeypatch.setattr("requests.post", fail)
    c = app.test_client()
    response = call(c, "/api/guest/chat", body)
    assert response.status_code == (400 if isinstance(body, list) else 410)
    if response.status_code == 410:
        assert "sign in" in response.json["error"].lower()
    assert c.get("/api/bootstrap").json["user"] is None
    assert c.get("/api/catalog").status_code == 200
    assert c.get("/api/workspace").status_code == 401
    with database(cfg) as db:
        for table in ("users", "packs", "jobs", "assets", "studio_messages"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_retired_route_preserves_origin_guard(setup):
    app, _ = setup
    c = app.test_client()
    assert c.post("/api/guest/chat", json={"message": "hi"}, headers={"Origin": "https://untrusted.invalid"}).status_code == 403
