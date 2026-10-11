"""Lifecycle fixtures never start a model, use CUDA, or contact a real service."""

import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace as NS

import pytest
import requests
from PIL import Image

from server import local_video as adapter
from server import local_video_lifecycle as life


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    life.atomic_json(path, value)


@pytest.fixture
def runtime(tmp_path):
    root = tmp_path / "runtime-root"
    root.mkdir()
    private = root / "runtime/private"
    private.mkdir(parents=True)
    policy = {"version": 1, "owner": "westicker", "exclusive": True, "enabled": True,
              "root": str(root), "allow_start": True, "allow_stop": True}
    write(private / "westicker-lifecycle-policy.json", policy)
    value = life.Runtime({"local_video_runtime_root": str(root), "local_video_url": "http://127.0.0.1:8190"})
    yield value
    value.session.close()


class FakeRuntime:
    def __init__(self, root):
        self.path = root / "admission.json"
        self.lock = root / "admission.lock"
        self.session = NS(close=lambda: None)
        self.started = self.stopped = self.checked = 0
        self.changed = False

    def policy(self):
        return {}

    def after_boot(self, record):
        return record

    def start(self, record, save):
        self.started += 1
        record["owned"] = {"comfyui": {"pid": 123, "instance": "engine"},
                           "webapp": {"pid": 456, "instance": "studio"}}
        save()

    def ready(self, owned):
        self.checked += 1
        if self.changed:
            raise life.Deferred("busy", "ownership", "Replaced runtime")

    def stop(self, owned):
        if self.changed:
            raise life.Deferred("draining", "ownership", "Replaced runtime")
        if owned:
            self.stopped += 1


def test_default_is_offline_without_any_runtime_command(monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: pytest.fail("No process operation allowed"))
    assert life.status({})["code"] == "owner_setup"


@pytest.mark.parametrize("field,value", [("owner", "other"), ("exclusive", False),
    ("enabled", False), ("allow_start", False), ("allow_stop", False), ("root", "/other"), ("version", 2)])
def test_installation_policy_requires_explicit_owner_control(runtime, field, value):
    path = runtime.private / "westicker-lifecycle-policy.json"
    policy = life.private_json(path)
    policy[field] = value
    write(path, policy)
    with pytest.raises(life.Deferred, match="owner_policy"):
        runtime.policy()


def test_private_policy_rejects_public_permissions_and_symlink(runtime):
    path = runtime.private / "westicker-lifecycle-policy.json"
    path.chmod(0o644)
    with pytest.raises(life.Deferred):
        runtime.policy()
    original = path.with_suffix(".original")
    path.rename(original)
    path.symlink_to(original)
    with pytest.raises(life.Deferred):
        runtime.policy()


def test_installed_policy_survives_reboot_and_elapsed_days(runtime, monkeypatch, tmp_path):
    boot = tmp_path / "boot"
    boot.write_text("different-boot")
    monkeypatch.setattr(life, "BOOT", boot)
    monkeypatch.setattr(life.time, "time", lambda: 999999999999)
    assert runtime.policy()["enabled"] is True


def test_start_environment_never_inherits_weakened_gates(runtime, monkeypatch):
    monkeypatch.setenv("H3_PARTIAL_PROFILE", "fl-int8-turbo")
    monkeypatch.setenv("H3_MIN_RAM_GIB", "1")
    monkeypatch.setenv("H3_CUDA_DEVICES", "0,1")
    monkeypatch.setenv("LD_LIBRARY_PATH", "/unverified")
    env = runtime.environment()
    assert env["H3_CUDA_DEVICES"] == "0" and env["H3_AUX_DEVICE"] == "gpu:0"
    assert env["H3_MIN_RAM_GIB"] == "48" and env["H3_MIN_GPU_FREE_MIB"] == "20000"
    assert "LD_LIBRARY_PATH" not in env and "H3_PARTIAL_PROFILE" not in env


def test_stale_driver_override_fails_closed_when_native_probe_fails(runtime, monkeypatch):
    path = runtime.private / "westicker-lifecycle-policy.json"
    value = life.private_json(path)
    value["driver"] = {"version": "0.1"}
    write(path, value)
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(subprocess.CalledProcessError(18, "nvidia-smi")))
    with pytest.raises(life.Deferred, match="driver_identity"):
        runtime.environment()


def test_repaired_native_driver_supersedes_old_compatibility_bundle(runtime, monkeypatch):
    path = runtime.private / "westicker-lifecycle-policy.json"
    value = life.private_json(path)
    value["driver"] = {"version": "0.1"}
    write(path, value)
    read = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw: "Kernel Module 999.10 installed" if str(p) == "/proc/driver/nvidia/version" else read(p, *a, **kw))
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: NS(stdout="999.10\n999.10\n"))
    assert "LD_LIBRARY_PATH" not in runtime.environment()


def resource_fixture(monkeypatch, *, ram=48, swap=75, free=20000, pids=(), failure=False):
    read = Path.read_text
    memory = f"MemAvailable: {int(ram * 1024**2)} kB\nSwapTotal: 100 kB\nSwapFree: {100-swap} kB\n"
    monkeypatch.setattr(Path, "read_text", lambda p, *a, **kw: memory if str(p) == "/proc/meminfo" else read(p, *a, **kw))
    def run(command, **kwargs):
        assert command[0] == "nvidia-smi" and kwargs["timeout"] == 10
        if failure:
            raise subprocess.CalledProcessError(18, command)
        return NS(stdout=(f"0, GPU-zero, {free}\n1, GPU-peer, 10\n" if "--query-gpu=" in command[1]
                          else "\n".join(f"{gpu}, {pid}" for gpu, pid in pids)))
    monkeypatch.setattr(subprocess, "run", run)


@pytest.mark.parametrize("values,code", [({"ram": 47.99}, "ram"), ({"swap": 76}, "swap"),
    ({"free": 19999}, "gpu_memory"), ({"pids": [("GPU-zero", 9)]}, "gpu_owner"), ({"failure": True}, "gpu_probe")])
def test_resources_fail_closed(monkeypatch, values, code):
    resource_fixture(monkeypatch, **values)
    with pytest.raises(life.Deferred, match=code):
        life.resources({})


def test_gate_boundaries_gpu1_peer_and_owned_engine(monkeypatch):
    resource_fixture(monkeypatch, pids=[("GPU-zero", 8), ("GPU-peer", 9)])
    life.resources({}, {8})


def test_shared_slot_is_exclusive_and_not_unlinked(tmp_path):
    lock = tmp_path / "lease.lock"
    with life.exclusive(lock):
        with pytest.raises(life.Deferred, match="lease_held"):
            with life.exclusive(lock):
                pytest.fail("Concurrent admission")
    with life.exclusive(lock):
        assert lock.exists()


def test_completed_attempt_cleans_only_started_runtime(tmp_path):
    runtime = FakeRuntime(tmp_path)
    lease = life.Admission(runtime, "attempt", "fingerprint", False)
    lease.prepare()
    lease.submitting()
    lease.receipt("provider")
    lease.complete()
    lease.close()
    assert runtime.started == runtime.stopped == 1 and runtime.checked == 2
    assert life.private_json(runtime.path)["state"] == "offline"


def test_ambiguous_post_holds_slot_across_crash_and_rejects_new_attempt(tmp_path):
    runtime = FakeRuntime(tmp_path)
    lease = life.Admission(runtime, "attempt", "fingerprint", False)
    lease.prepare()
    lease.submitting()
    lease.close()
    assert runtime.stopped == 0
    for key, fingerprint in [("attempt", "fingerprint"), ("other", "fingerprint"), ("attempt", "changed")]:
        with pytest.raises(life.Deferred, match="reconcile_attempt"):
            life.Admission(runtime, key, fingerprint, False)
    resumed = life.Admission(runtime, "attempt", "fingerprint", True)
    with pytest.raises(life.Deferred, match="duplicate_post"):
        resumed.submitting()
    resumed.receipt("original")
    with pytest.raises(life.Deferred, match="receipt_conflict"):
        resumed.receipt("changed")
    resumed.complete()
    resumed.close()
    assert runtime.started == runtime.stopped == 1


def test_owner_replacement_blocks_post_and_cleanup(tmp_path):
    runtime = FakeRuntime(tmp_path)
    lease = life.Admission(runtime, "attempt", "fingerprint", False)
    lease.prepare()
    runtime.changed = True
    with pytest.raises(life.Deferred, match="ownership"):
        lease.submitting()
    lease.close()
    assert runtime.stopped == 0
    assert life.private_json(runtime.path)["state"] == "draining"


@pytest.mark.parametrize("state", ["starting", "draining", "error"])
def test_crashed_lifecycle_is_not_automatically_reclaimed(tmp_path, state):
    runtime = FakeRuntime(tmp_path)
    write(runtime.path, {"version": 1, "owned": {}, "state": state})
    with pytest.raises(life.Deferred, match="reconcile_runtime"):
        life.Admission(runtime, "attempt", "fingerprint", False)
    assert runtime.started == runtime.stopped == 0


def session_fixture(**overrides):
    values = {"/queue": {"queue_running": [], "queue_pending": []},
              "/api/jobs?scope=active&limit=100": {"jobs": []},
              "/api/series?limit=100": {"series": []},
              "/api/settings": {"system_prompt": ""}}
    values.update(overrides)
    def get(url, **kw):
        path = "/" + url.split("://", 1)[1].split("/", 1)[1]
        return NS(raise_for_status=lambda: None, json=lambda: values[path])
    return NS(get=get)


@pytest.mark.parametrize("path,value", [
    ("/queue", {"queue_running": [], "queue_pending": ["peer"]}),
    ("/queue", {}), ("/api/jobs?scope=active&limit=100", {"jobs": ["peer"]}),
    ("/api/series?limit=100", {"series": [{"status": "waiting"}]}),
    ("/api/series?limit=100", {"series": [{"status": "unknown"}]}),
    ("/api/series?limit=100", {"series": [{"status": "completed"}] * 100}),
    ("/api/settings", {}), ("/api/settings", {"system_prompt": "Peer prompt"})])
def test_idle_gate_preserves_jobs_series_and_shared_settings(path, value):
    with pytest.raises(life.Deferred):
        life.idle(session_fixture(**{path: value}))


def test_idle_terminal_and_paused_series():
    life.idle(session_fixture(**{"/api/series?limit=100": {"series": [{"status": "paused"}, {"status": "completed"}]}}))


def test_persisted_work_checked_before_start(runtime, monkeypatch):
    import sqlite3
    for name, table in (("webapp-jobs.sqlite3", "jobs"), ("webapp-series.sqlite3", "series")):
        with sqlite3.connect(runtime.private / name) as db:
            db.execute(f"CREATE TABLE {table} (status TEXT)")
            db.execute(f"INSERT INTO {table} VALUES ('completed')")
    write(runtime.private / "h3-studio-settings.json", {"version": 1, "system_prompt": ""})
    runtime.persisted_idle()
    with sqlite3.connect(runtime.private / "webapp-series.sqlite3") as db:
        db.execute("INSERT INTO series VALUES ('waiting')")
    monkeypatch.setattr(runtime, "identities", lambda: {})
    monkeypatch.setattr(runtime, "ports_free", lambda: None)
    monkeypatch.setattr(runtime, "command", lambda *a, **kw: pytest.fail("No launch for saved work"))
    with pytest.raises(life.Deferred, match="saved_work"):
        runtime.start({"owned": {}}, lambda: None)


def test_preexisting_runtime_is_never_adopted(runtime, monkeypatch):
    monkeypatch.setattr(runtime, "identities", lambda: {"comfyui": {"pid": 99}})
    monkeypatch.setattr(runtime, "command", lambda *a, **kw: pytest.fail("No start or stop"))
    with pytest.raises(life.Deferred, match="existing_runtime"):
        runtime.start({"owned": {}}, lambda: None)


def test_canonical_start_pins_generated_instances_and_gpu0(runtime, monkeypatch):
    current, commands, saved = {}, [], []
    monkeypatch.setattr(runtime, "identities", lambda: dict(current))
    monkeypatch.setattr(runtime, "ports_free", lambda: None)
    monkeypatch.setattr(runtime, "persisted_idle", lambda: None)
    monkeypatch.setattr(life, "resources", lambda env: None)
    monkeypatch.setattr(runtime, "ready", lambda owned: None)
    def command(args, **kw):
        commands.append(args)
        env = kw["env"]
        assert env["H3_CUDA_DEVICES"] == "0" and env["H3_AUX_DEVICE"] == "gpu:0"
        for service, key in (("comfyui", "H3_RUNTIME_INSTANCE"), ("webapp", "H3_WEBAPP_INSTANCE")):
            if args[0].endswith(f"start_{service}.sh"):
                current[service] = {"instance": env[key]}
    monkeypatch.setattr(runtime, "command", command)
    record = {"owned": {}}
    runtime.start(record, lambda: saved.append(json.loads(json.dumps(record))))
    assert [Path(args[0]).name for args in commands] == ["check_resources.sh", "start_comfyui.sh", "start_webapp.sh"]
    assert saved[0]["state"] == "starting" and len(saved[0]["expected_instances"]) == 2
    assert record["state"] == "preparing"


def test_cleanup_refuses_identity_change_or_busy_queue(runtime, monkeypatch):
    owned = {"webapp": {"pid": 123, "instance": "original"}, "comfyui": {"pid": 456, "instance": "original"}}
    monkeypatch.setattr(runtime, "identities", lambda: {})
    monkeypatch.setattr(runtime, "command", lambda *a, **kw: pytest.fail("No signalling"))
    with pytest.raises(life.Deferred, match="ownership_changed"):
        runtime.stop(owned)
    monkeypatch.setattr(runtime, "identities", lambda: owned)
    monkeypatch.setattr(life, "idle", lambda session: (_ for _ in ()).throw(life.Deferred("busy", "jobs", "Peer work")))
    with pytest.raises(life.Deferred, match="jobs"):
        runtime.stop(owned)


def test_adapter_lost_reply_never_submits_a_second_time(tmp_path, monkeypatch):
    runtime = FakeRuntime(tmp_path)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    monkeypatch.setattr(adapter, "moderate", lambda *a: None)
    posts = []
    def post(url, **kw):
        posts.append(url)
        if url.endswith("/api/renders"):
            assert life.private_json(runtime.path)["state"] == "submitting"
            assert (tmp_path / "renders/job/item/intent.json").exists()
            raise requests.Timeout("Lost reply")
        return NS(raise_for_status=lambda: None, json=lambda: {"token": "fixture"})
    session = session_fixture()
    get = session.get
    session.get = lambda url, **kw: NS(raise_for_status=lambda: None, json=lambda: {"connected": True, "ready": True, "model_status": "verified"}) if "/health" in url else get(url, **kw)
    session.post = post
    session.close = lambda: None
    monkeypatch.setattr(adapter, "local_session", lambda: session)
    source = tmp_path / "reference.png"
    Image.new("RGB", (8, 8), "white").save(source)
    cfg = {"state": str(tmp_path), "local_video_url": "http://127.0.0.1:8190"}
    for _ in range(2):
        with pytest.raises(adapter.OutcomeUncertain):
            adapter.animate(cfg, {"id": "job"}, {"id": "item", "label": "Hello"}, source)
    assert len([url for url in posts if url.endswith("/api/renders")]) == 1
    assert runtime.stopped == 0 and life.private_json(runtime.path)["state"] == "submitting"


def test_local_session_rejects_redirects_and_proxies(monkeypatch):
    monkeypatch.setattr(requests.Session, "request", lambda *a, **kw: NS(status_code=302))
    session = life.local_session()
    assert session.trust_env is False
    with pytest.raises(life.Deferred, match="redirect"):
        session.get("http://127.0.0.1:8190/api/health")
    session.close()


def test_status_reports_offline_resources_busy_and_draining(runtime, monkeypatch):
    cfg = {"local_video_runtime_root": str(runtime.root), "local_video_url": "http://127.0.0.1:8190"}
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    monkeypatch.setattr(runtime, "identities", lambda: {})
    monkeypatch.setattr(runtime, "ports_free", lambda: None)
    monkeypatch.setattr(runtime, "persisted_idle", lambda: None)
    monkeypatch.setattr(life, "resources", lambda env: None)
    assert life.status(cfg)["state"] == "available"
    assert life.status(cfg)["can_submit"] is True
    assert not runtime.lock.exists() and not runtime.path.exists()
    def blocked(env):
        raise life.Deferred("blocked_resources", "ram", "48 GiB required")
    monkeypatch.setattr(life, "resources", blocked)
    assert life.status(cfg)["state"] == "blocked_resources"
    write(runtime.path, {"version": 1, "owned": {}, "state": "monitoring", "attempt": {"key": "old"}})
    assert life.status(cfg)["state"] == "busy"
    write(runtime.path, {"version": 1, "owned": {}, "state": "draining"})
    assert life.status(cfg)["state"] == "draining"


def test_cleanup_uses_captured_pidfd_identity_and_expected_engine_args(runtime, monkeypatch):
    owned = {"webapp": {"pid": 99999991, "instance": "original-web"},
             "comfyui": {"pid": 99999992, "instance": "original-engine"}}
    write(runtime.root / "runtime/webapp-state.json", owned["webapp"])
    calls = []
    monkeypatch.setattr(runtime, "identities", lambda: owned)
    monkeypatch.setattr(runtime, "persisted_idle", lambda: None)
    monkeypatch.setattr(runtime, "ports_free", lambda: None)
    monkeypatch.setattr(life, "idle", lambda session: None)
    monkeypatch.setattr(runtime, "identity_command", lambda *args: calls.append(args))
    monkeypatch.setattr(runtime, "command", lambda args, **kw: calls.append(tuple(args)))
    runtime.stop(owned)
    assert calls[0] == ("webapp", "signal", "--expect-pid", "99999991", "--expect-instance", "original-web", "--signal", "INT")
    assert calls[1] == ("webapp", "clear")
    assert calls[2][1:] == ("--expect-pid", "99999992", "--expect-instance", "original-engine")
    assert calls[2][0].endswith("stop_comfyui.sh")
    assert all("--force" not in args and "KILL" not in args for args in calls)


def test_second_resource_check_blocks_post_and_cleans_idle_fixture(tmp_path):
    runtime = FakeRuntime(tmp_path)
    lease = life.Admission(runtime, "attempt", "fingerprint", False)
    lease.prepare()
    def blocked(owned):
        raise life.Deferred("blocked_resources", "ram", "RAM changed")
    runtime.ready = blocked
    with pytest.raises(life.Deferred, match="blocked_resources"):
        lease.submitting()
    assert life.private_json(runtime.path)["state"] == "preparing"
    lease.close()
    assert runtime.stopped == 1


def test_legacy_receipt_resume_does_not_start_or_post_without_policy(monkeypatch):
    monkeypatch.setattr(life, "Runtime", lambda cfg: pytest.fail("Legacy download must not start a runtime"))
    with life.admission({}, "attempt", "fingerprint", resume=True) as lease:
        assert lease is None


@pytest.mark.parametrize("state", ["offline", "idle", "preparing", "starting", "draining"])
def test_reboot_recovers_only_safe_prepost_or_finished_leases(runtime, monkeypatch, state):
    record = {"version": 1, "state": state, "boot_id": "old-boot", "owned": {}, "attempt": {"key": "old"}}
    monkeypatch.setattr(runtime, "identities", lambda: {})
    monkeypatch.setattr(runtime, "ports_free", lambda: None)
    monkeypatch.setattr(runtime, "persisted_idle", lambda: None)
    write(runtime.path, record)
    lease = life.Admission(runtime, "new", "fingerprint", False)
    assert lease.record["attempt"]["key"] == "new"
    assert lease.record["boot_id"] == life.BOOT.read_text().strip()


@pytest.mark.parametrize("state", ["submitting", "monitoring", "error"])
def test_reboot_never_releases_uncertain_submission(runtime, state):
    record = {"version": 1, "state": state, "boot_id": "old-boot", "owned": {}, "attempt": {"key": "old"}}
    write(runtime.path, record)
    with pytest.raises(life.Deferred, match="reconcile_attempt"):
        life.Admission(runtime, "new", "fingerprint", False)
    assert life.private_json(runtime.path) == record


def test_reboot_recovery_preserves_a_new_owner(runtime, monkeypatch):
    record = {"version": 1, "state": "draining", "boot_id": "old-boot", "owned": {}}
    monkeypatch.setattr(runtime, "identities", lambda: {"comfyui": {"pid": 1}})
    with pytest.raises(life.Deferred, match="existing_runtime"):
        runtime.after_boot(record)


@pytest.mark.parametrize("returncode", [0, 3, 4])
def test_stale_canonical_state_requires_proof_original_is_gone(runtime, monkeypatch, returncode):
    path = runtime.root / "runtime/comfyui-state.json"
    record = {"pid": 99, "instance": "old-boot-instance"}
    write(path, record)
    calls = []
    def identity(service, *args, **kw):
        calls.append((service, args, kw))
        if args[0] == "verify":
            raise life.Deferred("error", "verify_required", "Alive identities require full verification")
        return NS(returncode=returncode)
    monkeypatch.setattr(runtime, "identity_command", identity)
    if returncode == 3:
        assert runtime.identities() == {}
    else:
        with pytest.raises(life.Deferred, match="verify_required" if returncode == 0 else "identity_unverified"):
            runtime.identities()
    assert life.private_json(path) == record
    assert calls[0][1] == ("alive", "--expect-pid", "99", "--expect-instance", "old-boot-instance")


def test_status_reports_held_lease_without_waiting(runtime):
    cfg = {"local_video_runtime_root": str(runtime.root), "local_video_url": "http://127.0.0.1:8190"}
    with life.exclusive(runtime.lock):
        result = life.status(cfg)
    assert result["code"] == "lease_held" and result["can_submit"] is False


def test_corrupt_receipt_intent_remains_uncertain(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"reference fingerprint")
    folder = tmp_path / "renders/job/item"
    folder.mkdir(parents=True)
    (folder / "receipt.json").write_text("{}")
    (folder / "intent.json").write_text("truncated{")
    with pytest.raises(adapter.OutcomeUncertain, match="different or unverified"):
        adapter.animate({"state": str(tmp_path), "local_video_url": "http://127.0.0.1:8190"},
                        {"id": "job"}, {"id": "item", "label": "Hello"}, source)
