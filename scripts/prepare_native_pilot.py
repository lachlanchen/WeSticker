"""Stage an exact-account native test pilot without replacing other app settings."""

import argparse
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.prepare_stripe_runtime import private_json


PILOT_FIELDS = {"purchase_enabled", "accept_sandbox", "purchase_user_ids", "sandbox_user_ids"}


def prepare(current, candidate, provider, user_id):
    if provider not in {"apple", "google"} or not re.fullmatch(r"[a-f0-9]{32}", user_id):
        raise ValueError("Choose one native provider and an existing app account ID")
    if set(candidate) != {"native_billing"}:
        raise ValueError("Pilot candidate must contain only native_billing")
    native = current.get("native_billing", {})
    before = native.get(provider, {})
    proposed = candidate["native_billing"].get(provider, {})
    identity = "bundle_id" if provider == "apple" else "package"
    if before.get(identity) != "art.lazying.westicker":
        raise ValueError("The current native configuration is not WeSticker")
    if ({k: v for k, v in before.items() if k not in PILOT_FIELDS}
            != {k: v for k, v in proposed.items() if k not in PILOT_FIELDS}):
        raise ValueError("Pilot may not change credentials, catalog or notification settings")
    if (proposed.get("purchase_enabled") is not True or proposed.get("accept_sandbox") is not True
            or proposed.get("purchase_user_ids") != [user_id]
            or proposed.get("sandbox_user_ids") != [user_id]):
        raise ValueError("Pilot must be restricted to exactly the verified app account")
    if before.get("purchase_enabled") and before.get("purchase_user_ids") != [user_id]:
        raise ValueError("Do not replace an existing native rollout")
    if before.get("purchase_user_ids") not in (None, [], [user_id]):
        raise ValueError("Another purchase pilot already exists")
    retained = before.get("sandbox_user_ids", [])
    if not isinstance(retained, list) or any(not isinstance(x, str) for x in retained):
        raise ValueError("Invalid existing sandbox delivery audience")
    # Keep prior test lineage eligible for renewal/recovery while only this owner
    # can start a new purchase. The other provider is never overwritten.
    chosen = before | {key: proposed[key] for key in PILOT_FIELDS}
    chosen["sandbox_user_ids"] = list(dict.fromkeys([*retained, user_id]))
    return current | {"native_billing": native | {provider: chosen}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--pilot-config", type=Path, required=True)
    parser.add_argument("--provider", choices=["apple", "google"], required=True)
    parser.add_argument("--user-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve() in {args.config.resolve(), args.pilot_config.resolve()}:
        raise SystemExit("Write a separate staged configuration")
    result = prepare(json.loads(args.config.read_text()), json.loads(args.pilot_config.read_text()),
                     args.provider, args.user_id)
    private_json(args.output, result)
    print(json.dumps({"prepared": True, "provider": args.provider,
                      "purchase_audience": 1, "unrelated_configuration_preserved": True}))


if __name__ == "__main__":
    main()
