"""Provision only WeSticker products/prices; never create or charge a customer."""

import argparse
import json
import os
from pathlib import Path
import sys

import stripe

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.store import PLANS


def provision(api, mode):
    product_id = "prod_westicker_creator_v1"
    try:
        product = api.v1.products.retrieve(product_id)
    except stripe.InvalidRequestError as error:
        if error.code != "resource_missing":
            raise
        product = api.v1.products.create(
            {"id": product_id, "name": "WeSticker Creator",
             "metadata": {"app": "westicker", "catalog": "202610-v1"}},
            options={"idempotency_key": product_id},
        )
    if (product.metadata.to_dict().get("app") != "westicker" or not product.active
            or product.livemode != (mode == "live")):
        raise ValueError("Product ownership/mode mismatch")
    prices = {}
    for plan in PLANS:
        lookup = "westicker_" + plan["id"] + "_monthly_202610_v1"
        found = api.v1.prices.list({"lookup_keys": [lookup], "limit": 2})
        if found.has_more or len(found.data) > 1:
            raise ValueError("Ambiguous existing price")
        price = found.data[0] if found.data else api.v1.prices.create(
            {"product": product_id, "currency": "usd", "unit_amount": plan["cents"],
             "recurring": {"interval": "month"}, "lookup_key": lookup,
             "nickname": "WeSticker " + plan["name"] + " monthly",
             "metadata": {"app": "westicker", "tier": plan["id"]}},
            options={"idempotency_key": lookup},
        )
        if (price.product != product_id or price.unit_amount != plan["cents"]
                or price.currency != "usd" or price.recurring.interval != "month"
                or price.recurring.interval_count != 1 or not price.active
                or price.livemode != (mode == "live")
                or price.metadata.to_dict().get("app") != "westicker"):
            raise ValueError("Price differs; preserved existing provider record")
        prices[plan["id"]] = price.id
    return {"mode": mode, "product": product_id, "stripe_prices": prices,
            "charges_created": 0, "subscriptions_created": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--mode", choices=["test", "live"], default="test")
    parser.add_argument("--expected-account", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.key_file.stat().st_mode & 0o077:
        raise SystemExit("Key file must be private (0600)")
    key = args.key_file.read_text().strip()
    if not key.startswith("sk_" + args.mode + "_"):
        raise SystemExit("Key mode mismatch")
    api = stripe.StripeClient(key, http_client=stripe.RequestsClient(timeout=30), max_network_retries=1)
    account = api.v1.accounts.retrieve_current()
    if account.id != args.expected_account:
        raise SystemExit("Unexpected Stripe account")
    result = provision(api, args.mode)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(args.output, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        json.dump(result, output, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
