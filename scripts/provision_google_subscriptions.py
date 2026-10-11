"""Provision WeSticker monthly plans; activation is explicit, purchases unsupported."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.native_billing import BUNDLE, google_session
from server.store import PLANS

BASE = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/" + BUNDLE


class ProviderError(RuntimeError):
    def __init__(self, status):
        self.status = status
        super().__init__(f"Google catalog HTTP {status}; inspect private provider state before retrying")


class Google:
    def __init__(self, cfg):
        self.session = google_session(cfg)

    def call(self, path, *, method="GET", data=None, params=None):
        if not (path == "/pricing:convertRegionPrices" or path == "/subscriptions"
                or path.startswith("/subscriptions/westicker_")):
            raise ValueError("Unexpected catalog path")
        if ":" in path and path != "/pricing:convertRegionPrices":
            if method != "POST" or not re.fullmatch(
                    r"/subscriptions/westicker_(pocket|creator|studio)_monthly/basePlans/monthly:activate", path):
                raise ValueError("Only exact WeSticker monthly-plan activation is supported")
        response = self.session.request(method, BASE + path, json=data, params=params,
                                        timeout=30, allow_redirects=False)
        if response.status_code not in (200, 201, 204):
            raise ProviderError(response.status_code)
        return response.json() if response.content else {}


def money(cents):
    return {"currencyCode": "USD", "units": str(cents // 100), "nanos": cents % 100 * 10_000_000}


def draft(plan):
    return {"packageName": BUNDLE, "productId": f"westicker_{plan['id']}_monthly",
            "listings": [{"languageCode": "en-US", "title": "WeSticker " + plan["name"],
                          "benefits": plan["features"]}],
            "taxAndComplianceSettings": {"eeaWithdrawalRightType": "WITHDRAWAL_RIGHT_SERVICE"},
            "basePlans": [{"basePlanId": "monthly", "autoRenewingBasePlanType": {
                "billingPeriodDuration": "P1M", "gracePeriodDuration": "P7D",
                "resubscribeState": "RESUBSCRIBE_STATE_INACTIVE"},
                "regionalConfigs": [{"regionCode": "US", "newSubscriberAvailability": True,
                                     "price": money(plan["cents"])}]}]}


def validate(product, plan, *, allow_active=False):
    if (product.get("packageName") != BUNDLE
            or product.get("productId") != draft(plan)["productId"]):
        raise ValueError("Wrong app or product")
    bases = product.get("basePlans", [])
    if len(bases) != 1 or bases[0].get("basePlanId") != "monthly":
        raise ValueError("Unexpected base plans; preserve existing catalog")
    base = bases[0]
    if base.get("autoRenewingBasePlanType", {}).get("billingPeriodDuration") != "P1M":
        raise ValueError("Existing duration differs from approved monthly plan")
    if base.get("state") not in ({"DRAFT", "ACTIVE"} if allow_active else {"DRAFT"}):
        raise ValueError("Existing base plan is not a closed draft; inspect before explicit activation")
    available = [r for r in base.get("regionalConfigs", []) if r.get("newSubscriberAvailability")]
    if len(available) != 1 or available[0].get("regionCode") != "US":
        raise ValueError("Unexpected availability; no territory expansion authorized")
    price = available[0].get("price", {})
    if (price.get("currencyCode") != "USD" or
            int(price.get("units", 0)) * 1_000_000_000 + int(price.get("nanos", 0))
            != plan["cents"] * 10_000_000):
        raise ValueError("Existing USD price differs; no price migration authorized")
    if base.get("otherRegionsConfig", {}).get("newSubscriberAvailability"):
        raise ValueError("Automatic territory expansion is not authorized")
    return {"product": product["productId"], "tier": plan["id"], "base_plan": "monthly",
            "state": base["state"], "usd_cents": plan["cents"], "period": "P1M"}


def private_write(path, value, *, exclusive=False):
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        json.dump(value, output, indent=2)
        output.write("\n")


def finish_plan(api, state, product, plan, *, apply, activate):
    result = validate(product, plan, allow_active=activate or not apply)
    if not activate or result["state"] == "ACTIVE":
        return result
    if not apply:
        raise ValueError("Activation requires --apply and --activate")
    intent = state / (plan["id"] + "-activation-intent.json")
    if intent.exists():
        raise ValueError("Unresolved activation intent; reconcile provider state before another write")
    path = "/subscriptions/" + product["productId"]
    private_write(intent, {"created": time.time(), "product": product,
                           "action": "activate-US-monthly-only"}, exclusive=True)
    saved = api.call(path + "/basePlans/monthly:activate", method="POST", data={})
    private_write(state / (plan["id"] + "-activation-receipt.json"), saved)
    fresh = validate(api.call(path), plan, allow_active=True)
    if fresh["state"] != "ACTIVE":
        raise ValueError("Activation is not confirmed; reconcile before retrying")
    return fresh


def provision(api, state, *, apply=False, regions_version=None, activate=False):
    if regions_version is not None and not re.fullmatch(r"20[0-9]{2}/[0-9]{2}", regions_version):
        raise ValueError("Use the version displayed in Google's supported-locations table")
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    results = []
    version = regions_version
    for plan in PLANS:
        desired = draft(plan)
        path = "/subscriptions/" + desired["productId"]
        try:
            current = api.call(path)
        except ProviderError as error:
            if error.status != 404:
                raise
            current = None
        if current and current.get("basePlans"):
            results.append(finish_plan(api, state, current, plan, apply=apply, activate=activate))
            continue
        if current and (current.get("packageName") != BUNDLE or current.get("productId") != desired["productId"]):
            raise ValueError("Unexpected existing app/product")
        if not apply:
            raise ValueError("Missing draft/base plan; use --apply for catalog provisioning only")
        intent = state / (plan["id"] + "-intent.json")
        if intent.exists():
            raise ValueError("Unresolved catalog intent; reconcile provider state before another write")
        if version is None:
            conversion = api.call("/pricing:convertRegionPrices", method="POST", data={"price": money(99)})
            version = conversion["regionVersion"]["version"]
        params = {"regionsVersion.version": version}
        if current:
            # Preserve unrelated tax/listing metadata; only add the absent base plan.
            data = dict(current, basePlans=desired["basePlans"])
            method = "PATCH"
            params["updateMask"] = "basePlans"
            target = path
        else:
            data, method, target = desired, "POST", "/subscriptions"
            params["productId"] = desired["productId"]
        private_write(intent, {"created": time.time(), "method": method, "path": target,
                               "request": data, "params": params}, exclusive=True)
        saved = api.call(target, method=method, data=data, params=params)
        private_write(state / (plan["id"] + "-receipt.json"), saved)
        fresh = api.call(path)
        results.append(finish_plan(api, state, fresh, plan, apply=apply, activate=activate))
    receipt = {"package": BUNDLE, "products": results, "observed": time.time(),
               "backend_sales_changed": False, "purchases": 0, "review_changed": False}
    private_write(state / "catalog.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--activate", action="store_true", help="Explicitly activate only validated US monthly plans; never changes backend sales")
    parser.add_argument("--regions-version", help="Observed official region-table version; avoids account-wide conversion permission")
    args = parser.parse_args()
    api = Google(json.loads(args.config.read_text()))
    try:
        print(json.dumps(provision(api, args.state, apply=args.apply,
                                   regions_version=args.regions_version, activate=args.activate), indent=2))
    finally:
        api.session.close()


if __name__ == "__main__":
    main()
