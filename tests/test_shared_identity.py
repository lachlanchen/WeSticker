"""Optional SDK contract tests; these do not qualify a live issuer login."""

import json
import time
import base64
import hashlib
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

pytest.importorskip("lazyingart_link")
from lazyingart_link.client import ENDPOINTS, LinkError
from lazyingart_link.onboard import stage
from server.app import create_app
from server.ingress import RelayGuard

ORIGIN = "https://westicker.example"


@pytest.fixture
def linked(tmp_path):
    tmp_path.chmod(0o700)
    private = tmp_path / "identity"
    stage(private, issuer="https://identity.example", client_id="westicker",
          audience="westicker", redirect_uri=ORIGIN + "/auth/lazyingart/callback")
    data = json.loads((private / "link.json").read_text())
    data["enabled"] = True
    (private / "link.json").write_text(json.dumps(data))
    app = create_app({"state": str(tmp_path / "state"), "origin": ORIGIN,
                      "providers": {"lazyingart": {"private_directory": str(private)}}})
    adapter = app.extensions["westicker_shared_identity"]
    control = {"active": True, "outage": False, "revoke_outage": False, "revocations": 0}
    cfg = adapter.client.config

    def transport(method, url, fields):
        if control["outage"]:
            raise LinkError("issuer_unavailable")
        if method == "GET":
            return {"issuer": cfg.issuer, "contract_version": 1,
                    **{k: cfg.issuer + v for k, v in ENDPOINTS.items()},
                    "response_types_supported": ["code"],
                    "grant_types_supported": ["authorization_code", "refresh_token"],
                    "code_challenge_methods_supported": ["S256"],
                    "token_endpoint_auth_methods_supported": ["client_secret_post"],
                    "scopes_supported": ["profile"],
                    "providers": {"password": True, "google": False, "apple": False, "github": False}}
        assert fields["client_secret"] == cfg.client_secret
        if url.endswith("/revoke"):
            if control["revoke_outage"]:
                raise LinkError("issuer_unavailable")
            control["revocations"] += 1
            return {"success": True}
        if url.endswith("/token"):
            return {"access_token": "a" * 43, "refresh_token": "r" * 64,
                    "expires_in": 600, "token_type": "Bearer", "scope": "profile"}
        if url.endswith("/introspect"):
            if not control["active"]:
                return {"active": False}
            now = int(time.time())
            subject = "la_" + "b" * 32
            return {"active": True, "iss": cfg.issuer, "sub": subject,
                    "client_id": cfg.client_id, "aud": cfg.audience, "scope": "profile",
                    "token_type": "Bearer", "iat": now, "exp": now + 600,
                    "auth_time": now - 100, "verified_legacy_identities": [],
                    "account": {"subject": subject, "display_name": "Test creator",
                                "account_status": "active", "email_verified": False}}
        raise AssertionError("Unexpected endpoint")

    adapter.client.transport = transport
    return app, control


def connect(app):
    client = app.test_client()
    response = client.get("/auth/lazyingart/start")
    query = parse_qs(urlsplit(response.location).query)
    assert query["code_challenge_method"] == ["S256"]
    callback = "/auth/lazyingart/callback?" + urlencode({
        "code": "c" * 43, "state": query["state"][0], "iss": "https://identity.example"})
    assert app.test_client().get(callback).status_code == 401
    assert client.get(callback).status_code == 302
    assert client.get(callback).status_code == 401
    return client


def test_sdk_identity_consent_replay_revocation_and_outage(linked):
    app, control = linked
    c = connect(app)
    boot = c.get("/api/bootstrap").json
    assert boot["user"]["name"] == "Test creator"
    assert c.get("/api/workspace").status_code == 403
    headers = {"Origin": ORIGIN, "X-CSRF-Token": boot["csrf"]}
    assert c.post("/api/account/consent", json={"adult": True, "terms": True}, headers=headers).status_code == 200
    assert c.get("/api/workspace").status_code == 200
    control["outage"] = True
    assert c.get("/api/workspace").status_code == 503
    control["outage"] = False
    assert c.get("/api/workspace").status_code == 200
    control["active"] = False
    assert c.get("/api/workspace").status_code == 401
    # Local sign-out must still work during issuer failure/revocation.
    assert c.post("/api/auth/logout", json={}, headers=headers).status_code == 200
    assert c.get("/api/bootstrap").json["user"] is None


def test_relay_does_not_trust_external_authorization():
    from werkzeug.test import Client
    from werkzeug.wrappers import Response
    def target(env, start):
        response = Response(env.get("HTTP_AUTHORIZATION", "") + "|" + env["REMOTE_ADDR"])
        return response(env, start)
    c = Client(RelayGuard(target, "secret", "westicker.example"), Response)
    assert c.get("/", headers={"Host": "westicker.example"}).status_code == 403
    assert c.get("/", headers={"Host": "wrong.example", "X-Westicker-Relay": "secret"}).status_code == 403
    r = c.get("/", headers={"Host": "westicker.example", "X-Westicker-Relay": "secret",
                            "Authorization": "upstream-impostor",
                            "X-Westicker-Client-Authorization": "Bearer app-token",
                            "X-Westicker-Client-IP": "192.0.2.1"})
    assert r.data == b"Bearer app-token|192.0.2.1"


def test_native_intent_survives_actual_oauth_callback_contract(linked):
    app, _ = linked
    c = app.test_client()
    verifier = "n" * 64
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    made = c.post("/api/native/link", json={"challenge": challenge, "app_return": True}, headers={"Origin": ORIGIN})
    id = made.json["id"]
    assert made.json["url"].endswith("&native_return=1")
    assert c.get("/auth/lazyingart/start?native_link=https://evil.example").status_code == 400
    response = c.get(f"/auth/lazyingart/start?native_link={id}&native_return=1&redirect_uri=https://evil.example")
    q = parse_qs(urlsplit(response.location).query)
    callback = "/auth/lazyingart/callback?" + urlencode({"code": "c"*43, "state": q["state"][0], "iss": "https://identity.example"})
    result = c.get(callback)
    assert result.status_code == 302
    assert parse_qs(urlsplit(result.location).query) == {"welcome": ["1"], "native_link": [id], "native_return": ["1"]}
    boot = c.get("/api/bootstrap").json
    headers = {"Origin": ORIGIN, "X-CSRF-Token": boot["csrf"]}
    c.post("/api/account/consent", json={"adult": True, "terms": True}, headers=headers)
    approved = c.post(f"/api/native/link/{id}/approve", json={"approved": True}, headers=headers)
    assert approved.json["return_url"] == f"art.lazying.westicker://auth/complete?link={id}"
    native = app.test_client()
    exchanged = native.post(f"/api/native/link/{id}/exchange", json={"verifier": verifier}, headers={"Origin": ORIGIN})
    assert exchanged.status_code == 200
    assert native.post(f"/api/native/link/{id}/exchange", json={"verifier": verifier}, headers={"Origin": ORIGIN, "X-CSRF-Token": exchanged.json["csrf"]}).status_code == 410


def test_cancel_validates_browser_state_before_friendly_return(linked):
    app, _ = linked
    client = app.test_client()
    response = client.get("/auth/lazyingart/start")
    state = parse_qs(urlsplit(response.location).query)["state"][0]
    callback = "/auth/lazyingart/callback?" + urlencode({
        "error": "access_denied", "state": state, "iss": "https://identity.example"})
    assert app.test_client().get(callback).status_code == 401
    cancelled = client.get(callback)
    assert cancelled.status_code == 302
    assert cancelled.location == ORIGIN + "/?login=cancelled"
    assert client.get("/api/bootstrap").json["user"] is None
    assert client.get(callback).status_code == 401


def test_delete_revokes_all_app_sessions_and_can_retry(linked):
    from server.store import database
    app, control = linked
    first = connect(app)
    second = connect(app)
    boot = second.get("/api/bootstrap").json
    headers = {"Origin": ORIGIN, "X-CSRF-Token": boot["csrf"]}
    control["revoke_outage"] = True
    assert second.post("/api/account/delete", json={"confirmation": "DELETE"}, headers=headers).status_code == 503
    with database(app.config["WESTICKER"]) as db:
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    control["revoke_outage"] = False
    # Revocation may already have invalidated the current central grant.
    control["active"] = False
    assert second.post("/api/account/delete", json={"confirmation": "DELETE"}, headers=headers).status_code == 200
    assert control["revocations"] == 2
    assert first.get("/api/workspace").status_code == 401
    assert second.get("/api/bootstrap").json["user"] is None
    adapter = app.extensions["westicker_shared_identity"]
    with adapter.store.transaction() as db:
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    with database(app.config["WESTICKER"]) as db:
        for table in ("users", "identities", "sessions", "shared_grants"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
