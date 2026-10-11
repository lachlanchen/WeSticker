"""Reconcile WeSticker's own monthly catalog, without a purchase or review submission."""

import argparse
from decimal import Decimal
import json
from pathlib import Path
import time
from urllib.parse import urlencode, urlsplit

from apple_release import Apple, BUNDLE, private_write

PLANS = [
    ("pocket", "Pocket", "0.99", 3, "3 image credits monthly. Create one sticker at a time."),
    ("creator", "Creator", "9.99", 2, "40 credits monthly. Create collections and animations."),
    ("studio", "Studio", "24.99", 1, "120 credits monthly. Larger packs and upload drafts."),
]


def rows(api, path):
    values = []
    for _ in range(20):
        result = api.call(path)
        values.extend(result["data"])
        more = result.get("links", {}).get("next")
        if not more:
            return values
        parsed = urlsplit(more)
        if parsed.scheme != "https" or parsed.netloc != "api.appstoreconnect.apple.com" or not parsed.path.startswith("/v1/"):
            raise ValueError("Unexpected catalog pagination origin.")
        path = parsed.path + "?" + parsed.query
    raise ValueError("Catalog pagination exceeded the bounded app lookup.")


def select(values, predicate):
    found = [x for x in values if predicate(x)]
    if len(found) > 1:
        raise ValueError("Ambiguous provider catalog; preserve existing records.")
    return found[0] if found else None


def create(api, state, label, path, data, apply):
    if not apply:
        raise ValueError(f"Missing {label}; run with --apply to provision catalog metadata.")
    intent = state / (label + "-intent.json")
    if intent.exists():
        raise ValueError(f"Unresolved {label} intent. Inspect provider state before repeating.")
    private_write(intent, {"created": time.time(), "request": data})
    result = api.call(path, {"data": data})["data"]
    private_write(state / (label + "-receipt.json"), result)
    return result


def provision(api, state, apply=False):
    apps = api.list("apps", bundleId=BUNDLE)
    if len(apps) != 1:
        raise ValueError("Expected exactly one existing WeSticker app.")
    app = apps[0]["id"]
    group = select(rows(api, f"/v1/apps/{app}/subscriptionGroups?limit=200"),
                   lambda x: x["attributes"]["referenceName"] == "WeSticker Membership")
    if not group:
        group = create(api, state, "group", "/v1/subscriptionGroups", {
            "type": "subscriptionGroups", "attributes": {"referenceName": "WeSticker Membership"},
            "relationships": {"app": {"data": {"type": "apps", "id": app}}}}, apply)
    gid = group["id"]
    translations = rows(api, f"/v1/subscriptionGroups/{gid}/subscriptionGroupLocalizations?limit=200")
    if not select(translations, lambda x: x["attributes"]["locale"] == "en-US"):
        create(api, state, "group-en", "/v1/subscriptionGroupLocalizations", {
            "type": "subscriptionGroupLocalizations", "attributes": {"locale": "en-US", "name": "WeSticker Membership"},
            "relationships": {"subscriptionGroup": {"data": {"type": "subscriptionGroups", "id": gid}}}}, apply)
    products = rows(api, f"/v1/subscriptionGroups/{gid}/subscriptions?limit=200")
    output = {}
    for tier, name, price, level, description in PLANS:
        if len(description) > 55:
            raise ValueError("Apple subscription descriptions must fit 55 characters.")
        product = BUNDLE + "." + tier + ".monthly"
        sub = select(products, lambda x: x["attributes"]["productId"] == product)
        if not sub:
            sub = create(api, state, tier, "/v1/subscriptions", {
                "type": "subscriptions", "attributes": {"name": "WeSticker " + name,
                    "productId": product, "subscriptionPeriod": "ONE_MONTH", "groupLevel": level,
                    "familySharable": False},
                "relationships": {"group": {"data": {"type": "subscriptionGroups", "id": gid}}}}, apply)
        if sub["attributes"]["subscriptionPeriod"] != "ONE_MONTH" or sub["attributes"]["groupLevel"] != level:
            raise ValueError("Existing product differs from the approved monthly contract.")
        sid = sub["id"]
        try:
            availability = api.call(f"/v1/subscriptions/{sid}/subscriptionAvailability")["data"]
        except RuntimeError as error:
            if not str(error).startswith("Apple HTTP 404:"):
                raise
            availability = None
        if availability is None:
            create(api, state, tier + "-availability", "/v1/subscriptionAvailabilities", {
                "type": "subscriptionAvailabilities", "attributes": {"availableInNewTerritories": False},
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sid}},
                    "availableTerritories": {"data": [{"type": "territories", "id": "USA"}]}}}, apply)
        locs = rows(api, f"/v1/subscriptions/{sid}/subscriptionLocalizations?limit=200")
        if not select(locs, lambda x: x["attributes"]["locale"] == "en-US"):
            create(api, state, tier + "-en-short", "/v1/subscriptionLocalizations", {
                "type": "subscriptionLocalizations", "attributes": {"name": name, "description": description, "locale": "en-US"},
                "relationships": {"subscription": {"data": {"type": "subscriptions", "id": sid}}}}, apply)
        query = urlencode({"filter[territory]": "USA", "limit": "200"})
        prices_response = api.call(f"/v1/subscriptions/{sid}/prices?" + query + "&include=subscriptionPricePoint")
        if prices_response.get("links", {}).get("next"):
            raise ValueError("Unexpectedly many current US prices; preserve existing catalog.")
        prices = prices_response["data"]
        if not prices:
            # Price points are immutable provider records; never fabricate their IDs.
            points = rows(api, f"/v1/subscriptions/{sid}/pricePoints?" + query)
            point = select(points, lambda x: Decimal(x["attributes"]["customerPrice"]) == Decimal(price))
            if not point:
                raise ValueError("The exact approved USD price point is unavailable.")
            create(api, state, tier + "-usd-available", "/v1/subscriptionPrices", {
                "type": "subscriptionPrices", "attributes": {"preserveCurrentPrice": True},
                "relationships": {
                    "subscription": {"data": {"type": "subscriptions", "id": sid}},
                    "subscriptionPricePoint": {"data": {"type": "subscriptionPricePoints", "id": point["id"]}},
                    "territory": {"data": {"type": "territories", "id": "USA"}}}}, apply)
        else:
            included = {x["id"]: x for x in prices_response.get("included", [])
                        if x["type"] == "subscriptionPricePoints"}
            for saved in prices:
                point = included[saved["relationships"]["subscriptionPricePoint"]["data"]["id"]]
                if Decimal(point["attributes"]["customerPrice"]) != Decimal(price):
                    raise ValueError("Existing USD price differs; no price change authorized.")
        fresh = api.call(f"/v1/subscriptions/{sid}")["data"]
        output[product] = {"tier": tier, "id": sid, "state": fresh["attributes"]["state"], "usd": price}
    return {"app": app, "bundle": BUNDLE, "group": gid, "products": output,
            "purchases": 0, "review_submitted": False, "sales_enabled": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    args.state.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = provision(Apple(json.loads(args.config.expanduser().read_text())), args.state, args.apply)
    private_write(args.state / "catalog.json", result)
    print(json.dumps(result, indent=2))
