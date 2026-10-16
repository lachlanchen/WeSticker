"""Isolated app/real-SDK contract tests. No live accounts, awards or purchases."""

import hashlib
import json
import time
from copy import deepcopy
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

from server.app import create_app
from server.store import database
from test_shared_identity import linked, connect, ORIGIN

SUBJECT = "la_" + "b" * 32
PASSWORD = "Isolated local creator 123!"


def headers(client):
    return {"Origin": ORIGIN, "X-CSRF-Token": client.get("/api/bootstrap").json["csrf"]}


def accept(client):
    return client.post("/api/account/consent", json={"adult": True, "terms": True}, headers=headers(client))


def register(app, name="Local creator"):
    app.config["WESTICKER"]["local_accounts"] = True
    client = app.test_client()
    assert client.post("/api/auth/register", json={"name": name, "email": name.replace(" ", "") + "@example.invalid",
                       "password": PASSWORD, "adult": True, "terms": True}, headers={"Origin": ORIGIN}).status_code == 200
    return client


def callback(client, target, *, cancel=False):
    query = parse_qs(urlsplit(target).query)
    fields = {"state": query["state"][0], "iss": "https://identity.example"}
    fields.update({"error": "access_denied"} if cancel else {"code": "c" * 43})
    return "/auth/lazyingart/callback?" + urlencode(fields)


@pytest.fixture
def points_env(linked):
    sdk = pytest.importorskip("lazyingart_link")
    if not hasattr(sdk, "PointsClient"):
        pytest.skip("Qualification requires the delivered points SDK; installed profile SDK stays unchanged")
    from lazyingart_link.points import CONTRACT, GRANT, RESOURCE, TARGET, TOKEN_TYPE, points_asset
    from lazyingart_link.onboard import load_private
    from server.shared_account import READ_SCOPE

    app, control = linked
    adapter = app.extensions["westicker_shared_account"]
    profile = adapter.profile
    cfg = app.config["WESTICKER"]
    cfg.update(shared_points_read_enabled=True, shared_account_linking_enabled=True)
    options, key = load_private(cfg["providers"]["lazyingart"]["private_directory"])
    adapter.points_store = sdk.LinkStore(profile.store.path.parent / "points-sessions.sqlite", options, key)
    original = profile.client.transport
    control.update(points_subject=SUBJECT, points_outage=False, points_active=True, qualified=True,
                   resource_calls=0, snapshot_changes={}, after_read=None, freshness=0)

    def transport(method, url, fields):
        if fields and fields.get("grant_type") == GRANT:
            assert fields["scope"] == READ_SCOPE
            assert fields["audience"] == TARGET
            return dict(access_token="d" * 43, token_type="Bearer", issued_token_type=TOKEN_TYPE,
                        expires_in=200, scope=READ_SCOPE)
        result = original(method, url, fields)
        if method == "GET":
            result.update(adapter_contracts=[CONTRACT], resource_delegations=[],
                          scopes_supported=["profile", READ_SCOPE])
            result["grant_types_supported"].append(GRANT)
            if control["qualified"]:
                result["resource_delegations"].append(dict(
                    contract=CONTRACT, delegation_version=1, actor_client_id="westicker",
                    source_audience="westicker", audience=TARGET, scope=READ_SCOPE,
                    resource_client_id=RESOURCE, max_token_lifetime_seconds=300,
                    max_future_iat_skew_seconds=30, refresh_supported=False, chained_delegation_supported=False))
        elif "refresh_token" in result:
            result.update(access_token="p" * 43, scope="profile " + READ_SCOPE)
        elif result.get("active"):
            result.update(scope="profile " + READ_SCOPE, sub=control["points_subject"],
                          auth_time=int(time.time()) - control["freshness"])
            result["account"]["subject"] = control["points_subject"]
            if not control["points_active"]:
                return {"active": False}
        return result

    def resource(method, url, token, body):
        assert (method, url, token, body) == ("GET", "https://coin.lazying.art/api/points/v1/balance", "d" * 43, None)
        control["resource_calls"] += 1
        if control["points_outage"]:
            raise sdk.LinkError("ledger_unavailable")
        asset = points_asset()
        snapshot = dict(schema_version=1, contract=CONTRACT, as_of=int(time.time()),
                        account={"issuer": options.issuer, "subject": SUBJECT},
                        balance_id="lac_fun_points_" + hashlib.sha256(json.dumps(
                            [options.issuer, SUBJECT, asset["asset_id"]], separators=(",", ":")).encode()).hexdigest(),
                        revision="7", asset=asset, ledger="fun_points", pending_points="2", awarded_points="3",
                        reversed_points="8", counts={"pending": 1, "awarded": 1, "reversed": 2}, spendable=False,
                        aggregation="canonical_account_snapshot_do_not_sum_across_apps")
        snapshot.update(deepcopy(control["snapshot_changes"]))
        if control["after_read"]:
            control["after_read"]()
        return snapshot

    adapter.points = sdk.PointsClient(options, scopes=(READ_SCOPE,), resource_origin="https://coin.lazying.art",
                                     transport=transport, points_transport=resource)
    return app, control, adapter


def consent_points(app, client):
    response = client.post("/api/account/shared/points/consent", json={"confirmed": True}, headers=headers(client))
    assert response.status_code == 200, response.json
    query = parse_qs(urlsplit(response.json["url"]).query)
    assert query["scope"] == ["profile lac.points.balance.read"]
    assert query["redirect_uri"] == [ORIGIN + "/auth/lazyingart/callback"]
    assert "reuse_consent" not in query
    result = client.get(callback(client, response.json["url"]))
    assert result.status_code == 302, result.json


def test_disabled_is_not_zero_and_requires_auth(linked):
    app, _ = linked
    client = register(app)
    status = client.get("/api/account/shared")
    assert status.json["linked"] is False
    assert status.json["points"]["state"] == "disabled"
    balance = client.get("/api/account/shared/points")
    assert balance.json == {"state": "disabled", "asset_id": "lazyingart.fun-points.v1"}
    assert balance.headers["Cache-Control"] == "no-store"
    assert app.test_client().get("/api/account/shared").status_code == 401
    for suffix in ("link", "points/consent"):
        assert client.post("/api/account/shared/" + suffix, json={"confirmed": True}).status_code == 403
    assert client.post("/api/account/shared/points", json={}, headers=headers(client)).status_code == 405
    assert not any("intents" in str(rule) or "reversals" in str(rule) for rule in app.url_map.iter_rules())


def test_additive_migration_preserves_existing_creator_and_session(linked):
    from server.store import initialize
    app, _ = linked
    client = register(app)
    cfg = app.config["WESTICKER"]
    owner = client.get("/api/bootstrap").json["user"]["id"]
    with database(cfg) as db:
        db.execute("UPDATE users SET credits=17,plan='creator' WHERE id=?", (owner,))
        db.execute("INSERT INTO entitlements VALUES(?,?,?)", (owner, "owned-pack", "original-purchase"))
        db.execute("ALTER TABLE sessions DROP COLUMN auth_kind")
        db.execute("ALTER TABLE native_links DROP COLUMN auth_kind")
        before = [tuple(r) for r in db.execute("SELECT * FROM users")]
    initialize(cfg)
    initialize(cfg)
    with database(cfg) as db:
        assert [tuple(r) for r in db.execute("SELECT * FROM users")] == before
        assert db.execute("SELECT auth_kind FROM sessions WHERE user_id=?", (owner,)).fetchone()[0] == "legacy"
        assert tuple(db.execute("SELECT * FROM entitlements").fetchone()) == (owner, "owned-pack", "original-purchase")
    assert client.get("/api/bootstrap").json["user"]["credits"] == 17


def test_profile_permission_is_not_points_consent(points_env):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    assert client.get("/api/account/shared").json["linked"]
    assert client.get("/api/account/shared/points").json["state"] == "consent_required"
    assert control["resource_calls"] == 0
    assert client.post("/api/account/shared/points/consent", json={}, headers=headers(client)).status_code == 400
    control["qualified"] = False
    assert client.post("/api/account/shared/points/consent", json={"confirmed": True}, headers=headers(client)).status_code == 503


def test_balance_net_not_subtracted_or_added_preserves_local_values(points_env):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    owner = client.get("/api/bootstrap").json["user"]["id"]
    with database(app.config["WESTICKER"]) as db:
        db.execute("UPDATE users SET credits=19,plan='creator',expires=? WHERE id=?", (time.time() + 3600, owner))
        db.execute("INSERT INTO entitlements VALUES(?,?,?)", (owner, "private-test-pack", "test-purchase"))
    consent_points(app, client)
    for _ in range(2):
        result = client.get("/api/account/shared/points").json
        assert result["awarded_points"] == "3"  # already net, despite reversed=8
        assert "account" not in result and "token" not in json.dumps(result)
    control["snapshot_changes"] = {"revision": "8", "awarded_points": "0"}
    assert client.get("/api/account/shared/points").json["awarded_points"] == "0"
    boot = client.get("/api/bootstrap").json
    assert boot["user"]["credits"] == 19 and boot["user"]["plan"] == "creator"
    with database(app.config["WESTICKER"]) as db:
        assert db.execute("SELECT count(*) FROM entitlements WHERE user_id=?", (owner,)).fetchone()[0] == 1


@pytest.mark.parametrize("change", [
    {"revision": "6"}, {"awarded_points": True}, {"awarded_points": "03"},
    {"as_of": 1}, {"as_of": 9999999999999}, {"asset": {"asset_id": "ethereum.LAC"}},
    {"account": {"issuer": "https://identity.example", "subject": "la_" + "x" * 32}},
])
def test_bad_snapshot_is_unavailable_not_zero(points_env, change):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    consent_points(app, client)
    assert client.get("/api/account/shared/points").json["state"] == "ready"
    control["snapshot_changes"] = change
    result = client.get("/api/account/shared/points").json
    assert result["state"] == "unavailable" and "awarded_points" not in result


def test_outage_logout_and_reconnect_keep_revision(points_env):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    consent_points(app, client)
    client.get("/api/account/shared/points")
    control["points_outage"] = True
    assert client.get("/api/account/shared/points").json["state"] == "unavailable"
    control["revoke_outage"] = True
    assert client.post("/api/auth/logout", json={}, headers=headers(client)).status_code == 200
    assert client.get("/api/account/shared/points").status_code == 401
    with database(app.config["WESTICKER"]) as db:
        row = db.execute("SELECT * FROM shared_points_connections").fetchone()
        assert row["state"] == "held" and row["revision"] == "7"


def test_consent_cancel_replay_browser_and_subject_binding(points_env):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    response = client.post("/api/account/shared/points/consent", json={"confirmed": True}, headers=headers(client))
    cancelled = callback(client, response.json["url"], cancel=True)
    assert app.test_client().get(cancelled).status_code == 401
    assert "connection=cancelled" in client.get(cancelled).location
    assert client.get(cancelled).status_code == 401
    response = client.post("/api/account/shared/points/consent", json={"confirmed": True}, headers=headers(client))
    control["points_subject"] = "la_" + "c" * 32
    assert client.get(callback(client, response.json["url"])).status_code == 409
    with database(app.config["WESTICKER"]) as db:
        assert db.execute("SELECT count(*) FROM shared_points_connections").fetchone()[0] == 0


def test_account_switch_and_logout_during_read(points_env):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    response = client.post("/api/account/shared/points/consent", json={"confirmed": True}, headers=headers(client))
    local = register(app, "Other creator")
    client.set_cookie("westicker_session", local.get_cookie("westicker_session").value)
    assert client.get(callback(client, response.json["url"])).status_code == 401
    client = connect(app)
    consent_points(app, client)
    def hold():
        with database(app.config["WESTICKER"]) as db:
            db.execute("UPDATE shared_points_connections SET state='held'")
    control["after_read"] = hold
    assert client.get("/api/account/shared/points").json["state"] == "unavailable"


def test_explicit_link_needs_local_and_fresh_central_proof(points_env, monkeypatch):
    app, control, adapter = points_env
    client = register(app)
    owner = client.get("/api/bootstrap").json["user"]["id"]
    real_authorize = adapter.profile.client.authorize
    def fresh(store, binding, **kwargs):
        assert not kwargs or kwargs == {"prompt": "login", "reuse_consent": False}
        return real_authorize(store, binding)  # fixture lacks provider-select; proof below is still real SDK
    monkeypatch.setattr(adapter.profile.client, "authorize", fresh)
    original_transport = adapter.profile.client.transport
    def identity(method, url, fields):
        value = original_transport(method, url, fields)
        if value.get("active"):
            value["auth_time"] = int(time.time()) - control["freshness"]
        return value
    adapter.profile.client.transport = identity
    endpoint = "/api/account/shared/link"
    assert client.post(endpoint, json={"confirmed": True, "password": "wrong"}, headers=headers(client)).status_code == 401
    control["freshness"] = 400
    made = client.post(endpoint, json={"confirmed": True, "password": PASSWORD}, headers=headers(client))
    assert client.get(callback(client, made.json["url"])).status_code == 401
    control["freshness"] = 0
    made = client.post(endpoint, json={"confirmed": True, "password": PASSWORD}, headers=headers(client))
    assert client.get(callback(client, made.json["url"])).status_code == 302
    assert client.get("/api/bootstrap").json["user"]["id"] == owner
    control["outage"] = True
    assert client.get("/api/workspace").status_code == 200  # local login remains independent
    control["outage"] = False
    assert connect(app).get("/api/bootstrap").json["user"]["id"] == owner
    other = register(app, "Unmerged creator")
    made = other.post(endpoint, json={"confirmed": True, "password": PASSWORD}, headers=headers(other))
    assert other.get(callback(other, made.json["url"])).status_code == 409
    with database(app.config["WESTICKER"]) as db:
        assert db.execute("SELECT count(*) FROM users").fetchone()[0] == 2
        assert db.execute("SELECT user_id FROM identities WHERE subject=?", (SUBJECT,)).fetchone()[0] == owner


def test_deleted_or_changed_mapping_never_accepts_balance(points_env):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    consent_points(app, client)
    with database(app.config["WESTICKER"]) as db:
        db.execute("UPDATE shared_points_connections SET subject=?", ("la_" + "x" * 32,))
    assert client.get("/api/account/shared/points").json["state"] == "reconnect"
    assert control["resource_calls"] == 0


def test_expired_callback_and_feature_disabled_mid_flow(points_env):
    app, _, _ = points_env
    client = connect(app)
    accept(client)
    made = client.post("/api/account/shared/points/consent", json={"confirmed": True}, headers=headers(client))
    with database(app.config["WESTICKER"]) as db:
        db.execute("UPDATE shared_account_attempts SET created=?", (time.time() - 400,))
    assert client.get(callback(client, made.json["url"])).status_code == 401
    made = client.post("/api/account/shared/points/consent", json={"confirmed": True}, headers=headers(client))
    app.config["WESTICKER"]["shared_points_read_enabled"] = False
    assert client.get(callback(client, made.json["url"])).status_code == 503
    assert client.get("/api/account/shared/points").json["state"] == "disabled"


def test_restart_cleanup_does_not_revoke_accepted_consent(points_env):
    app, control, adapter = points_env
    client = connect(app)
    accept(client)
    consent_points(app, client)
    assert adapter.cleanup()["reconciled"] == 0
    assert client.get("/api/account/shared/points").json["state"] == "ready"
    # Simulate termination after SDK adoption, before the app mapping commit.
    store = adapter.points_store
    binding = "b" * 43
    target = adapter.points.authorize(store, binding)
    completion_id, identity = store.complete_pending(adapter.points, ORIGIN + callback(client, target), binding)
    session_id = store.adopt_completion(completion_id, expected_subject=SUBJECT)
    with database(app.config["WESTICKER"]) as db:
        db.execute("INSERT INTO shared_account_returns VALUES(?,?,?,?,?)",
                   ("interrupted", "points", identity.subject, completion_id, time.time() - 400))
    assert adapter.cleanup()["reconciled"] == 1
    with store.transaction() as db:
        assert db.execute("SELECT state FROM sessions WHERE id=?", (session_id,)).fetchone()[0] == "revoked"
    assert client.get("/api/account/shared/points").json["state"] == "ready"


def test_disabling_reads_preserves_credential_cleanup(points_env):
    from server.shared_account import SharedAccount
    app, _, adapter = points_env
    client = connect(app)
    accept(client)
    consent_points(app, client)
    cfg = app.config["WESTICKER"]
    cfg["shared_points_read_enabled"] = False
    restarted = SharedAccount(app, cfg)
    assert restarted.points_store is not None
    # Keep the qualified fixture transport; no issuer or ledger requests go live.
    restarted.points = adapter.points
    app.extensions["westicker_shared_account"] = restarted
    owner = client.get("/api/bootstrap").json["user"]["id"]
    assert restarted.status({"id": owner})["points"]["state"] == "disabled"
    assert restarted.balance({"id": owner})["state"] == "disabled"
    restarted.disconnect(owner, required=True)
    with database(cfg) as db:
        assert db.execute("SELECT state FROM shared_points_connections").fetchone()[0] == "revoked"


def test_revoked_points_does_not_revoke_profile_and_deletion_waits(points_env):
    app, control, _ = points_env
    client = connect(app)
    accept(client)
    consent_points(app, client)
    control["points_active"] = False
    assert client.get("/api/account/shared/points").json["state"] == "reconnect"
    assert client.get("/api/workspace").status_code == 200
    control["revoke_outage"] = True
    result = client.post("/api/account/delete", json={"confirmation": "DELETE"}, headers=headers(client))
    assert result.status_code == 503
    assert client.get("/api/bootstrap").json["user"]
    control["revoke_outage"] = False
    assert client.post("/api/account/delete", json={"confirmation": "DELETE"}, headers=headers(client)).status_code == 200
