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


@pytest.mark.parametrize("count,internal,app", [(0, True, "app"), (2, True, "app"),
                                               (1, False, "app"), (1, True, "other")])
def test_group_lookup_fails_closed_without_store_writes(publisher, count, internal, app):
    class API:
        def list(self, resource, **filters):
            return [{"id": "group", "attributes": {"name": "WeSticker Internal",
                                                     "isInternalGroup": internal}}] * count

        def call(self, path):
            assert path == "/v1/betaGroups/group/app"
            return {"data": {"id": app}}

    with pytest.raises(RuntimeError):
        publisher.existing_internal_group(API(), "app")


def test_existing_internal_group_is_reused(publisher):
    class API:
        def list(self, resource, **filters):
            assert resource == "betaGroups" and filters == {"app": "app"}
            return [{"id": "group", "attributes": {"name": "WeSticker Internal", "isInternalGroup": True}}]

        def call(self, path):
            assert path == "/v1/betaGroups/group/app"
            return {"data": {"id": "app"}}

    assert publisher.existing_internal_group(API(), "app")["id"] == "group"
