"""Bundle the shared public catalog/posters for real native Apple and Android UI."""
import json
from pathlib import Path
import shutil
from PIL import Image

root = Path(__file__).resolve().parents[1]
source = root / "public"
for destination, apple in [(root / "android/app/src/main/native-assets", False), (root / "apple/CatalogAssets", True)]:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "creator-plans.json", destination / "creator-plans.json")
    shutil.copy2(source / "icon-512.png", destination / "app-icon.png")
    data = json.loads((source / "catalog.json").read_text())
    for pack in data["packs"]:
        for item in [pack] + [s for group in pack["stickers"].values() for s in group]:
            field = "banner" if "banner" in item else "poster"
            relative = item[field].lstrip("/")
            target = destination / relative
            if apple:
                target = target.with_suffix(".png")
                item[field] = "/" + str(target.relative_to(destination))
            target.parent.mkdir(parents=True, exist_ok=True)
            if apple:
                with Image.open(source / relative) as im:
                    im.save(target)
            else:
                shutil.copy2(source / relative, target)
    (destination / "catalog.json").write_text(json.dumps(data, ensure_ascii=False))
print("Native catalog and posters synchronized; no HTML/JavaScript bundled.")
