"""Optional SDK contract tests; these do not qualify a live issuer login."""

import json
import time
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
    control = {"active": True, "outage": False}
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
