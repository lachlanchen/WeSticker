"""Job-lifetime ownership fixtures; no GPU, provider call or actual render."""

from contextlib import contextmanager
import json

import pytest

from server import local_video_lifecycle as life
from server.store import database
from server.worker import work_once
from test_animation_admission_api import prepared
from test_app import setup, call
from test_local_video_lifecycle import FakeRuntime


def finish(lease):
    lease.prepare()
    lease.submitting()
    lease.receipt("provider")
    lease.complete()


def test_serial_pack_keeps_one_runtime_and_exclusive_job_slot(tmp_path, monkeypatch):
    runtime = FakeRuntime(tmp_path)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    cfg = {}
    with life.job_admission(cfg) as batch:
        for number in range(3):
            with life.admission(cfg, str(number), str(number), batch=batch) as lease:
                finish(lease)
            assert runtime.started == 1 and runtime.stopped == 0
            with pytest.raises(life.Deferred, match="lease_held"):
                with life.exclusive(runtime.lock):
                    pytest.fail("The slot must remain held between items")
    assert runtime.stopped == 1
    assert life.private_json(runtime.path)["state"] == "offline"


def test_job_lease_refuses_other_configuration_parallel_or_closed_use(tmp_path, monkeypatch):
    runtime = FakeRuntime(tmp_path)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    cfg = {}
    with life.job_admission(cfg) as batch:
        with pytest.raises(life.Deferred, match="job_lease"):
            with life.admission({}, "other", "fingerprint", batch=batch):
                pytest.fail("Foreign configuration")
        with life.admission(cfg, "one", "fingerprint", batch=batch) as lease:
            with pytest.raises(life.Deferred, match="job_lease"):
                with life.admission(cfg, "two", "fingerprint", batch=batch):
                    pytest.fail("Concurrent item")
            finish(lease)
    with pytest.raises(life.Deferred, match="job_lease"):
        with life.admission(cfg, "three", "fingerprint", batch=batch):
            pytest.fail("Expired job context")


def test_uncertain_second_item_keeps_exact_receipt_and_does_not_stop(tmp_path, monkeypatch):
    runtime = FakeRuntime(tmp_path)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    cfg = {}
    with pytest.raises(RuntimeError, match="Lost response"):
        with life.job_admission(cfg) as batch:
            with life.admission(cfg, "one", "one", batch=batch) as lease:
                finish(lease)
            with life.admission(cfg, "two", "two", batch=batch) as lease:
                lease.prepare()
                lease.submitting()
                raise RuntimeError("Lost response")
    record = life.private_json(runtime.path)
    assert record["attempt"] == {"key": "two", "fingerprint": "two"}
    assert record["state"] == "submitting"
    assert runtime.started == 1 and runtime.stopped == 0
    with pytest.raises(life.Deferred, match="reconcile_attempt"):
        with life.admission(cfg, "three", "three"):
            pytest.fail("Never replace an uncertain item")


def test_prepost_failure_drains_owned_runtime_once(tmp_path, monkeypatch):
    runtime = FakeRuntime(tmp_path)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    cfg = {}
    with pytest.raises(ValueError, match="Unapproved"):
        with life.job_admission(cfg) as batch:
            with life.admission(cfg, "one", "one", batch=batch) as lease:
                lease.prepare()
                raise ValueError("Unapproved reference")
    assert runtime.started == runtime.stopped == 1


def test_worker_uses_one_batch_and_refunds_only_unfinished_items(setup, monkeypatch, tmp_path):
    _, cfg, client, pack, first = prepared(setup)
    with database(cfg) as db:
        row = db.execute("SELECT items FROM packs WHERE id=?", (pack,)).fetchone()
        items = json.loads(row[0])
        items.append(items[0] | {"id": "second", "label": "Thanks"})
        db.execute("UPDATE packs SET items=? WHERE id=?", (json.dumps(items), pack))
    monkeypatch.setattr("server.app.animation_status", lambda cfg: {"can_submit": True})
    result = call(client, f"/api/packs/{pack}/generate", {"kind": "animate",
        "items": [first, "second"], "attempt": "two-item-animation-batch", "consent": True})
    assert result.status_code == 202
    scope = object()
    events = []

    @contextmanager
    def batch(config):
        assert config is cfg
        events.append("enter")
        try:
            yield scope
        finally:
            events.append("exit")

    def animate(config, job, item, source, *, batch):
        assert batch is scope
        events.append(item["id"])
        if item["id"] == "second":
            raise ValueError("Resources changed before submission")
        output = tmp_path / "fixture.gif"
        output.write_bytes(b"GIF89a")
        return output

    monkeypatch.setattr("server.worker.job_admission", batch)
    monkeypatch.setattr("server.worker.animate", animate)
    assert work_once(cfg)
    assert events == ["enter", first, "second", "exit"]
    assert client.get("/api/bootstrap").json["user"]["credits"] == 97
    with database(cfg) as db:
        job = db.execute("SELECT * FROM jobs WHERE id=?", (result.json["id"],)).fetchone()
        assert job["state"] == "failed" and json.loads(job["data"])["completed"] == 3
