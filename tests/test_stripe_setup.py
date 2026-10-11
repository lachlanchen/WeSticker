"""Provider setup fixtures; these tests do not create a payment."""

import json
from types import SimpleNamespace as NS

import pytest
import stripe

from scripts import prepare_stripe_runtime as setup


def obj(**value):
    return stripe.StripeObject.construct_from(value, None)


@pytest.fixture
def provider(monkeypatch):
    calls = []
    portal = obj(id="portal_test", livemode=False, active=True,
                 metadata={"app": "westicker"}, features={"subscription_update": {"enabled": False}})
    endpoint = obj(id="endpoint_test", livemode=False, status="enabled",
                   url="https://example.test/api/billing/webhook", enabled_events=setup.EVENTS,
                   metadata={"app": "westicker"}, secret="test-secret")

    def create(kind, value, params, options):
        calls.append((kind, params, options))
        return value

    api = NS(v1=NS(
        accounts=NS(retrieve_current=lambda: obj(id="merchant_test")),
        billing_portal=NS(configurations=NS(
            create=lambda p, options: create("portal", portal, p, options), retrieve=lambda _: portal)),
        webhook_endpoints=NS(
            create=lambda p, options: create("webhook", endpoint, p, options),
            retrieve=lambda _: endpoint, list=lambda _: NS(auto_paging_iter=lambda: iter([]))),
    ))
    monkeypatch.setattr(setup, "provision", lambda api, mode: {"stripe_prices": {"pocket": "price_test"}})
    return api, calls, portal, endpoint


def test_preparation_preserves_other_configuration_and_keeps_sales_closed(provider, tmp_path):
    api, calls, _, _ = provider
    cfg = {"origin": "https://example.test", "native_billing": {"apple": {"purchase_enabled": False}},
           "providers": {"lazyingart": {}}, "stripe_purchase_enabled": True}
    receipt = tmp_path / "setup.json"
    prepared = setup.prepare(api, cfg, "test", receipt)
    assert prepared["native_billing"] == cfg["native_billing"]
    assert prepared["providers"] == cfg["providers"]
    assert prepared["stripe_purchase_enabled"] is False
    assert receipt.stat().st_mode & 0o077 == 0
    assert len(calls) == 2
    assert setup.prepare(api, cfg, "test", receipt) == prepared
    assert len(calls) == 2


def test_different_origin_preserves_existing_receipt(provider, tmp_path):
    api, calls, _, _ = provider
    receipt = tmp_path / "setup.json"
    receipt.write_text(json.dumps({"origin": "https://other.test", "mode": "test", "merchant": "merchant_test"}))
    before = receipt.read_bytes()
    with pytest.raises(ValueError, match="another app"):
        setup.prepare(api, {"origin": "https://example.test"}, "test", receipt)
    assert not calls and receipt.read_bytes() == before


def test_existing_webhook_without_secret_does_not_duplicate(provider, tmp_path):
    api, calls, _, endpoint = provider
    api.v1.webhook_endpoints.list = lambda _: NS(auto_paging_iter=lambda: iter([endpoint]))
    with pytest.raises(ValueError, match="saved signing secret"):
        setup.prepare(api, {"origin": "https://example.test"}, "test", tmp_path / "setup.json")
    assert [c[0] for c in calls] == ["portal"]


def test_unqualified_portal_rejected(provider, tmp_path):
    api, calls, portal, _ = provider
    portal.features.subscription_update.enabled = True
    with pytest.raises(ValueError, match="Portal ownership"):
        setup.prepare(api, {"origin": "https://example.test"}, "test", tmp_path / "setup.json")
    assert [c[0] for c in calls] == ["portal"]


@pytest.mark.parametrize("origin", ["http://example.test", "https://example.test/path", "https://user@example.test"])
def test_bad_origin_is_rejected_before_mutation(provider, tmp_path, origin):
    api, calls, _, _ = provider
    with pytest.raises(ValueError, match="canonical HTTPS"):
        setup.prepare(api, {"origin": origin}, "test", tmp_path / "setup.json")
    assert not calls
