"""One approved public-reference animation through the real guarded adapter.

No engine startup, production enablement or automatic rerun. A failed/uncertain
folder remains evidence; recovery observes its existing receipt, never a new ID.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.local_video import animate
from server.store import settings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--public-reference", type=Path, required=True)
    p.add_argument("--submit-one", action="store_true", required=True)
    p.add_argument("--resume-receipt", action="store_true", help="Recover the existing provider ID only; no new render")
    args = p.parse_args()
    os.umask(0o077)
    os.environ["WESTICKER_CONFIG"] = str(args.config.resolve())
    cfg = settings()
    state = args.state.resolve()
    state.mkdir(parents=True, exist_ok=args.resume_receipt)
    if args.resume_receipt:
        assert (state / "renders/public-aya-animation-20261011/wave-once-01/receipt.json").is_file(), "An existing receipt is required"
    cfg.update(state=str(state), local_video_url="http://127.0.0.1:8190")
    with Image.open(args.public_reference) as image:
        picture = ImageOps.exif_transpose(image).convert("RGBA")
        picture.thumbnail((480, 480))
        canvas = Image.new("RGBA", (512, 512), "white")
        canvas.alpha_composite(picture, ((512-picture.width)//2, (512-picture.height)//2))
        canvas.convert("RGB").save(state / "reference.png")
    evidence = {"source_sha256": hashlib.sha256(args.public_reference.read_bytes()).hexdigest(),
        "normalized_sha256": hashlib.sha256((state / "reference.png").read_bytes()).hexdigest(),
        "scope": "single public Aya canary", "production_enabled": False,
        "profile": "quality_int8_offload", "duration_requested": 5, "dimensions": [512, 512]}
    (state / "preflight.json").write_text(json.dumps(evidence, indent=2))
    result = animate(cfg, {"id": "public-aya-animation-20261011"},
        {"id": "wave-once-01", "label": "Hello", "action":
         "Aya raises her right hand beside her face, gives two small wrist waves, blinks with a warm smile, then lowers her hand to the original relaxed pose. Her feet remain planted; the skirt moves softly."},
        state / "reference.png")
    evidence.update(gif=str(result), state="rendered-needs-visual-review")
    (state / "result.json").write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
