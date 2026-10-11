"""Prepare app-owned Stripe catalog, Portal and webhook; keep new sales closed."""

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

import stripe

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.provision_stripe import provision

EVENTS = [
    "checkout.session.completed", "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed", "checkout.session.expired",
    "customer.subscription.created", "customer.subscription.updated",
    "customer.subscription.deleted", "invoice.paid", "invoice.payment_failed",
    "invoice.payment_action_required", "invoice.voided", "invoice.marked_uncollectible",
    "charge.refunded", "refund.created", "refund.updated", "refund.failed",
    "charge.dispute.created", "charge.dispute.updated", "charge.dispute.closed",
]


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stage = path.with_name(path.name + ".stage")
    fd = os.open(stage, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stage, path)


def prepare(api, cfg, mode, receipt_path):
    origin = cfg["origin"].rstrip("/")
    url = urlsplit(origin)
    if url.scheme != "https" or url.path or url.query or url.fragment or url.username:
        raise ValueError("Use the app's canonical HTTPS origin")
    endpoint_url = origin + "/api/billing/webhook"
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    identity = {"origin": origin, "mode": mode, "merchant": api.v1.accounts.retrieve_current().id}
    if receipt and any(receipt.get(k) != v for k, v in identity.items()):
        raise ValueError("Existing preparation belongs to another app origin/mode/merchant")
    receipt.update(identity)
    catalog = provision(api, mode)
    receipt["catalog"] = catalog
    private_json(receipt_path, receipt)
    if not receipt.get("portal"):
        portal = api.v1.billing_portal.configurations.create({
            "business_profile": {"headline": "WeSticker billing",
                "privacy_policy_url": origin + "/privacy.html", "terms_of_service_url": origin + "/terms.html"},
            "features": {
                "invoice_history": {"enabled": True},
                "payment_method_update": {"enabled": True},
                "subscription_cancel": {"enabled": True, "mode": "at_period_end", "proration_behavior": "none"},
                "subscription_update": {"enabled": False},
                "customer_update": {"enabled": False},
            },
            "metadata": {"app": "westicker", "configuration": "subscriptions-v1"},
        }, options={"idempotency_key": "westicker-portal-" + mode + "-v1"})
        receipt["portal"] = portal.id
        private_json(receipt_path, receipt)
    portal = api.v1.billing_portal.configurations.retrieve(receipt["portal"])
    if (portal.livemode != (mode == "live") or not portal.active
            or portal.metadata.to_dict().get("app") != "westicker"
            or portal.features.subscription_update.enabled):
        raise ValueError("Portal ownership or features differ")
    if not receipt.get("endpoint"):
        existing = [e for e in api.v1.webhook_endpoints.list({"limit": 100}).auto_paging_iter()
                    if e.url == endpoint_url]
        if existing:
            raise ValueError("Existing endpoint needs its saved signing secret; no duplicate created")
        endpoint = api.v1.webhook_endpoints.create({
            "url": endpoint_url, "enabled_events": EVENTS,
            "description": "WeSticker subscriptions",
            "metadata": {"app": "westicker", "configuration": "subscriptions-v1"},
        }, options={"idempotency_key": "westicker-webhook-" + mode + "-v1"})
        receipt.update(endpoint=endpoint.id, signing_secret=endpoint.secret)
        private_json(receipt_path, receipt)
    endpoint = api.v1.webhook_endpoints.retrieve(receipt["endpoint"])
    if (endpoint.livemode != (mode == "live") or endpoint.url != endpoint_url
            or endpoint.status != "enabled" or endpoint.metadata.to_dict().get("app") != "westicker"
            or set(endpoint.enabled_events) != set(EVENTS) or not receipt.get("signing_secret")):
        raise ValueError("Webhook ownership, events or signing secret differ")
    return cfg | {
        "stripe_mode": mode, "stripe_account": identity["merchant"],
        "stripe_prices": catalog["stripe_prices"], "stripe_portal_configuration": receipt["portal"],
        "stripe_webhook_secret": receipt["signing_secret"], "stripe_purchase_enabled": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--account-file", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["test", "live"], required=True)
    args = parser.parse_args()
    if args.output.resolve() == args.config.resolve():
        raise SystemExit("Stage a separate configuration, then activate after verification")
    key = os.environ.get("WESTICKER_STRIPE_KEY", "")
    if not key.startswith("sk_" + args.mode + "_"):
        raise SystemExit("Private environment key missing or mode mismatch")
    api = stripe.StripeClient(key, http_client=stripe.RequestsClient(timeout=30), max_network_retries=1)
    expected = json.loads(args.account_file.read_text())["id"]
    if api.v1.accounts.retrieve_current().id != expected:
        raise SystemExit("Unexpected merchant")
    cfg = prepare(api, json.loads(args.config.read_text()), args.mode, args.receipt)
    private_json(args.output, cfg | {"stripe_key": key})
    print(json.dumps({"prepared": True, "mode": args.mode, "sales_enabled": False,
                      "prices": 3, "charges_created": 0, "subscriptions_created": 0}))


if __name__ == "__main__":
    main()
