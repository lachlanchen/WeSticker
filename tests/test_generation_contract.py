import json
import fcntl
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from server.generation import capabilities, check_moderation, load_keys, private_key, provider_origin
from server.app import create_app
from server.store import database
from server.worker import work_once
from server.local_video import animate, OutcomeUncertain, require_idle, video_output
from test_app import ORIGIN, call, draft, signup


@pytest.mark.parametrize("payload", [{}, {"results": []}, {"results": None},
                                    {"results": [{}]}, {"results": [{"flagged": "false"}]},
                                    {"results": [{"flagged": 0}]}, []])
def test_moderation_must_explicitly_accept(payload):
    with pytest.raises(ValueError, match="incomplete"):
        check_moderation(payload)


def test_moderation_accept_and_block():
    check_moderation({"results": [{"flagged": False}]})
    with pytest.raises(ValueError, match="safety review"):
        check_moderation({"results": [{"flagged": False}, {"flagged": True}]})


def test_key_is_not_permission_to_sell_generation():
    cfg = {"image_api_key": "fixture", "local_video_url": "http://127.0.0.1:8190"}
    assert capabilities(cfg) == {"ai_images": False, "animation": False}
    assert capabilities(cfg | {"image_generation_enabled": True})["ai_images"]
    assert not capabilities(cfg | {"image_generation_enabled": "true"})["ai_images"]
    assert capabilities({"animation_enabled": True, "moderation_api_key": "safety",
                         "local_video_url": cfg["local_video_url"]})["animation"]


def test_private_key_files(tmp_path):
    path = tmp_path / "image.key"
    path.write_text("fixture-key")
    path.chmod(0o600)
    assert load_keys({"image_api_key_file": str(path)})["image_api_key"] == "fixture-key"
    with pytest.raises(ValueError, match="exactly one"):
        load_keys({"image_api_key_file": str(path), "image_api_key": "other"})
    alias = tmp_path / "alias"
    alias.symlink_to(path)
    with pytest.raises(ValueError):
        private_key(alias)
    path.chmod(0o644)
    with pytest.raises(ValueError):
        private_key(path)


@pytest.mark.parametrize("url", ["http://remote.example/v1", "https://x:y@example.com/v1",
                                "https://example.com/v1?key=secret", "file:///tmp/api"])
def test_provider_transport_is_pinned(url):
    with pytest.raises(ValueError):
        provider_origin(url)


def test_incomplete_moderation_refunds_without_image_submission(tmp_path, monkeypatch):
    app = create_app({"state": str(tmp_path), "origin": ORIGIN, "local_accounts": True,
                      "image_api_key": "fixture", "image_generation_enabled": True})
    client = app.test_client()
    signup(client)
    pack, _ = draft(client)
    row = client.get("/api/workspace").json["packs"][0]["items"][0]
    calls = []
    def incomplete(url, **kwargs):
        calls.append(url)
        assert kwargs["allow_redirects"] is False
        return NS(raise_for_status=lambda: None, json=lambda: {"results": []})
    monkeypatch.setattr("server.worker.requests.post", incomplete)
    result = call(client, f"/api/packs/{pack}/generate", {
        "kind": "ai", "items": [row["id"]], "attempt": "moderation-incomplete-1", "consent": True})
    assert result.status_code == 202
    work_once(app.config["WESTICKER"])
    assert len(calls) == 1 and calls[0].endswith("/moderations")
    assert client.get("/api/bootstrap").json["limits"]["trial_images"] == 1
    assert client.get("/api/workspace").json["jobs"][0]["state"] == "failed"
    assert not list(tmp_path.glob("renders/*/*/image-intent.json"))


@pytest.mark.parametrize("url", ["https://localhost:8190", "http://user@127.0.0.1:8190",
                                "http://127.0.0.1:8190/api", "http://127.0.0.1:8190?remote=x"])
def test_local_renderer_requires_an_exact_loopback_origin(tmp_path, url):
    with pytest.raises(ValueError, match="protected local"):
        animate({"state": str(tmp_path), "local_video_url": url},
                {"id": "job"}, {"id": "item"}, tmp_path / "not-read.png")


def test_animation_attempt_cannot_be_submitted_concurrently(tmp_path):
    folder = tmp_path / "renders/job/item"
    folder.mkdir(parents=True)
    with (folder / "attempt.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(OutcomeUncertain, match="already being observed"):
            animate({"state": str(tmp_path), "local_video_url": "http://127.0.0.1:8190"},
                    {"id": "job"}, {"id": "item"}, tmp_path / "not-read.png")


def test_animation_recovery_must_match_the_original_request(tmp_path):
    folder = tmp_path / "renders/job/item"
    folder.mkdir(parents=True)
    (folder / "intent.json").write_text(json.dumps({"fingerprint": "different"}))
    (folder / "receipt.json").write_text(json.dumps({"id": "prior-provider-job"}))
    image = tmp_path / "ref.png"
    image.write_bytes(b"source fingerprint only; no decode or upload")
    with pytest.raises(OutcomeUncertain, match="different or unverified"):
        animate({"state": str(tmp_path), "local_video_url": "http://127.0.0.1:8190"},
                {"id": "job"}, {"id": "item", "label": "Hello"}, image)


@pytest.mark.parametrize("jobs,series,prompt", [([{"id": "busy"}], [], ""),
    ([], [{"status": "running"}], ""), ([], [], "Shared instructions"),
    ([], [{"status": "completed"}] * 100, "")])
def test_local_renderer_preserves_shared_active_work(jobs, series, prompt):
    def get(url, **kw):
        value = {"jobs": jobs} if "/jobs?" in url else {"series": series} if "/series?" in url else {"system_prompt": prompt}
        return NS(raise_for_status=lambda: None, json=lambda: value)
    with pytest.raises(ValueError, match="deferred"):
        require_idle(NS(get=get), "http://127.0.0.1:8190")


def test_current_localvideo_output_uses_media_type_not_required_filename():
    assert video_output({"outputs": [{"id": 0, "media_type": "video", "node_id": "15"}]}) == 0
    assert video_output({"outputs": [{"id": 3, "filename": "original.mp4"}]}) == 3
    for outputs in ([], [{"id": 0, "media_type": "image"}],
                    [{"id": 0, "media_type": "video"}, {"id": 1, "media_type": "video"}]):
        with pytest.raises(OutcomeUncertain):
            video_output({"outputs": outputs})
