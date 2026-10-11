import hashlib
import json
import sqlite3
import sys

import pytest

from scripts import activate_creator_runtime as activate


@pytest.fixture
def release(tmp_path):
    root = tmp_path / "release"
    (root / "dist").mkdir(parents=True)
    (root / "public").mkdir()
    (root / "dist/catalog.json").write_text("{}")
    (root / "public/catalog.json").write_text("{}")
    hashes = {"dist/catalog.json": hashlib.sha256(b"{}").hexdigest()}
    (root / "manifest.json").write_text(json.dumps({
        "files": hashes,
        "sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
    }))
    return root


def test_verify_snapshot_and_reject_modified_catalog(release):
    activate.verify_release(release)
    (release / "public/catalog.json").write_text("[]")
    with pytest.raises(RuntimeError, match="catalog differs"):
        activate.verify_release(release)
    (release / "public/catalog.json").write_text("{}")
    (release / "dist/catalog.json").write_text("[]")
    with pytest.raises(RuntimeError, match="content differs"):
        activate.verify_release(release)


@pytest.mark.parametrize("state", ["queued", "running"])
def test_idle_guard_preserves_active_jobs(tmp_path, state):
    with sqlite3.connect(tmp_path / "westicker.sqlite") as db:
        db.execute("CREATE TABLE jobs(state TEXT)")
        db.execute("INSERT INTO jobs VALUES (?)", (state,))
    with pytest.raises(RuntimeError, match="Wait for existing jobs"):
        activate.require_idle({"state": str(tmp_path)})


@pytest.mark.parametrize("failure", ["admission", "health", None])
def test_activation_rollback_and_admission_order(tmp_path, release, monkeypatch, failure):
    previous = tmp_path / "old"
    previous.mkdir()
    current = tmp_path / "current"
    current.symlink_to(previous)
    config = tmp_path / "config.json"
    config.write_text('{"origin":"https://westicker.example"}')
    checks, commands = [], []
    def idle(_):
        checks.append(1)
        if failure == "admission" and len(checks) == 2:
            raise RuntimeError("Wait for existing jobs")
    def health(_):
        if failure == "health":
            raise RuntimeError("unhealthy")
    monkeypatch.setattr(activate, "require_idle", idle)
    monkeypatch.setattr(activate, "health", health)
    monkeypatch.setattr(activate.subprocess, "run", lambda command, **kw: commands.append(command))
    monkeypatch.setattr(sys, "argv", ["activate", "--release", str(release), "--current", str(current), "--config", str(config)])
    if failure:
        with pytest.raises(RuntimeError):
            activate.main()
        assert current.resolve() == previous
        assert commands[-1][2] == "start"
    else:
        activate.main()
        assert current.resolve() == release
    assert commands[0] == ["systemctl", "--user", "stop", "westicker-creator-api.service"]
    if failure == "admission":
        assert not any(c[2] == "stop" and "westicker-creator-worker.service" in c for c in commands)
