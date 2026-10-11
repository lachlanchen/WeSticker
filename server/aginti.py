"""Isolated AgInTi image adapter; never starts an agent conversation or retries."""

import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .local_video import OutcomeUncertain


def invoke(cfg, payload):
    state = Path(cfg["state"]).resolve()
    request = dict(payload, agintiRoot=cfg["aginti_root"], workspace=str(state))
    fd, name = tempfile.mkstemp(prefix="aginti-", suffix=".json", dir=state)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(request, handle)
        result = subprocess.run(
            [cfg.get("aginti_node", "node"), str(Path(__file__).with_name("aginti-runner.mjs")), name],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=720, check=False,
            cwd=state,
        )
        if result.returncode:
            raise ValueError("AgInTi operation incomplete. Inspect the saved job before retrying.")
        return json.loads(result.stdout)
    finally:
        Path(name).unlink(missing_ok=True)


def moderate(cfg, text, paths):
    return invoke(cfg, {"mode": "moderate", "input": [
        {"type": "text", "text": text},
        *[{"type": "image_url", "image_url": {
            "url": "data:image/png;base64," + base64.b64encode(Path(p).read_bytes()).decode()
        }} for p in paths],
    ]})


def generate(cfg, job, item, prompt, references):
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(value)) for value in [job["id"], item["id"]]):
        raise ValueError("Invalid image attempt")
    state = Path(cfg["state"]).resolve()
    folder = state / "renders" / job["id"] / item["id"]
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    fingerprint = hashlib.sha256(json.dumps({"prompt": prompt,
        "model": cfg.get("aginti_image_model", "nano-banana-2"),
        "refs": [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in references],
    }, sort_keys=True).encode()).hexdigest()
    with (folder / "aginti.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise OutcomeUncertain("This image is already being observed.") from None
        intent = folder / "aginti-intent.json"
        if intent.exists():
            if json.loads(intent.read_text()).get("fingerprint") != fingerprint:
                raise OutcomeUncertain("Existing image belongs to a different request.")
        else:
            with intent.open("x") as handle:
                json.dump({"fingerprint": fingerprint}, handle)
                handle.flush()
                os.fsync(handle.fileno())
        receipt = folder / "aginti-receipt.json"
        if receipt.exists():
            saved = json.loads(receipt.read_text())
            output = Path(saved["path"]).resolve()
            if (saved.get("fingerprint") != fingerprint or not output.is_relative_to(folder)
                    or hashlib.sha256(output.read_bytes()).hexdigest() != saved.get("sha256")):
                raise OutcomeUncertain("Saved image receipt failed integrity verification.")
            return output.read_bytes()
        try:
            result = invoke(cfg, {"mode": "image", "folder": str(folder), "prompt": prompt,
                "model": cfg.get("aginti_image_model", "nano-banana-2"),
                "references": [str(Path(p).resolve()) for p in references]})
            output = Path(result["path"]).resolve()
            if (not output.is_relative_to(folder) or not output.is_file()
                    or output.stat().st_size > 25_000_000):
                raise ValueError("Invalid AgInTi image artifact")
            binary = output.read_bytes()
            with receipt.open("x") as handle:
                json.dump({"path": str(output), "fingerprint": fingerprint,
                    "sha256": hashlib.sha256(binary).hexdigest()}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            return binary
        except Exception:
            if (folder / "network-intent.json").exists():
                raise OutcomeUncertain("AgInTi request is saved; reconcile it without resubmission.") from None
            raise
