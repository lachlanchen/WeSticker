"""Receipt observation and permission fixtures; no real HTTP, GPU or process control."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from server import local_video as adapter
from server import local_video_lifecycle as life
from test_local_video_lifecycle import runtime, write


OWNED = {"webapp": {"pid": 99999991, "instance": "original-web"},
         "comfyui": {"pid": 99999992, "instance": "original-engine"}}
PROVIDER = "12345678-1234-1234-1234-123456789012"


def policy(runtime, **updates):
    path = runtime.private / "westicker-lifecycle-policy.json"
    write(path, life.private_json(path) | updates)


@pytest.mark.parametrize("updates", [{"enabled": False}, {"allow_start": False},
    {"enabled": False, "allow_start": False}, {"allow_stop": False}])
def test_closed_admission_preserves_identity_only_observation(runtime, monkeypatch, updates):
    policy(runtime, **updates)
    monkeypatch.setattr(runtime, "identities", lambda: OWNED)
    monkeypatch.setattr(life, "resources", lambda *a: pytest.fail("No cold gate for observation"))
    monkeypatch.setattr(life, "idle", lambda *a: pytest.fail("Original job may be running"))
    monkeypatch.setattr(life, "get_json", lambda *a: pytest.fail("No deep/model health gate"))
    monkeypatch.setattr(runtime, "environment", lambda: pytest.fail("No driver environment needed"))
    assert runtime.observe(OWNED) == OWNED
    assert runtime.ready(OWNED, new_submission=False) == OWNED
    with pytest.raises(life.Deferred, match="owner_policy"):
        runtime.ready(OWNED)
    assert life.status({"local_video_runtime_root": str(runtime.root),
                        "local_video_url": "http://127.0.0.1:8190"})["can_submit"] is False


@pytest.mark.parametrize("current", [{}, {"webapp": OWNED["webapp"]},
    OWNED | {"webapp": OWNED["webapp"] | {"instance": "replacement"}},
    OWNED | {"comfyui": OWNED["comfyui"] | {"pid": 111}}])
def test_observation_refuses_missing_partial_or_replaced_identity(runtime, monkeypatch, current):
    monkeypatch.setattr(runtime, "identities", lambda: current)
    monkeypatch.setattr(runtime.session, "get", lambda *a, **kw: pytest.fail("No HTTP to a replacement"))
    with pytest.raises(life.Deferred, match="ownership"):
        runtime.observe(OWNED)


@pytest.mark.parametrize("field", ["enabled", "allow_start", "allow_stop"])
@pytest.mark.parametrize("value", [None, "false", 0])
def test_observation_does_not_accept_malformed_permission_flags(runtime, field, value):
    policy(runtime, **{field: value})
    with pytest.raises(life.Deferred, match="owner_policy"):
        runtime.policy("observe")


@pytest.mark.parametrize("updates", [{"enabled": False}, {"allow_start": False},
    {"enabled": False, "allow_start": False}])
def test_closed_new_work_can_drain_exact_owned_runtime(runtime, monkeypatch, updates):
    policy(runtime, **updates)
    write(runtime.root / "runtime/webapp-state.json", OWNED["webapp"])
    calls = []
    monkeypatch.setattr(runtime, "identities", lambda: OWNED)
    monkeypatch.setattr(runtime, "persisted_idle", lambda: None)
    monkeypatch.setattr(runtime, "ports_free", lambda: None)
    monkeypatch.setattr(life, "idle", lambda session: None)
    monkeypatch.setattr(runtime, "drain", lambda *a: None)
    monkeypatch.setattr(runtime, "release", lambda *a: None)
    monkeypatch.setattr(life, "resources", lambda *a: pytest.fail("Drain must not need free GPU memory"))
    monkeypatch.setattr(runtime, "identity_command", lambda *a: calls.append(a))
    monkeypatch.setattr(runtime, "command", lambda args, **kw: calls.append(tuple(args)))
    runtime.stop(OWNED)
    assert calls[0][:2] == ("webapp", "signal")
    assert calls[-1][1:] == ("--expect-pid", "99999992", "--expect-instance", "original-engine")


@pytest.mark.parametrize("during_idle", [False, True])
def test_explicit_stop_revocation_blocks_signalling(runtime, monkeypatch, during_idle):
    monkeypatch.setattr(runtime, "identities", lambda: OWNED)
    monkeypatch.setattr(runtime, "identity_command", lambda *a: pytest.fail("Revoked cleanup must not signal"))
    monkeypatch.setattr(runtime, "command", lambda *a, **kw: pytest.fail("Revoked cleanup must not stop engine"))
    monkeypatch.setattr(life, "idle", lambda *a: None)
    monkeypatch.setattr(runtime, "persisted_idle", lambda: policy(runtime, allow_stop=False))
    if not during_idle:
        policy(runtime, allow_stop=False)
    with pytest.raises(life.Deferred, match="drain_revoked"):
        runtime.stop(OWNED)


def saved_attempt(runtime, tmp_path):
    source = tmp_path / "source.png"
    source.write_bytes(b"approved fixture reference")
    item = {"id": "item", "label": "Hello"}
    folder = tmp_path / "renders/job/item"
    folder.mkdir(parents=True)
    fingerprint = hashlib.sha256(json.dumps({
        "source": hashlib.sha256(source.read_bytes()).hexdigest(), "label": "Hello", "action": "",
        "profile": "quality_int8_offload", "size": [512, 512], "duration": 5,
    }, sort_keys=True).encode()).hexdigest()
    key = hashlib.sha256(str(folder.resolve()).encode()).hexdigest()
    write(folder / "intent.json", {"fingerprint": fingerprint})
    write(folder / "receipt.json", {"id": PROVIDER})
    write(runtime.path, {"version": 1, "state": "monitoring", "owned": OWNED,
        "attempt": {"key": key, "fingerprint": fingerprint}, "provider": PROVIDER,
        "boot_id": life.BOOT.read_text().strip()})
    cfg = {"state": str(tmp_path), "local_video_runtime_root": str(runtime.root),
           "local_video_url": "http://127.0.0.1:8190"}
    return source, item, folder, cfg


def observation_fixture(runtime, monkeypatch, *, replace_at=None):
    calls = []
    changed = False
    def identities():
        return OWNED | {"webapp": {"pid": 1, "instance": "replacement"}} if changed else OWNED
    def change(stage):
        nonlocal changed
        if stage == replace_at:
            changed = True
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            change("status")
            return {"id": PROVIDER, "status": "completed", "outputs": [{"id": 0, "media_type": "video"}]}
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def iter_content(self, size):
            yield b"fixture video bytes"
            change("download")
    def get(url, **kwargs):
        assert "/api/jobs/" + PROVIDER in url
        calls.append(url)
        return Response()
    session = NS(get=get, close=lambda: None,
                 post=lambda *a, **kw: pytest.fail("Receipt recovery must never POST"))
    monkeypatch.setattr(runtime, "identities", identities)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    monkeypatch.setattr(adapter, "local_session", lambda: session)
    monkeypatch.setattr(runtime, "start", lambda *a: pytest.fail("No start during receipt recovery"))
    monkeypatch.setattr(runtime, "ready", lambda *a, **kw: pytest.fail("No readiness gate during recovery"))
    monkeypatch.setattr(life, "resources", lambda *a: pytest.fail("No cold resource gate"))
    monkeypatch.setattr(life, "get_json", lambda *a: pytest.fail("No model/queue readiness gate"))
    def ffmpeg(args, **kwargs):
        assert args[0] == "ffmpeg"
        if "-loop" in args:
            Path(args[-1]).write_bytes(b"GIF89a fixture")
    monkeypatch.setattr(adapter.subprocess, "run", ffmpeg)
    change("before")
    return calls


@pytest.mark.parametrize("batch_mode", [False, True])
@pytest.mark.parametrize("stop_allowed", [False, True])
def test_managed_receipt_recovers_after_admission_closure(runtime, tmp_path, monkeypatch, batch_mode, stop_allowed):
    source, item, folder, cfg = saved_attempt(runtime, tmp_path)
    policy(runtime, enabled=False, allow_start=False, allow_stop=stop_allowed)
    calls = observation_fixture(runtime, monkeypatch)
    stopped = []
    def stop(owned, fence=None):
        runtime.policy("drain")
        stopped.append(owned)
    monkeypatch.setattr(runtime, "stop", stop)
    if batch_mode:
        with life.job_admission(cfg) as batch:
            result = adapter.animate(cfg, {"id": "job"}, item, source, batch=batch)
    else:
        result = adapter.animate(cfg, {"id": "job"}, item, source)
    assert result == folder / "clean.gif" and result.exists()
    assert len(calls) == 2 and (folder / "receipt.json").exists()
    record = life.private_json(runtime.path)
    assert record["state"] == ("offline" if stop_allowed else "draining")
    assert len(stopped) == int(stop_allowed)
    if not stop_allowed:
        assert record["cleanup"]["code"] == "drain_revoked" and record["owned"] == OWNED


@pytest.mark.parametrize("stage,count", [("before", 0), ("status", 1), ("download", 2)])
def test_receipt_recovery_checks_identity_before_and_after_io(runtime, tmp_path, monkeypatch, stage, count):
    source, item, folder, cfg = saved_attempt(runtime, tmp_path)
    calls = observation_fixture(runtime, monkeypatch, replace_at=stage)
    monkeypatch.setattr(runtime, "stop", lambda *a: pytest.fail("Uncertain observation must retain ownership"))
    with pytest.raises(adapter.OutcomeUncertain):
        adapter.animate(cfg, {"id": "job"}, item, source)
    assert len(calls) == count
    assert not (folder / "original.mp4").exists() and not (folder / "clean.gif").exists()
    if stage == "download":
        assert (folder / "download.part").read_bytes() == b"fixture video bytes"
    else:
        assert not (folder / "status.json").exists()
    record = life.private_json(runtime.path)
    assert record["provider"] == PROVIDER and record["owned"] == OWNED


def test_managed_receipt_without_ownership_record_never_observes(runtime, tmp_path, monkeypatch):
    source, item, folder, cfg = saved_attempt(runtime, tmp_path)
    runtime.path.unlink()
    calls = observation_fixture(runtime, monkeypatch)
    with pytest.raises(adapter.OutcomeUncertain):
        adapter.animate(cfg, {"id": "job"}, item, source)
    assert calls == [] and not runtime.path.exists()


def test_job_context_after_closure_cannot_admit_a_new_item(runtime, monkeypatch):
    policy(runtime, enabled=False)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    cfg = {}
    with life.job_admission(cfg) as batch:
        with pytest.raises(life.Deferred, match="owner_policy"):
            with life.admission(cfg, "new", "fingerprint", batch=batch):
                pytest.fail("Closed admission must not yield a new attempt")
    assert not runtime.path.exists()
