import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw
import pytest

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


def test_selected_frames_does_not_rekey_white_foreground(tmp_path):
    frames = []
    for index in range(5):
        frame = Image.new("RGBA", (32, 32))
        ImageDraw.Draw(frame).rectangle((0, 2 + index, 16, 20 + index), fill="white")
        frames.append(frame)
    source = tmp_path / "master.png"
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=200)
    selected, _ = line.selected_frames(source, 32)
    assert selected[0].getpixel((0, 10)) == (255, 255, 255, 255)
    assert selected[0].getpixel((31, 31))[3] == 0


def test_opaque_source_requires_explicit_legacy_choice(tmp_path):
    source = tmp_path / "opaque.png"
    Image.new("RGB", (32, 32), "white").save(source)
    with pytest.raises(ValueError, match="reviewed RGBA"):
        line.selected_frames(source, 32)


def test_blank_alpha_master_is_rejected(tmp_path):
    source = tmp_path / "blank.png"
    Image.new("RGBA", (32, 32)).save(source)
    with pytest.raises(ValueError, match="Blank alpha"):
        line.selected_frames(source, 32)


@pytest.mark.parametrize("palettes", [(None,), (192,), (128,)])
def test_apng_retains_every_soft_alpha_value(tmp_path, palettes):
    frames = []
    for index in range(20):
        frame = Image.new("RGBA", (270, 270))
        draw = ImageDraw.Draw(frame)
        for alpha in range(1, 256):
            draw.line((alpha, 20 + index, alpha, 180 + index), fill=(255, 255, 255, alpha))
        frames.append(frame)
    target = tmp_path / "soft.png"
    line.encode(frames, target, palettes=palettes)
    line.validate(target, (270, 270))
    with Image.open(target) as image:
        for index, original in enumerate(frames):
            image.seek(index)
            assert image.convert("RGBA").getchannel("A").tobytes() == original.getchannel("A").tobytes()


def test_joint_palette_keeps_white_parts_and_soft_edges(tmp_path):
    import shutil
    if not shutil.which("pngquant"):
        pytest.skip("Optional pngquant not installed")
    frames = []
    for i in range(20):
        frame = Image.new("RGBA", (270, 270))
        draw = ImageDraw.Draw(frame)
        draw.rectangle((30+i, 30, 130+i, 150), fill="white")
        draw.line((29+i, 30, 29+i, 150), fill=(255,255,255,100))
        draw.rectangle((60+i, 70, 80+i, 100), fill=(0,0,0,0))
        frames.append(frame)
    target = tmp_path/"indexed.png"
    report = line.encode_soft_palette(frames, target)
    assert report["solid_loss_fraction"] == 0
    with Image.open(target) as image:
        assert image.n_frames == 20
        for i in range(20):
            image.seek(i)
            rgba = image.convert("RGBA")
            assert rgba.getpixel((40+i,60))[3] == 255
            assert rgba.getpixel((65+i,80))[3] == 0
            assert 0 < rgba.getpixel((29+i,60))[3] < 255


def test_joint_palette_accepts_identical_frames_with_preserved_timing(tmp_path):
    import shutil
    if not shutil.which("pngquant"):
        pytest.skip("Optional pngquant not installed")
    frames = []
    for index in range(10):
        frame = Image.new("RGBA", (80,80))
        ImageDraw.Draw(frame).rectangle((10+index,10,40+index,60), fill="white")
        frames.extend([frame,frame.copy()])
    target = tmp_path/"coalesced.png"
    report = line.encode_soft_palette(frames,target)
    assert report["solid_loss_fraction"] == 0
    result = line.validate(target,(80,80))
    assert result["duration_ms"] == 4000
    assert 5 <= result["frames"] <= 20
