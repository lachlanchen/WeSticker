"""Bounded periodic recovery of existing app-owned purchases, never new sales."""
import json

from .app import create_app
from .billing import reconcile_stripe


def main():
    app = create_app()
    cfg = app.config["WESTICKER"]
    results = {}
    failed = False
    for name in ("native", "stripe"):
        try:
            if name == "native":
                result = app.extensions["westicker"]["reconcile_native"](limit=25, budget_seconds=45)
                failed |= bool(result.get("failed") or result.get("missing_lookups"))
            elif cfg.get("stripe_key"):
                result = reconcile_stripe(cfg, limit=25, budget_seconds=45)
                failed |= bool(result.get("errors"))
            else:
                result = {"configured": False}
            results[name] = result
        except Exception:
            failed = True
            results[name] = {"error": "recovery_unavailable"}
    print(json.dumps(results, sort_keys=True))
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
