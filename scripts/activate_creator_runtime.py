"""Activate one staged backend only while its queue is idle; retain rollback."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from urllib.request import urlopen


def verify_release(release):
    manifest = json.loads((release / "manifest.json").read_text())
    hashes = manifest["files"]
    if not hashes or hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest() != manifest["sha256"]:
        raise RuntimeError("Invalid release manifest")
    for name, digest in hashes.items():
        path = release / name
        if not path.resolve().is_relative_to(release) or path.is_symlink():
            raise RuntimeError("Invalid release path")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError("Release content differs from manifest")
    if (release / "public/catalog.json").read_bytes() != (release / "dist/catalog.json").read_bytes():
        raise RuntimeError("API catalog differs from web catalog")


def require_idle(cfg):
    path = (Path(cfg["state"]) / "westicker.sqlite").resolve()
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        if db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('queued','running')").fetchone()[0]:
            raise RuntimeError("Wait for existing jobs")
        has_chat = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='studio_messages'").fetchone()
        if has_chat and db.execute("SELECT COUNT(*) FROM studio_messages WHERE state='working'").fetchone()[0]:
            raise RuntimeError("Wait for existing chat requests")


def health(url):
    for _ in range(15):
        try:
            with urlopen(url, timeout=2) as response:
                body = json.load(response)
            if body.get("ok") and body.get("app") == "westicker":
                return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Activated API did not become healthy")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--release", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--config-candidate", type=Path, help="Atomically install private settings with the release")
    p.add_argument("--current", type=Path, required=True)
    p.add_argument("--health-url", help="Defaults to the configured public origin, including its ingress guard")
    args = p.parse_args()
    lock = args.current.with_name(args.current.name + ".activation.lock").open("a")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    release = args.release.resolve()
    verify_release(release)
    original_config = args.config.read_bytes()
    cfg = json.loads(original_config)
    candidate = args.config_candidate.read_bytes() if args.config_candidate else original_config
    proposed_config = json.loads(candidate)
    if any(proposed_config.get(key) != cfg.get(key) for key in ("state", "origin")):
        raise RuntimeError("Runtime activation cannot change the database or origin")
    require_idle(cfg)
    previous = args.current.resolve()
    staged = args.current.with_name(args.current.name + ".next")
    config_staged = args.config.with_name(args.config.name + ".next")
    services = ["westicker-creator-api.service", "westicker-creator-worker.service"]
    if staged.exists() or staged.is_symlink() or config_staged.exists() or config_staged.is_symlink():
        raise RuntimeError("Another activation may be in progress")
    config_changed = False
    def install_settings(content):
        fd = os.open(config_staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(config_staged, args.config)
    try:
        # Close admission before the second queue check; never interrupt a render.
        subprocess.run(["systemctl", "--user", "stop", services[0]], check=True)
        require_idle(cfg)
        subprocess.run(["systemctl", "--user", "stop", services[1]], check=True)
        if args.config.read_bytes() != original_config:
            raise RuntimeError("Configuration changed during activation")
        if candidate != original_config:
            backup = args.config.with_name(args.config.name + ".previous-" + str(time.time_ns()))
            fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(original_config)
            install_settings(candidate)
            config_changed = True
        staged.symlink_to(release)
        os.replace(staged, args.current)
        subprocess.run(["systemctl", "--user", "restart", *services], check=True)
        health(args.health_url or cfg["origin"].rstrip("/") + "/api/health")
    except BaseException:
        changed = args.current.resolve() != previous
        if changed:
            subprocess.run(["systemctl", "--user", "stop", *services], check=True)
            staged.symlink_to(previous)
            os.replace(staged, args.current)
        if config_changed:
            subprocess.run(["systemctl", "--user", "stop", *services], check=True)
            install_settings(original_config)
        subprocess.run(["systemctl", "--user", "start", *services], check=True)
        raise
    print(json.dumps({"previous": str(previous), "current": str(release)}))


if __name__ == "__main__":
    main()
