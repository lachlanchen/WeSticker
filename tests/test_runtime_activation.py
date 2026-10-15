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


def test_idle_guard_preserves_active_chat(tmp_path):
    with sqlite3.connect(tmp_path / "westicker.sqlite") as db:
        db.execute("CREATE TABLE jobs(state TEXT)")
        db.execute("CREATE TABLE studio_messages(state TEXT)")
        db.execute("INSERT INTO studio_messages VALUES ('working')")
    with pytest.raises(RuntimeError, match="chat requests"):
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


@pytest.mark.parametrize('fail_health', [False, True])
def test_private_configuration_is_transactional_with_release(tmp_path, release, monkeypatch, fail_health):
    previous = tmp_path / 'old'
    previous.mkdir()
    current = tmp_path / 'current'
    current.symlink_to(previous)
    config = tmp_path / 'config.json'
    original = b'{"state":"private-data","origin":"https://westicker.example","chat_provider":"compatible"}'
    config.write_bytes(original)
    candidate = tmp_path / 'candidate.json'
    candidate.write_text(json.dumps(json.loads(original) | {'chat_provider': 'aginti'}))
    monkeypatch.setattr(activate, 'require_idle', lambda cfg: None)
    monkeypatch.setattr(activate.subprocess, 'run', lambda *a, **k: None)
    def health(_):
        assert json.loads(config.read_text())['chat_provider'] == 'aginti'
        if fail_health: raise RuntimeError('failed')
    monkeypatch.setattr(activate, 'health', health)
    monkeypatch.setattr(sys, 'argv', ['activate', '--release', str(release), '--current', str(current),
        '--config', str(config), '--config-candidate', str(candidate)])
    if fail_health:
        with pytest.raises(RuntimeError): activate.main()
        assert config.read_bytes() == original and current.resolve() == previous
    else:
        activate.main()
        assert json.loads(config.read_text())['chat_provider'] == 'aginti'
    assert config.stat().st_mode & 0o777 == 0o600
    assert next(tmp_path.glob('config.json.previous-*')).read_bytes() == original
