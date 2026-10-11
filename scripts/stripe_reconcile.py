"""Read provider truth and drain durable Stripe notifications; never open sales."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.billing import reconcile_stripe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    try:
        cfg = json.loads(args.config.read_text())
        result = reconcile_stripe(cfg)
        print(json.dumps(result))
        return 1 if result["errors"] else 0
    except Exception as error:
        print(json.dumps({"error": type(error).__name__, "action": "Check private configuration and pending inbox; do not create a replacement purchase."}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
