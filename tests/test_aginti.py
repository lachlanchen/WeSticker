import json
from pathlib import Path

import pytest

from server import aginti
from server.generation import capabilities
from server.local_video import OutcomeUncertain
from server.media import exterior_alpha
from PIL import Image, ImageDraw


def test_aginti_requires_qualification_and_enable():
    cfg = {"image_provider": "aginti", "aginti_root": "/operator/path", "image_generation_enabled": True}
    assert not capabilities(cfg)["ai_images"]
    assert capabilities(cfg | {"aginti_qualified": True})["ai_images"]
    assert not capabilities(cfg | {"aginti_qualified": "true"})["ai_images"]


def test_aginti_receipt_recovery_never_calls_provider(tmp_path, monkeypatch):
    ref = tmp_path / "reference.png"
    ref.write_bytes(b"fixture-reference")
    calls = []
    def provider(cfg, request):
        calls.append(request)
        out = Path(request["folder"]) / "original.png"
        out.write_bytes(b"fixture-generated-image")
        return {"path": str(out)}
    monkeypatch.setattr(aginti, "invoke", provider)
    cfg = {"state": str(tmp_path)}
    assert aginti.generate(cfg, {"id": "job"}, {"id": "item"}, "hello", [ref]) == b"fixture-generated-image"
    assert aginti.generate(cfg, {"id": "job"}, {"id": "item"}, "hello", [ref]) == b"fixture-generated-image"
    assert len(calls) == 1
    with pytest.raises(OutcomeUncertain, match="different"):
        aginti.generate(cfg, {"id": "job"}, {"id": "item"}, "changed", [ref])
    assert len(calls) == 1


def test_aginti_lost_response_is_uncertain(tmp_path, monkeypatch):
    ref = tmp_path / "reference.png"
    ref.write_bytes(b"fixture-reference")
    def failed(cfg, request):
        (Path(request["folder"]) / "network-intent.json").write_text("{}")
        raise ValueError("Transport unavailable")
    monkeypatch.setattr(aginti, "invoke", failed)
    with pytest.raises(OutcomeUncertain):
        aginti.generate({"state": str(tmp_path)}, {"id": "job"}, {"id": "item"}, "hello", [ref])


def test_exterior_matte_preserves_enclosed_white_and_source():
    original = Image.new("RGBA", (80, 80), "white")
    draw = ImageDraw.Draw(original)
    draw.rectangle((10, 10, 70, 70), fill="black")
    draw.rectangle((25, 25, 55, 55), fill="white")
    image = exterior_alpha(original)
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((40, 40)) == (255, 255, 255, 255)
    assert original.getpixel((0, 0))[3] == 255
