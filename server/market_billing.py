"""Separate creator purchases; only verified paid sessions grant downloads."""

import time
from flask import abort, jsonify, request
from .store import database


def apply_market_receipt(cfg, api, event):
    event_type = event["type"]
    if event_type not in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.expired",
        "charge.refunded",
    }:
        return False
    obj = event["data"]["object"]
    if event_type == "charge.refunded":
        charge = api.v1.charges.retrieve(obj["id"]).to_dict()
        if charge.get("metadata", {}).get("app") != "westicker" or charge.get("metadata", {}).get("kind") != "pack":
            return False
        if charge.get("livemode") is not (cfg.get("stripe_mode") == "live"):
            raise ValueError("Marketplace refund mode mismatch")
        if charge.get("amount_refunded", 0) < charge.get("amount", 1):
            return True
        with database(cfg) as db:
            db.execute(
                "DELETE FROM entitlements WHERE source=?",
                ("stripe-pi:" + str(charge.get("payment_intent")),),
            )
        return True
    checkout = api.v1.checkout.sessions.retrieve(obj["id"]).to_dict()
    if checkout.get("livemode") is not (cfg.get("stripe_mode") == "live"):
        raise ValueError("Marketplace session mode mismatch")
    if checkout.get("metadata", {}).get("app") != "westicker":
        return True
    if event_type == "checkout.session.expired":
        if checkout.get("status") == "expired":
            with database(cfg) as db:
                db.execute("DELETE FROM checkouts WHERE session=?", (checkout["id"],))
        return True
    metadata = checkout["metadata"]
    if metadata.get("kind") != "pack":
        return False
    if checkout.get("payment_status") != "paid":
        return True
    intent = api.v1.payment_intents.retrieve(checkout["payment_intent"]).to_dict()
    charge = api.v1.charges.retrieve(intent["latest_charge"]).to_dict()
    if (intent.get("status") != "succeeded" or charge.get("livemode") is not (cfg.get("stripe_mode") == "live")
            or charge.get("customer") != checkout.get("customer")):
        raise ValueError("Marketplace payment mismatch")
    if charge.get("disputed") or charge.get("amount_refunded", 0) >= charge.get("amount", 1):
        with database(cfg) as db:
            db.execute("DELETE FROM entitlements WHERE source=?", ("stripe-pi:" + checkout["payment_intent"],))
        return True
    with database(cfg) as db:
        db.execute("BEGIN IMMEDIATE")
        order = db.execute(
            "SELECT * FROM checkouts WHERE session=? AND kind='pack'", (checkout["id"],)
        ).fetchone()
        if not order:
            raise ValueError("Paid session has no matching WeSticker order.")
        pack = db.execute(
            "SELECT * FROM packs WHERE id=?", (order["target"],)
        ).fetchone()
        user = db.execute(
            "SELECT * FROM users WHERE id=?", (order["user_id"],)
        ).fetchone()
        if not pack or not user:
            raise ValueError("Order needs operator reconciliation.")
        if (
            metadata.get("owner") != order["user_id"]
            or metadata.get("pack") != order["target"]
            or checkout.get("client_reference_id") != order["user_id"]
            or checkout.get("customer") != user["customer"]
            or checkout.get("currency") != "usd"
            or checkout.get("amount_total") != pack["price"]
        ):
            raise ValueError("Paid session did not match its immutable order.")
        db.execute(
            "INSERT OR IGNORE INTO entitlements VALUES(?,?,?)",
            (user["id"], pack["id"], "stripe-pi:" + checkout["payment_intent"]),
        )
    return True


def register_market_billing(app, cfg, client):
    ext = app.extensions["westicker"]

    @app.post("/api/market/<id>/buy")
    def buy(id):
        user = ext["current"]()
        body = request.get_json() or {}
        attempt = body.get("attempt")
        if not cfg.get("creator_sales_enabled"):
            abort(503, description="Creator sales are not open yet.")
        if not isinstance(attempt, str) or not 16 <= len(attempt) <= 64:
            abort(400)
        api = client()
        with database(cfg) as db:
            pack = db.execute(
                "SELECT p.*,u.connect_id,u.payout_ready FROM packs p JOIN users u ON p.user_id=u.id WHERE p.id=? AND p.status='listed'",
                (id,),
            ).fetchone()
            if not pack:
                abort(404)
            if (
                pack["user_id"] == user["id"]
                or db.execute(
                    "SELECT user_id FROM entitlements WHERE user_id=? AND pack_id=?",
                    (user["id"], id),
                ).fetchone()
            ):
                return jsonify(download=f"/api/market/{id}/download")
            if not pack["payout_ready"] or not pack["connect_id"]:
                abort(409, description="Creator payouts need attention.")
        account = api.v1.accounts.retrieve(pack["connect_id"]).to_dict()
        if (
            not account.get("payouts_enabled")
            or account.get("capabilities", {}).get("transfers") != "active"
        ):
            abort(409)
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT * FROM checkouts WHERE id=?", (attempt,)
            ).fetchone()
            if prior:
                if (
                    prior["user_id"] != user["id"]
                    or prior["target"] != id
                    or prior["kind"] != "pack"
                ):
                    abort(409)
                if prior["url"]:
                    return jsonify(url=prior["url"])
            else:
                pending = db.execute(
                    "SELECT * FROM checkouts WHERE user_id=? AND kind='pack' AND target=? AND created>?",
                    (user["id"], id, time.time() - 86400),
                ).fetchone()
                if pending:
                    if pending["url"]:
                        return jsonify(url=pending["url"])
                    abort(
                        409,
                        description="An existing purchase needs reconciliation. Nothing new was charged.",
                    )
                db.execute(
                    "INSERT INTO checkouts VALUES(?,?,?,?,?,?,?)",
                    (attempt, user["id"], "pack", id, None, None, time.time()),
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
        metadata = {
            "app": "westicker",
            "kind": "pack",
            "owner": user["id"],
            "pack": id,
            "attempt": attempt,
        }
        result = api.v1.checkout.sessions.create(
            {
                "mode": "payment",
                "customer": customer,
                "client_reference_id": user["id"],
                "line_items": [
                    {
                        "quantity": 1,
                        "price_data": {
                            "currency": "usd",
                            "unit_amount": pack["price"],
                            "product_data": {
                                "name": pack["title"],
                                "metadata": {"app": "westicker", "pack": id},
                            },
                        },
                    }
                ],
                "metadata": metadata,
                "payment_intent_data": {
                    "metadata": metadata,
                    "application_fee_amount": round(pack["price"] * 0.15),
                    "transfer_data": {"destination": pack["connect_id"]},
                },
                "success_url": cfg["origin"] + "/?purchase=return",
                "cancel_url": cfg["origin"] + "/?purchase=cancelled",
                "expires_at": int(time.time()) + 1800,
                "adaptive_pricing": {"enabled": False},
            },
            options={"idempotency_key": "westicker-pack-" + attempt},
        )
        with database(cfg) as db:
            db.execute(
                "UPDATE checkouts SET session=?,url=? WHERE id=?",
                (result.id, result.url, attempt),
            )
        return jsonify(url=result.url)
