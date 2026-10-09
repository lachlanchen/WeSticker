"""Receipt unit tests use explicit fixtures, not claimed store purchases."""

from dataclasses import replace
from types import SimpleNamespace as Obj
import time
import uuid

import pytest

from server.app import create_app
from server import native_billing as billing
from server.native_billing import Purchase, apply_purchase, binding, verification_lock
from server.store import database
from test_app import call, signup


@pytest.fixture
def native(tmp_path):
    cfg = {"state": str(tmp_path), "origin": "http://localhost:18642", "local_accounts": True,
           "native_billing": {"apple": {"products": {"art.lazying.westicker.pocket.monthly": "pocket"},
                                          "purchase_enabled": True}}}
    app = create_app(cfg)
    client = app.test_client()
    signup(client)
    owner = client.get("/api/bootstrap").get_json()["user"]["id"]
    receipt = Purchase("apple", "Sandbox", "123", "456", binding(owner, "apple"),
                       "art.lazying.westicker.pocket.monthly", "pocket", "active", time.time()+3600)
    return cfg, client, owner, receipt


def test_verified_receipt_grants_once(native):
    cfg, client, owner, receipt = native
    assert apply_purchase(cfg, owner, receipt)["active"]
    assert apply_purchase(cfg, owner, receipt)["active"]
    assert client.get("/api/bootstrap").get_json()["user"]["credits"] == 3
    with database(cfg) as db:
        db.execute("UPDATE users SET credits=1 WHERE id=?", (owner,))
    apply_purchase(cfg, owner, receipt)
    assert client.get("/api/bootstrap").get_json()["user"]["credits"] == 1
    apply_purchase(cfg, owner, replace(receipt, transaction="457", expires=time.time()+7200))
    assert client.get("/api/bootstrap").get_json()["user"]["credits"] == 3


def test_binding_and_catalog_checked(native):
    cfg, _, owner, receipt = native
    with pytest.raises(ValueError):
        apply_purchase(cfg, owner, replace(receipt, binding=str(uuid.uuid4())))
    with pytest.raises(ValueError):
        apply_purchase(cfg, owner, replace(receipt, product="another.app.product"))
    with database(cfg) as db:
        assert db.execute("SELECT count(*) FROM native_grants").fetchone()[0] == 0


def test_expired_and_revoked_do_not_grant(native):
    cfg, client, owner, receipt = native
    assert not apply_purchase(cfg, owner, replace(receipt, expires=time.time()-1))["active"]
    apply_purchase(cfg, owner, receipt)
    assert not apply_purchase(cfg, owner, replace(receipt, state="revoked"))["active"]
    user = client.get("/api/bootstrap").get_json()["user"]
    assert user["plan"] == "free" and user["credits"] == 3


def test_other_subscription_not_canceled_by_old_revocation(native):
    cfg, client, owner, receipt = native
    apply_purchase(cfg, owner, receipt)
    apply_purchase(cfg, owner, replace(receipt, reference="124", transaction="457"))
    apply_purchase(cfg, owner, replace(receipt, state="revoked"))
    assert client.get("/api/bootstrap").get_json()["user"]["plan"] == "pocket"


def test_prepare_is_idempotent_and_blocks_duplicate_purchase(native):
    _, client, _, receipt = native
    body = {"provider": "apple", "product": receipt.product, "attempt": str(uuid.uuid4())}
    first = call(client, "/api/billing/native/prepare", body)
    assert first.status_code == 200
    assert call(client, "/api/billing/native/prepare", body).get_json() == first.get_json()
    assert call(client, "/api/billing/native/prepare", body | {"attempt": str(uuid.uuid4())}).status_code == 409
    assert call(client, "/api/billing/native/outcome", {"attempt": body["attempt"], "state": "pending"}).status_code == 200
    assert call(client, "/api/billing/native/prepare", body).status_code == 409


def test_client_claims_do_not_grant(native):
    _, client, _, receipt = native
    result = call(client, "/api/billing/native/verify", {
        "provider": "apple", "reference": "fake", "environment": "Sandbox", "plan": "studio", "credits": 999,
    })
    assert result.status_code == 400
    assert client.get("/api/bootstrap").get_json()["user"]["credits"] == 0


def test_native_verify_requires_auth_and_csrf(native):
    cfg, client, _, _ = native
    app = create_app(cfg)
    assert app.test_client().get("/api/billing/native/catalog").status_code == 401
    assert client.post("/api/billing/native/verify", json={"provider": "apple"}).status_code == 403


def test_restore_is_serialized_per_owner(native):
    cfg, client, owner, _ = native
    with verification_lock(cfg, owner):
        with pytest.raises(BlockingIOError):
            with verification_lock(cfg, owner):
                pytest.fail("Concurrent verification entered")
        result = call(client, "/api/billing/native/verify", {"provider": "apple"})
        assert result.status_code == 409
        with verification_lock(cfg, "another-account"):
            pass
    with verification_lock(cfg, owner):
        pass


@pytest.fixture
def apple_fixture(native, monkeypatch):
    cfg, _, owner, receipt = native
    cfg["native_billing"]["apple"]["app_id"] = 123
    tx = Obj(bundleId=billing.BUNDLE, environment="Sandbox", originalTransactionId="123",
             transactionId="456", type="Auto-Renewable Subscription", inAppOwnershipType="PURCHASED",
             quantity=1, appAccountToken=binding(owner, "apple"), productId=receipt.product,
             expiresDate=int((time.time()+3600)*1000), revocationDate=None, isUpgraded=False)
    renewal = Obj(environment="Sandbox", originalTransactionId="123", productId=receipt.product,
                  gracePeriodExpiresDate=int((time.time()+7200)*1000))
    item = Obj(originalTransactionId="123", signedTransactionInfo="verified-fixture",
               signedRenewalInfo="verified-fixture", status=1)
    response = Obj(bundleId=billing.BUNDLE, data=[Obj(lastTransactions=[item])])
    client = Obj(get_all_subscription_statuses=lambda _: response)
    verifier = Obj(verify_and_decode_signed_transaction=lambda _: tx,
                   verify_and_decode_renewal_info=lambda _: renewal)
    monkeypatch.setattr(billing, "apple_components", lambda *_: (client, verifier))
    return cfg, tx, renewal, item


def test_apple_verified_status_and_grace(apple_fixture):
    cfg, tx, renewal, item = apple_fixture
    assert billing.verify_apple(cfg, "123", "Sandbox").state == "active"
    item.status = 4
    result = billing.verify_apple(cfg, "123", "Sandbox")
    assert result.state == "grace" and result.expires == renewal.gracePeriodExpiresDate/1000
    tx.revocationDate = int(time.time()*1000)
    assert billing.verify_apple(cfg, "123", "Sandbox").state == "revoked"


@pytest.mark.parametrize("field,value", [
    ("bundleId", "another.app"), ("environment", "Production"),
    ("originalTransactionId", "another"), ("inAppOwnershipType", "FAMILY_SHARED"),
    ("type", "Consumable"), ("appAccountToken", None), ("productId", "another.product"),
])
def test_apple_rejects_mismatched_verified_payload(apple_fixture, field, value):
    cfg, tx, _, _ = apple_fixture
    setattr(tx, field, value)
    with pytest.raises(ValueError):
        billing.verify_apple(cfg, "123", "Sandbox")


@pytest.fixture
def google_fixture(native, monkeypatch):
    cfg, _, owner, _ = native
    product = "westicker_pocket_monthly"
    cfg["native_billing"]["google"] = {"products": {product: "pocket"}, "accept_sandbox": True}
    data = {"testPurchase": {}, "subscriptionState": "SUBSCRIPTION_STATE_CANCELED",
            "externalAccountIdentifiers": {"obfuscatedExternalAccountId": binding(owner, "google")},
            "lineItems": [{"productId": product, "offerDetails": {"basePlanId": "monthly"},
                           "autoRenewingPlan": {}, "latestSuccessfulOrderId": "fixture-order",
                           "expiryTime": "2099-01-01T00:00:00Z"}]}
    response = Obj(raise_for_status=lambda: None, json=lambda: data)
    session = Obj(get=lambda *args, **kwargs: response)
    monkeypatch.setattr(billing, "google_session", lambda *_: session)
    return cfg, data


def test_google_cancelled_still_paid_through_and_hold(google_fixture):
    cfg, data = google_fixture
    result, _, _ = billing.verify_google(cfg, "test-purchase-token")
    assert result.state == "active" and result.environment == "Sandbox"
    data["subscriptionState"] = "SUBSCRIPTION_STATE_ON_HOLD"
    assert billing.verify_google(cfg, "test-purchase-token")[0].state == "hold"
    cfg["native_billing"]["google"]["accept_sandbox"] = False
    with pytest.raises(ValueError):
        billing.verify_google(cfg, "test-purchase-token")


def test_google_requires_paid_order_and_account(google_fixture):
    cfg, data = google_fixture
    data["externalAccountIdentifiers"] = {}
    with pytest.raises(ValueError):
        billing.verify_google(cfg, "test-purchase-token")
    data["externalAccountIdentifiers"] = {"obfuscatedExternalAccountId": "fixture"}
    del data["lineItems"][0]["latestSuccessfulOrderId"]
    with pytest.raises(ValueError):
        billing.verify_google(cfg, "test-purchase-token")


def test_google_acknowledgement_retry_does_not_double_grant(native, monkeypatch):
    cfg, client, owner, receipt = native
    cfg["native_billing"]["google"] = {"products": {"westicker_pocket_monthly": "pocket"}}
    receipt = replace(receipt, provider="google", binding=binding(owner, "google"),
                      product="westicker_pocket_monthly")
    attempts = []
    def acknowledge(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("Simulated transport failure after durable delivery")
        return Obj(raise_for_status=lambda: None)
    monkeypatch.setattr(billing, "verify_google", lambda *_: (
        receipt, {"acknowledgementState": "ACKNOWLEDGEMENT_STATE_PENDING"}, Obj(post=acknowledge)))
    body = {"provider": "google", "token": "test-purchase-token"}
    assert call(client, "/api/billing/native/verify", body).status_code == 503
    assert call(client, "/api/billing/native/verify", body).status_code == 200
    assert client.get("/api/bootstrap").get_json()["user"]["credits"] == 3
