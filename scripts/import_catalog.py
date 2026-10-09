"""Import only public approved artwork metadata, without touching the AYA store."""

import argparse
import copy
import json
from pathlib import Path
from PIL import Image, ImageOps

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source", type=Path, help="Approved public catalog.json")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
catalog = copy.deepcopy(json.loads(args.source.read_text()))


def preview(source):
    local = args.source.parent / source.lstrip("/")
    relative = Path("previews") / Path(source).relative_to("/media").with_suffix(
        ".webp"
    )
    target = root / "public" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(local) as image:
        image.convert("RGBA").save(target, "WEBP", quality=86, method=6)
    return "/" + relative.as_posix()


for pack in catalog["packs"]:
    for key in ("banner", "cover"):
        pack[key] = preview(pack[key])
    for stickers in pack["stickers"].values():
        for sticker in stickers:
            sticker["poster"] = preview(sticker["poster"])
            sticker["gif"] = "https://aya.lazying.art" + sticker["gif"]
catalog["attribution"] = {
    "owner": "LazyingArt",
    "source": "https://aya.lazying.art",
    "use": "personal-use previews; independent WeSticker subscriptions",
}
(root / "public/catalog.json").write_text(
    json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
)
poster = args.source.parent / "media/vol-01/compact/01-aya-morning.png"
with Image.open(poster) as image:
    for size in (192, 512):
        canvas = Image.new("RGBA", (size, size), "#fff1f6")
        figure = ImageOps.contain(
            image.convert("RGBA"), (round(size * 0.9), round(size * 0.9))
        )
        canvas.alpha_composite(
            figure, ((size - figure.width) // 2, (size - figure.height) // 2)
        )
        canvas.save(root / "public" / f"icon-{size}.png")
print(
    json.dumps(
        {
            "packs": len(catalog["packs"]),
            "stickers": sum(p["count"] for p in catalog["packs"]),
        }
    )
)
