"""Export the selected icon master for web and genuine native applications."""

from pathlib import Path
import json
from PIL import Image, ImageOps

root = Path(__file__).resolve().parents[1]
with Image.open(root / "assets/icons/aya-lala-sky-blue-v2.png") as source:
    image = source.convert("RGBA")
    for side in (192, 512):
        image.resize((side, side), Image.Resampling.LANCZOS).save(root / f"public/icon-{side}.png")
    for density, side in {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }.items():
        folder = root / "android/app/src/main/res" / ("mipmap-" + density)
        folder.mkdir(parents=True, exist_ok=True)
        for name in ("ic_launcher.png", "ic_launcher_round.png"):
            image.resize((side, side), Image.Resampling.LANCZOS).save(folder / name)
        canvas = round(side * 2.25)
        foreground = Image.new("RGBA", (canvas, canvas), "#C5EAFE")
        scaled = ImageOps.contain(image, (round(canvas * .74), round(canvas * .74)), Image.Resampling.LANCZOS)
        foreground.alpha_composite(scaled, ((canvas-scaled.width)//2, (canvas-scaled.height)//2))
        foreground.save(folder / "ic_launcher_foreground.png")
    folder = root / "ios/App/App/Assets.xcassets/AppIcon.appiconset"
    image.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS).save(
        folder / "AppIcon-512@2x.png"
    )
    folder = root / "macos/Assets.xcassets/AppIcon.appiconset"
    folder.mkdir(parents=True, exist_ok=True)
    images = []
    for side in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            name = f"icon-{side}-{scale}.png"
            image.resize((side * scale, side * scale), Image.Resampling.LANCZOS).save(folder / name)
            images.append({"idiom": "mac", "size": f"{side}x{side}", "scale": f"{scale}x", "filename": name})
    (folder / "Contents.json").write_text(json.dumps({"images": images, "info": {"version": 1, "author": "xcode"}}, indent=2))
print("Web, Android, iOS and macOS icons exported from Aya + Lala master.")
