import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location("line_export", Path(__file__).parents[1] / "scripts/export_line_pack.py")
line = importlib.util.module_from_spec(spec)
spec.loader.exec_module(line)


def test_exterior_alpha_keeps_enclosed_white():
    image = Image.new("RGBA", (32, 32), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((6, 6, 25, 25), outline="black", width=3)
    result = line.exterior_alpha(image)
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((15, 15))[3] == 255
    assert result.getpixel((6, 6))[3] == 255
    assert image.getpixel((0, 0))[3] == 255


def test_apng_frames_duration_transparency(tmp_path):
    frames = []
    for i in range(20):
        frame = Image.new("RGBA", (270, 270))
        ImageDraw.Draw(frame).ellipse((20 + i, 20, 180 + i, 180), fill="orange")
        frames.append(frame)
    path = tmp_path / "01.png"
    line.encode(frames, path)
    result = line.validate(path, (270, 270))
    assert result["frames"] == 20
    assert result["duration_ms"] == 4000


def test_wrong_pack_count_rejected_without_output(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="8, 16 or 24"):
        line.export_pack({"packs": [{"id": "twelve", "stickers": {"ja": [{}] * 12}}]}, tmp_path, "twelve", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_palette_fallback_retains_transparency_and_white(tmp_path):
    frames = []
    for i in range(20):
        frame = Image.new("RGBA", (270, 270))
        draw = ImageDraw.Draw(frame)
        draw.rectangle((20 + i, 20, 180 + i, 180), fill="white", outline="black", width=3)
        frames.append(frame)
    target = tmp_path / "palette.png"
    assert line.encode(frames, target, palettes=(192,)) == 192
    line.validate(target, (270, 270))
    with Image.open(target) as image:
        for index in range(image.n_frames):
            image.seek(index)
            rgba = image.convert("RGBA")
            assert rgba.getpixel((0, 0))[3] == 0
            # Palette sampling can shift white slightly; it must stay opaque.
            r, g, b, alpha = rgba.getpixel((100, 100))
            assert min(r, g, b) >= 245 and alpha == 255
