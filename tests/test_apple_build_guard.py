import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    "apple_build_guard", Path(__file__).resolve().parents[1] / "scripts/apple_build_guard.py")
guard_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard_module)


@pytest.fixture
def guard(tmp_path):
    return guard_module.AppleBuildGuard(owner="WeSticker-test", checkout=tmp_path,
        operation="disposable test", handoff="test-only explicit pass", path=tmp_path / "guard")


def invoke(guard, tmp_path, command=None, preflight=lambda: None, cleanup=lambda: True, timeout=5):
    with (tmp_path / "operation.log").open("w") as log:
        return guard_module.run_guarded(guard, command or [sys.executable, "-c", "pass"],
            cwd=tmp_path, log=log, timeout=timeout, preflight=preflight, verify_cleanup=cleanup)


def stop_test_child(guard):
    # Only the disposable test's explicitly tracked process group is signalled.
    for child in guard.children:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        child.wait(timeout=5)


def test_exact_common_path_and_no_automatic_cleanup():
    assert str(guard_module.GUARD_PATH) == "/tmp/lazyingart-apple-build.lock"
    assert not hasattr(guard_module.AppleBuildGuard, "__exit__")


def test_success_checks_before_and_after_lock(guard, tmp_path):
    seen = []
    assert invoke(guard, tmp_path, preflight=lambda: seen.append(guard.path.exists())) == 0
    assert seen == [False, True]
    assert guard.released and not guard.path.exists()


def test_failed_command_can_release_after_verified_cleanup(guard, tmp_path):
    assert invoke(guard, tmp_path, [sys.executable, "-c", "raise SystemExit(7)"]) == 7
    assert guard.released and not guard.path.exists()


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling-symlink"])
def test_existing_paths_are_never_replaced(guard, tmp_path, kind):
    target = tmp_path / "peer"
    target.write_text("preserve peer")
    if kind == "directory":
        guard.path.mkdir()
        (guard.path / "partial-owner").write_text("peer")
    elif kind == "file":
        guard.path.write_text("incompatible peer flock")
    else:
        guard.path.symlink_to(target if kind == "symlink" else tmp_path / "absent")
    before = guard.path.lstat()
    with pytest.raises(FileExistsError):
        guard.acquire()
    assert guard.path.lstat().st_ino == before.st_ino
    assert target.read_text() == "preserve peer"


def test_owner_metadata_complete_and_private(guard):
    guard.acquire()
    data = json.loads((guard.path / "owner.json").read_text())
    assert {"protocol", "host", "owner", "token", "wrapperPid", "wrapperStarted",
            "acquiredUTC", "checkout", "operation", "handoff"} <= data.keys()
    assert data["protocol"] == 1
    assert guard.path.stat().st_mode & 0o777 == 0o700
    assert (guard.path / "owner.json").stat().st_mode & 0o777 == 0o600
    guard.release(cleanup_verified=True)


@pytest.mark.parametrize("change", ["token", "owner", "extra", "symlink", "inode"])
def test_mutated_guard_is_retained(guard, tmp_path, change):
    guard.acquire()
    metadata = guard.path / "owner.json"
    if change in ("token", "owner"):
        data = json.loads(metadata.read_text())
        data[change] = "peer"
        metadata.write_text(json.dumps(data))
    elif change == "extra":
        (guard.path / "unexpected").touch()
    elif change == "symlink":
        copy = tmp_path / "metadata-copy"
        metadata.rename(copy)
        metadata.symlink_to(copy)
    else:
        guard.path.rename(tmp_path / "original-guard")
        guard.path.mkdir()
        metadata.write_text(json.dumps(guard.record))
    with pytest.raises(guard_module.GuardRetained):
        guard.release(cleanup_verified=True)
    assert guard.path.exists() and metadata.exists()


def test_post_acquisition_conflict_releases_only_own_empty_operation(guard, tmp_path):
    def probe():
        if guard.path.exists():
            raise guard_module.PreflightConflict("peer build discovered")
    with pytest.raises(guard_module.PreflightConflict):
        invoke(guard, tmp_path, preflight=probe)
    assert guard.released and not guard.children


def test_pre_acquisition_conflict_never_acquires(guard, tmp_path):
    def probe():
        raise guard_module.PreflightConflict("predecessor still owns host")
    with pytest.raises(guard_module.PreflightConflict):
        invoke(guard, tmp_path, preflight=probe)
    assert not guard.path.exists() and not guard.children


def test_partial_acquisition_is_not_removed(guard, monkeypatch):
    def failed_metadata(*args, **kwargs):
        raise OSError("metadata probe failed")
    monkeypatch.setattr(subprocess, "check_output", failed_metadata)
    with pytest.raises(OSError):
        guard.acquire()
    assert guard.path.is_dir() and not (guard.path / "owner.json").exists()
    with pytest.raises(FileExistsError):
        guard_module.AppleBuildGuard(owner="next", checkout="/source", operation="test",
            handoff="explicit test pass", path=guard.path).acquire()


def test_failed_launch_retains_guard(guard, tmp_path):
    with pytest.raises(FileNotFoundError):
        invoke(guard, tmp_path, [str(tmp_path / "not-an-executable")])
    with pytest.raises(guard_module.GuardRetained):
        guard.release(cleanup_verified=True)
    assert guard.path.exists() and not guard.children


def test_uncertain_post_acquisition_probe_retains_guard(guard, tmp_path):
    def probe():
        if guard.path.exists():
            raise OSError("resource probe failed")
    with pytest.raises(OSError):
        invoke(guard, tmp_path, preflight=probe)
    assert guard.path.exists() and not guard.children


def test_failed_cleanup_retains_guard(guard, tmp_path):
    with pytest.raises(guard_module.GuardRetained):
        invoke(guard, tmp_path, cleanup=lambda: False)
    assert guard.path.exists()


def test_timeout_never_releases_live_child(guard, tmp_path):
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            invoke(guard, tmp_path, [sys.executable, "-c", "import time; time.sleep(30)"], timeout=0.1)
        with pytest.raises(guard_module.GuardRetained):
            guard.release(cleanup_verified=True)
        assert guard.path.exists() and guard.children[0].poll() is None
    finally:
        stop_test_child(guard)


def test_interrupted_wait_retains_guard(guard, tmp_path, monkeypatch):
    original = subprocess.Popen.wait
    try:
        with monkeypatch.context() as patch:
            patch.setattr(subprocess.Popen, "wait", lambda *a, **k: (_ for _ in ()).throw(KeyboardInterrupt()))
            with pytest.raises(KeyboardInterrupt):
                invoke(guard, tmp_path, [sys.executable, "-c", "import time; time.sleep(30)"])
        assert subprocess.Popen.wait is original
        with pytest.raises(guard_module.GuardRetained):
            guard.release(cleanup_verified=True)
        assert guard.path.exists()
    finally:
        stop_test_child(guard)


def test_live_group_is_checked_even_when_direct_child_exited(guard, monkeypatch):
    guard.acquire()
    class CompletedChild:
        pid = 987654
        def poll(self):
            return 0
    guard.children.append(CompletedChild())
    checked = []
    monkeypatch.setattr(os, "killpg", lambda group, sig: checked.append((group, sig)))
    with pytest.raises(guard_module.GuardRetained):
        guard.release(cleanup_verified=True)
    assert checked == [(987654, 0)] and guard.path.exists()
