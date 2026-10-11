"""Deterministic fixtures, not Stripe sandbox or real-money payment evidence."""

from copy import deepcopy
import hashlib
import hmac
import json
import time
from types import SimpleNamespace as NS

import pytest
import stripe

from server.app import create_app
from server import billing
from server.store import database
from test_app import call, signup


class Obj(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as error:
            raise AttributeError(key) from error

    def to_dict(self):
        return deepcopy(dict(self))


def page(items):
    return NS(data=[Obj(i) for i in items], auto_paging_iter=lambda: iter(Obj(i) for i in items))


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    cfg = dict(state=str(tmp_path), origin="http://localhost:18642", local_accounts=True,
               stripe_key="sk_test_fixture", stripe_webhook_secret="whsec_fixture",
               stripe_mode="test", stripe_account="acct_fixture", stripe_purchase_enabled=True,
               stripe_prices={"pocket": "price_pocket"})
    app = create_app(cfg)
    cfg = app.config["WESTICKER"]
    app.config["TESTING"] = True
    client = app.test_client()
    signup(client)
    owner = client.get("/api/bootstrap").get_json()["user"]["id"]
    now = int(time.time())
    customer = Obj(id="cus_owned", livemode=False, metadata={"app": "westicker", "owner": owner})
    price = Obj(id="price_pocket", livemode=False, active=True, product="prod_owned", currency="usd",
                unit_amount=99, metadata={"app": "westicker", "tier": "pocket"},
                recurring={"interval": "month", "interval_count": 1})
    sub = Obj(id="sub_owned", livemode=False, customer=customer.id, status="active",
              metadata={"app": "westicker", "owner": owner}, latest_invoice="in_first",
              items={"data": [{"price": {"id": price.id}, "quantity": 1}]})
    invoice = Obj(id="in_first", livemode=False, subscription=sub.id, customer=customer.id,
                  status="paid", amount_paid=99, currency="usd", billing_reason="subscription_create",
                  lines={"data": [{"price": {"id": price.id}, "quantity": 1, "amount": 99,
                                   "currency": "usd", "period": {"start": now - 60, "end": now + 3600}}]})
    invoices = {invoice.id: invoice}
    charges = {"ch_" + invoice.id: Obj(id="ch_" + invoice.id, livemode=False, customer=customer.id,
                                      amount=99, amount_refunded=0, currency="usd", paid=True)}
    sessions, requests = {}, []

    def create_session(params, options):
        requests.append((deepcopy(params), deepcopy(options)))
        value = Obj(params | dict(id="cs_owned", livemode=False, status="open", url="https://checkout.stripe.test/owned"))
        sessions[value.id] = value
        return value

    api = NS(v1=NS(
        accounts=NS(retrieve_current=lambda: Obj(id=cfg["stripe_account"])),
        customers=NS(retrieve=lambda _: customer, create=lambda *a, **k: customer),
        prices=NS(retrieve=lambda _: price),
        products=NS(retrieve=lambda _: Obj(id="prod_owned", active=True, livemode=False, metadata={"app": "westicker"})),
        subscriptions=NS(retrieve=lambda _: sub, list=lambda _: page([sub]) if getattr(api, "include_sub", True) else page([])),
        invoices=NS(retrieve=lambda ident: invoices[ident], list=lambda _: page([i for i in invoices.values() if i["status"] == "paid"][-1:])),
        invoice_payments=NS(list=lambda p: page([dict(id="inpay_" + p["invoice"], livemode=False, invoice=p["invoice"],
                                                   payment={"type": "payment_intent", "payment_intent": "pi_" + p["invoice"]})])),
        payment_intents=NS(retrieve=lambda ident: Obj(id=ident, livemode=False, status="succeeded", customer=customer.id,
                                                     latest_charge="ch_" + ident[3:])),
        charges=NS(retrieve=lambda ident: charges[ident]),
        checkout=NS(sessions=NS(create=create_session, retrieve=lambda ident: sessions[ident], list=lambda _: page(list(sessions.values())))),
    ))
    monkeypatch.setattr(stripe, "StripeClient", lambda *a, **k: api)
    with database(cfg) as db:
        db.execute("UPDATE users SET customer=? WHERE id=?", (customer.id, owner))
    return NS(cfg=cfg, app=app, client=client, owner=owner, api=api, now=now, sub=sub,
              invoice=invoice, invoices=invoices, charges=charges, customer=customer, price=price,
              requests=requests, sessions=sessions)


def user(s):
    with database(s.cfg) as db:
        return dict(db.execute("SELECT * FROM users WHERE id=?", (s.owner,)).fetchone())


def notify(s, kind="invoice.paid", ident="in_first", event_id="evt_one", **extra):
    event = dict(id=event_id, type=kind, livemode=False, data={"object": {"id": ident}}) | extra
    raw = json.dumps(event).encode()
    stamp = str(int(time.time()))
    signature = hmac.new(s.cfg["stripe_webhook_secret"].encode(), stamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
    return s.client.post("/api/billing/webhook", data=raw, headers={"Stripe-Signature": f"t={stamp},v1={signature}"})


def test_paid_once_across_duplicate_events_and_reconciliation(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    assert user(s)["credits"] == 3
    with database(s.cfg) as db:
        db.execute("UPDATE users SET credits=1 WHERE id=?", (s.owner,))
    assert notify(s).status_code == 200
    assert notify(s, event_id="evt_same_invoice").status_code == 200
    assert billing.reconcile_stripe(s.cfg)["errors"] == 0
    assert user(s)["credits"] == 1


def test_bad_signature_never_enters_inbox(sandbox):
    s = sandbox
    assert s.client.post("/api/billing/webhook", data=b"{}", headers={"Stripe-Signature": "bad"}).status_code == 400
    with database(s.cfg) as db:
        assert db.execute("SELECT count(*) FROM stripe_inbox").fetchone()[0] == 0


def test_status_is_owner_scoped_and_never_exposes_checkout_urls(sandbox):
    s = sandbox
    with database(s.cfg) as db:
        db.execute("INSERT INTO checkouts VALUES(?,?,?,?,?,?,?)", (
            "owned-attempt", s.owner, "subscription", "pocket", "cs_private",
            "https://checkout.stripe.com/private", time.time()))
        db.execute("INSERT INTO stripe_orders VALUES(?,?,?,?,?,?)", (
            "owned-attempt", s.owner, "price_pocket", "{}", "reserved", time.time()))
    result = s.client.get("/api/billing/status")
    assert result.status_code == 200
    assert result.json["attempts"] == [{"attempt": "owned-attempt", "plan": "pocket", "state": "reserved"}]
    assert "cs_private" not in result.text and "stripe.com" not in result.text
    assert s.app.test_client().get("/api/billing/status").status_code == 401


@pytest.mark.parametrize("extra", [{"livemode": True}, {"account": "acct_foreign"}, {"context": "acct_foreign"}])
def test_signed_wrong_mode_or_merchant_rejected(sandbox, extra):
    assert notify(sandbox, **extra).status_code == 400
    assert user(sandbox)["credits"] == 0


def test_failure_is_durable_and_periodic_retry_recovers(sandbox):
    s = sandbox
    retrieve = s.api.v1.invoices.retrieve
    s.api.v1.invoices.retrieve = lambda _: (_ for _ in ()).throw(stripe.APIConnectionError("fixture network failure"))
    assert notify(s).status_code == 503
    with database(s.cfg) as db:
        row = db.execute("SELECT * FROM stripe_inbox").fetchone()
        assert row["state"] == "pending" and row["attempts"] == 1 and row["error"] == "APIConnectionError"
    s.api.v1.invoices.retrieve = retrieve
    assert billing.reconcile_stripe(s.cfg)["errors"] == 0
    assert user(s)["credits"] == 3
    with database(s.cfg) as db:
        assert db.execute("SELECT state FROM stripe_inbox").fetchone()[0] == "done"


def test_crash_lease_is_recoverable(sandbox):
    s = sandbox
    with database(s.cfg) as db:
        db.execute("INSERT INTO stripe_inbox(id,merchant,mode,kind,object_id,state,lease,lease_until,created,updated) VALUES(?,?,?,?,?,'processing','dead',?,?,?)",
                   ("evt_crash", "acct_fixture", "test", "invoice.paid", "in_first", time.time()-1, time.time(), time.time()))
    assert billing.reconcile_stripe(s.cfg)["events"] == 1
    assert user(s)["credits"] == 3


def test_failed_renewal_does_not_extend_paid_period_then_recovers(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    renewal = Obj(deepcopy(s.invoice))
    renewal.update(id="in_renewal", status="open", amount_paid=0, billing_reason="subscription_cycle")
    renewal["lines"]["data"][0]["period"] = {"start": s.now+3600, "end": s.now+7200}
    s.invoices[renewal.id] = renewal
    s.sub.update(latest_invoice=renewal.id, status="past_due")
    assert notify(s, "invoice.payment_failed", renewal.id, "evt_failed").status_code == 200
    assert user(s)["expires"] == s.now + 3600
    billing.reconcile_subscription(s.cfg, s.api, s.sub.id, now=s.now+3601)
    assert user(s)["plan"] == "free"
    renewal.update(status="paid", amount_paid=99)
    s.sub["status"] = "active"
    s.charges["ch_" + renewal.id] = Obj(s.charges["ch_in_first"] | {"id": "ch_" + renewal.id})
    billing.reconcile_subscription(s.cfg, s.api, s.sub.id, now=s.now+3602)
    assert user(s)["credits"] == 3 and user(s)["expires"] == s.now+7200


def test_cancel_retains_paid_through_then_expires(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    s.sub["status"] = "canceled"
    assert notify(s, "customer.subscription.deleted", s.sub.id, "evt_cancel").status_code == 200
    assert user(s)["plan"] == "pocket"
    billing.reconcile_subscription(s.cfg, s.api, s.sub.id, now=s.now+3601)
    assert user(s)["plan"] == "free" and user(s)["credits"] == 0


@pytest.mark.parametrize("before", [True, False])
def test_full_refund_cannot_be_undone_by_reordered_paid_event(sandbox, before):
    s = sandbox
    if not before:
        assert notify(s).status_code == 200
    s.charges["ch_in_first"]["amount_refunded"] = 99
    assert notify(s, "charge.refunded", "ch_in_first", "evt_refund").status_code == 200
    assert notify(s, event_id="evt_late_paid").status_code == 200
    assert user(s)["plan"] == "free" and user(s)["credits"] == 0


def test_partial_refund_keeps_period_without_minting(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    with database(s.cfg) as db:
        db.execute("UPDATE users SET credits=1 WHERE id=?", (s.owner,))
    s.charges["ch_in_first"]["amount_refunded"] = 50
    assert notify(s, "charge.refunded", "ch_in_first", "evt_refund").status_code == 200
    assert user(s)["plan"] == "pocket" and user(s)["credits"] == 1


def test_disputed_charge_holds_access(sandbox):
    s = sandbox
    s.charges["ch_in_first"]["disputed"] = True
    assert notify(s).status_code == 200
    assert user(s)["plan"] == "free"


@pytest.mark.parametrize("change", ["customer", "owner", "price", "mode", "merchant", "quantity", "currency"])
def test_binding_failures_never_grant(sandbox, change):
    s = sandbox
    if change == "customer":
        s.invoice["customer"] = "cus_other"
    elif change == "owner":
        s.sub["metadata"]["owner"] = "other-owner"
    elif change == "price":
        s.price["metadata"]["app"] = "otherapp"
    elif change == "mode":
        s.sub["livemode"] = True
    elif change == "merchant":
        s.api.v1.accounts.retrieve_current = lambda: Obj(id="acct_foreign")
    elif change == "quantity":
        s.sub["items"]["data"][0]["quantity"] = 2
    elif change == "currency":
        s.invoice["currency"] = "eur"
    assert notify(s).status_code == 503
    assert user(s)["credits"] == 0


def test_database_cannot_switch_merchant(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    s.cfg["stripe_account"] = "acct_changed"
    assert notify(s, event_id="evt_changed").status_code == 503


@pytest.mark.parametrize("change", ["zero", "proration"])
def test_zero_paid_and_proration_do_not_grant(sandbox, change):
    s = sandbox
    if change == "zero":
        s.invoice["amount_paid"] = 0
    else:
        s.invoice["billing_reason"] = "subscription_update"
    assert notify(s).status_code == 200
    assert user(s)["credits"] == 0


def test_stale_stripe_receipt_does_not_overwrite_native(sandbox):
    s = sandbox
    with database(s.cfg) as db:
        db.execute("UPDATE users SET plan='studio',credits=100,expires=?,subscription_id='apple:current' WHERE id=?", (s.now+7000, s.owner))
    assert notify(s).status_code == 200
    assert user(s)["plan"] == "studio" and user(s)["credits"] == 100


def test_checkout_gate_and_no_purchase_restore(sandbox):
    s = sandbox
    s.cfg["stripe_purchase_enabled"] = False
    assert call(s.client, "/api/billing/subscribe", {"plan": "pocket", "attempt": "attempt-fixture-0001"}).status_code == 503
    assert call(s.client, "/api/billing/restore").status_code == 200
    assert user(s)["plan"] == "pocket" and not s.requests


def test_checkout_timeout_reuses_identical_durable_parameters(sandbox):
    s = sandbox
    s.api.include_sub = False
    create = s.api.v1.checkout.sessions.create
    attempts = []

    def uncertain(params, options):
        attempts.append((deepcopy(params), deepcopy(options)))
        if len(attempts) == 1:
            raise stripe.APIConnectionError("fixture uncertain create")
        return create(params, options)

    s.api.v1.checkout.sessions.create = uncertain
    body = {"plan": "pocket", "attempt": "attempt-fixture-0001"}
    assert call(s.client, "/api/billing/subscribe", body).status_code == 503
    assert call(s.client, "/api/billing/subscribe", body).status_code == 200
    assert attempts[0] == attempts[1]
    assert attempts[0][0]["payment_method_types"] == ["card"]
    assert "WeSticker Pocket: 3 credits each month." in attempts[0][0]["custom_text"]["submit"]["message"]
    assert call(s.client, "/api/billing/subscribe", body).status_code == 200
    assert len(attempts) == 2


def test_uncertain_checkout_after_idempotency_window_never_recreates(sandbox):
    s = sandbox
    s.api.include_sub = False
    def uncertain(*a, **k):
        raise stripe.APIConnectionError("fixture unknown outcome")
    s.api.v1.checkout.sessions.create = uncertain
    body = {"plan": "pocket", "attempt": "attempt-fixture-0001"}
    assert call(s.client, "/api/billing/subscribe", body).status_code == 503
    with database(s.cfg) as db:
        db.execute("UPDATE stripe_orders SET created=?", (time.time()-86400,))
    s.api.v1.checkout.sessions.create = lambda *a, **k: pytest.fail("Stale operation recreated")
    assert call(s.client, "/api/billing/subscribe", body).status_code == 409
    assert call(s.client, "/api/billing/subscribe", body | {"attempt": "attempt-fixture-0002"}).status_code == 409


def test_modern_invoice_shape(sandbox):
    s = sandbox
    s.invoice["parent"] = {"subscription_details": {"subscription": s.invoice.pop("subscription")}}
    line = s.invoice["lines"]["data"][0]
    line["pricing"] = {"price_details": {"price": line.pop("price")["id"]}}
    line["parent"] = {"subscription_item_details": {"proration": False}}
    assert notify(s).status_code == 200
    assert user(s)["credits"] == 3


def test_event_id_collision_cannot_change_object(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    assert notify(s, ident="in_other").status_code == 400


def test_busy_worker_still_persists_notification(sandbox):
    s = sandbox
    with billing.stripe_lock(s.cfg):
        assert notify(s).status_code == 503
    with database(s.cfg) as db:
        assert db.execute("SELECT state FROM stripe_inbox").fetchone()[0] == "pending"
    assert billing.reconcile_stripe(s.cfg)["events"] == 1
    assert user(s)["credits"] == 3


def test_worker_limit_rotates_customers_across_restarts_and_failures(sandbox, monkeypatch):
    s = sandbox
    with database(s.cfg) as db:
        db.execute("UPDATE users SET customer=NULL WHERE id=?", (s.owner,))
        for index in range(6):
            db.execute("INSERT INTO users(id,name,created,customer) VALUES(?,?,?,?)",
                       (f"owner-{index}", "Fixture", time.time(), f"cus-{index}"))
    seen = []

    def visit(cfg, api, owner, customer, **kwargs):
        seen.append(owner)
        if owner == "owner-0":
            raise ValueError("Poison fixture")
        return True

    monkeypatch.setattr(billing, "reconcile_customer", visit)
    for _ in range(3):
        result = billing.reconcile_stripe(s.cfg, limit=2)
        assert result["checked"] == 2
    assert seen == [f"owner-{index}" for index in range(6)]
    billing.reconcile_stripe(s.cfg, limit=1)
    assert seen[-1] == "owner-0"


def test_worker_rotates_poison_events_and_alternates_customer_lane(sandbox, monkeypatch):
    s = sandbox
    with database(s.cfg) as db:
        for index in range(3):
            db.execute("INSERT INTO stripe_inbox(id,merchant,mode,kind,object_id,created,updated) VALUES(?,?,?,?,?,?,?)",
                       (f"evt-{index}", "acct_fixture", "test", "invoice.paid", "in_first", 1, 1))
    seen = []

    def failed(cfg, event_id, **kwargs):
        seen.append(event_id)
        raise ValueError("Poison fixture")

    def customer(*args, **kwargs):
        seen.append("customer")
        return True

    monkeypatch.setattr(billing, "process_inbox", failed)
    monkeypatch.setattr(billing, "reconcile_customer", customer)
    for _ in range(6):
        assert billing.reconcile_stripe(s.cfg, limit=1)["checked"] == 1
    assert seen == ["evt-0", "customer", "evt-1", "customer", "evt-2", "customer"]


def test_worker_budget_checks_before_provider_calls_and_rotates(sandbox, monkeypatch):
    s = sandbox
    clock = [100.0]
    monkeypatch.setattr(billing.time, "monotonic", lambda: clock[0])
    calls = []

    def retrieve(_):
        calls.append("customer")
        clock[0] += 2
        return s.customer

    s.api.v1.customers.retrieve = retrieve
    s.api.v1.checkout.sessions.list = lambda _: pytest.fail("Provider call started after budget")
    result = billing.reconcile_stripe(s.cfg, budget_seconds=1)
    assert calls == ["customer"]
    assert result["checked"] == 1 and result["budget_exhausted"]


def test_worker_pages_resume_and_do_not_autopage(sandbox, monkeypatch):
    s = sandbox
    visits, pages = [], []
    subscriptions = [dict(s.sub, id=f"sub-{index}") for index in range(12)]

    def listing(params):
        assert params["limit"] == 5
        pages.append(params.get("starting_after"))
        start = next((i+1 for i, item in enumerate(subscriptions) if item["id"] == params.get("starting_after")), 0)
        result = page(subscriptions[start:start+5])
        result.has_more = start + 5 < len(subscriptions)
        result.auto_paging_iter = lambda: pytest.fail("Unbounded provider page")
        return result

    s.api.v1.subscriptions.list = listing
    monkeypatch.setattr(billing, "reconcile_subscription", lambda cfg, api, ident, **kw: visits.append(ident))
    for _ in range(3):
        assert billing.reconcile_stripe(s.cfg, limit=1)["errors"] == 0
    assert visits == [item["id"] for item in subscriptions]
    assert pages == [None, "sub-4", "sub-9"]
    billing.reconcile_stripe(s.cfg, limit=1)
    assert pages[-1] is None


def test_bounded_refund_scan_stays_pending_until_error_free_sweep(sandbox, monkeypatch):
    s = sandbox
    subscriptions = [dict(s.sub, id=f"sub-{index}") for index in range(6)]

    def listing(params):
        start = 5 if params.get("starting_after") == "sub-4" else 0
        result = page(subscriptions[start:start+5])
        result.has_more = start == 0
        return result

    def failed(cfg, api, ident, **kwargs):
        if ident == "sub-0":
            raise ValueError("Temporary fixture failure")

    s.api.v1.subscriptions.list = listing
    monkeypatch.setattr(billing, "reconcile_subscription", failed)
    with database(s.cfg) as db:
        db.execute("INSERT INTO stripe_inbox(id,merchant,mode,kind,object_id,created,updated) VALUES(?,?,?,?,?,?,?)",
                   ("evt-refund", "acct_fixture", "test", "charge.refunded", "ch_in_first", 1, 1))
    with pytest.raises(ValueError):
        billing.process_inbox(s.cfg, "evt-refund", deadline=time.monotonic()+45)
    with pytest.raises(billing._ScanPending):
        billing.process_inbox(s.cfg, "evt-refund", deadline=time.monotonic()+45)
    monkeypatch.setattr(billing, "reconcile_subscription", lambda *args, **kwargs: True)
    with pytest.raises(billing._ScanPending):
        billing.process_inbox(s.cfg, "evt-refund", deadline=time.monotonic()+45)
    billing.process_inbox(s.cfg, "evt-refund", deadline=time.monotonic()+45)
    with database(s.cfg) as db:
        assert db.execute("SELECT state FROM stripe_inbox WHERE id='evt-refund'").fetchone()[0] == "done"


def test_reconcile_batch_lock_prevents_cursor_races(sandbox):
    with billing.stripe_lock(sandbox.cfg, "stripe-reconcile.lock"):
        result = billing.reconcile_stripe(sandbox.cfg)
    assert result["busy"] == 1 and result["checked"] == 0


def test_crash_after_delivery_before_ack_cannot_mint_again(sandbox, monkeypatch):
    s = sandbox
    process = billing.process_stripe_event
    def delivered_then_crashed(*args):
        process(*args)
        raise stripe.APIConnectionError("fixture crash after committed grant")
    monkeypatch.setattr(billing, "process_stripe_event", delivered_then_crashed)
    assert notify(s).status_code == 503
    with database(s.cfg) as db:
        db.execute("UPDATE users SET credits=1 WHERE id=?", (s.owner,))
    monkeypatch.setattr(billing, "process_stripe_event", process)
    assert notify(s).status_code == 200
    assert user(s)["credits"] == 1


def test_subscription_owner_cannot_be_rebound(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    other = "another-local-owner"
    with database(s.cfg) as db:
        db.execute("UPDATE users SET customer=NULL WHERE id=?", (s.owner,))
        db.execute("INSERT INTO users(id,name,created,customer) VALUES(?,?,?,?)", (other, "Other", time.time(), s.customer.id))
    s.customer["metadata"]["owner"] = other
    s.sub["metadata"]["owner"] = other
    with pytest.raises(ValueError):
        billing.reconcile_subscription(s.cfg, s.api, s.sub.id)
    with database(s.cfg) as db:
        assert db.execute("SELECT credits FROM users WHERE id=?", (other,)).fetchone()[0] == 0


def test_legacy_invoice_marker_does_not_refill_spent_credits(sandbox):
    s = sandbox
    with database(s.cfg) as db:
        db.execute("INSERT INTO billing_events VALUES(?,?)", ("invoice:in_first", time.time()))
        db.execute("UPDATE users SET plan='pocket',expires=?,credits=1,subscription_id=? WHERE id=?", (s.now+3600, s.sub.id, s.owner))
    assert notify(s).status_code == 200
    assert user(s)["credits"] == 1


def test_stale_refund_does_not_revoke_current_renewal(sandbox):
    s = sandbox
    assert notify(s).status_code == 200
    renewal = Obj(deepcopy(dict(s.invoice)))
    renewal.update(id="in_new", billing_reason="subscription_cycle")
    renewal["lines"]["data"][0]["period"] = {"start": s.now-1, "end": s.now+7200}
    s.invoices[renewal.id] = renewal
    s.sub["latest_invoice"] = renewal.id
    s.charges["ch_in_new"] = Obj(s.charges["ch_in_first"] | {"id": "ch_in_new"})
    assert notify(s, ident=renewal.id, event_id="evt_new").status_code == 200
    with database(s.cfg) as db:
        db.execute("UPDATE users SET credits=1 WHERE id=?", (s.owner,))
    s.charges["ch_in_first"]["amount_refunded"] = 99
    assert notify(s, "charge.refunded", "ch_in_first", "evt_old_refund").status_code == 200
    assert user(s)["expires"] == s.now+7200 and user(s)["credits"] == 1


def test_checkout_price_drift_never_changes_reserved_request(sandbox):
    s = sandbox
    s.api.include_sub = False
    body = {"plan": "pocket", "attempt": "attempt-fixture-0001"}
    assert call(s.client, "/api/billing/subscribe", body).status_code == 200
    s.cfg["stripe_prices"]["pocket"] = "price_replaced"
    assert call(s.client, "/api/billing/subscribe", body).status_code == 409
    assert len(s.requests) == 1


def test_native_switch_expires_confirmed_open_checkout(sandbox):
    s = sandbox
    s.api.include_sub = False
    body = {"plan": "pocket", "attempt": "attempt-fixture-0001"}
    assert call(s.client, "/api/billing/subscribe", body).status_code == 200
    def expire(ident, **kwargs):
        s.sessions[ident]["status"] = "expired"
    s.api.v1.checkout.sessions.expire = expire
    with s.app.test_request_context():
        assert s.app.extensions["westicker"]["close_stripe_checkouts"](user(s))
    assert s.sessions["cs_owned"]["status"] == "expired"
    assert call(s.client, "/api/billing/subscribe", body).status_code == 409


def test_native_switch_blocks_uncertain_checkout(sandbox):
    from werkzeug.exceptions import Conflict
    s = sandbox
    s.api.include_sub = False
    def uncertain(*a, **k):
        raise stripe.APIConnectionError("fixture unknown outcome")
    s.api.v1.checkout.sessions.create = uncertain
    assert call(s.client, "/api/billing/subscribe", {"plan": "pocket", "attempt": "attempt-fixture-0001"}).status_code == 503
    with s.app.test_request_context(), pytest.raises(Conflict):
        s.app.extensions["westicker"]["close_stripe_checkouts"](user(s))


def test_no_cash_or_trial_cannot_mint_paid_credits(sandbox):
    s = sandbox
    s.api.v1.invoice_payments.list = lambda _: page([])
    assert notify(s).status_code == 503
    assert user(s)["credits"] == 0


def test_portal_does_not_use_unqualified_merchant_default(sandbox):
    s = sandbox
    assert call(s.client, "/api/billing/manage").status_code == 503


def test_restore_does_not_need_new_purchase_or_webhook_secret(sandbox):
    s = sandbox
    s.cfg["stripe_purchase_enabled"] = False
    del s.cfg["stripe_webhook_secret"]
    assert call(s.client, "/api/billing/restore").status_code == 200
    assert user(s)["plan"] == "pocket"


def test_deletion_closes_open_checkout_without_touching_another_app(sandbox):
    s = sandbox
    s.api.include_sub = False
    body = {"plan": "pocket", "attempt": "attempt-fixture-0001"}
    assert call(s.client, "/api/billing/subscribe", body).status_code == 200
    foreign = Obj(deepcopy(dict(s.sessions["cs_owned"])))
    foreign.update(id="cs_foreign", metadata={"app": "anotherapp", "owner": s.owner})
    s.sessions[foreign.id] = foreign
    def expire(ident, **kwargs):
        s.sessions[ident]["status"] = "expired"
    s.api.v1.checkout.sessions.expire = expire
    with s.app.test_request_context():
        s.app.extensions["westicker"]["cancel_for_deletion"](user(s))
    assert s.sessions["cs_owned"]["status"] == "expired"
    assert s.sessions["cs_foreign"]["status"] == "open"


def test_legacy_expired_checkout_can_be_closed_for_native_switch(sandbox):
    s = sandbox
    s.api.include_sub = False
    body = {"plan": "pocket", "attempt": "attempt-fixture-0001"}
    assert call(s.client, "/api/billing/subscribe", body).status_code == 200
    with database(s.cfg) as db:
        db.execute("DELETE FROM stripe_orders")
    s.sessions["cs_owned"]["status"] = "expired"
    with s.app.test_request_context():
        assert s.app.extensions["westicker"]["close_stripe_checkouts"](user(s))
    assert call(s.client, "/api/billing/subscribe", body).status_code == 409
