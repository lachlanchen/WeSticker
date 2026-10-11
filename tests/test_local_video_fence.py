"""Canonical client contract fixtures. No services, GPU, signals or real HTTP."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import requests
from PIL import Image

from server import local_video as adapter
from server import local_video_lifecycle as life
from test_local_video_lifecycle import runtime, write
from test_local_video_recovery import policy


OWNED = {"webapp": {"pid": 99999991, "instance": "11111111-1111-4111-8111-111111111111"},
         "comfyui": {"pid": 99999992, "instance": "22222222-2222-4222-8222-222222222222"}}
FENCE = {"generation": "33333333-3333-4333-8333-333333333333", "token": "a" * 64, "state": "held"}
MID = "44444444-4444-4444-8444-444444444444"


def reply(state="held", **changes):
    return {"version": 1, "owner": "westicker", "generation": FENCE["generation"],
            "studio_instance": OWNED["webapp"]["instance"],
            "engine_instance": OWNED["comfyui"]["instance"], "state": state, **changes}


def transport(runtime, monkeypatch, replies):
    calls = []
    iterator = iter(replies)
    def request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        value = next(iterator)
        if isinstance(value, Exception):
            raise value
        return NS(raise_for_status=lambda: None, json=lambda: value)
    monkeypatch.setattr(runtime, "identities", lambda: copy.deepcopy(OWNED))
    monkeypatch.setattr(runtime.session, "request", request)
    return calls


def no_readiness(runtime, monkeypatch):
    monkeypatch.setattr(life, "resources", lambda *a: pytest.fail("No resources before matching completion"))
    monkeypatch.setattr(runtime, "ready", lambda *a: pytest.fail("No readiness before matching completion"))
    monkeypatch.setattr(runtime, "command", lambda *a, **kw: pytest.fail("No command before matching completion"))


def test_claim_and_observation_use_request_local_bound_headers(runtime, monkeypatch):
    calls = transport(runtime, monkeypatch, [reply(), reply()])
    no_readiness(runtime, monkeypatch)
    before = dict(runtime.session.headers)
    runtime.claim(OWNED, FENCE)
    runtime.claim(OWNED, FENCE, recover=True)
    assert [row[0] for row in calls] == ["POST", "GET"]
    assert calls[0][1].endswith("/api/admission/claim")
    assert calls[1][1].endswith("/api/admission")
    assert calls[0][2]["json"] == {} and "json" not in calls[1][2]
    for _, _, kw in calls:
        assert kw["headers"] == runtime.headers(OWNED, FENCE)
        assert kw["timeout"] == 10
    assert dict(runtime.session.headers) == before


@pytest.mark.parametrize("change", [{"owner": "other"}, {"version": 2}, {"generation": MID},
    {"studio_instance": MID}, {"engine_instance": MID}])
def test_mismatched_canonical_binding_rejected(runtime, monkeypatch, change):
    transport(runtime, monkeypatch, [reply(**change)])
    with pytest.raises(life.Deferred, match="fence_binding"):
        runtime.claim(OWNED, FENCE)


@pytest.mark.parametrize("change", [{"generation": "bad"}, {"token": "not-private"}, {"token": None}])
def test_malformed_private_credentials_never_sent(runtime, monkeypatch, change):
    calls = transport(runtime, monkeypatch, [])
    with pytest.raises(life.Deferred, match="fence_record"):
        runtime.claim(OWNED, FENCE | change)
    assert calls == []


def test_identity_replaced_during_canonical_response_is_rejected(runtime, monkeypatch):
    transport(runtime, monkeypatch, [reply()])
    identities = iter([OWNED, OWNED | {"webapp": OWNED["webapp"] | {"instance": MID}}])
    monkeypatch.setattr(runtime, "identities", lambda: next(identities))
    with pytest.raises(life.Deferred, match="ownership"):
        runtime.claim(OWNED, FENCE)


def test_lost_claim_preserves_private_binding_and_recovers_with_get_only(runtime, monkeypatch):
    write(runtime.path, {"version": 1, "state": "idle", "owned": OWNED})
    requests_seen = []
    def request(method, url, **kwargs):
        saved = life.private_json(runtime.path)
        assert saved["state"] == "claiming"
        assert kwargs["headers"]["X-H3-Lease-Generation"] == saved["fence"]["generation"]
        assert kwargs["headers"]["X-H3-Lease-Token"] == saved["fence"]["token"]
        requests_seen.append((method, saved["fence"].copy()))
        if method == "POST":
            raise requests.Timeout("lost claim reply")
        return NS(raise_for_status=lambda: None,
                  json=lambda: reply(generation=saved["fence"]["generation"]))
    monkeypatch.setattr(runtime.session, "request", request)
    monkeypatch.setattr(runtime, "identities", lambda: OWNED)
    monkeypatch.setattr(runtime, "ready", lambda *a: None)
    monkeypatch.setattr(runtime, "stop", lambda *a: pytest.fail("Uncertain claim remains held"))
    first = life.Admission(runtime, "item", "fingerprint", False)
    with pytest.raises(life.Deferred, match="fence_observation"):
        first.prepare()
    first.close()
    saved = life.private_json(runtime.path)
    assert runtime.path.stat().st_mode & 0o077 == 0
    recovered = life.Admission(runtime, "item", "fingerprint", False)
    recovered.prepare()
    assert [row[0] for row in requests_seen] == ["POST", "GET"]
    assert requests_seen[0][1] == requests_seen[1][1] == saved["fence"]
    assert recovered.record["fence"]["state"] == "held"


def test_confirmed_claim_allows_cleanup_when_first_dispatch_readiness_fails(runtime, monkeypatch):
    write(runtime.path, {"version": 1, "state": "idle", "owned": OWNED})
    events = []
    def claim(owned, fence, **kwargs):
        events.append("claim")
        assert life.private_json(runtime.path)["fence"] == fence
    monkeypatch.setattr(runtime, "claim", claim)
    def ready(owned):
        assert events == ["claim"]
        raise life.Deferred("blocked_resources", "ram", "no dispatch")
    monkeypatch.setattr(runtime, "ready", ready)
    def stop(owned, fence):
        assert owned == OWNED and fence["state"] == "held"
        events.append("drain-owned")
    monkeypatch.setattr(runtime, "stop", stop)
    lease = life.Admission(runtime, "first", "fingerprint", False)
    with pytest.raises(life.Deferred, match="ram"):
        lease.prepare()
    lease.close()
    assert events == ["claim", "drain-owned"]
    assert life.private_json(runtime.path)["state"] == "offline"


@pytest.mark.parametrize("recover", [False, True])
def test_only_matching_worker_completion_allows_unchanged_resource_gates(runtime, monkeypatch, recover):
    states = (["queued"] if not recover else []) + ["running", "completed"]
    calls = transport(runtime, monkeypatch, [reply(state, maintenance_id=MID) for state in states] + [reply()])
    events = []
    saved = []
    monkeypatch.setattr(life.time, "sleep", lambda seconds: events.append("wait"))
    monkeypatch.setattr(life, "resources", lambda env, pids: events.append(("resources", env, pids)))
    monkeypatch.setattr(runtime, "command", lambda args, **kw: events.append(("canonical", args, kw)))
    monkeypatch.setattr(runtime, "ready", lambda owned: events.append(("ready", owned)))
    maintenance = {"id": MID, "state": "intent"}
    runtime.unload(OWNED, FENCE, maintenance, lambda: saved.append(maintenance.copy()), recover=recover)
    assert [entry["state"] for entry in saved] == states
    assert events[0] == "wait" and events[1][0] == "resources"
    assert events[1][1]["H3_MIN_RAM_GIB"] == "48"
    assert events[1][1]["H3_MIN_GPU_FREE_MIB"] == "20000"
    assert events[1][2] == {OWNED["comfyui"]["pid"]}
    assert events[2][0] == "canonical" and events[2][1] == [str(runtime.root / "scripts/check_resources.sh")]
    assert events[3] == ("ready", OWNED)
    assert sum(method == "POST" for method, _, _ in calls) == int(not recover)
    assert calls[-1][1].endswith("/api/admission")


@pytest.mark.parametrize("bad,code", [(reply("completed", maintenance_id="wrong"), "maintenance_binding"),
    (reply("held", maintenance_id=MID), "maintenance_binding"),
    (reply("failed", maintenance_id=MID), "maintenance_failed"),
    (requests.Timeout(), "fence_observation")])
def test_unverified_unload_never_runs_resources_or_admits_next_render(runtime, monkeypatch, bad, code):
    transport(runtime, monkeypatch, [bad])
    no_readiness(runtime, monkeypatch)
    saved = []
    maintenance = {"id": MID, "state": "intent"}
    with pytest.raises(life.Deferred, match=code):
        runtime.unload(OWNED, FENCE, maintenance, lambda: saved.append(maintenance.copy()))
    assert maintenance["id"] == MID
    if code == "maintenance_failed":
        assert saved == [{"id": MID, "state": "failed"}]


def test_pending_timeout_does_not_infer_completion_from_empty_queue(runtime, monkeypatch):
    calls = transport(runtime, monkeypatch, [reply("queued", maintenance_id=MID)])
    no_readiness(runtime, monkeypatch)
    times = iter([0, 61])
    monkeypatch.setattr(life.time, "monotonic", lambda: next(times))
    maintenance = {"id": MID, "state": "intent"}
    with pytest.raises(life.Deferred, match="maintenance_pending"):
        runtime.unload(OWNED, FENCE, maintenance, lambda: None)
    assert maintenance == {"id": MID, "state": "queued"} and len(calls) == 1


@pytest.mark.parametrize("which", ["resources", "canonical"])
def test_cold_gate_failure_after_ack_still_blocks_dispatch(runtime, monkeypatch, which):
    calls = transport(runtime, monkeypatch, [reply("completed", maintenance_id=MID)])
    def fail(*a, **kw):
        raise life.Deferred("blocked_resources", "ram", "unchanged 48GiB gate")
    monkeypatch.setattr(life, "resources", fail if which == "resources" else lambda *a: None)
    monkeypatch.setattr(runtime, "command", fail)
    monkeypatch.setattr(runtime, "ready", lambda *a: pytest.fail("Must not proceed after a failed gate"))
    with pytest.raises(life.Deferred, match="ram"):
        runtime.unload(OWNED, FENCE, {"id": MID}, lambda: None, recover=True)
    assert len(calls) == 1 and calls[0][0] == "GET"


def test_lost_unload_reply_recovers_same_id_with_get_only(runtime, monkeypatch):
    write(runtime.path, {"version": 1, "state": "idle", "owned": OWNED,
                        "fence": FENCE, "needs_unload": True})
    calls = []
    def request(method, url, **kwargs):
        saved = life.private_json(runtime.path)
        assert saved["state"] == ("preparing" if url.endswith("/api/admission") else "maintenance")
        maintenance = saved["maintenance"]
        calls.append((method, url, copy.deepcopy(saved)))
        if method == "POST":
            assert kwargs["json"]["maintenance_id"] == maintenance["id"]
            raise requests.Timeout()
        value = reply("completed", maintenance_id=maintenance["id"]) if "/maintenance/" in url else reply()
        return NS(raise_for_status=lambda: None, json=lambda: value)
    monkeypatch.setattr(runtime.session, "request", request)
    monkeypatch.setattr(runtime, "identities", lambda: OWNED)
    monkeypatch.setattr(runtime, "ready", lambda *a: None)
    monkeypatch.setattr(life, "resources", lambda *a: None)
    monkeypatch.setattr(runtime, "command", lambda *a, **kw: None)
    monkeypatch.setattr(runtime, "stop", lambda *a: pytest.fail("Uncertain maintenance must remain held"))
    first = life.Admission(runtime, "second", "fingerprint", False)
    with pytest.raises(life.Deferred, match="fence_observation"):
        first.prepare()
    first.close()
    saved = life.private_json(runtime.path)
    recovered = life.Admission(runtime, "second", "fingerprint", False)
    recovered.prepare()
    assert [row[0] for row in calls] == ["POST", "GET", "GET"]
    assert calls[1][1].endswith(saved["maintenance"]["id"])
    assert calls[0][2]["fence"] == calls[1][2]["fence"] == FENCE
    assert recovered.record["needs_unload"] is False and "maintenance" not in recovered.record


def test_admission_closed_can_drain_but_cannot_claim(runtime, monkeypatch):
    policy(runtime, enabled=False, allow_start=False)
    calls = transport(runtime, monkeypatch, [reply("draining")])
    no_readiness(runtime, monkeypatch)
    runtime.drain(OWNED, FENCE)
    with pytest.raises(life.Deferred, match="owner_policy"):
        runtime.claim(OWNED, FENCE)
    assert len(calls) == 1 and calls[0][1].endswith("/api/admission/drain")


def test_closed_admission_can_observe_lost_claim_without_authorizing_dispatch(runtime, monkeypatch):
    policy(runtime, enabled=False, allow_start=False)
    calls = transport(runtime, monkeypatch, [reply()])
    no_readiness(runtime, monkeypatch)
    runtime.claim(OWNED, FENCE, recover=True)
    with pytest.raises(life.Deferred, match="owner_policy"):
        runtime.claim(OWNED, FENCE)
    assert [(method, url.rsplit("/", 1)[1]) for method, url, _ in calls] == [("GET", "admission")]


def test_closed_admission_can_record_unload_ack_but_cannot_readmit(runtime, monkeypatch):
    policy(runtime, enabled=False, allow_start=False)
    calls = transport(runtime, monkeypatch, [reply("completed", maintenance_id=MID)])
    no_readiness(runtime, monkeypatch)
    maintenance = {"id": MID, "state": "intent"}
    saved = []
    with pytest.raises(life.Deferred, match="owner_policy"):
        runtime.unload(OWNED, FENCE, maintenance, lambda: saved.append(maintenance.copy()), recover=True)
    assert saved == [{"id": MID, "state": "completed"}]
    assert len(calls) == 1 and calls[0][0] == "GET"


def test_unconfirmed_drain_never_signals(runtime, monkeypatch):
    transport(runtime, monkeypatch, [reply("maintenance")])
    monkeypatch.setattr(life, "idle", lambda *a: None)
    monkeypatch.setattr(runtime, "persisted_idle", lambda: None)
    monkeypatch.setattr(runtime, "identity_command", lambda *a: pytest.fail("No signal before confirmed drain"))
    with pytest.raises(life.Deferred, match="fence_not_draining"):
        runtime.stop(OWNED, FENCE)


@pytest.mark.parametrize("result,code", [(reply("released"), None), (reply("held"), "release_unverified"),
    (reply("released", generation=MID), "fence_binding"), ("invalid-json", "release_unverified")])
def test_offline_release_validates_receipt_and_keeps_credentials_off_argv(runtime, monkeypatch, result, code):
    policy(runtime, enabled=False, allow_start=False)
    calls = []
    monkeypatch.setattr(runtime, "ports_free", lambda: calls.append("ports-free"))
    def command(args, **kwargs):
        assert calls == ["ports-free"]
        calls.append((args, kwargs))
        assert args == ["/usr/bin/python3", str(runtime.root / "scripts/runtime_admission.py"), "release"]
        assert json.loads(kwargs["input"]) == runtime.headers(OWNED, FENCE)
        assert FENCE["token"] not in " ".join(args)
        return NS(stdout=result if isinstance(result, str) else json.dumps(result))
    monkeypatch.setattr(runtime, "command", command)
    if code:
        with pytest.raises(life.Deferred, match=code):
            runtime.release(OWNED, FENCE)
    else:
        runtime.release(OWNED, FENCE)


def test_release_refuses_listener_before_sending_credentials(runtime, monkeypatch):
    def ports():
        raise life.Deferred("busy", "foreign_listener", "preserve peer")
    monkeypatch.setattr(runtime, "ports_free", ports)
    monkeypatch.setattr(runtime, "command", lambda *a, **kw: pytest.fail("No release while listener exists"))
    with pytest.raises(life.Deferred, match="foreign_listener"):
        runtime.release(OWNED, FENCE)


@pytest.mark.parametrize("second_gate_passes,close_on_unload", [(True, False), (False, False), (False, True)])
def test_two_item_adapter_one_claim_one_unload_one_post_per_item(runtime, tmp_path, monkeypatch, second_gate_passes, close_on_unload):
    events = []
    requests_seen = []
    maintenance_id = None
    maintenance_polls = 0
    render_count = 0
    unloaded = False
    generation = None
    token = None
    class Response:
        def __init__(self, value):
            self.value = value
        def raise_for_status(self):
            pass
        def json(self):
            return self.value
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def iter_content(self, size):
            yield b"fixture video"
    def request(method, url, **kwargs):
        nonlocal maintenance_id, maintenance_polls, render_count, unloaded, generation, token
        path = url.split("8190")[-1]
        requests_seen.append((method, path))
        if method == "POST" or path == "/api/admission" or path.startswith("/api/maintenance/"):
            headers = kwargs["headers"]
            if generation is None:
                generation, token = headers["X-H3-Lease-Generation"], headers["X-H3-Lease-Token"]
            assert headers == runtime.headers(OWNED, {"generation": generation, "token": token})
        value = reply(generation=generation)
        if path == "/api/admission/claim":
            assert life.private_json(runtime.path)["state"] == "claiming"
        elif path == "/api/maintenance/unload":
            assert render_count == 1
            maintenance_id = kwargs["json"]["maintenance_id"]
            assert life.private_json(runtime.path)["maintenance"]["id"] == maintenance_id
            value.update(state="queued", maintenance_id=maintenance_id)
        elif path.startswith("/api/maintenance/"):
            assert path.endswith(maintenance_id)
            maintenance_polls += 1
            unloaded = maintenance_polls == 2
            value.update(state="completed" if unloaded else "running", maintenance_id=maintenance_id)
            if unloaded and close_on_unload:
                policy(runtime, enabled=False, allow_start=False)
        elif path == "/api/uploads?kind=image":
            value = {"token": "fixture-upload"}
        elif path == "/api/renders":
            render_count += 1
            assert life.private_json(runtime.path)["state"] == "submitting"
            assert (tmp_path / f"renders/job/item{render_count}/intent.json").exists()
            assert render_count <= 2
            if render_count == 2:
                assert unloaded and second_gate_passes
            value = {"id": f"55555555-5555-4555-8555-55555555555{render_count}"}
        elif path.startswith("/api/jobs/"):
            value = {"status": "completed", "outputs": [{"id": 0, "media_type": "video"}]}
        elif path.startswith("/api/health"):
            value = {"connected": True, "ready": True, "model_status": "verified"}
        elif path == "/api/jobs?scope=active&limit=100":
            value = {"jobs": []}
        elif path == "/api/series?limit=100":
            value = {"series": []}
        elif path == "/api/settings":
            value = {"system_prompt": ""}
        elif path == "/api/admission/drain":
            assert render_count == (2 if second_gate_passes else 1)
            events.append("drain")
            value["state"] = "draining"
        else:
            assert path == "/api/admission"
        return Response(value)
    monkeypatch.setattr(runtime.session, "request", request)
    monkeypatch.setattr(runtime, "identities", lambda: OWNED)
    monkeypatch.setattr(life, "Runtime", lambda cfg: runtime)
    monkeypatch.setattr(adapter, "local_session", lambda: NS(
        get=lambda url, **kw: request("GET", url, **kw),
        post=lambda url, **kw: request("POST", url, **kw), close=lambda: None))
    monkeypatch.setattr(adapter, "moderate", lambda *a: None)
    monkeypatch.setattr(life.time, "sleep", lambda *a: None)
    monkeypatch.setattr(life, "idle", lambda *a: None)
    def resources(env, pids=()):
        events.append("gate")
        assert env["H3_MIN_RAM_GIB"] == "48" and env["H3_MIN_GPU_FREE_MIB"] == "20000"
        if unloaded and not second_gate_passes:
            raise life.Deferred("blocked_resources", "ram", "unchanged RAM gate")
    monkeypatch.setattr(life, "resources", resources)
    def start(record, save):
        events.append("start")
        record["owned"] = copy.deepcopy(OWNED)
        write(runtime.root / "runtime/webapp-state.json", OWNED["webapp"])
        save()
    monkeypatch.setattr(runtime, "start", start)
    monkeypatch.setattr(runtime, "ports_free", lambda: events.append("ports-free"))
    monkeypatch.setattr(runtime, "persisted_idle", lambda: None)
    monkeypatch.setattr(runtime, "identity_command", lambda service, verb, *a: events.append(verb))
    def command(args, **kwargs):
        if args[-1] == "release":
            credentials = json.loads(kwargs["input"])
            assert credentials["X-H3-Lease-Token"] == token
            events.append("release")
            return NS(stdout=json.dumps(reply("released", generation=generation)))
        if args[0].endswith("stop_comfyui.sh"):
            events.append("stop-engine")
        else:
            assert args[0].endswith("check_resources.sh") and unloaded
            events.append("canonical-gate")
        return NS(stdout="")
    monkeypatch.setattr(runtime, "command", command)
    def ffmpeg(args, **kwargs):
        assert args[0] == "ffmpeg"
        if "-loop" in args:
            Path(args[-1]).write_bytes(b"GIF89a fixture")
    monkeypatch.setattr(adapter.subprocess, "run", ffmpeg)
    source = tmp_path / "source.png"
    Image.new("RGB", (16, 16), "white").save(source)
    cfg = {"state": str(tmp_path), "local_video_url": "http://127.0.0.1:8190",
           "local_video_runtime_root": str(runtime.root)}
    with life.job_admission(cfg) as batch:
        first = adapter.animate(cfg, {"id": "job"}, {"id": "item1", "label": "Hello"}, source, batch=batch)
        assert first.exists() and "drain" not in events
        if second_gate_passes:
            second = adapter.animate(cfg, {"id": "job"}, {"id": "item2", "label": "Thanks"}, source, batch=batch)
            assert second.exists()
        else:
            with pytest.raises(life.Deferred, match="owner_policy" if close_on_unload else "ram"):
                adapter.animate(cfg, {"id": "job"}, {"id": "item2", "label": "Thanks"}, source, batch=batch)
    assert requests_seen.count(("POST", "/api/admission/claim")) == 1
    assert requests_seen.count(("POST", "/api/maintenance/unload")) == 1
    assert requests_seen.count(("POST", "/api/renders")) == (2 if second_gate_passes else 1)
    assert events.count("start") == 1
    saved = life.private_json(runtime.path)
    assert saved["state"] == "offline" and "fence" not in saved
    assert events[-7:] == ["drain", "signal", "clear", "stop-engine", "ports-free", "ports-free", "release"]
    assert events.count("signal") == events.count("stop-engine") == events.count("release") == 1
