"""Merge app-specific notification configuration without enabling native purchases."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_stripe_runtime import private_json


def prepare(current, staging):
    if set(staging) != {"native_billing"}:
        raise ValueError("Native staging must contain only native_billing")
    native = staging["native_billing"]
    if not isinstance(native, dict):
        raise ValueError("Invalid native configuration")
    for provider, identity in (("apple", "bundle_id"), ("google", "package")):
        cfg = native.get(provider, {})
        if cfg.get(identity) != "art.lazying.westicker":
            raise ValueError("Native staging belongs to another app")
        if (cfg.get("purchase_enabled") is not False
                or cfg.get("purchase_user_ids") or cfg.get("sandbox_user_ids")):
            raise ValueError("Notification preparation must keep purchase/delivery pilot lists closed")
        expected = {(f"art.lazying.westicker.{tier}.monthly" if provider == "apple"
                     else f"westicker_{tier}_monthly"): tier
                    for tier in ("pocket", "creator", "studio")}
        if cfg.get("products") != expected:
            raise ValueError("Incomplete native tier catalog")
    prior = current.get("native_billing", {})
    for provider in ("apple", "google"):
        if (prior.get(provider, {}).get("purchase_enabled")
                or prior.get(provider, {}).get("purchase_user_ids")
                or prior.get(provider, {}).get("sandbox_user_ids")):
            raise ValueError("Do not replace an active native rollout with notification-only staging")
    return current | {"native_billing": native}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--native-config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {args.config.resolve(), args.native_config.resolve()}:
        raise SystemExit("Write a separate staged configuration")
    result = prepare(json.loads(args.config.read_text()), json.loads(args.native_config.read_text()))
    private_json(args.output, result)
    print(json.dumps({"prepared": True, "native_sales_enabled": False,
                      "unrelated_configuration_preserved": True}))


if __name__ == "__main__":
    main()
