import base64
import hashlib
import hmac
import io
import json
import time
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import requests
from PIL import Image
import stripe

from server.app import create_app
from server.store import database
from server.worker import work_once
from test_app import ORIGIN, call, signup, draft
from test_stripe_lifecycle import sandbox as stripe_contract


@pytest.fixture
def services(tmp_path):
    cfg = {
        "state": str(tmp_path),
        "origin": ORIGIN,
        "local_accounts": True,
        "stripe_key": "sk_test_fixture_not_real",
        "stripe_webhook_secret": "whsec_fixture_not_real",
        "stripe_prices": {"pocket": "price_pocket", "creator": "price_creator"},
        "stripe_mode": "test",
        "stripe_account": "acct_fixture",
        "stripe_purchase_enabled": True,
        "creator_sales_enabled": True,
        "wechat_worker_enabled": True,
    }
    app = create_app(cfg)
    app.config["TESTING"] = True
    client = app.test_client()
    signup(client)
    return app, app.config["WESTICKER"], client


def plan(cfg, client, name="studio", credits=120):
    id = client.get("/api/bootstrap").get_json()["user"]["id"]
    with database(cfg) as db:
        db.execute(
            "UPDATE users SET plan=?,credits=?,expires=?,payout_ready=1,connect_id=? WHERE id=?",
            (name, credits, time.time() + 86400, "acct_fixture", id),
        )
    return id


def reviewed(cfg, client):
    id, _ = draft(client)
    assert (
        call(
            client,
            f"/api/packs/{id}/generate",
            {"kind": "photo", "attempt": "make-review-pack-1234", "consent": True},
        ).status_code
        == 202
    )
    work_once(cfg)
    items = client.get("/api/workspace").get_json()["packs"][0]["items"]
    for item in items:
        item["approved"] = True
    assert (
        call(client, f"/api/packs/{id}", {"items": items}, method="PATCH").status_code
        == 200
    )
    return id


def test_listing_freezes_reviewed_exports(services):
    app, cfg, c = services
    plan(cfg, c)
    id = reviewed(cfg, c)
    assert call(c, f"/api/packs/{id}/listing", {"rights": True}).status_code == 400
    assert (
        call(
            c,
            f"/api/packs/{id}/listing",
            {"rights": True, "public_consent": True, "price": 99},
        ).status_code
        == 200
    )
    assert c.get("/api/market").get_json()["packs"] == []
    assert c.get(f"/api/market/{id}/preview/1.png").status_code == 404
    with database(cfg) as db:
        db.execute("UPDATE packs SET status='listed' WHERE id=?", (id,))
    public = app.test_client()
    listing = public.get("/api/market").get_json()["packs"][0]
    assert "items" not in listing and "refs" not in listing
    assert public.get(listing["preview"]).status_code == 200
    assert public.get(f"/api/market/{id}/download").status_code == 401
    assert c.get(f"/api/market/{id}/download").status_code == 200
    assert call(c, f"/api/packs/{id}", {"items": []}, method="PATCH").status_code == 409


def test_wechat_ticket_is_private_idempotent_and_draft_only(services):
    app, cfg, c = services
    owner = plan(cfg, c)
    id = reviewed(cfg, c)
    body = {
        "consent": True,
        "draft_only": True,
        "copyright": "Test Creator",
        "description": "My original daily greetings.",
    }
    r = call(c, f"/api/packs/{id}/wechat", body)
    assert r.status_code == 202, r.get_json()
    ticket = r.get_json()["id"]
    repeat = call(c, f"/api/packs/{id}/wechat", body)
    assert repeat.get_json()["id"] == ticket
    manifest = json.loads(
        (Path(cfg["state"]) / "wechat" / owner / ticket / "manifest.json").read_text()
    )
    assert manifest["mode"] == "draft_only" and len(manifest["stickers"]) == 8
    assert c.get("/api/wechat/" + ticket).get_json()["state"] == "awaiting_browser"
    other = app.test_client()
    signup(other, "other@example.test")
    assert other.get("/api/wechat/" + ticket).status_code == 404


def test_ai_single_credit_moderation_and_ambiguity(services, monkeypatch):
    app, cfg, c = services
    cfg["image_api_key"] = "fixture-not-real"
    cfg["image_generation_enabled"] = True
    plan(cfg, c, "pocket", 3)
    id, _ = draft(c)
    item = c.get("/api/workspace").get_json()["packs"][0]["items"][0]["id"]
    body = {
        "kind": "ai",
        "items": [item],
        "attempt": "ai-one-expression-123",
        "consent": True,
    }
    assert call(c, f"/api/packs/{id}/generate", body).status_code == 202
    assert c.get("/api/bootstrap").get_json()["user"]["credits"] == 2

    def blocked(*args, **kwargs):
        return NS(
            raise_for_status=lambda: None, json=lambda: {"results": [{"flagged": True}]}
        )

    monkeypatch.setattr("server.worker.requests.post", blocked)
    assert work_once(cfg)
    assert c.get("/api/bootstrap").get_json()["user"]["credits"] == 3
    assert (
        call(
            c, f"/api/packs/{id}/generate", body | {"attempt": "ai-two-expression-123"}
        ).status_code
        == 202
    )
    calls = []

    def uncertain(url, **kwargs):
        calls.append(url)
        if url.endswith("/moderations"):
            return NS(
                raise_for_status=lambda: None,
                json=lambda: {"results": [{"flagged": False}]},
            )
        raise requests.Timeout("Synthetic provider timeout")

    monkeypatch.setattr("server.worker.requests.post", uncertain)
    work_once(cfg)
    assert calls[-1].endswith("/images/edits")
    assert c.get("/api/workspace").get_json()["jobs"][0]["state"] == "uncertain"
    assert c.get("/api/bootstrap").get_json()["user"]["credits"] == 2
    assert (
        call(
            c,
            f"/api/packs/{id}/generate",
            body | {"attempt": "ai-three-expression-123"},
        ).status_code
        == 409
    )
    assert not work_once(cfg)


def test_ai_result_updates_selected_only(services, monkeypatch):
    _, cfg, c = services
    cfg["image_api_key"] = "fixture-not-real"
    cfg["image_generation_enabled"] = True
    plan(cfg, c, "pocket", 3)
    id, _ = draft(c)
    item = c.get("/api/workspace").get_json()["packs"][0]["items"][1]["id"]
    image = io.BytesIO()
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(image, "PNG")

    def result(url, **kw):
        return NS(
            raise_for_status=lambda: None,
            json=lambda: (
                {"results": [{"flagged": False}]}
                if url.endswith("/moderations")
                else {
                    "data": [{"b64_json": base64.b64encode(image.getvalue()).decode()}]
                }
            ),
        )

    monkeypatch.setattr("server.worker.requests.post", result)
    call(
        c,
        f"/api/packs/{id}/generate",
        {
            "kind": "ai",
            "items": [item],
            "attempt": "ai-success-test-1234",
            "consent": True,
        },
    )
    work_once(cfg)
    items = c.get("/api/workspace").get_json()["packs"][0]["items"]
    assert len([x for x in items if x["asset"]]) == 1
    assert items[1]["asset"] and not items[1]["approved"]


class Obj(dict):
    def to_dict(self):
        return dict(self)

    def __getattr__(self, name):
        return self[name]


def event(client, cfg, payload):
    payload = {"livemode": False} | payload
    raw = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    signature = hmac.new(
        cfg["stripe_webhook_secret"].encode(),
        stamp.encode() + b"." + raw,
        hashlib.sha256,
    ).hexdigest()
    return client.post(
        "/api/billing/webhook",
        data=raw,
        headers={
            "Stripe-Signature": f"t={stamp},v1={signature}",
            "Content-Type": "application/json",
        },
    )


def test_checkout_idempotency_and_signed_invoice(stripe_contract):
    s = stripe_contract
    cfg, c, owner = s.cfg, s.client, s.owner
    s.api.include_sub = False
    body = {"plan": "pocket", "attempt": "checkout-unique-1234"}
    first = call(c, "/api/billing/subscribe", body)
    assert first.status_code == 200
    assert call(c, "/api/billing/subscribe", body).get_json() == first.get_json()
    assert (
        call(
            c, "/api/billing/subscribe", body | {"attempt": "different-attempt-1234"}
        ).status_code
        == 409
    )
    assert len(s.requests) == 1
    assert (
        call(
            c,
            "/api/billing/subscribe",
            {"plan": "creator", "attempt": "different-plan-1234"},
        ).status_code
        == 503
    )
    payload = {
        "id": "evt_fixture",
        "type": "invoice.paid",
        "data": {"object": {"id": s.invoice.id}},
    }
    assert (
        c.post(
            "/api/billing/webhook", json=payload, headers={"Stripe-Signature": "bad"}
        ).status_code
        == 400
    )
    assert event(c, cfg, payload).status_code == 200
    assert c.get("/api/bootstrap").get_json()["user"]["plan"] == "pocket"
    with database(cfg) as db:
        db.execute("UPDATE users SET credits=1 WHERE id=?", (owner,))
    assert event(c, cfg, payload | {"id": "evt_duplicate_invoice"}).status_code == 200
    assert c.get("/api/bootstrap").get_json()["user"]["credits"] == 1


def test_market_receipt_not_success_url_grants_access(services, monkeypatch):
    app, cfg, seller = services
    plan(cfg, seller)
    id = reviewed(cfg, seller)
    call(
        seller,
        f"/api/packs/{id}/listing",
        {"rights": True, "public_consent": True, "price": 99},
    )
    with database(cfg) as db:
        db.execute("UPDATE packs SET status='listed' WHERE id=?", (id,))
    buyer = app.test_client()
    signup(buyer, "buyer@example.test")
    owner = buyer.get("/api/bootstrap").get_json()["user"]["id"]
    checkout = Obj(
        id="cs_market",
        livemode=False,
        mode="payment",
        metadata={"app": "westicker", "kind": "pack", "owner": owner, "pack": id},
        client_reference_id=owner,
        customer="cus_buyer",
        currency="usd",
        amount_total=99,
        payment_intent="pi_market",
        payment_status="paid",
    )
    with database(cfg) as db:
        db.execute("UPDATE users SET customer=? WHERE id=?", ("cus_buyer", owner))
        db.execute(
            "INSERT INTO checkouts VALUES(?,?,?,?,?,?,?)",
            (
                "market-test-order-123",
                owner,
                "pack",
                id,
                "cs_market",
                "https://example.invalid",
                time.time(),
            ),
        )
    charge = Obj(id="ch_market", livemode=False, customer="cus_buyer", paid=True,
                 amount=99, amount_refunded=0, currency="usd", payment_intent="pi_market",
                 metadata={"app": "westicker", "kind": "pack", "owner": owner})
    api = NS(
        v1=NS(
            accounts=NS(retrieve_current=lambda: Obj(id="acct_fixture")),
            customers=NS(retrieve=lambda _: Obj(id="cus_buyer", livemode=False, metadata={"app": "westicker", "owner": owner})),
            checkout=NS(sessions=NS(retrieve=lambda _: checkout, list=lambda _: NS(auto_paging_iter=lambda: iter([])))),
            subscriptions=NS(list=lambda _: NS(auto_paging_iter=lambda: iter([]))),
            payment_intents=NS(retrieve=lambda _: Obj(id="pi_market", status="succeeded", latest_charge="ch_market")),
            charges=NS(retrieve=lambda _: charge),
        )
    )
    monkeypatch.setattr(stripe, "StripeClient", lambda *a, **k: api)
    assert buyer.get(f"/api/market/{id}/download").status_code == 402
    payload = {
        "id": "evt_market",
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_market"}},
    }
    assert event(buyer, cfg, payload).status_code == 200
    assert buyer.get(f"/api/market/{id}/download").status_code == 200
    charge["amount_refunded"] = 99
    assert (
        event(
            buyer,
            cfg,
            {
                "id": "evt_refund",
                "type": "charge.refunded",
                "data": {"object": {"id": "ch_market"}},
            },
        ).status_code
        == 200
    )
    assert buyer.get(f"/api/market/{id}/download").status_code == 402
