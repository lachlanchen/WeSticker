"""Availability is a preflight, not a charge or permission to replay a render."""

import pytest

from server.worker import work_once
from test_app import setup, call, draft, signup
from test_studio import upgrade


def prepared(setup):
    app, _ = setup
    cfg = app.config["WESTICKER"]
    client = app.test_client()
    signup(client)
    pack, _ = draft(client)
    result = call(client, f"/api/packs/{pack}/generate", {
        "kind": "photo", "attempt": "prepare-animation-photo", "consent": True,
    })
    assert result.status_code == 202
    assert work_once(cfg)
    row = client.get("/api/workspace").json["packs"][0]["items"][0]
    assert call(client, f"/api/packs/{pack}", {
        "items": [row | {"approved": True}],
    }, method="PATCH").status_code == 200
    upgrade(client, cfg)
    cfg.update(animation_enabled=True, local_video_url="http://127.0.0.1:8190",
               moderation_api_key="fixture")
    return app, cfg, client, pack, row["id"]


@pytest.mark.parametrize("state", ["offline", "busy", "blocked_resources", "error"])
def test_unavailable_animation_does_not_reserve_credits(setup, monkeypatch, state):
    app, _, client, pack, item = prepared(setup)
    unavailable = {"state": state, "can_submit": False, "message": "Renderer needs attention."}
    monkeypatch.setattr("server.studio.animation_status", lambda cfg: unavailable)
    monkeypatch.setattr("server.app.animation_status", lambda cfg: unavailable)
    body = {"kind": "animate", "items": [item]}
    quote = call(client, f"/api/packs/{pack}/quote", body)
    assert quote.status_code == 200
    assert quote.json["can_generate"] is False
    assert quote.json["availability"] == unavailable
    assert quote.json["reason"] == unavailable["message"]
    response = call(client, f"/api/packs/{pack}/generate", body | {
        "attempt": "unavailable-animation-request", "consent": True,
    })
    assert response.status_code == 503
    assert client.get("/api/bootstrap").json["user"]["credits"] == 100
    assert len(client.get("/api/workspace").json["jobs"]) == 1


def test_ready_quote_can_become_busy_before_confirmation(setup, monkeypatch):
    _, _, client, pack, item = prepared(setup)
    monkeypatch.setattr("server.studio.animation_status", lambda cfg: {
        "state": "available", "can_submit": True,
    })
    monkeypatch.setattr("server.app.animation_status", lambda cfg: {
        "state": "busy", "can_submit": False, "message": "Another render is active.",
    })
    body = {"kind": "animate", "items": [item]}
    assert call(client, f"/api/packs/{pack}/quote", body).json["can_generate"] is True
    result = call(client, f"/api/packs/{pack}/generate", body | {
        "attempt": "animation-became-busy", "consent": True,
    })
    assert result.status_code == 503
    assert client.get("/api/bootstrap").json["user"]["credits"] == 100


def test_existing_attempt_survives_closed_provider_without_new_probe(setup, monkeypatch):
    _, cfg, client, pack, item = prepared(setup)
    monkeypatch.setattr("server.app.animation_status", lambda cfg: {
        "state": "available", "can_submit": True,
    })
    body = {"kind": "animate", "items": [item],
            "attempt": "one-animation-only", "consent": True}
    first = call(client, f"/api/packs/{pack}/generate", body)
    assert first.status_code == 202
    assert client.get("/api/bootstrap").json["user"]["credits"] == 97
    cfg["animation_enabled"] = False

    def unexpected_probe(cfg):
        pytest.fail("Recovery must not start or probe a new renderer")

    monkeypatch.setattr("server.app.animation_status", unexpected_probe)
    replay = call(client, f"/api/packs/{pack}/generate", body)
    assert replay.status_code == 200 and replay.json == first.json
    assert client.get("/api/bootstrap").json["user"]["credits"] == 97
    assert len(client.get("/api/workspace").json["jobs"]) == 2
    changed = call(client, f"/api/packs/{pack}/generate", body | {"items": []})
    assert changed.status_code == 409
    other_kind = call(client, f"/api/packs/{pack}/generate", body | {"kind": "photo"})
    assert other_kind.status_code == 409
