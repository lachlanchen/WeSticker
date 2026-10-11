"""Single-item LocalVideoGen adapter with installed on-demand ownership policy."""

import hashlib
import json
import fcntl
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlparse
from PIL import Image
from .generation import moderate
from .local_video_lifecycle import admission, atomic_json, local_session, status as lifecycle_status


class OutcomeUncertain(RuntimeError):
    pass


def require_idle(session, base):
    def get(path):
        response = session.get(base + path, timeout=30)
        response.raise_for_status()
        return response.json()
    jobs = get("/api/jobs?scope=active&limit=100")
    series = get("/api/series?limit=100")
    if not isinstance(jobs.get("jobs"), list) or jobs["jobs"]:
        raise ValueError("Animation deferred: another render is active.")
    records = series.get("series")
    if (not isinstance(records, list) or len(records) >= 100
            or any(r.get("status") in {"queued", "running", "stitching"} for r in records)):
        raise ValueError("Animation deferred: series queue needs review.")
    if get("/api/settings").get("system_prompt", "").strip():
        raise ValueError("Animation deferred: shared renderer instructions need review.")


def video_output(state):
    outputs = [x for x in state.get("outputs", []) if isinstance(x, dict)
               and (x.get("media_type") == "video" or str(x.get("filename", "")).lower().endswith(".mp4"))
               and type(x.get("id")) is int and x["id"] >= 0]
    if len(outputs) != 1:
        raise OutcomeUncertain("Render finished; inspect the saved output list before download.")
    return outputs[0]["id"]


def animate(cfg, job, item, source, *, batch=None):
    if any(not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", str(value)) for value in (job["id"], item["id"])):
        raise ValueError("Invalid animation attempt identity.")
    folder = Path(cfg["state"]) / "renders" / job["id"] / item["id"]
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (folder / "attempt.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise OutcomeUncertain("This animation attempt is already being observed.") from error
        return _animate(cfg, job, item, source, batch=batch)


def _animate(cfg, job, item, source, *, batch=None):
    base = cfg["local_video_url"].rstrip("/")
    parsed = urlparse(base)
    if (parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.scheme != "http" or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment):
        raise ValueError("LocalVideoGen must use a protected local endpoint.")
    folder = Path(cfg["state"]) / "renders" / job["id"] / item["id"]
    folder.mkdir(parents=True, exist_ok=True)
    intent = folder / "intent.json"
    receipt = folder / "receipt.json"
    if intent.exists() and not receipt.exists():
        raise OutcomeUncertain("Existing submission intent needs reconciliation.")
    fingerprint = hashlib.sha256(json.dumps({
        "source": hashlib.sha256(Path(source).read_bytes()).hexdigest(),
        "label": item["label"], "action": item.get("action", ""),
        "profile": "quality_int8_offload", "size": [512, 512], "duration": 5,
    }, sort_keys=True).encode()).hexdigest()
    if receipt.exists():
        try:
            if not intent.exists() or json.loads(intent.read_text()).get("fingerprint") != fingerprint:
                raise ValueError("Fingerprint differs")
        except (OSError, ValueError, AttributeError) as error:
            raise OutcomeUncertain("Saved render belongs to a different or unverified request.") from error
    session = local_session()
    try:
        key = hashlib.sha256(str(folder.resolve()).encode()).hexdigest()
        with admission(cfg, key, fingerprint, resume=receipt.exists(), batch=batch) as lease:
            result = _run(cfg, job, item, source, base, folder, intent, receipt, fingerprint, session, lease)
            if lease:
                lease.complete()
            return result
    except Exception as error:
        if intent.exists() and not isinstance(error, OutcomeUncertain):
            raise OutcomeUncertain("Saved animation intent/receipt needs recovery, not another submission.") from error
        raise
    finally:
        session.close()


def _run(cfg, job, item, source, base, folder, intent, receipt, fingerprint, session, lease):
    if receipt.exists():
        provider = json.loads(receipt.read_text())["id"]
        if not isinstance(provider, str) or not re.fullmatch(r"[a-f0-9-]{36}", provider):
            raise OutcomeUncertain("Saved render receipt has an invalid provider identity.")
        if lease:
            lease.receipt(provider)
    else:
        lease.prepare()
        health = session.get(base + "/api/health?deep=1", timeout=30)
        health.raise_for_status()
        ready = health.json()
        if not (ready.get("connected") is True and ready.get("ready") is True
                and ready.get("model_status") == "verified"):
            raise ValueError("Animation engine is not ready. Nothing was submitted.")
        require_idle(session, base)
        moderate(cfg, item["label"] + " " + item.get("action", ""), [source])
        with Image.open(source) as raw:
            image = raw.convert("RGBA")
            canvas = Image.new("RGBA", image.size, "white")
            canvas.alpha_composite(image)
            canvas.convert("RGB").save(folder / "reference.png")
        with (folder / "reference.png").open("rb") as stream:
            uploaded = session.post(
                base + "/api/uploads?kind=image", files={"file": stream}, timeout=120,
                headers=lease.mutation_headers(),
            )
        uploaded.raise_for_status()
        token = uploaded.json()["token"]
        entity = {
            "id": "lead",
            "kind": "character",
            "label": "the exact single character in the approved reference",
            "count": 1,
            "parts": {},
            "contact_points": ["feet"],
            "roles": ["performer"],
            "inserted": False,
        }
        floor = {
            "id": "floor",
            "kind": "set_piece",
            "label": "plain studio floor",
            "count": 1,
            "parts": {},
            "contact_points": ["surface"],
            "roles": [],
            "inserted": False,
        }
        payload = {
            "mode": "i2v",
            "profile": "quality_int8_offload",
            "width": 512,
            "height": 512,
            "duration": 5,
            "seed": int(hashlib.sha256(item["id"].encode()).hexdigest()[:7], 16),
            "first_frame": token,
            "audio_intent": "ambient",
            "dialogue": [],
            "prompt": f"The exact single reference character acts out this everyday expression: {item['label']}. Action: {item.get('action', '')}. Preserve the face, clothing and palette. A motivated gesture with anticipation, weight shift, hand motion and a relaxed settling pose; gentle blinking and naturally responding sleeves. Whole character visible, locked camera and clean white backdrop. No lettering or speech.",
            "physical_contract": {
                "entities": [entity, floor],
                "contacts": [
                    {
                        "source": "lead:feet",
                        "target": "floor:surface",
                        "relation": "balanced on",
                    }
                ],
                "motions": [
                    {"entity": "lead", "kind": kind, "description": description}
                    for kind, description in [
                        ("body_balance", "Balance naturally during the gesture."),
                        (
                            "blink_or_head_reaction",
                            "A small blink and motivated head reaction.",
                        ),
                        (
                            "secondary_response",
                            "Clothes respond gently to body motion.",
                        ),
                    ]
                ],
            },
        }
        (folder / "request.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2)
        )
        # Recheck ownership/resources/queues under the shared admission lock,
        # then durably reserve the uncertain-outcome slot before the sole POST.
        headers = lease.submitting()
        atomic_json(intent, {"created": time.time(), "job": job["id"], "item": item["id"],
                            "fingerprint": fingerprint, "request_sha256": hashlib.sha256(
                                (folder / "request.json").read_bytes()).hexdigest()})
        try:
            result = session.post(base + "/api/renders", json=payload, headers=headers, timeout=120)
            result.raise_for_status()
            data = result.json()
            provider = data["id"]
            if not isinstance(provider, str) or not re.fullmatch(r"[a-f0-9-]{36}", provider):
                raise ValueError("Unexpected render receipt identity.")
            atomic_json(receipt, data)
            lease.receipt(provider)
        except Exception as e:
            raise OutcomeUncertain(
                "Local render outcome uncertain; inspect the saved intent."
            ) from e
    deadline = time.monotonic() + 3600
    try:
        while time.monotonic() < deadline:
            if lease:
                lease.observe()
            response = session.get(base + "/api/jobs/" + provider, timeout=30)
            response.raise_for_status()
            state = response.json()
            if lease:
                lease.observe()
            (folder / "status.json").write_text(json.dumps(state, indent=2))
            if state.get("status") in {"completed", "done", "succeeded"}:
                break
            if state.get("status") in {"failed", "error", "cancelled", "canceled"}:
                raise OutcomeUncertain(
                    "Local job stopped; preserve its provider ID for operator review."
                )
            time.sleep(10)
        else:
            raise OutcomeUncertain(
                "Render is still pending. Inspect the existing job; do not submit another."
            )
        video = folder / "original.mp4"
        if not video.exists():
            output_id = video_output(state)
            if lease:
                lease.observe()
            with session.get(
                base + f"/api/jobs/{provider}/outputs/{output_id}?download=1",
                stream=True,
                timeout=120,
            ) as response:
                response.raise_for_status()
                with (folder / "download.part").open("wb") as stream:
                    total = 0
                    for chunk in response.iter_content(65536):
                        total += len(chunk)
                        if total > 100_000_000:
                            raise ValueError("Unexpectedly large render.")
                        stream.write(chunk)
            if lease:
                lease.observe()
            (folder / "download.part").replace(video)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"],
            check=True,
            timeout=120,
        )
        gif = folder / "clean.gif"
        if not gif.exists():
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(video),
                    "-t",
                    "5.2",
                    "-filter_complex",
                    "fps=12,scale=240:240:force_original_aspect_ratio=decrease,pad=240:240:(ow-iw)/2:(oh-ih)/2:white,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse",
                    "-loop",
                    "0",
                    str(gif),
                ],
                check=True,
                timeout=120,
            )
        return gif
    except Exception as e:
        if isinstance(e, OutcomeUncertain):
            raise
        raise OutcomeUncertain(
            "Render receipt retained. Download or packaging needs operator recovery, not a new render."
        ) from e
