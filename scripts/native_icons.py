"""Resize approved public artwork into platform icon assets; no generation."""

from pathlib import Path
from PIL import Image, ImageOps

root = Path(__file__).resolve().parents[1]
with Image.open(root / "public/icon-512.png") as source:
    image = source.convert("RGBA")
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
        foreground = Image.new("RGBA", (side * 2, side * 2))
        scaled = ImageOps.contain(image, (side, side), Image.Resampling.LANCZOS)
        foreground.alpha_composite(scaled, (side // 2, side // 2))
        foreground.save(folder / "ic_launcher_foreground.png")
    folder = root / "ios/App/App/Assets.xcassets/AppIcon.appiconset"
    image.convert("RGB").resize((1024, 1024), Image.Resampling.LANCZOS).save(
        folder / "AppIcon-512@2x.png"
    )
print("Native icons exported from approved Aya artwork.")
