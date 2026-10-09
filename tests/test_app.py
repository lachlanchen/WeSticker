import io
import zipfile
from pathlib import Path
import pytest
from PIL import Image
from server.app import create_app
from server.worker import work_once

ORIGIN = "http://localhost:18642"


@pytest.fixture
def setup(tmp_path):
    cfg = {"state": str(tmp_path), "origin": ORIGIN, "local_accounts": True}
    app = create_app(cfg)
    app.config["TESTING"] = True
    return app, cfg


def call(client, path, body=None, method="POST", **kw):
    boot = client.get("/api/bootstrap").get_json()
    headers = {"Origin": ORIGIN, "X-CSRF-Token": boot.get("csrf") or ""}
    return client.open(path, method=method, json=body, headers=headers, **kw)


def signup(client, email="creator@example.com"):
    result = call(
        client,
        "/api/auth/register",
        {
            "email": email,
            "password": "correct horse test 123",
            "name": "Test Creator",
            "adult": True,
            "terms": True,
        },
    )
    assert result.status_code == 200, result.get_json()


def upload(client):
    data = io.BytesIO()
    Image.new("RGB", (96, 96), (240, 80, 110)).save(data, "PNG")
    data.seek(0)
    csrf = client.get("/api/bootstrap").get_json()["csrf"]
    result = client.post(
        "/api/assets",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        data={"rights": "yes", "file": (data, "photo.png")},
    )
    assert result.status_code == 201, result.get_json()
    return result.get_json()["id"]


def draft(client):
    ref = upload(client)
    c = call(
        client,
        "/api/characters",
        {"name": "Pink friend", "style": "figurine", "refs": [ref]},
    ).get_json()["id"]
    assert (
        call(client, f"/api/characters/{c}/lock", {"approved": True}).status_code == 200
    )
    result = call(
        client,
        "/api/packs",
        {"character": c, "title": "A tiny day", "theme": "daily", "language": "en"},
    )
    assert result.status_code == 201, result.get_json()
    return result.get_json()["id"], ref


def test_guest_catalog(setup):
    app, _ = setup
    c = app.test_client()
    assert c.get("/api/bootstrap").get_json()["user"] is None
    catalog = c.get("/api/catalog").get_json()
    assert len(catalog["packs"]) == 10
    assert sum(p["count"] for p in catalog["packs"]) == 156
    assert c.get("/api/workspace").status_code == 401


def test_register_consent_and_password(setup):
    app, _ = setup
    c = app.test_client()
    assert (
        call(
            c, "/api/auth/register", {"email": "x@y.z", "password": "123", "name": "Me"}
        ).status_code
        == 400
    )
    assert (
        call(
            c,
            "/api/auth/register",
            {
                "email": "x@y.z",
                "password": "long enough password",
                "name": "Me",
                "terms": True,
            },
        ).status_code
        == 400
    )
    signup(c)
    assert c.get("/api/bootstrap").get_json()["user"]["plan"] == "free"


def test_origin_and_csrf(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    assert c.post("/api/auth/logout", json={}).status_code == 403
    assert (
        c.post("/api/auth/logout", json={}, headers={"Origin": ORIGIN}).status_code
        == 403
    )
    assert call(c, "/api/auth/logout", {}).status_code == 200
    assert c.get("/api/bootstrap").get_json()["user"] is None


def test_private_asset_isolation(setup):
    app, _ = setup
    a = app.test_client()
    b = app.test_client()
    signup(a)
    signup(b, "other@example.com")
    id = upload(a)
    assert a.get("/api/assets/" + id).status_code == 200
    assert b.get("/api/assets/" + id).status_code == 404
    assert app.test_client().get("/api/assets/" + id).status_code == 401


def test_lock_required(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    ref = upload(c)
    id = call(
        c, "/api/characters", {"name": "Test", "style": "photo", "refs": [ref]}
    ).get_json()["id"]
    assert call(c, "/api/packs", {"character": id, "title": "Pack"}).status_code == 409


def test_photo_end_to_end(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    body = {"kind": "photo", "attempt": "same-attempt-123456789", "consent": True}
    first = call(c, f"/api/packs/{id}/generate", body)
    assert first.status_code == 202, first.get_json()
    second = call(c, f"/api/packs/{id}/generate", body)
    assert second.get_json()["id"] == first.get_json()["id"]
    assert work_once(app.config["WESTICKER"]) is True
    w = c.get("/api/workspace").get_json()
    assert w["jobs"][0]["state"] == "review"
    assert c.get(f"/api/packs/{id}/export").status_code == 409
    items = w["packs"][0]["items"]
    for item in items:
        item["approved"] = True
    assert (
        call(c, f"/api/packs/{id}", {"items": items}, method="PATCH").status_code == 200
    )
    result = c.get(f"/api/packs/{id}/export")
    assert result.status_code == 200
    with zipfile.ZipFile(io.BytesIO(result.data)) as z:
        assert "metadata.json" in z.namelist() and "banner.jpg" in z.namelist()
        assert len([n for n in z.namelist() if n.startswith("stickers/")]) == 8
        image = Image.open(io.BytesIO(z.read("stickers/01.png")))
        assert image.size == (240, 240) and image.mode == "RGBA"


def test_no_free_ai_or_duplicate_jobs(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    assert (
        call(
            c,
            f"/api/packs/{id}/generate",
            {"kind": "ai", "attempt": "another-attempt-123", "consent": True},
        ).status_code
        == 503
    )
    body = {"kind": "photo", "attempt": "attempt-1234567890", "consent": True}
    assert call(c, f"/api/packs/{id}/generate", body).status_code == 202
    assert (
        call(
            c, f"/api/packs/{id}/generate", body | {"attempt": "different-attempt-12"}
        ).status_code
        == 409
    )


def test_reports_and_blocking(setup):
    app, _ = setup
    c = app.test_client()
    assert (
        call(
            c, "/api/reports", {"target": "vol-01", "reason": "This needs a review."}
        ).status_code
        == 201
    )
    assert call(c, "/api/blocks", {"creator": "abc"}).status_code == 401
    signup(c)
    assert call(c, "/api/blocks", {"creator": "abc"}).status_code == 200


def test_delete_removes_assets(setup):
    app, cfg = setup
    c = app.test_client()
    signup(c)
    upload(c)
    assert call(c, "/api/account/delete", {"confirmation": "NO"}).status_code == 400
    assert call(c, "/api/account/delete", {"confirmation": "DELETE"}).status_code == 200
    assert not list((Path(cfg["state"]) / "assets").glob("*.png"))
    assert c.get("/api/bootstrap").get_json()["user"] is None


def test_unconfigured_billing_and_auth(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    assert c.get("/auth/google/start").status_code == 503
    assert (
        call(
            c,
            "/api/billing/subscribe",
            {"plan": "pocket", "attempt": "not-a-real-order-123"},
        ).status_code
        == 503
    )
    assert c.get("/api/default/vol-01/download/zh").status_code == 402


def test_cross_user_pack_rejected(setup):
    app, _ = setup
    a = app.test_client()
    b = app.test_client()
    signup(a)
    signup(b, "second@example.com")
    id, _ = draft(a)
    assert b.get(f"/api/packs/{id}/export").status_code == 404
    assert (
        call(
            b,
            f"/api/packs/{id}/generate",
            {"kind": "photo", "attempt": "bad-attempt-123456", "consent": True},
        ).status_code
        == 404
    )


def test_wechat_is_never_submission(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    id, _ = draft(c)
    assert (
        call(
            c, f"/api/packs/{id}/wechat", {"draft_only": True, "consent": True}
        ).status_code
        == 403
    )
    assert call(c, f"/api/packs/{id}/listing", {"rights": True}).status_code == 503


def test_wrong_file_upload(setup):
    app, _ = setup
    c = app.test_client()
    signup(c)
    csrf = c.get("/api/bootstrap").get_json()["csrf"]
    result = c.post(
        "/api/assets",
        headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        data={
            "rights": "yes",
            "file": (io.BytesIO(b"<script>evil</script>"), "fake.png"),
        },
    )
    assert result.status_code == 400
