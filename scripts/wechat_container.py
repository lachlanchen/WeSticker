"""Provision exactly one isolated browser per customer. Never mount a host profile."""

import argparse
import json
from pathlib import Path
import secrets
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.store import settings, database

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("action", choices=["start", "upload", "stop"])
parser.add_argument("ticket")
parser.add_argument("--port", type=int, default=18643)
args = parser.parse_args()
cfg = settings()
root = Path(cfg["state"]).resolve()
with database(cfg) as db:
    ticket = db.execute(
        "SELECT * FROM upload_tickets WHERE id=?", (args.ticket,)
    ).fetchone()
if not ticket:
    raise SystemExit("Unknown ticket.")
owner = ticket["user_id"]
name = "westicker-wechat-" + owner
if not owner.isalnum() or not args.ticket.isalnum():
    raise SystemExit("Invalid identifier.")
if args.action == "stop":
    subprocess.run(["docker", "stop", name], check=True)
    for receipt in (root / "wechat" / owner).glob("*/runtime.json"):
        receipt.rename(receipt.with_name("runtime-stopped.json"))
    raise SystemExit()
if args.action == "upload":
    subprocess.run(
        ["docker", "exec", name, "node", "/agent/wechat-agent.mjs"], check=True
    )
    raise SystemExit()
if not 1024 <= args.port <= 65535:
    raise SystemExit("Invalid port.")
existing = subprocess.run(["docker", "inspect", name], capture_output=True)
if existing.returncode == 0:
    raise SystemExit(
        "Existing customer browser found. Reuse/stop it; no duplicate will be launched."
    )
private = root / "wechat" / owner
private.mkdir(parents=True, exist_ok=True, mode=0o700)
password = private / "vnc-password"
if not password.exists():
    password.write_text(secrets.token_hex(4))
    password.chmod(0o600)
profile = private / "profile"
profile.mkdir(exist_ok=True, mode=0o700)
folder = (root / ticket["path"]).resolve()
if not folder.is_relative_to(private):
    raise SystemExit("Unsafe handoff path.")
# Bind files retain owner UID so no root-owned customer artifacts are created.
import os

subprocess.run(
    [
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        name,
        "--user",
        f"{os.getuid()}:{os.getgid()}",
        "--memory=2g",
        "--cpus=2",
        "--pids-limit=256",
        "--shm-size=256m",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,size=512m",
        "-e",
        "HOME=/tmp",
        "-p",
        f"127.0.0.1:{args.port}:6080",
        "-v",
        f"{profile}:/profile",
        "-v",
        f"{folder}:/work",
        "-v",
        f"{password}:/run/secrets/vnc_password:ro",
        "westicker-wechat:local",
    ],
    check=True,
)
(folder / "runtime.json").write_text(
    json.dumps(
        {
            "container": name,
            "url": f"http://127.0.0.1:{args.port}/vnc.html?autoconnect=1&resize=scale",
            "password_file": str(password),
        },
        indent=2,
    )
)
print(f"http://127.0.0.1:{args.port}/vnc.html?autoconnect=1&resize=scale")
print(
    "Credentials remain in the private runtime record. Login, then open an empty new-album form before the upload action."
)
