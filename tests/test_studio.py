import base64
import hashlib
import io
import json
import time
from pathlib import Path

import pytest
from PIL import Image
from server.store import database
from server.worker import work_once
from test_app import setup, call, signup, draft, ORIGIN


def upgrade(client, cfg, plan="creator", expires=None):
    user = client.get("/api/bootstrap").json["user"]["id"]
    with database(cfg) as db:
        db.execute(
            "UPDATE users SET plan=?,expires=?,credits=100 WHERE id=?",
            (plan, expires or time.time() + 86400, user),
        )


def test_free_single_and_tier_limits(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    p = c.get("/api/workspace").json["packs"][0]
    assert len(p["items"]) == 1
    assert c.get("/api/bootstrap").json["limits"]["pack_size"] == 1
    assert c.get("/api/bootstrap").json["limits"]["packs"] == 2
    assert (
        call(
            c,
            f"/api/packs/{id}",
            {"items": p["items"] + [{"label": "Extra"}]},
            method="PATCH",
        ).status_code
        == 400
    )
    for plan, count in [("pocket", 8), ("creator", 16), ("studio", 24)]:
        upgrade(c, cfg, plan)
        assert c.get("/api/bootstrap").json["limits"]["pack_size"] == count
        result = call(
            c,
            f"/api/packs/{id}",
            {"items": [{"label": str(i)} for i in range(count)]},
            method="PATCH",
        )
        assert result.status_code == 200
        assert (
            call(
                c,
                f"/api/packs/{id}",
                {"items": [{"label": str(i)} for i in range(count + 1)]},
                method="PATCH",
            ).status_code
            == 400
        )


def test_pack_count_enforced_and_expiry_preserves_library(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    upgrade(c, cfg, "pocket")
    id, _ = draft(c)
    p = c.get("/api/workspace").json["packs"][0]
    body = {"character": p["character_id"], "title": "Another", "language": "en"}
    assert call(c, "/api/packs", body).status_code == 201
    assert call(c, "/api/packs", body).status_code == 403
    upgrade(c, cfg, "pocket", time.time() - 1)
    w = c.get("/api/workspace").json
    assert len(w["packs"]) == 2 and w["limits"]["pack_size"] == 1
    assert len(next(p for p in w["packs"] if p["id"] == id)["items"]) == 8
    assert (
        call(
            c,
            f"/api/packs/{id}/generate",
            {"kind": "photo", "consent": True, "attempt": "expired-plan-test-123"},
        ).status_code
        == 403
    )


def test_revision_and_asset_protection(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    id, ref = draft(c)
    p = c.get("/api/workspace").json["packs"][0]
    body = {"items": p["items"], "revision": p["revision"]}
    assert call(c, f"/api/packs/{id}", body, method="PATCH").status_code == 200
    assert call(c, f"/api/packs/{id}", body, method="PATCH").status_code == 409
    body["items"][0]["asset"] = ref
    assert (
        call(
            c, f"/api/packs/{id}", {"items": body["items"]}, method="PATCH"
        ).status_code
        == 400
    )


def test_chat_proposal_is_explicit_and_idempotent(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    before = c.get("/api/workspace").json["packs"][0]
    body = {"text": "change 1 to Hello there", "attempt": "chat-same-attempt-123"}
    proposal = call(c, f"/api/packs/{id}/chat", body).json
    assert proposal["result"]["items"][0]["label"] == "Hello there"
    assert proposal["result"]["source"] == "offline"
    assert call(c, f"/api/packs/{id}/chat", body).json["id"] == proposal["id"]
    assert c.get("/api/workspace").json["packs"][0]["items"] == before["items"]
    assert len(c.get(f"/api/packs/{id}/conversation").json["messages"]) == 1
    assert (
        call(
            c,
            f"/api/packs/{id}",
            {
                "items": proposal["result"]["items"],
                "revision": proposal["result"]["revision"],
            },
            method="PATCH",
        ).status_code
        == 200
    )
    assert c.get("/api/workspace").json["jobs"] == []


def test_planner_never_applies_or_charges(setup, monkeypatch):
    app, cfg = setup
    app.config["WESTICKER"]["chat_api_key"] = "test-only"
    c = app.test_client()
    signup(c)
    id, _ = draft(c)

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "reply": "A friendly wave",
                                    "items": [
                                        {
                                            "label": "Hi!",
                                            "action": "Lift one hand and wave twice, then relax.",
                                            "approved": True,
                                            "asset": "bad",
                                        }
                                    ],
                                }
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr("server.studio.requests.post", lambda *a, **k: Response())
    result = call(
        c,
        f"/api/packs/{id}/chat",
        {"text": "Make this friendly", "attempt": "real-provider-contract"},
    ).json["result"]
    assert (
        result["source"] == "assistant"
        and not result["items"][0]["approved"]
        and not result["items"][0]["asset"]
    )
    assert c.get("/api/workspace").json["jobs"] == []


def test_free_image_reservation_and_definite_failure_refund(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    app.config["WESTICKER"]["image_api_key"] = "test-only"
    p = c.get("/api/workspace").json["packs"][0]
    body = {
        "kind": "ai",
        "items": [p["items"][0]["id"]],
        "attempt": "free-trial-image-123",
        "consent": True,
        "revision": p["revision"],
    }
    assert call(c, f"/api/packs/{id}/quote", body).json["can_generate"]
    result = call(c, f"/api/packs/{id}/generate", body)
    assert result.status_code == 202
    assert c.get("/api/bootstrap").json["limits"]["trial_images"] == 0
    assert call(c, f"/api/packs/{id}/generate", body).json["id"] == result.json["id"]
    # Known failure before submission refunds the reserved trial, not paid credits.
    worker_cfg = app.config["WESTICKER"] | {"image_api_key": None}
    work_once(worker_cfg)
    assert c.get("/api/bootstrap").json["limits"]["trial_images"] == 1
    assert c.get("/api/bootstrap").json["user"]["credits"] == 0


def test_versions_and_action_approval_invalidation(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    call(
        c,
        f"/api/packs/{id}/generate",
        {"kind": "photo", "attempt": "photo-for-history-123", "consent": True},
    )
    work_once(app.config["WESTICKER"])
    rows = c.get("/api/workspace").json["packs"][0]["items"]
    rows[0]["approved"] = True
    assert (
        call(c, f"/api/packs/{id}", {"items": rows}, method="PATCH").status_code == 200
    )
    rows[0]["action"] = "Wave a hand"
    call(c, f"/api/packs/{id}", {"items": rows}, method="PATCH")
    assert not c.get("/api/workspace").json["packs"][0]["items"][0]["approved"]
    assert c.get(f"/api/packs/{id}/versions").json["versions"][0]["items"][0]["asset"]
    other = app.test_client()
    signup(other, "other@example.com")
    assert other.get(f"/api/packs/{id}/versions").status_code == 404
    assert other.get(f"/api/packs/{id}/conversation").status_code == 404


def test_native_pkce_requires_approval_and_single_exchange(setup):
    app, _ = setup
    browser = app.test_client()
    native = app.test_client()
    signup(browser)
    verifier = "x" * 43
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    link = call(native, "/api/native/link", {"challenge": challenge}).json["id"]
    assert (
        call(
            native, f"/api/native/link/{link}/exchange", {"verifier": verifier}
        ).status_code
        == 202
    )
    assert (
        call(
            browser, f"/api/native/link/{link}/approve", {"approved": True}
        ).status_code
        == 200
    )
    assert (
        call(
            native, f"/api/native/link/{link}/exchange", {"verifier": "z" * 43}
        ).status_code
        == 410
    )
    response = call(native, f"/api/native/link/{link}/exchange", {"verifier": verifier})
    assert response.status_code == 200 and response.json["token"]
    assert (
        call(
            native, f"/api/native/link/{link}/exchange", {"verifier": verifier}
        ).status_code
        == 410
    )
    auth = {"Authorization": "Bearer " + response.json["token"]}
    assert app.test_client().get("/api/workspace", headers=auth).status_code == 200
    assert (
        app.test_client().post("/api/auth/logout", headers=auth, json={}).status_code
        == 403
    )
    headers = auth | {"Origin": ORIGIN, "X-CSRF-Token": response.json["csrf"]}
    assert (
        app.test_client().post("/api/auth/logout", headers=headers, json={}).status_code
        == 200
    )
    assert app.test_client().get("/api/workspace", headers=auth).status_code == 401
    assert browser.get("/api/workspace").status_code == 200


def test_chat_before_references_and_explicit_character_binding(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    made = call(c, "/api/packs", {"title": "Let's chat", "language": "en"})
    assert made.status_code == 201
    id = made.json["id"]
    p = c.get("/api/workspace").json["packs"][0]
    assert p["character_id"] is None
    proposal = call(c, f"/api/packs/{id}/chat", {"text": "change 1 to Hi", "attempt": "chat-before-reference-1"})
    assert proposal.status_code == 200
    quote = call(c, f"/api/packs/{id}/quote", {"kind": "photo", "items": [p["items"][0]["id"]]})
    assert quote.json["can_generate"] is False
    assert call(c, f"/api/packs/{id}/generate", {"kind": "photo", "consent": True, "attempt": "reference-missing-123"}).status_code == 409
    other, _ = draft(c)
    character = next(x for x in c.get("/api/workspace").json["packs"] if x["id"] == other)["character_id"]
    assert call(c, f"/api/packs/{id}/character", {"character": character, "revision": p["revision"]}).status_code == 200
    assert call(c, f"/api/packs/{id}/character", {"character": character, "revision": p["revision"]}).status_code == 409


def test_assistant_can_converse_without_modifying_table(setup, monkeypatch):
    app, _ = setup
    app.config["WESTICKER"]["chat_api_key"] = "test-only"
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    before = c.get("/api/workspace").json["packs"][0]
    class Response:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"reply": "Who is your sticker for?", "items": None})}}]}
    monkeypatch.setattr("server.studio.requests.post", lambda *a, **k: Response())
    result = call(c, f"/api/packs/{id}/chat", {"text": "Can we brainstorm?", "attempt": "conversation-only-123"})
    assert result.status_code == 200 and result.json["result"]["items"] is None
    after = c.get("/api/workspace").json
    assert after["packs"][0]["items"] == before["items"] and not after["jobs"]


def test_private_thumbnail_keeps_original_and_ownership(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    image = io.BytesIO()
    Image.new("RGB", (900, 600), "#4499dd").save(image, "PNG")
    image.seek(0)
    response = c.post(
        "/api/assets",
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": c.get("/api/bootstrap").json["csrf"],
        },
        data={"rights": "yes", "file": (image, "reference.png")},
    )
    assert response.status_code == 201
    path = "/api/assets/" + response.json["id"]
    original = c.get(path)
    preview = c.get(path + "?preview=1")
    assert Image.open(io.BytesIO(original.data)).size == (900, 600)
    assert Image.open(io.BytesIO(preview.data)).size == (320, 213)
    assert "no-store" in preview.headers["Cache-Control"]
    other = app.test_client()
    signup(other, "outsider@example.com")
    assert other.get(path + "?preview=1").status_code == 404
    assert c.get(path).data == original.data


def test_animation_preview_preserves_all_frames_and_is_private(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    owner = c.get("/api/bootstrap").json["user"]["id"]
    path = Path(cfg["state"]) / "assets" / "motion.gif"
    frames = [Image.new("RGB", (64, 64), color) for color in ("red", "blue")]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=120, loop=0)
    original = path.read_bytes()
    with database(cfg) as db:
        db.execute("INSERT INTO assets VALUES(?,?,?,?,?,?,?)", (
            "motion", owner, "assets/motion.gif", hashlib.sha256(original).hexdigest(),
            "animation", time.time(), None))
    response = c.get("/api/assets/motion?preview=1")
    assert response.status_code == 200
    assert response.mimetype == "image/gif"
    assert response.data == original
    image = Image.open(io.BytesIO(response.data))
    assert image.n_frames == 2
    assert image.info["loop"] == 0
    assert "no-store" in response.headers["Cache-Control"]
    other = app.test_client()
    signup(other, "animation-outsider@example.com")
    assert other.get("/api/assets/motion?preview=1").status_code == 404
    assert app.test_client().get("/api/assets/motion?preview=1").status_code == 401


def test_new_external_account_can_accept_terms_without_workspace_access(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    owner = c.get("/api/bootstrap").json["user"]["id"]
    with database(cfg) as db:
        db.execute("UPDATE users SET consented=0 WHERE id=?", (owner,))
    assert c.get("/api/bootstrap").json["user"]["consented"] == 0
    assert c.get("/api/workspace").status_code == 403
    assert call(c, "/api/account/consent", {"adult": False, "terms": True}).status_code == 400
    assert call(c, "/api/account/consent", {"adult": True, "terms": True}).status_code == 200
    assert c.get("/api/workspace").status_code == 200
