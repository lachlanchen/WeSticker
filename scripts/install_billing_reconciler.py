"""Install bounded purchase recovery for this app; never start a purchase."""

import argparse
import os
from pathlib import Path
import subprocess


def unit_text(root, config):
    for path in (root, config):
        if any(c in str(path) for c in ('\n', '\r', '"', '%', '\\')):
            raise ValueError("Unsupported systemd path")
    return f'''[Unit]
Description=WeSticker existing-purchase reconciliation
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory="{root}/.runtime/creator-current"
Environment="WESTICKER_CONFIG={config}"
ExecStart="{root}/.venv/bin/python" -m server.reconcile
TimeoutStartSec=150
UMask=0077
NoNewPrivileges=true
'''


TIMER = '''[Unit]
Description=WeSticker bounded billing recovery schedule

[Timer]
OnBootSec=2min
OnUnitInactiveSec=5min
RandomizedDelaySec=15
Unit=westicker-billing-reconcile.service

[Install]
WantedBy=timers.target
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    root, config = args.root.resolve(), args.config.resolve()
    if not (root / ".runtime/creator-current/server/reconcile.py").is_file() or not config.is_file():
        raise SystemExit("Active runtime and private configuration required")
    folder = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "systemd/user"
    folder.mkdir(parents=True, exist_ok=True)
    for name, text in (("service", unit_text(root, config)), ("timer", TIMER)):
        path = folder / ("westicker-billing-reconcile." + name)
        if path.exists() and path.read_text() != text:
            raise SystemExit("Existing unit differs; preserve it for review")
        path.write_text(text)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "westicker-billing-reconcile.timer"], check=True)
    print("WeSticker recovery timer installed; no purchase is created.")


if __name__ == "__main__":
    main()
