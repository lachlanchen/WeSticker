"""Single worker; preserves ambiguous paid outcomes instead of blindly retrying."""

import argparse
import base64
import fcntl
import hashlib
import io
import json
from pathlib import Path
import time

from PIL import Image
import requests

from .store import audit, database, initialize, settings, uid
from .local_video import animate, OutcomeUncertain
from .generation import moderate, provider_origin
from . import aginti
from .media import exterior_alpha


def openai_image(cfg, job, item, fields, files, refs):
    folder = Path(cfg["state"]) / "renders" / job["id"] / item["id"]
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    intent = folder / "image-intent.json"
    if intent.exists():
        raise OutcomeUncertain("Existing image request must be reconciled, not repeated.")
    with intent.open("x") as handle:
        json.dump({"created": time.time(), "job": job["id"], "item": item["id"],
            "request": fields, "references": [{"id": r["id"], "sha256": r["sha256"]} for r in refs]}, handle)
    try:
        api = provider_origin(cfg.get("image_api_origin", "https://api.openai.com/v1"))
        result = requests.post(api + "/images/edits",
            headers={"Authorization": "Bearer " + cfg["image_api_key"]},
            data=fields, files=files, timeout=300, allow_redirects=False)
        result.raise_for_status()
        payload = result.json()
        binary = base64.b64decode(payload["data"][0]["b64_json"], validate=True)
        if len(binary) > 25_000_000:
            raise ValueError("Provider image exceeded the expected limit.")
        (folder / "original.png").write_bytes(binary)
        (folder / "image-receipt.json").write_text(json.dumps({
            "created": payload.get("created"), "usage": payload.get("usage"),
            "request_id": getattr(result, "headers", {}).get("x-request-id"),
            "sha256": hashlib.sha256(binary).hexdigest()}))
        return binary
    except Exception:
        raise OutcomeUncertain("Image request saved; reconcile before retrying.") from None


def work_once(cfg):
    with database(cfg) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT 1"
        ).fetchone()
        if not row:
            return False
        job = dict(row)
        db.execute(
            "UPDATE jobs SET state='running',updated=? WHERE id=?",
            (time.time(), job["id"]),
        )
    state = Path(cfg["state"])
    data = json.loads(job["data"])
    items = data["items"]
    submitted = False
    try:
        with database(cfg) as db:
            character = dict(
                db.execute(
                    "SELECT * FROM characters WHERE id=? AND user_id=?",
                    (data["character"], job["user_id"]),
                ).fetchone()
            )
            refs = [
                dict(
                    db.execute(
                        "SELECT * FROM assets WHERE id=? AND user_id=?",
                        (ref, job["user_id"]),
                    ).fetchone()
                )
                for ref in json.loads(character["refs"])
            ]
        if not refs or any(not (state / r["path"]).is_file() for r in refs):
            raise ValueError(
                "Reference expired. Upload fresh references before another generation."
            )
        selected = [
            item
            for item in items
            if item["id"] in data.get("selected", [x["id"] for x in items])
        ]
        if job["kind"] == "photo":
            for i, item in enumerate(selected):
                item["asset"] = refs[i % len(refs)]["id"]
                item["approved"] = False
        elif job["kind"] == "animate":
            for index, item in enumerate(selected):
                with database(cfg) as db:
                    asset = db.execute(
                        "SELECT * FROM assets WHERE id=? AND user_id=?",
                        (item["asset"], job["user_id"]),
                    ).fetchone()
                if not asset:
                    raise ValueError("Approved animation reference is unavailable.")
                result = animate(cfg, job, item, state / asset["path"])
                id = uid()
                path = Path("assets") / (id + ".gif")
                path_target = state / path
                path_target.write_bytes(result.read_bytes())
                item["asset"] = id
                item["approved"] = False
                data["completed"] = (index + 1) * 3
                with database(cfg) as db:
                    db.execute(
                        "INSERT INTO assets VALUES(?,?,?,?,?,?,?)",
                        (
                            id,
                            job["user_id"],
                            str(path),
                            hashlib.sha256(path_target.read_bytes()).hexdigest(),
                            "animation",
                            time.time(),
                            None,
                        ),
                    )
                    db.execute(
                        "UPDATE jobs SET progress=?,data=?,updated=? WHERE id=?",
                        (
                            round((index + 1) / len(selected) * 100),
                            json.dumps(data),
                            time.time(),
                            job["id"],
                        ),
                    )
                    db.execute(
                        "UPDATE packs SET items=?,updated=?,revision=revision+1 WHERE id=?",
                        (
                            json.dumps(items, ensure_ascii=False),
                            time.time(),
                            job["pack_id"],
                        ),
                    )
        else:
            use_aginti = cfg.get("image_provider") == "aginti"
            if not use_aginti and not cfg.get("image_api_key"):
                raise ValueError("Image provider is not configured.")
            moderate(cfg, character["name"] + " " + ", ".join(
                i["label"] + " " + i.get("action", "") for i in items),
                [state / r["path"] for r in refs])
            for index, item in enumerate(selected):
                prompt = f"Create one charming {character['style']} chat sticker of the exact character in the supplied references. Preserve face, fur or skin, outfit, palette and proportions. Expression meaning: {item['label']}. Action direction: {item.get('action', '')}. One clear readable pose, whole body inside frame, transparent background. No lettering; captions are added separately."
                if use_aginti:
                    prompt = prompt.replace("transparent background", "plain neutral white background for cutout")
                files = [
                    (
                        "image[]",
                        (
                            "reference.png",
                            (state / r["path"]).read_bytes(),
                            "image/png",
                        ),
                    )
                    for r in refs
                ]
                fields = {
                    "model": cfg["image_model"],
                    "prompt": prompt,
                    "n": "1",
                    "size": "1024x1024",
                    "quality": "medium",
                    "background": "transparent",
                    "output_format": "png",
                }
                if cfg["image_model"] in {"gpt-image-1", "gpt-image-1.5"}:
                    fields["input_fidelity"] = "high"
                with database(cfg) as db:
                    audit(
                        db,
                        job["user_id"],
                        "image_submission_intent",
                        {"job": job["id"], "item": item["id"]},
                    )
                binary = (aginti.generate(cfg, job, item, prompt, [state / r["path"] for r in refs])
                          if use_aginti else openai_image(cfg, job, item, fields, files, refs))
                submitted = True
                if use_aginti:
                    # Preserve the paid original even if output screening needs review.
                    original = state / "renders" / job["id"] / item["id"] / "screening.png"
                    original.write_bytes(binary)
                    moderate(cfg, item["label"], [original])
                image = Image.open(io.BytesIO(binary)).convert("RGBA")
                image.thumbnail((1024, 1024))
                if use_aginti:
                    image = exterior_alpha(image)
                asset = uid()
                path = Path("assets") / (asset + ".png")
                image.save(state / path, "PNG")
                item["asset"] = asset
                item["approved"] = False
                data["completed"] = index + 1
                with database(cfg) as db:
                    db.execute(
                        "INSERT INTO assets VALUES(?,?,?,?,?,?,?)",
                        (
                            asset,
                            job["user_id"],
                            str(path),
                            hashlib.sha256((state / path).read_bytes()).hexdigest(),
                            "generated",
                            time.time(),
                            None,
                        ),
                    )
                    db.execute(
                        "UPDATE jobs SET progress=?,data=?,updated=? WHERE id=?",
                        (
                            round((index + 1) / len(selected) * 100),
                            json.dumps(data),
                            time.time(),
                            job["id"],
                        ),
                    )
                    db.execute(
                        "UPDATE packs SET items=?,updated=?,revision=revision+1 WHERE id=?",
                        (
                            json.dumps(items, ensure_ascii=False),
                            time.time(),
                            job["pack_id"],
                        ),
                    )
                submitted = False
        with database(cfg) as db:
            db.execute(
                "UPDATE packs SET items=?,updated=?,revision=revision+1 WHERE id=?",
                (json.dumps(items, ensure_ascii=False), time.time(), job["pack_id"]),
            )
            db.execute(
                "UPDATE jobs SET state='review',progress=100,data=?,updated=? WHERE id=?",
                (json.dumps(data), time.time(), job["id"]),
            )
    except Exception as error:
        if isinstance(error, OutcomeUncertain):
            submitted = True
        # Preserve partial output. A response lost after submission holds the reservation.
        message = (
            "Provider outcome uncertain. Inspect this job; do not resubmit."
            if submitted
            else str(error)[:300]
        )
        with database(cfg) as db:
            db.execute(
                "UPDATE jobs SET state=?,error=?,updated=? WHERE id=?",
                (
                    "uncertain" if submitted else "failed",
                    message,
                    time.time(),
                    job["id"],
                ),
            )
            if not submitted:
                balance = (
                    "trial_images"
                    if data.get("balance") == "trial_images"
                    else "credits"
                )
                db.execute(
                    f"UPDATE users SET {balance}={balance}+? WHERE id=?",
                    (max(0, data["cost"] - data.get("completed", 0)), job["user_id"]),
                )
        return True
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    cfg = settings()
    initialize(cfg)
    with (Path(cfg["state"]) / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with database(cfg) as db:
            db.execute(
                "UPDATE jobs SET state='uncertain',error='Worker interrupted. Inspect before continuing.' WHERE state='running'"
            )
        while True:
            worked = work_once(cfg)
            if args.once:
                break
            if not worked:
                time.sleep(2)


if __name__ == "__main__":
    main()
