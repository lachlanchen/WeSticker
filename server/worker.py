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
                        "UPDATE packs SET items=?,updated=? WHERE id=?",
                        (
                            json.dumps(items, ensure_ascii=False),
                            time.time(),
                            job["pack_id"],
                        ),
                    )
        else:
            if not cfg.get("image_api_key"):
                raise ValueError("Image provider is not configured.")
            headers = {"Authorization": "Bearer " + cfg["image_api_key"]}
            api = cfg.get("image_api_origin", "https://api.openai.com/v1").rstrip("/")
            # Service endpoints are operator configuration, never accepted from users.
            moderation = requests.post(
                api + "/moderations",
                headers=headers,
                json={
                    "model": cfg["moderation_model"],
                    "input": [
                        {
                            "type": "text",
                            "text": character["name"]
                            + " "
                            + ", ".join(i["label"] for i in items),
                        },
                        *[
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/png;base64,"
                                    + base64.b64encode(
                                        (state / r["path"]).read_bytes()
                                    ).decode()
                                },
                            }
                            for r in refs
                        ],
                    ],
                },
                timeout=60,
            )
            moderation.raise_for_status()
            if any(x["flagged"] for x in moderation.json()["results"]):
                raise ValueError(
                    "Reference or caption needs a safety review. No image was generated."
                )
            for index, item in enumerate(selected):
                prompt = f"Create one charming {character['style']} chat sticker of the exact character in the supplied references. Preserve face, fur or skin, outfit, palette and proportions. Expression/action meaning: {item['label']}. One clear readable pose, whole body inside frame, transparent background. No lettering; captions are added separately."
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
                submitted = True
                result = requests.post(
                    api + "/images/edits",
                    headers=headers,
                    data=fields,
                    files=files,
                    timeout=300,
                )
                result.raise_for_status()
                binary = base64.b64decode(
                    result.json()["data"][0]["b64_json"], validate=True
                )
                image = Image.open(io.BytesIO(binary)).convert("RGBA")
                image.thumbnail((1024, 1024))
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
                        "UPDATE packs SET items=?,updated=? WHERE id=?",
                        (
                            json.dumps(items, ensure_ascii=False),
                            time.time(),
                            job["pack_id"],
                        ),
                    )
                submitted = False
        with database(cfg) as db:
            db.execute(
                "UPDATE packs SET items=?,updated=? WHERE id=?",
                (json.dumps(items, ensure_ascii=False), time.time(), job["pack_id"]),
            )
            db.execute(
                "UPDATE jobs SET state='review',progress=100,updated=? WHERE id=?",
                (time.time(), job["id"]),
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
                db.execute(
                    "UPDATE users SET credits=credits+? WHERE id=?",
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
