"""Bounded cleanup of interrupted account consent. No sign-in or ledger writes."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.app import create_app


if __name__ == "__main__":
    app = create_app()
    print(json.dumps(app.extensions["westicker_shared_account"].cleanup()))
