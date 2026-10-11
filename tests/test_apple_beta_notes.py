from pathlib import Path

import pytest


@pytest.fixture
def publisher(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from scripts import apple_beta_publish
    return apple_beta_publish


def test_metadata_attachment_requires_current_notes(publisher):
    with pytest.raises(ValueError, match="exact build"):
        publisher.release_notes("attach", None)


@pytest.mark.parametrize("action", ["status", "upload"])
def test_non_metadata_actions_do_not_invent_notes(publisher, action):
    assert publisher.release_notes(action, None) is None


def test_notes_preserve_reviewed_scope(publisher, tmp_path):
    notes = tmp_path / "notes.txt"
    notes.write_text("  Compact chat. Payment qualification is separate.\n")
    assert publisher.release_notes("attach", notes) == "Compact chat. Payment qualification is separate."


@pytest.mark.parametrize("text", [" \n", "x" * 4001])
def test_invalid_notes_rejected(publisher, tmp_path, text):
    notes = tmp_path / "notes.txt"
    notes.write_text(text)
    with pytest.raises(ValueError, match="1-4000"):
        publisher.release_notes("attach", notes)
