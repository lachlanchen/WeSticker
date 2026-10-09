"""Independent, server-verified WeSticker Stripe subscriptions. No client grants."""

import time

from flask import abort, jsonify, request
import stripe

from .store import PLANS, database
from .market_billing import apply_market_receipt, register_market_billing


def register_billing(app, cfg):
    ext = app.extensions["westicker"]

    def client():
        if not cfg.get("stripe_key") or not cfg.get("stripe_webhook_secret"):
            abort(
                503, description="Billing is not connected. You have not been charged."
            )
        return stripe.StripeClient(
            cfg["stripe_key"],
            max_network_retries=1,
            http_client=stripe.RequestsClient(timeout=25),
        )

    def plan_for_price(price):
        return next(
            (p for p in PLANS if cfg.get("stripe_prices", {}).get(p["id"]) == price),
            None,
        )

    register_market_billing(app, cfg, client)

    def cancel_for_deletion(user):
        api = client()
        subscriptions = api.v1.subscriptions.list(
            {"customer": user["customer"], "status": "all", "limit": 100}
        )
        for subscription in subscriptions.auto_paging_iter():
            value = subscription.to_dict()
            meta = value.get("metadata", {})
            if (
                meta.get("app") == "westicker"
                and meta.get("owner") == user["id"]
                and value.get("status") not in {"canceled", "incomplete_expired"}
            ):
                api.v1.subscriptions.cancel(value["id"])

    ext["cancel_for_deletion"] = cancel_for_deletion

    @app.post("/api/billing/subscribe")
    def subscribe():
        user = ext["current"]()
        body = request.get_json() or {}
        plan = body.get("plan")
        attempt = body.get("attempt")
        if (
            not isinstance(attempt, str)
            or not 16 <= len(attempt) <= 64
            or plan not in {p["id"] for p in PLANS}
        ):
            abort(400)
        price = cfg.get("stripe_prices", {}).get(plan)
        if not price:
            abort(503, description="This plan is not on sale yet.")
        api = client()
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT * FROM checkouts WHERE id=?", (attempt,)
            ).fetchone()
            if prior:
                if prior["user_id"] != user["id"] or prior["target"] != plan:
                    abort(409)
                if prior["url"]:
                    return jsonify(url=prior["url"])
            elif user["expires"] > time.time():
                abort(
                    409,
                    description="Manage your existing subscription instead of buying twice.",
                )
            else:
                native_pending = db.execute(
                    "SELECT 1 FROM native_intents WHERE user_id=? AND state IN ('prepared','pending')",
                    (user["id"],),
                ).fetchone()
                if native_pending:
                    abort(409, description="Restore the pending native purchase before starting another checkout.")
                pending = db.execute(
                    "SELECT * FROM checkouts WHERE user_id=? AND kind='subscription' AND created>? ORDER BY created DESC LIMIT 1",
                    (user["id"], time.time() - 86400),
                ).fetchone()
                if pending:
                    if pending["target"] == plan and pending["url"]:
                        return jsonify(url=pending["url"])
                    abort(
                        409,
                        description="An earlier checkout is still reserved. Resume or reconcile it before starting another.",
                    )
                db.execute(
                    "INSERT INTO checkouts VALUES(?,?,?,?,?,?,?)",
                    (
                        attempt,
                        user["id"],
                        "subscription",
                        plan,
                        None,
                        None,
                        time.time(),
                    ),
                )
        customer = user["customer"]
        if not customer:
            customer = api.v1.customers.create(
                {"metadata": {"app": "westicker", "owner": user["id"]}},
                options={"idempotency_key": "westicker-customer-" + user["id"]},
            ).id
            with database(cfg) as db:
                db.execute(
                    "UPDATE users SET customer=? WHERE id=?", (customer, user["id"])
                )
        result = api.v1.checkout.sessions.create(
            {
                "mode": "subscription",
                "customer": customer,
                "line_items": [{"price": price, "quantity": 1}],
                "client_reference_id": user["id"],
                "metadata": {
                    "app": "westicker",
                    "attempt": attempt,
                    "owner": user["id"],
                },
                "subscription_data": {
                    "metadata": {"app": "westicker", "owner": user["id"]}
                },
                "success_url": cfg["origin"] + "/?billing=return",
                "cancel_url": cfg["origin"] + "/?billing=cancelled",
                "adaptive_pricing": {"enabled": False},
                "expires_at": int(time.time()) + 1800,
            },
            options={"idempotency_key": "westicker-checkout-" + attempt},
        )
        with database(cfg) as db:
            db.execute(
                "UPDATE checkouts SET session=?,url=? WHERE id=?",
                (result.id, result.url, attempt),
            )
        return jsonify(url=result.url)

    @app.post("/api/billing/manage")
    def portal():
        user = ext["current"]()
        if not user["customer"]:
            abort(404, description="No subscription to manage yet.")
        result = client().v1.billing_portal.sessions.create(
            {"customer": user["customer"], "return_url": cfg["origin"] + "/?account=1"}
        )
        return jsonify(url=result.url)

    @app.post("/api/billing/webhook")
    def webhook():
        api = client()
        try:
            event = stripe.Webhook.construct_event(
                request.get_data(),
                request.headers.get("Stripe-Signature", ""),
                cfg["stripe_webhook_secret"],
            ).to_dict()
        except (ValueError, stripe.SignatureVerificationError):
            abort(400)
        with database(cfg) as db:
            if db.execute(
                "SELECT id FROM billing_events WHERE id=?", (event["id"],)
            ).fetchone():
                return jsonify(received=True)
        data = event["data"]["object"]
        event_type = event["type"]
        if apply_market_receipt(cfg, api, event):
            with database(cfg) as db:
                db.execute(
                    "INSERT OR IGNORE INTO billing_events VALUES(?,?)",
                    (event["id"], time.time()),
                )
            return jsonify(received=True)
        if event_type == "invoice.paid":
            invoice = api.v1.invoices.retrieve(data["id"]).to_dict()
            if invoice["status"] != "paid":
                abort(400)
            sub_id = invoice.get("subscription") or invoice.get("parent", {}).get(
                "subscription_details", {}
            ).get("subscription")
            if sub_id:
                sub = api.v1.subscriptions.retrieve(sub_id).to_dict()
                if sub.get("metadata", {}).get("app") == "westicker":
                    owner = sub["metadata"]["owner"]
                    line = sub["items"]["data"][0]
                    plan = plan_for_price(line["price"]["id"])
                    if not plan or len(sub["items"]["data"]) != 1:
                        abort(400)
                    expires = line.get(
                        "current_period_end", sub.get("current_period_end", 0)
                    )
                    with database(cfg) as db:
                        db.execute("BEGIN IMMEDIATE")
                        if db.execute(
                            "SELECT id FROM billing_events WHERE id=?", (event["id"],)
                        ).fetchone():
                            return jsonify(received=True)
                        user = db.execute(
                            "SELECT * FROM users WHERE id=? AND customer=?",
                            (owner, sub["customer"]),
                        ).fetchone()
                        if (
                            user
                            and sub.get("status") in {"active", "trialing"}
                            and sub.get("latest_invoice") == invoice["id"]
                            and expires > user["expires"]
                        ):
                            # A paid billing period grants its quota once, not for duplicate event IDs.
                            receipt = "invoice:" + invoice["id"]
                            if not db.execute(
                                "SELECT id FROM billing_events WHERE id=?", (receipt,)
                            ).fetchone():
                                db.execute(
                                    "UPDATE users SET plan=?,expires=?,credits=?,subscription_id=? WHERE id=?",
                                    (
                                        plan["id"],
                                        expires,
                                        plan["credits"],
                                        sub["id"],
                                        owner,
                                    ),
                                )
                                db.execute(
                                    "INSERT INTO billing_events VALUES(?,?)",
                                    (receipt, time.time()),
                                )
                        db.execute(
                            "INSERT INTO billing_events VALUES(?,?)",
                            (event["id"], time.time()),
                        )
                    return jsonify(received=True)
        elif event_type == "customer.subscription.deleted":
            sub = api.v1.subscriptions.retrieve(data["id"]).to_dict()
            if (
                sub.get("metadata", {}).get("app") == "westicker"
                and sub["status"] == "canceled"
            ):
                with database(cfg) as db:
                    db.execute(
                        "UPDATE users SET plan='free',expires=0,credits=0,subscription_id=NULL WHERE id=? AND customer=? AND subscription_id=?",
                        (sub["metadata"].get("owner"), sub["customer"], sub["id"]),
                    )
        with database(cfg) as db:
            db.execute(
                "INSERT OR IGNORE INTO billing_events VALUES(?,?)",
                (event["id"], time.time()),
            )
        return jsonify(received=True)

    @app.post("/api/creator/onboard")
    def onboard():
        user = ext["current"]()
        if not cfg.get("creator_sales_enabled"):
            abort(503, description="Creator payouts are not open yet.")
        api = client()
        account = user["connect_id"]
        if not account:
            result = api.v1.accounts.create(
                {
                    "type": "express",
                    "capabilities": {"transfers": {"requested": True}},
                    "metadata": {"app": "westicker", "owner": user["id"]},
                },
                options={"idempotency_key": "westicker-creator-" + user["id"]},
            )
            account = result.id
            with database(cfg) as db:
                db.execute(
                    "UPDATE users SET connect_id=? WHERE id=?", (account, user["id"])
                )
        link = api.v1.account_links.create(
            {
                "account": account,
                "refresh_url": cfg["origin"] + "/?payout=retry",
                "return_url": cfg["origin"] + "/?payout=return",
                "type": "account_onboarding",
            }
        )
        return jsonify(url=link.url)

    @app.post("/api/creator/status")
    def creator_status():
        user = ext["current"]()
        if not user["connect_id"]:
            return jsonify(ready=False)
        account = client().v1.accounts.retrieve(user["connect_id"]).to_dict()
        ready = (
            account.get("payouts_enabled") is True
            and account.get("details_submitted") is True
            and account.get("capabilities", {}).get("transfers") == "active"
        )
        with database(cfg) as db:
            db.execute(
                "UPDATE users SET payout_ready=? WHERE id=?", (int(ready), user["id"])
            )
        return jsonify(ready=ready)
