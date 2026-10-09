import hashlib
import io
import time
from pathlib import Path

import pytest
from PIL import Image

from server.app import create_app
from server.media import sticker_gif
from server.store import database
from server.local_video import animate, OutcomeUncertain
from test_app import ORIGIN, signup, call, draft


@pytest.fixture
def case(tmp_path):
    app = create_app({"state": str(tmp_path), "origin": ORIGIN, "local_accounts": True})
    app.config["TESTING"] = True
    c = app.test_client()
    signup(c)
    return app, app.config["WESTICKER"], c


def test_json_object_and_duplicate_items(case):
    app, cfg, c = case
    id, _ = draft(c)
    assert call(c, "/api/characters", []).status_code == 400
    item = c.get("/api/workspace").get_json()["packs"][0]["items"][0]
    assert (
        call(c, f"/api/packs/{id}", {"items": [item, item]}, method="PATCH").status_code
        == 400
    )
    assert (
        call(
            c,
            f"/api/packs/{id}/generate",
            {
                "kind": "photo",
                "attempt": "bad-items-list-1234",
                "consent": True,
                "items": [{}],
            },
        ).status_code
        == 400
    )


def test_missing_reference_fails_before_reservation(case):
    app, cfg, c = case
    id, ref = draft(c)
    with database(cfg) as db:
        path = db.execute("SELECT path FROM assets WHERE id=?", (ref,)).fetchone()[0]
    (Path(cfg["state"]) / path).unlink()
    assert (
        call(
            c,
            f"/api/packs/{id}/generate",
            {"kind": "photo", "attempt": "expired-reference-123", "consent": True},
        ).status_code
        == 409
    )
    assert c.get("/api/workspace").get_json()["jobs"] == []


def test_creator_consent_required_after_social_login(case):
    app, cfg, c = case
    user = c.get("/api/bootstrap").get_json()["user"]["id"]
    with database(cfg) as db:
        db.execute("UPDATE users SET consented=0 WHERE id=?", (user,))
    assert c.get("/api/workspace").status_code == 403
    assert (
        call(c, "/api/account/consent", {"adult": False, "terms": True}).status_code
        == 400
    )
    assert (
        call(c, "/api/account/consent", {"adult": True, "terms": True}).status_code
        == 200
    )
    assert c.get("/api/workspace").status_code == 200


def test_captioned_gif_keeps_animation_and_original(tmp_path):
    path = tmp_path / "original.gif"
    a = Image.new("RGBA", (240, 240), "red")
    b = Image.new("RGBA", (240, 240), "blue")
    a.save(path, "GIF", save_all=True, append_images=[b], duration=[100, 100], loop=0)
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    data = sticker_gif(path, "Hello", {})
    result = Image.open(io.BytesIO(data))
    assert result.size == (240, 240) and result.n_frames == 2 and len(data) < 500_000
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original


def test_animation_requires_provider_and_reference_approval(case):
    app, cfg, c = case
    id, _ = draft(c)
    assert (
        call(
            c,
            f"/api/packs/{id}/generate",
            {"kind": "animate", "attempt": "animate-test-1234", "consent": True},
        ).status_code
        == 503
    )
    cfg.update(local_video_url="http://127.0.0.1:8190", image_api_key="fixture")
    user = c.get("/api/bootstrap").get_json()["user"]["id"]
    with database(cfg) as db:
        db.execute(
            "UPDATE users SET plan='creator',credits=40,expires=? WHERE id=?",
            (time.time() + 86400, user),
        )
    assert (
        call(
            c,
            f"/api/packs/{id}/generate",
            {"kind": "animate", "attempt": "animate-test-1234", "consent": True},
        ).status_code
        == 409
    )


def test_ambiguous_local_render_never_resubmitted(tmp_path):
    job = {"id": "job"}
    item = {"id": "item"}
    folder = tmp_path / "renders/job/item"
    folder.mkdir(parents=True)
    (folder / "intent.json").write_text("{}")
    with pytest.raises(OutcomeUncertain):
        animate(
            {"state": str(tmp_path), "local_video_url": "http://127.0.0.1:8190"},
            job,
            item,
            tmp_path / "missing.png",
        )


def test_delete_pack_and_generated_exports(case):
    app, cfg, c = case
    id, _ = draft(c)
    folder = Path(cfg["state"]) / "listings" / id
    folder.mkdir(parents=True)
    (folder / "pack.zip").write_bytes(b"private")
    assert call(c, "/api/account/delete", {"confirmation": "DELETE"}).status_code == 200
    assert not folder.exists()


def test_production_security_headers(case):
    app, cfg, c = case
    response = c.get("/api/bootstrap")
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
