"""Operator-only listing decisions. No public administrator endpoint."""

import argparse
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.store import audit, database, settings
from server.market import listing_dir

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("pack")
parser.add_argument("decision", choices=["approve", "reject", "hide"])
parser.add_argument("--reason", required=True)
parser.add_argument("--rights-checked", action="store_true")
args = parser.parse_args()
cfg = settings()
with database(cfg) as db:
    db.execute("BEGIN IMMEDIATE")
    pack = db.execute("SELECT * FROM packs WHERE id=?", (args.pack,)).fetchone()
    if not pack:
        raise SystemExit("Pack not found.")
    if args.decision == "approve":
        if (
            not args.rights_checked
            or pack["status"] != "moderation"
            or not (listing_dir(cfg, args.pack) / "pack.zip").is_file()
        ):
            raise SystemExit(
                "Review the exact exported artwork and rights before approval."
            )
        status = "listed"
    else:
        status = "rejected" if args.decision == "reject" else "hidden"
    db.execute(
        "UPDATE packs SET status=?,updated=? WHERE id=?",
        (status, time.time(), args.pack),
    )
    audit(
        db,
        "operator",
        "listing_" + args.decision,
        {"pack": args.pack, "reason": args.reason},
    )
print(status)
