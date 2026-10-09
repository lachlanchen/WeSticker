"""Start or stop this project's single local review runtime."""

import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["start", "stop", "status"])
args = parser.parse_args()
runtime = root / ".runtime"
runtime.mkdir(exist_ok=True, mode=0o700)
receipt = runtime / "processes.json"
if args.action == "status":
    print(receipt.read_text() if receipt.exists() else "No owned runtime.")
    raise SystemExit()
if args.action == "stop":
    if receipt.exists():
        data = json.loads(receipt.read_text())
        for name, pid in data["pids"].items():
            try:
                cwd = Path(f"/proc/{pid}/cwd").resolve()
                if cwd == root:
                    os.killpg(pid, signal.SIGTERM)
            except (FileNotFoundError, ProcessLookupError):
                pass
        receipt.unlink()
    raise SystemExit()
if receipt.exists():
    raise SystemExit(
        "Runtime receipt exists; inspect status instead of starting duplicates."
    )
for port in (18641, 18642):
    with socket.socket() as sock:
        if sock.connect_ex(("127.0.0.1", port)) == 0:
            raise SystemExit(f"Port {port} is in use.")
cfg = root / ".config/local.json"
if not cfg.exists():
    raise SystemExit(
        "Create .config/local.json first. No shared credentials are inferred."
    )
env = os.environ | {"WESTICKER_CONFIG": str(cfg)}
commands = {
    "api": [str(root / ".venv/bin/python"), "-m", "server.app"],
    "worker": [str(root / ".venv/bin/python"), "-m", "server.worker"],
    "web": ["npm", "run", "dev"],
}
pids = {}
for name, command in commands.items():
    with (runtime / f"{name}.log").open("ab") as log:
        p = subprocess.Popen(
            command,
            cwd=root,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=log,
            start_new_session=True,
        )
    pids[name] = p.pid
receipt.write_text(
    json.dumps(
        {"pids": pids, "url": "http://127.0.0.1:18642", "started": time.time()},
        indent=2,
    )
)
print("http://127.0.0.1:18642")
