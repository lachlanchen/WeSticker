"""Create private loopback-only demo configuration without overwriting anything."""

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
folder = root / ".config"
folder.mkdir(exist_ok=True, mode=0o700)
path = folder / "local.json"
if path.exists():
    raise SystemExit("Existing local configuration preserved.")
cfg = json.loads((root / "config.example.json").read_text())
cfg.update(state=str(root / "data"), local_accounts=True)
with path.open("x") as stream:
    json.dump(cfg, stream, indent=2)
path.chmod(0o600)
print("Local demo configuration created. Third-party services remain disconnected.")
