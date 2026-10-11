"""API-only WeSticker test-clock lifecycle. Not browser or public-webhook proof."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time
import traceback
import uuid

import stripe

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import create_app
from server.billing import reconcile_stripe, reconcile_subscription, stripe_client, stripe_lock, verified_price
from server.store import database


def private_json(path, value):
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(value, stream, indent=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--account-file", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    evidence = {"mode": "test", "source": "Stripe API test objects + in-process app routes",
                "browser_completed_checkout": False, "browser_portal_qualified": False,
                "provider_delivered_webhook": False, "real_money": False, "cases": {}, "objects": {}, "cleanup": {}}
    report = args.output / "evidence.json"
    api = clock = sub = None
    checkout_ids = []
    run = uuid.uuid4().hex
    evidence["source_sha256"] = {name: hashlib.sha256((Path(__file__).resolve().parents[1] / name).read_bytes()).hexdigest()
                                 for name in ("server/billing.py", "server/market_billing.py", "scripts/stripe_sandbox_qa.py")}
    snapshots = []

    def record(name, value=True):
        evidence["cases"][name] = value
        private_json(report, evidence)
        print(json.dumps({"case": name, "result": value}), flush=True)

    try:
        key = args.key_file.read_text().strip()
        account = json.loads(args.account_file.read_text())
        catalog = json.loads(args.catalog.read_text())
        assert not args.key_file.stat().st_mode & 0o077, "Key file must be private"
        assert key.startswith("sk_test_") and account["mode"] == catalog["mode"] == "test"
        cfg = dict(state=str(args.output / "state"), origin="http://localhost:18642", local_accounts=True,
                   stripe_key=key, stripe_account=account["id"], stripe_mode="test",
                   stripe_webhook_secret="whsec_local_qa_" + secrets.token_hex(24),
                   stripe_prices=catalog["stripe_prices"], stripe_purchase_enabled=True)
        app = create_app(cfg)
        cfg = app.config["WESTICKER"]
        api = stripe_client(cfg)
        for ident in cfg["stripe_prices"].values():
            verified_price(cfg, api, ident)
        record("merchant_mode_existing_catalog")

        client = app.test_client()

        def post(path, body=None):
            boot = client.get("/api/bootstrap").get_json()
            return client.post(path, json=body or {}, headers={"Origin": cfg["origin"], "X-CSRF-Token": boot.get("csrf") or ""})

        registered = post("/api/auth/register", {"email": run + "@example.invalid", "password": secrets.token_urlsafe(32),
                                                "name": "WeSticker Stripe QA", "adult": True, "terms": True})
        assert registered.status_code == 200
        owner = client.get("/api/bootstrap").get_json()["user"]["id"]
        body = {"plan": "pocket", "attempt": run}
        response = post("/api/billing/subscribe", body)
        assert response.status_code == 200, "App checkout creation failed"
        assert post("/api/billing/subscribe", body).get_json() == response.get_json()
        with database(cfg) as db:
            checkout = dict(db.execute("SELECT * FROM checkouts WHERE id=?", (run,)).fetchone())
        checkout_ids.append(checkout["session"])
        evidence["objects"]["checkout"] = checkout["session"]
        session = api.v1.checkout.sessions.retrieve(checkout["session"]).to_dict()
        assert session["livemode"] is False and session["status"] == "open" and session["payment_status"] == "unpaid"
        assert session["url"].startswith("https://checkout.stripe.com/")
        assert session["amount_total"] == 99 and session["currency"] == "usd"
        assert post("/api/billing/subscribe", body | {"attempt": uuid.uuid4().hex}).status_code == 409
        record("hosted_checkout_created_retrieved_idempotent_not_paid")
        api.v1.checkout.sessions.expire(session["id"])
        assert reconcile_stripe(cfg)["errors"] == 0
        assert post("/api/billing/subscribe", body).status_code == 409
        assert client.get("/api/bootstrap").get_json()["user"]["plan"] == "free"
        record("abandoned_checkout_expired_without_access")

        clock = api.v1.test_helpers.test_clocks.create({"frozen_time": int(time.time()), "name": "WeSticker QA " + run}, options={"idempotency_key": run + "-clock"})
        evidence["objects"]["clock"] = clock.id
        private_json(report, evidence)
        clock_owner = uuid.uuid4().hex
        customer = api.v1.customers.create({"test_clock": clock.id, "metadata": {"app": "westicker", "owner": clock_owner, "qa_run": run}}, options={"idempotency_key": run + "-customer"})
        evidence["objects"]["clock_customer"] = customer.id
        with database(cfg) as db:
            db.execute("INSERT INTO users(id,name,created,consented,customer) VALUES(?,?,?,1,?)", (clock_owner, "Stripe Clock QA", time.time(), customer.id))

        def set_payment_method(method):
            pm = api.v1.payment_methods.attach(method, {"customer": customer.id})
            api.v1.customers.update(customer.id, {"invoice_settings": {"default_payment_method": pm.id}})
            return pm.id

        good_pm = set_payment_method("pm_card_visa")
        sub = api.v1.subscriptions.create({"customer": customer.id, "items": [{"price": cfg["stripe_prices"]["pocket"]}],
                                           "metadata": {"app": "westicker", "owner": clock_owner, "qa_run": run},
                                           "payment_behavior": "error_if_incomplete"}, options={"idempotency_key": run + "-subscription"})
        evidence["objects"]["subscription"] = sub.id
        private_json(report, evidence)

        def state():
            with database(cfg) as db:
                return dict(db.execute("SELECT plan,credits,expires FROM users WHERE id=?", (clock_owner,)).fetchone())

        def sync():
            frozen = api.v1.test_helpers.test_clocks.retrieve(clock.id).frozen_time
            with stripe_lock(cfg):
                reconcile_subscription(cfg, api, sub.id, now=frozen)
            actual = api.v1.subscriptions.retrieve(sub.id).to_dict(for_json=True)
            invoice = api.v1.invoices.retrieve(actual["latest_invoice"]).to_dict(for_json=True)
            snapshot = {"frozen_time": frozen, "subscription": actual, "latest_invoice": invoice, "app": state()}
            snapshot["invoice_payments"] = [p.to_dict(for_json=True) for p in api.v1.invoice_payments.list({"invoice": invoice["id"]}).auto_paging_iter()]
            snapshots.append(snapshot)
            private_json(args.output / "provider-snapshots.json", snapshots)
            return state()

        def current_sub():
            return api.v1.subscriptions.retrieve(sub.id).to_dict()

        def advance(target):
            api.v1.test_helpers.test_clocks.advance(clock.id, {"frozen_time": target})
            for _ in range(60):
                status = api.v1.test_helpers.test_clocks.retrieve(clock.id)
                if status.status == "ready":
                    return
                if status.status == "internal_failure":
                    raise RuntimeError("Stripe clock failed")
                time.sleep(2)
            raise TimeoutError("Stripe test clock did not settle")

        first = sync()
        assert first["plan"] == "pocket" and first["credits"] == 3
        first_invoice = current_sub()["latest_invoice"]
        evidence["objects"]["initial_invoice"] = first_invoice
        record("test_clock_initial_paid_invoice_and_app_grant")
        with database(cfg) as db:
            db.execute("UPDATE users SET credits=1 WHERE id=?", (clock_owner,))
        assert sync()["credits"] == 1
        record("provider_reconciliation_does_not_duplicate_credits")

        advance(int(first["expires"]) + 7200)
        renewed = sync()
        renewal_invoice = current_sub()["latest_invoice"]
        assert renewal_invoice != first_invoice and renewed["expires"] > first["expires"] and renewed["credits"] == 3
        evidence["objects"]["renewal_invoice"] = renewal_invoice
        record("test_clock_actual_monthly_renewal")

        set_payment_method("pm_card_chargeCustomerFail")
        advance(int(renewed["expires"]) + 7200)
        failed_sub = current_sub()
        failed_invoice = api.v1.invoices.retrieve(failed_sub["latest_invoice"]).to_dict()
        evidence["objects"]["failed_invoice"] = failed_invoice["id"]
        assert failed_invoice["status"] == "open" and failed_invoice["amount_paid"] == 0
        assert sync()["plan"] == "free"
        record("test_clock_failed_renewal_no_unpaid_access")

        api.v1.customers.update(customer.id, {"invoice_settings": {"default_payment_method": good_pm}})
        api.v1.invoices.pay(failed_invoice["id"], {"payment_method": good_pm}, options={"idempotency_key": run + "-recover"})
        recovered = sync()
        assert recovered["plan"] == "pocket" and recovered["credits"] == 3 and recovered["expires"] > renewed["expires"]
        record("test_clock_failed_payment_recovery")

        api.v1.subscriptions.update(sub.id, {"cancel_at_period_end": True})
        assert sync()["expires"] == recovered["expires"] and state()["plan"] == "pocket"
        record("cancellation_keeps_paid_through_access")
        payments = api.v1.invoice_payments.list({"invoice": failed_invoice["id"], "status": "paid"})
        payment = payments.data[0].to_dict()["payment"]
        refund = api.v1.refunds.create({"payment_intent": payment["payment_intent"], "metadata": {"app": "westicker", "qa_run": run}}, options={"idempotency_key": run + "-refund"})
        evidence["objects"]["test_refund"] = refund.id
        assert api.v1.charges.retrieve(refund.charge).livemode is False and refund.status == "succeeded"
        private_json(args.output / "test-refund.json", refund.to_dict(for_json=True))
        assert sync()["plan"] == "free" and state()["credits"] == 0
        assert sync()["plan"] == "free"
        record("actual_test_refund_revokes_and_stays_revoked")
        advance(int(recovered["expires"]) + 1)
        assert current_sub()["status"] == "canceled" and sync()["plan"] == "free"
        record("test_clock_canceled_expiry")
        evidence["status"] = "passed"
    except Exception as error:
        evidence["status"] = "blocked"
        evidence["error_type"] = type(error).__name__
        # Provider exception strings may contain private identifiers. Keep only
        # safe codes in evidence and stdout; inspect objects privately if needed.
        evidence["error_code"] = getattr(error, "code", None)
        frame = traceback.extract_tb(error.__traceback__)[-1]
        evidence["error_location"] = {"file": Path(frame.filename).name, "line": frame.lineno, "function": frame.name}
        print(json.dumps({"status": "blocked", "error_type": type(error).__name__, "code": getattr(error, "code", None)}), flush=True)
    finally:
        if api:
            for session_id in checkout_ids:
                try:
                    session = api.v1.checkout.sessions.retrieve(session_id)
                    if session.status == "open":
                        api.v1.checkout.sessions.expire(session_id)
                    evidence["cleanup"]["checkout_closed"] = True
                except Exception as error:
                    evidence["cleanup"]["checkout_error"] = type(error).__name__
            if clock:
                try:
                    api.v1.test_helpers.test_clocks.delete(clock.id)
                    evidence["cleanup"]["clock_and_simulation_deleted"] = True
                except Exception as error:
                    evidence["cleanup"]["clock_error"] = type(error).__name__
        private_json(report, evidence)
    print(json.dumps({"status": evidence.get("status"), "cases": len(evidence["cases"]), "evidence": str(report)}))
    return 0 if evidence.get("status") == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
