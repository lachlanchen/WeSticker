"""One approved public-reference canary through the real WeSticker worker.

Paid once. This private run folder is exclusive and must not be reused for retries.
Does not enable production or upload private customer imagery.
"""
import argparse
import io
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.app import create_app
from server.aginti import invoke
from server.worker import work_once


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--aginti-root", required=True)
    parser.add_argument("--node", default="node")
    parser.add_argument("--public-reference", required=True, type=Path)
    parser.add_argument("--submit-one", action="store_true", required=True)
    args = parser.parse_args()
    os.umask(0o077)
    os.environ.pop("WESTICKER_CONFIG", None)
    os.environ.pop("WESTICKER_LAZYINGART_CONFIG", None)
    state = args.state.resolve()
    state.mkdir(parents=True, exist_ok=False)
    cfg = {"state": str(state), "origin": "http://localhost:18642", "local_accounts": True,
        "image_provider": "aginti", "aginti_root": args.aginti_root, "aginti_node": args.node,
        "aginti_qualified": True, "image_generation_enabled": True,
        "aginti_image_model": "nano-banana-2"}
    if invoke(cfg, {"mode": "doctor"}) != {"image": True, "safety": True}:
        raise RuntimeError("AgInTi prerequisites unavailable")
    app = create_app(cfg)
    client = app.test_client()
    def call(url, body):
        csrf = client.get("/api/bootstrap").json.get("csrf", "")
        result = client.post(url, json=body, headers={"Origin": cfg["origin"], "X-CSRF-Token": csrf})
        if result.status_code not in (200, 201, 202):
            raise RuntimeError(f"Canary step failed: {url} {result.status_code}")
        return result.json
    call("/api/auth/register", {"email": "aginti-canary@fixture.invalid", "name": "Public Aya QA",
        "password": secrets.token_urlsafe(32), "adult": True, "terms": True})
    result = client.post("/api/assets", headers={"Origin": cfg["origin"],
        "X-CSRF-Token": client.get("/api/bootstrap").json["csrf"]},
        data={"rights": "yes", "file": (io.BytesIO(args.public_reference.read_bytes()), "aya.png")})
    if result.status_code != 201:
        raise RuntimeError("Public reference upload failed")
    character = call("/api/characters", {"name": "Aya Chan", "style": "figurine",
        "refs": [result.json["id"]]})["id"]
    call(f"/api/characters/{character}/lock", {"approved": True})
    pack = call("/api/packs", {"character": character, "title": "Aya says hello", "theme": "daily", "language": "en"})["id"]
    item = client.get("/api/workspace").json["packs"][0]["items"][0]
    payload = {"kind": "ai", "items": [item["id"]], "attempt": "aginti-public-aya-canary-01", "consent": True}
    job = call(f"/api/packs/{pack}/generate", payload)["id"]
    assert call(f"/api/packs/{pack}/generate", payload)["id"] == job
    work_once(app.config["WESTICKER"])
    workspace = client.get("/api/workspace").json
    saved = workspace["jobs"][0]
    output = {"job": job, "state": saved["state"], "error": saved.get("error"),
        "pack": pack, "items": workspace["packs"][0]["items"], "provider": "aginti-grsai",
        "live_image_request": True, "production_enabled": False}
    (state / "qualification.json").write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    if saved["state"] != "review":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
