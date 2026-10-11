"""Synthetic provider/crypto fixtures only. No store transactions or credentials."""

import base64
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace as Obj
import time
import uuid

from cryptography.fernet import Fernet
import pytest

from server.app import create_app
from server import native_billing as billing
from server import native_reconcile as recovery
from server.store import database
from test_app import call, signup


@pytest.fixture
def native(tmp_path, monkeypatch):
    key = tmp_path / "native.key"
    key.write_bytes(Fernet.generate_key())
    key.chmod(0o600)
    cfg = {"state": str(tmp_path), "origin": "http://localhost:18642", "local_accounts": True,
           "native_billing": {"key_file": str(key),
               "apple": {"products": {"westicker.pocket": "pocket"}, "accept_sandbox": True,
                         "app_id": 42, "notifications_enabled": True},
               "google": {"package": billing.BUNDLE, "products": {"westicker.pocket": "pocket", "westicker.creator": "creator"},
                          "accept_sandbox": True, "notifications_enabled": True,
                          "notifications": {"audience": "https://westicker.invalid/push", "service_account_email": "push@westicker.invalid",
                                            "service_account_subject": "12345", "subscription": "projects/fixture/subscriptions/westicker"}}}}
    app = create_app(cfg)
    app.config["TESTING"] = True
    client = app.test_client()
    signup(client)
    owner = client.get("/api/bootstrap").get_json()["user"]["id"]
    receipt = billing.Purchase("apple", "Sandbox", "123456789012345678", "987654321098765432",
                               billing.binding(owner, "apple"), "westicker.pocket", "pocket", "active", time.time() + 3600)
    receipts, reads = {receipt.reference: receipt}, []

    def verify(cfg, reference, environment):
        reads.append(reference)
        result = receipts[reference]
        assert environment == result.environment
        return result

    monkeypatch.setattr(billing, "verify_apple", verify)
    return Obj(cfg=cfg, app=app, client=client, owner=owner, receipt=receipt, key=key, receipts=receipts, reads=reads)


def deliver(native, receipt=None, lookup=None):
    receipt = receipt or native.receipt
    return billing.apply_purchase(native.cfg, native.owner, receipt, lookup=lookup or receipt.reference)


def due(native):
    with database(native.cfg) as db:
        db.execute("UPDATE native_lookups SET next_attempt=0")


def user(native):
    with database(native.cfg) as db:
        return dict(db.execute("SELECT * FROM users WHERE id=?", (native.owner,)).fetchone())


def lookup_row(native):
    with database(native.cfg) as db:
        return dict(db.execute("SELECT * FROM native_lookups").fetchone())


def google_purchase(native, token="fixture-google-purchase-token", **kwargs):
    return replace(native.receipt, provider="google", binding=billing.binding(native.owner, "google"),
                   reference=recovery.digest(token), **kwargs)


def test_encrypted_durable_references_restart_and_idempotent_renewal(native):
    deliver(native)
    with database(native.cfg) as db:
        dump = "\n".join(db.iterdump())
        assert native.receipt.reference not in dump
        assert native.receipt.transaction not in dump
        db.execute("UPDATE users SET credits=1 WHERE id=?", (native.owner,))
    assert recovery.read_lookup(native.cfg, lookup_row(native)) == native.receipt.reference
    create_app(native.cfg)
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert user(native)["credits"] == 1
    native.receipts[native.receipt.reference] = replace(native.receipt, transaction="renewal", expires=time.time() + 7200)
    due(native)
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert user(native)["credits"] == 3
    with database(native.cfg) as db:
        assert db.execute("SELECT count(*) FROM native_grants").fetchone()[0] == 2


@pytest.mark.parametrize("state,expired,expected", [
    ("grace", False, "pocket"), ("expired", True, "free"), ("revoked", False, "free"),
    ("hold", False, "free"), ("pending", False, "free"), ("active", True, "free"),
])
def test_periodic_grace_refund_hold_pending_expiry(native, state, expired, expected):
    deliver(native)
    native.receipts[native.receipt.reference] = replace(native.receipt, state=state,
                                                       expires=time.time() + (-1 if expired else 3600))
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert user(native)["plan"] == expected
    assert user(native)["credits"] == 3


def test_outage_is_redacted_backed_off_and_never_extends_expiry(native, monkeypatch, caplog):
    deliver(native)
    with database(native.cfg) as db:
        db.execute("UPDATE users SET expires=? WHERE id=?", (time.time() - 1, native.owner))

    def fail(*args):
        raise RuntimeError("PRIVATE-TOKEN-DO-NOT-LOG")

    monkeypatch.setattr(billing, "verify_apple", fail)
    result = recovery.reconcile_due(native.cfg)
    assert result["failed"] == result["expired"] == 1
    assert user(native)["plan"] == "free"
    row = lookup_row(native)
    assert row["failures"] == 1 and row["next_attempt"] >= time.time() + 55
    assert row["last_error"] == "verification_unavailable"
    assert recovery.reconcile_due(native.cfg)["checked"] == 0
    assert "PRIVATE-TOKEN" not in caplog.text


@pytest.mark.parametrize("damage", ["missing", "permissions", "corrupt"])
def test_key_required_before_delivery(native, damage):
    if damage == "missing":
        native.key.unlink()
    elif damage == "permissions":
        native.key.chmod(0o644)
    else:
        native.key.write_bytes(b"invalid")
    result = call(native.client, "/api/billing/native/verify", {
        "provider": "apple", "reference": native.receipt.reference, "environment": "Sandbox"})
    assert result.status_code == 503
    assert native.reads == [] and user(native)["credits"] == 0
    with database(native.cfg) as db:
        assert db.execute("SELECT count(*) FROM native_grants").fetchone()[0] == 0
    native.cfg["native_billing"]["apple"]["purchase_enabled"] = True
    catalog = native.client.get("/api/billing/native/catalog").get_json()
    assert not catalog["providers"]["apple"]["purchase_enabled"]
    assert call(native.client, "/api/billing/native/prepare", {
        "provider": "apple", "product": native.receipt.product, "attempt": str(uuid.uuid4())}).status_code == 503


def test_ciphertext_is_owner_app_source_bound(native, monkeypatch):
    deliver(native)
    row = lookup_row(native)
    for field in ("user_id", "source", "environment"):
        with pytest.raises(RuntimeError, match="lookup unavailable"):
            recovery.read_lookup(native.cfg, row | {field: "different"})
    monkeypatch.setattr(billing, "BUNDLE", "another.app")
    with pytest.raises(RuntimeError, match="lookup unavailable"):
        recovery.read_lookup(native.cfg, row)


def test_corrupt_ciphertext_does_not_call_provider(native):
    deliver(native)
    with database(native.cfg) as db:
        db.execute("UPDATE native_lookups SET ciphertext=?", (b"corrupt",))
    assert recovery.reconcile_due(native.cfg)["failed"] == 1
    assert native.reads == [] and user(native)["plan"] == "pocket"


def test_bounded_batches_and_busy_locks(native):
    for number in range(3):
        receipt = replace(native.receipt, reference=str(800 + number), transaction=str(900 + number))
        native.receipts[receipt.reference] = receipt
        deliver(native, receipt)
    with billing.verification_lock(native.cfg, native.owner):
        assert recovery.reconcile_due(native.cfg, limit=2)["busy"] == 2
    assert native.reads == []
    assert recovery.reconcile_due(native.cfg, limit=2)["checked"] == 2
    assert recovery.reconcile_due(native.cfg, limit=2)["checked"] == 1
    with billing.verification_lock(native.cfg, "native-reconcile-batch"):
        assert recovery.reconcile_due(native.cfg)["busy"] == 1


def test_batch_budget_stops_between_reads(native, monkeypatch):
    deliver(native)
    times = iter([10, 12])
    monkeypatch.setattr(recovery.time, "monotonic", lambda: next(times))
    assert recovery.reconcile_due(native.cfg, budget_seconds=1)["checked"] == 0


def test_wakeup_during_reconcile_is_not_lost(native, monkeypatch):
    deliver(native)

    def verify(*args):
        recovery.enqueue_notification(native.cfg, "apple", (str(uuid.uuid4()), native.receipt.reference, "Sandbox"))
        return native.receipt

    monkeypatch.setattr(billing, "verify_apple", verify)
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert lookup_row(native)["next_attempt"] == 0


@pytest.mark.parametrize("explicit_hook", [True, False])
def test_account_deletion_cleans_recovery_and_late_delivery(native, explicit_hook):
    deliver(native)
    recovery.enqueue_notification(native.cfg, "apple", (str(uuid.uuid4()), native.receipt.reference, "Sandbox"))
    with database(native.cfg) as db:
        if explicit_hook:
            recovery.delete_native_account(db, native.owner)
        db.execute("DELETE FROM users WHERE id=?", (native.owner,))
    for table in ("native_lookups", "native_notifications", "native_owner_bindings", "native_grants", "native_subscriptions", "native_lineage"):
        with database(native.cfg) as db:
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    assert recovery.reconcile_due(native.cfg)["checked"] == 0
    with pytest.raises(ValueError, match="Account no longer exists"):
        deliver(native)
    assert recovery.enqueue_notification(native.cfg, "apple", (str(uuid.uuid4()), native.receipt.reference, "Sandbox")) == "unowned"


def test_google_ack_retry_uses_encrypted_token_without_credit_regrant(native, monkeypatch):
    token = "fixture-google-purchase-token"
    purchase = google_purchase(native, token)
    acks = []

    def acknowledge(*args, **kwargs):
        acks.append(1)
        if len(acks) == 1:
            raise RuntimeError("private-token-in-provider-error")
        return Obj(raise_for_status=lambda: None)

    monkeypatch.setattr(billing, "verify_google", lambda *_: (
        purchase, {"acknowledgementState": "ACKNOWLEDGEMENT_STATE_PENDING"}, Obj(post=acknowledge)))
    result = call(native.client, "/api/billing/native/verify", {"provider": "google", "token": token})
    assert result.status_code == 503
    assert b"private-token" not in result.data
    assert recovery.read_lookup(native.cfg, lookup_row(native)) == token
    assert token not in str(lookup_row(native))
    with database(native.cfg) as db:
        db.execute("UPDATE users SET credits=1 WHERE id=?", (native.owner,))
    create_app(native.cfg)
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert len(acks) == 2 and user(native)["credits"] == 1


def test_google_periodic_environment_cannot_change(native, monkeypatch):
    token = "fixture-google-purchase-token"
    purchase = google_purchase(native, token)
    deliver(native, purchase, token)
    monkeypatch.setattr(billing, "verify_google", lambda *_: (replace(purchase, environment="Production"), {}, Obj()))
    assert recovery.reconcile_due(native.cfg)["failed"] == 1
    with database(native.cfg) as db:
        assert db.execute("SELECT count(*) FROM native_subscriptions").fetchone()[0] == 1


def test_replacement_lineage_blocks_old_active_restore_and_revocation(native):
    old_token, new_token = "old-google-purchase-token", "new-google-purchase-token"
    old = google_purchase(native, old_token)
    new = google_purchase(native, new_token, transaction="new-order", product="westicker.creator", tier="creator", replaces=old.reference)
    deliver(native, old, old_token)
    deliver(native, new, new_token)
    assert user(native)["plan"] == "creator" and user(native)["credits"] == 40
    for stale in (old, replace(old, state="revoked"), replace(old, transaction="stale-new-order")):
        assert deliver(native, stale, old_token)["superseded"]
        assert user(native)["plan"] == "creator" and user(native)["credits"] == 40
    deliver(native, replace(new, state="revoked"), new_token)
    assert user(native)["plan"] == "free"
    assert not deliver(native, old, old_token)["active"]


def test_pending_replacement_does_not_retire_paid_predecessor(native):
    old_token, new_token = "old-google-purchase-token", "new-google-purchase-token"
    old = google_purchase(native, old_token)
    new = google_purchase(native, new_token, transaction="pending-order", replaces=old.reference, state="pending")
    deliver(native, old, old_token)
    deliver(native, new, new_token)
    assert user(native)["plan"] == "pocket"
    with database(native.cfg) as db:
        assert db.execute("SELECT count(*) FROM native_lineage").fetchone()[0] == 0


@pytest.mark.parametrize("state", ["active", "grace", "hold", "pending"])
def test_unresolved_ownership_blocks_new_purchase_even_after_local_expiry(native, state):
    native.cfg["native_billing"]["apple"]["purchase_enabled"] = True
    deliver(native, replace(native.receipt, state=state, expires=time.time() - 1))
    assert call(native.client, "/api/billing/native/prepare", {
        "provider": "apple", "product": native.receipt.product, "attempt": str(uuid.uuid4())}).status_code == 409


def test_fresh_expired_state_allows_new_prepare(native):
    native.cfg["native_billing"]["apple"]["purchase_enabled"] = True
    deliver(native, replace(native.receipt, state="expired", expires=time.time() - 1))
    assert call(native.client, "/api/billing/native/prepare", {
        "provider": "apple", "product": native.receipt.product, "attempt": str(uuid.uuid4())}).status_code == 200


def test_replacement_owner_conflict_and_unknown_predecessor_tombstone(native):
    token, predecessor = "new-google-purchase-token", "old-google-purchase-token"
    old = google_purchase(native, predecessor)
    new = google_purchase(native, token, transaction="new-order", replaces=old.reference)
    deliver(native, new, token)
    assert deliver(native, old, predecessor)["superseded"]
    other = native.app.test_client()
    signup(other, "another@example.com")
    owner = other.get("/api/bootstrap").get_json()["user"]["id"]
    stolen = replace(new, reference=recovery.digest("other-purchase-token"), binding=billing.binding(owner, "google"))
    with pytest.raises(ValueError, match="another account"):
        billing.apply_purchase(native.cfg, owner, stolen, lookup="other-purchase-token")


def test_duplicate_wakeup_never_grants_from_event(native):
    deliver(native)
    event = (str(uuid.uuid4()), native.receipt.reference, "Sandbox")
    assert recovery.enqueue_notification(native.cfg, "apple", event) == "queued"
    with database(native.cfg) as db:
        db.execute("UPDATE users SET credits=0 WHERE id=?", (native.owner,))
        db.execute("UPDATE native_lookups SET next_attempt=12345")
    assert recovery.enqueue_notification(native.cfg, "apple", event) == "duplicate"
    assert lookup_row(native)["next_attempt"] == 12345
    assert user(native)["credits"] == 0 and native.reads == []


def test_notification_before_client_delivery_resolves_only_fresh_owner(native):
    native.client.get("/api/billing/native/catalog")
    assert recovery.enqueue_notification(native.cfg, "apple", (str(uuid.uuid4()), native.receipt.reference, "Sandbox")) == "queued"
    assert user(native)["credits"] == 0 and len(native.reads) == 1
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert len(native.reads) == 2 and user(native)["credits"] == 3


def google_body(native, **changes):
    payload = {"version": "1.0", "packageName": billing.BUNDLE, "eventTimeMillis": str(int(time.time() * 1000)),
               "subscriptionNotification": {"version": "1.0", "notificationType": 2, "purchaseToken": "fixture-google-purchase-token"}}
    payload.update(changes)
    return {"subscription": native.cfg["native_billing"]["google"]["notifications"]["subscription"],
            "message": {"messageId": "123456", "data": base64.b64encode(json.dumps(payload).encode()).decode()}}


@pytest.fixture
def signed_google(native, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from google.auth.transport.requests import Request
    import jwt

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setattr(Request, "__call__", lambda *args, **kwargs: Obj(status=200, data=json.dumps({"fixture": public}).encode()))
    auth = native.cfg["native_billing"]["google"]["notifications"]
    claims = {"iss": "https://accounts.google.com", "aud": auth["audience"], "email": auth["service_account_email"],
              "sub": auth["service_account_subject"], "email_verified": True, "iat": int(time.time()), "exp": int(time.time()) + 3600}

    def token(**changes):
        return "Bearer " + jwt.encode(claims | changes, key, algorithm="RS256", headers={"kid": "fixture"})

    return token


def test_google_oidc_signature_and_exact_claims(native, signed_google):
    result = recovery.google_event(native.cfg, google_body(native), signed_google())
    assert result == ("123456", "fixture-google-purchase-token", None)
    for change in ({"aud": "foreign"}, {"iss": "foreign"}, {"email": "foreign"}, {"sub": "foreign"},
                   {"email_verified": False}, {"email_verified": "true"}, {"exp": int(time.time()) - 100}):
        with pytest.raises(recovery.NotificationError) as error:
            recovery.google_event(native.cfg, google_body(native), signed_google(**change))
        assert error.value.status == 401
    token = signed_google()
    header, payload, signature = token.split(".")
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(recovery.NotificationError):
        recovery.google_event(native.cfg, google_body(native), ".".join((header, payload, signature)))


def test_google_wrong_package_subscription_test_and_void(native, signed_google):
    for body in (google_body(native, packageName="another.app"), google_body(native) | {"subscription": "foreign"}):
        with pytest.raises(recovery.NotificationError) as error:
            recovery.google_event(native.cfg, body, signed_google())
        assert error.value.status == 400
    test = google_body(native)
    payload = {"version": "1.0", "packageName": billing.BUNDLE, "testNotification": {"version": "1.0"}}
    test["message"]["data"] = base64.b64encode(json.dumps(payload).encode()).decode()
    assert recovery.google_event(native.cfg, test, signed_google()) is None
    payload.pop("testNotification")
    payload["voidedPurchaseNotification"] = {"productType": 1, "purchaseToken": "fixture-google-purchase-token", "refundType": 1}
    test["message"]["data"] = base64.b64encode(json.dumps(payload).encode()).decode()
    assert recovery.google_event(native.cfg, test, signed_google())[1] == "fixture-google-purchase-token"


@pytest.fixture
def signed_apple(native, monkeypatch):
    """Real ES256/chain verification against an ephemeral test-only trust root."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID, ObjectIdentifier
    from appstoreserverlibrary.models.Environment import Environment
    from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
    import jwt

    now = datetime.now(timezone.utc)
    keys = [ec.generate_private_key(ec.SECP256R1()) for _ in range(3)]
    names = [x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]) for name in ("fixture-root", "fixture-intermediate", "fixture-leaf")]
    certs = []
    for index in range(3):
        issuer = max(0, index - 1)
        cert = (x509.CertificateBuilder().subject_name(names[index]).issuer_name(names[issuer])
                .public_key(keys[index].public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=1))
                .add_extension(x509.BasicConstraints(ca=index < 2, path_length=None), critical=True)
                .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False,
                                            data_encipherment=False, key_agreement=False, key_cert_sign=index < 2,
                                            crl_sign=index < 2, encipher_only=False, decipher_only=False), critical=True)
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(keys[index].public_key()), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(keys[issuer].public_key()), critical=False))
        if index:
            oid = "1.2.840.113635.100.6.2.1" if index == 1 else "1.2.840.113635.100.6.11.1"
            cert = cert.add_extension(x509.UnrecognizedExtension(ObjectIdentifier(oid), b"\x05\x00"), critical=False)
        certs.append(cert.sign(keys[issuer], hashes.SHA256()))
    chain = [base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode() for cert in reversed(certs)]

    def components(cfg, environment):
        env = Environment.SANDBOX if environment == "Sandbox" else Environment.PRODUCTION
        # Offline only in this fixture. Production apple_components always uses OCSP.
        return None, SignedDataVerifier([certs[0].public_bytes(serialization.Encoding.DER)], False, env, billing.BUNDLE, 42)

    monkeypatch.setattr(billing, "apple_components", components)

    def signed(transaction_changes=None, **changes):
        transaction = {"bundleId": billing.BUNDLE, "environment": "Sandbox", "productId": native.receipt.product,
                       "originalTransactionId": native.receipt.reference, "signedDate": int(time.time() * 1000)}
        transaction.update(transaction_changes or {})
        tx = jwt.encode(transaction, keys[2], algorithm="ES256", headers={"x5c": chain})
        payload = {"notificationUUID": str(uuid.uuid4()), "notificationType": "DID_RENEW", "version": "2.0",
                   "signedDate": int(time.time() * 1000),
                   "data": {"bundleId": billing.BUNDLE, "environment": "Sandbox", "signedTransactionInfo": tx}}
        payload.update(changes)
        return {"signedPayload": jwt.encode(payload, keys[2], algorithm="ES256", headers={"x5c": chain})}

    return signed


def test_apple_real_signatures_wrong_app_environment_and_tampering(native, signed_apple):
    body = signed_apple()
    assert recovery.apple_event(native.cfg, body)[1:] == (native.receipt.reference, "Sandbox")
    header, payload, signature = body["signedPayload"].split(".")
    signature = ("A" if signature[0] != "A" else "B") + signature[1:]
    with pytest.raises(recovery.NotificationError) as error:
        recovery.apple_event(native.cfg, {"signedPayload": ".".join((header, payload, signature))})
    assert error.value.status == 400
    with pytest.raises(recovery.NotificationError):
        recovery.apple_event(native.cfg, signed_apple(data={"bundleId": "another.app", "environment": "Sandbox"}))
    for changes in ({"bundleId": "another.app"}, {"environment": "Production"}, {"productId": "another.product"}):
        with pytest.raises(recovery.NotificationError):
            recovery.apple_event(native.cfg, signed_apple(transaction_changes=changes))
    assert recovery.apple_event(native.cfg, signed_apple(notificationType="TEST")) is None
    native.cfg["native_billing"]["apple"]["accept_sandbox"] = False
    with pytest.raises(recovery.NotificationError):
        recovery.apple_event(native.cfg, body)


def test_apple_notification_http_is_durable_not_a_grant(native, signed_apple):
    headers = {}
    body = signed_apple()
    client = native.app.test_client()
    path = "/api/billing/native/notifications/apple"
    assert client.post(path, json=body, headers=headers).status_code == 200
    assert client.post(path, json=body, headers=headers).status_code == 200
    assert user(native)["credits"] == 0
    with database(native.cfg) as db:
        assert db.execute("SELECT count(*) FROM native_notifications").fetchone()[0] == 1
    native.receipts[native.receipt.reference] = replace(native.receipt, state="revoked")
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert user(native)["credits"] == 0 and user(native)["plan"] == "free"
    assert client.post(path, json={"signedPayload": "unsigned"}, headers=headers).status_code == 400
    assert client.post(path, data=b"x" * (recovery.MAX_EVENT_BYTES + 1), headers=headers).status_code == 413


def test_google_notification_http_requires_oidc(native, signed_google, monkeypatch):
    token = "fixture-google-purchase-token"
    purchase = google_purchase(native, token)
    monkeypatch.setattr(billing, "verify_google", lambda *_: (purchase, {}, Obj()))
    native.client.get("/api/billing/native/catalog")
    client = native.app.test_client()
    path = "/api/billing/native/notifications/google"
    headers = {}
    assert client.post(path, json=google_body(native), headers=headers).status_code == 401
    headers["Authorization"] = signed_google()
    assert client.post(path, json=google_body(native), headers=headers).status_code == 200
    assert user(native)["credits"] == 0
    assert recovery.reconcile_due(native.cfg)["verified"] == 1
    assert user(native)["credits"] == 3


def test_legacy_hash_migration_preserves_grant_idempotency(native):
    receipt = native.receipt
    source = ":".join((receipt.provider, receipt.environment, receipt.reference))
    grant = ":".join((receipt.provider, receipt.environment, receipt.transaction))
    with database(native.cfg) as db:
        db.execute("INSERT INTO native_subscriptions VALUES(?,?,?,?,?,?,?,?)",
                   (source, native.owner, receipt.provider, receipt.product, receipt.tier, receipt.state, receipt.expires, time.time()))
        db.execute("INSERT INTO native_grants VALUES(?,?,?)", (grant, native.owner, time.time()))
        db.execute("UPDATE users SET subscription_id=?,credits=1 WHERE id=?", (source, native.owner))
    recovery.initialize_recovery(native.cfg)
    assert recovery.read_lookup(native.cfg, lookup_row(native)) == receipt.reference
    deliver(native)
    assert user(native)["credits"] == 1
    assert user(native)["subscription_id"] == recovery.purchase_source(receipt)


@pytest.mark.parametrize("provider_state,expected", [
    ("SUBSCRIPTION_STATE_ACTIVE", "active"), ("SUBSCRIPTION_STATE_IN_GRACE_PERIOD", "grace"),
    ("SUBSCRIPTION_STATE_ON_HOLD", "hold"), ("SUBSCRIPTION_STATE_PENDING", "pending"),
    ("SUBSCRIPTION_STATE_EXPIRED", "expired"),
])
def test_google_adapter_keeps_nonterminal_ownership_after_paid_expiry(native, monkeypatch, provider_state, expected):
    token = "fixture-google-purchase-token"
    data = {"testPurchase": {}, "subscriptionState": provider_state,
            "externalAccountIdentifiers": {"obfuscatedExternalAccountId": billing.binding(native.owner, "google")},
            "linkedPurchaseToken": "fixture-previous-purchase-token",
            "lineItems": [{"productId": "westicker.pocket", "offerDetails": {"basePlanId": "monthly"},
                           "autoRenewingPlan": {}, "expiryTime": "2020-01-01T00:00:00Z",
                           "latestSuccessfulOrderId": "fixture-paid-order"}]}
    if expected == "pending":
        del data["lineItems"][0]["expiryTime"]
    response = Obj(raise_for_status=lambda: None, json=lambda: data)
    monkeypatch.setattr(billing, "google_session", lambda *_: Obj(get=lambda *args, **kwargs: response))
    purchase, _, _ = billing.verify_google(native.cfg, token)
    assert purchase.state == expected
    assert purchase.replaces == recovery.digest(data["linkedPurchaseToken"])
    assert not deliver(native, purchase, token)["active"]


def test_transient_signature_services_request_provider_redelivery(native, signed_google, monkeypatch):
    from appstoreserverlibrary.signed_data_verifier import VerificationException, VerificationStatus
    from google.auth.exceptions import TransportError
    from google.auth.transport.requests import Request

    def fail_apple(*args):
        raise VerificationException(VerificationStatus.RETRYABLE_VERIFICATION_FAILURE)

    monkeypatch.setattr(billing, "apple_components", lambda *_: (None, Obj(verify_and_decode_notification=fail_apple)))
    with pytest.raises(recovery.NotificationError) as error:
        recovery.apple_event(native.cfg, {"signedPayload": "fixture"})
    assert error.value.status == 503

    def fail_google(*args, **kwargs):
        raise TransportError("private-provider-details")

    monkeypatch.setattr(Request, "__call__", fail_google)
    with pytest.raises(recovery.NotificationError) as error:
        recovery.google_event(native.cfg, google_body(native), signed_google())
    assert error.value.status == 503
