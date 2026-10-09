"""Delete expired private references only; never touch generated candidates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
from server.store import settings, database

cfg = settings()
root = Path(cfg["state"])
with database(cfg) as db:
    rows = db.execute(
        "SELECT a.* FROM assets a WHERE kind='reference' AND expires<? AND NOT EXISTS (SELECT 1 FROM jobs j WHERE j.user_id=a.user_id AND j.state IN ('queued','running','uncertain'))",
        (time.time(),),
    ).fetchall()
    for row in rows:
        path = root / row["path"]
        if path.is_relative_to(root / "assets"):
            path.unlink(missing_ok=True)
        db.execute("DELETE FROM assets WHERE id=?", (row["id"],))
print(f"Expired references deleted: {len(rows)}. Generated outputs unchanged.")
