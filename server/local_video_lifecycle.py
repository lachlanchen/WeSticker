"""Installed ownership and fenced admission for private canonical LocalVideoGen.

No daemon, GPU import, automatic lease expiry/steal, or render POST lives here.
Canonical Studio/engine enforcement is required; a caller flock alone is not it.
"""

from contextlib import contextmanager, nullcontext
import csv
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import stat
import subprocess
import tempfile
import time
import uuid

import requests


BOOT = Path("/proc/sys/kernel/random/boot_id")
PORTS = {"comfyui": 8188, "webapp": 8190}
JOB_TERMINAL = {"completed", "success", "failed", "error", "cancelled"}
SERIES_IDLE = {"ready", "paused", "completed", "failed", "cancelled"}


class Deferred(ValueError):
    def __init__(self, state, code, message):
        self.status = {"state": state, "code": code, "message": message, "can_submit": False}
        super().__init__(f"Animation deferred ({state}/{code}): {message}")


def atomic_json(path, value):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=".lifecycle-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def private_json(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise Deferred("error", "private_state", "Runtime ownership files must be private and owner-controlled.")
        value = json.load(stream)
        if not isinstance(value, dict):
            raise ValueError("Invalid ownership record")
        return value


@contextmanager
def exclusive(path, create=True):
    flags = os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT if create else 0)
    fd = os.open(path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise Deferred("error", "lock_owner", "The admission lock has an unexpected owner.")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Deferred("busy", "lease_held", "Another lifecycle or animation observer holds the lease.") from error
        yield
    finally:
        os.close(fd)


def local_session():
    session = requests.Session()
    session.trust_env = False
    original = session.request
    def request(method, url, **kwargs):
        kwargs["allow_redirects"] = False
        response = original(method, url, **kwargs)
        if 300 <= response.status_code < 400:
            raise Deferred("error", "redirect", "The local renderer redirected a request.")
        return response
    session.request = request
    return session


def get_json(session, url):
    response = session.get(url, timeout=10)
    response.raise_for_status()
    value = response.json()
    if not isinstance(value, dict):
        raise Deferred("error", "response_shape", "The renderer returned an invalid status.")
    return value


def idle(session, base="http://127.0.0.1:8190", engine="http://127.0.0.1:8188"):
    queue = get_json(session, engine + "/queue")
    for key in ("queue_running", "queue_pending"):
        if not isinstance(queue.get(key), list) or queue[key]:
            raise Deferred("busy", "engine_queue", "The engine queue is busy or unverifiable.")
    jobs = get_json(session, base + "/api/jobs?scope=active&limit=100")
    if not isinstance(jobs.get("jobs"), list) or jobs["jobs"]:
        raise Deferred("busy", "jobs", "Another render is active or unverifiable.")
    records = get_json(session, base + "/api/series?limit=100").get("series")
    if (not isinstance(records, list) or len(records) >= 100
            or any(not isinstance(row, dict) or row.get("status") not in SERIES_IDLE for row in records)):
        raise Deferred("busy", "series", "The series queue needs owner review.")
    prompt = get_json(session, base + "/api/settings").get("system_prompt")
    if not isinstance(prompt, str) or prompt.strip():
        raise Deferred("busy", "shared_prompt", "Shared renderer instructions need owner review.")


def resources(env, allowed_pids=()):
    memory = {k: int(v.split()[0]) for k, v in
              (line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())}
    if memory["MemAvailable"] < 48 * 1024**2:
        raise Deferred("blocked_resources", "ram", "48 GiB available RAM is required; nothing was submitted.")
    if memory["SwapTotal"] and (memory["SwapTotal"] - memory["SwapFree"]) * 100 > memory["SwapTotal"] * 75:
        raise Deferred("blocked_resources", "swap", "Swap use must be at most 75%; shared work is preserved.")
    def query(option):
        result = subprocess.run(["nvidia-smi", option, "--format=csv,noheader,nounits"],
                                env=env, capture_output=True, text=True, timeout=10, check=True)
        return list(csv.reader(result.stdout.splitlines(), skipinitialspace=True))
    try:
        devices = query("--query-gpu=index,uuid,memory.free")
        gpu = [row for row in devices if len(row) == 3 and row[0].strip() == "0"]
        if len(gpu) != 1 or int(gpu[0][2]) < 20000:
            raise Deferred("blocked_resources", "gpu_memory", "GPU 0 needs at least 20,000 MiB free.")
        for row in query("--query-compute-apps=gpu_uuid,pid"):
            if len(row) != 2:
                raise ValueError("Invalid GPU process row")
            if row[0].strip() == gpu[0][1].strip() and int(row[1]) not in allowed_pids:
                raise Deferred("busy", "gpu_owner", "GPU 0 has another compute owner; nothing will be stopped.")
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        if isinstance(error, Deferred):
            raise
        raise Deferred("blocked_resources", "gpu_probe", "GPU identity/resources are unavailable; check the loaded driver environment.") from error


class Runtime:
    def __init__(self, cfg):
        root = cfg.get("local_video_runtime_root")
        if not root:
            raise Deferred("offline", "owner_setup", "On-demand runtime ownership is not configured.")
        self.root = Path(root).resolve(strict=True)
        if cfg.get("local_video_url", "").rstrip("/") != "http://127.0.0.1:8190":
            raise Deferred("error", "origin", "Managed lifecycle requires the canonical loopback endpoint.")
        self.private = self.root / "runtime/private"
        self.path = self.private / "app-admission.json"
        self.lock = self.private / "app-admission.lock"
        self.session = local_session()

    def policy(self, operation="admit"):
        if operation not in {"admit", "observe", "drain"}:
            raise ValueError("Unknown lifecycle permission")
        try:
            value = private_json(self.private / "westicker-lifecycle-policy.json")
            if (value.get("version") != 1 or value.get("owner") != "westicker"
                    or value.get("exclusive") is not True
                    or str(self.root) != value.get("root")
                    or any(type(value.get(key)) is not bool
                           for key in ("enabled", "allow_start", "allow_stop"))):
                raise ValueError("Installation policy is invalid")
        except (OSError, ValueError) as error:
            raise Deferred("offline", "owner_policy", "Runtime ownership policy is absent or unverifiable; no service was adopted.") from error
        if operation == "admit" and not all(value[key] for key in ("enabled", "allow_start", "allow_stop")):
            raise Deferred("offline", "owner_policy", "New animation admission is disabled; existing receipts remain recoverable.")
        if operation == "drain" and not value["allow_stop"]:
            raise Deferred("draining", "drain_revoked", "Owned cleanup permission is revoked; preserve the runtime for its owner's manual handoff.")
        return value

    def environment(self):
        policy = self.policy()
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("H3_", "CUDA_", "LOCALVIDEOGEN_", "LD_"))}
        env.update(H3_CUDA_DEVICES="0", H3_AUX_DEVICE="gpu:0", H3_PORT="8188",
                   H3_WEBAPP_PORT="8190", H3_COMFY_URL="http://127.0.0.1:8188",
                   H3_MIN_RAM_GIB="48", H3_MIN_GPU_FREE_MIB="20000")
        driver = policy.get("driver")
        if driver:
            # A repaired system stack wins after reboot; retained compatibility
            # files are a validated fallback, not a permanent driver pin.
            try:
                native = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                        env=env, capture_output=True, text=True, timeout=10, check=True)
                loaded = Path("/proc/driver/nvidia/version").read_text()
                versions = native.stdout.splitlines()
                if versions and all(re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", v.strip())
                                    and re.search(r"\s" + re.escape(v.strip()) + r"\s", loaded) for v in versions):
                    return env
            except (OSError, subprocess.SubprocessError):
                pass
            try:
                version = driver["version"]
                loaded = Path("/proc/driver/nvidia/version").read_text()
                if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)+", version) or not re.search(r"\s" + re.escape(version) + r"\s", loaded):
                    raise ValueError("Driver release changed")
                directory = Path(driver["directory"]).resolve(strict=True)
                libraries = Path(driver["libraries"]).resolve(strict=True)
                names = ["nvidia-smi"] + [f"{name}.so.{version}" for name in
                         ("libcuda", "libnvidia-ml", "libnvidia-ptxjitcompiler", "libnvidia-nvvm", "libnvidia-gpucomp")]
                for name in names:
                    with (directory / name).open("rb") as stream:
                        digest = hashlib.file_digest(stream, "sha256").hexdigest()
                    if digest != driver["sha256"][name]:
                        raise ValueError("Driver file changed")
                    if name != "nvidia-smi" and (libraries / (name.rsplit(".so.", 1)[0] + ".so.1")).resolve(strict=True) != directory / name:
                        raise ValueError("Library link changed")
                env["PATH"] = str(directory) + os.pathsep + env.get("PATH", os.defpath)
                env["LD_LIBRARY_PATH"] = str(libraries)
            except (KeyError, OSError, TypeError, ValueError) as error:
                raise Deferred("blocked_resources", "driver_identity", "The approved driver bundle no longer matches the loaded kernel and hashes.") from error
        return env

    def command(self, args, *, env=None, timeout=30, check=True, input=None):
        try:
            return subprocess.run(args, cwd=self.root, env=env, timeout=timeout,
                                  check=check, capture_output=True, text=True, input=input)
        except (OSError, subprocess.SubprocessError) as error:
            raise Deferred("error", "runtime_command", "Canonical runtime operation failed; preserve its state/log and reconcile ownership.") from error

    def identity_command(self, service, *args, check=True):
        return self.command(["/usr/bin/python3", str(self.root / "scripts/runtime_identity.py"),
                             "--service", service, *args], check=check)

    def identities(self):
        result = {}
        for service, port in PORTS.items():
            path = self.root / f"runtime/{service}-state.json"
            if not path.exists():
                continue
            value = private_json(path)
            alive = self.identity_command(service, "alive", "--expect-pid", str(value["pid"]),
                                          "--expect-instance", value["instance"], check=False)
            if private_json(path) != value:
                raise Deferred("error", "identity_changed", "Runtime identity changed during verification.")
            if alive.returncode == 3:
                # Canonical startup clears its own proven-dead state under its
                # own lock. Observing it here never deletes another owner's file.
                continue
            if alive.returncode != 0:
                raise Deferred("error", "identity_unverified", "The original runtime identity could not be verified.")
            self.identity_command(service, "verify")
            if private_json(path) != value or value.get("port") != port:
                raise Deferred("error", "identity_changed", "Runtime identity changed during verification.")
            args = value["argv"]
            if service == "comfyui" and ("--cuda-device" not in args or args[args.index("--cuda-device") + 1] != "0"):
                raise Deferred("busy", "gpu_route", "The engine is not exclusively routed to GPU 0.")
            if service == "webapp":
                environment = Path(f"/proc/{value['pid']}/environ").read_bytes().split(b"\0")
                if b"H3_AUX_DEVICE=gpu:0" not in environment:
                    raise Deferred("busy", "gpu_route", "Studio auxiliary stages are not routed to GPU 0.")
            listener = self.command(["ss", "-H", "-ltnp", f"sport = :{port}"]).stdout
            if f"127.0.0.1:{port}" not in listener or f"pid={value['pid']}," not in listener or len(listener.splitlines()) != 1:
                raise Deferred("error", "listener", "Runtime listener/owner is not the expected loopback process.")
            result[service] = value
        return result

    def ports_free(self):
        if self.command(["ss", "-H", "-ltn", "( sport = :8188 or sport = :8190 )"]).stdout.strip():
            raise Deferred("busy", "foreign_listener", "A pre-existing listener must remain with its owner.")

    def persisted_idle(self):
        for name, table, terminal in (("webapp-jobs.sqlite3", "jobs", JOB_TERMINAL),
                                      ("webapp-series.sqlite3", "series", SERIES_IDLE)):
            path = self.private / name
            if not path.is_file() or path.is_symlink():
                raise Deferred("error", "registry", "The canonical saved-work registry needs owner review.")
            try:
                with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2) as db:
                    states = {row[0] for row in db.execute(f"SELECT DISTINCT status FROM {table}")}
                if not states <= terminal:
                    raise Deferred("busy", "saved_work", "Saved jobs or runnable series must remain with their owner.")
            except sqlite3.Error as error:
                raise Deferred("error", "registry", "Saved work cannot be verified read-only.") from error
        settings = private_json(self.private / "h3-studio-settings.json")
        if settings.get("version") != 1 or not isinstance(settings.get("system_prompt"), str) or settings["system_prompt"].strip():
            raise Deferred("busy", "shared_prompt", "Shared renderer instructions need owner review.")

    def observe(self, owned):
        """Verify a captured origin/instance, not readiness for another render."""
        self.policy("observe")
        current = self.identities()
        if current != owned or set(current) != set(PORTS):
            raise Deferred("busy", "ownership", "The expected complete runtime identity is unavailable; no service was adopted.")
        return current

    def ready(self, owned, *, new_submission=True):
        if not new_submission:
            return self.observe(owned)
        self.policy()
        current = self.observe(owned)
        resources(self.environment(), {current["comfyui"]["pid"]})
        idle(self.session)
        health = get_json(self.session, "http://127.0.0.1:8190/api/health?deep=1")
        if not (health.get("connected") is True and health.get("ready") is True and health.get("model_status") == "verified"):
            raise Deferred("starting", "not_ready", "Model-verified deep readiness is not established.")

    def headers(self, owned, fence):
        try:
            generation, token = fence["generation"], fence["token"]
            if str(uuid.UUID(generation)) != generation or not re.fullmatch(r"[a-f0-9]{64}", token):
                raise ValueError("Invalid lease credentials")
            instances = {name: owned[name]["instance"] for name in PORTS}
            if any(not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value)
                   for value in instances.values()):
                raise ValueError("Invalid instance")
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise Deferred("error", "fence_record", "The private canonical lease binding needs owner reconciliation.") from error
        return {"X-H3-Lease-Owner": "westicker", "X-H3-Lease-Generation": generation,
                "X-H3-Lease-Token": token, "X-H3-Studio-Instance": instances["webapp"],
                "X-H3-Engine-Instance": instances["comfyui"]}

    def fenced(self, owned, fence, method, path, *, payload=None):
        self.observe(owned)
        headers = self.headers(owned, fence)
        try:
            response = self.session.request(method, "http://127.0.0.1:8190" + path,
                                            headers=headers, timeout=10,
                                            **({"json": payload} if method == "POST" else {}))
            response.raise_for_status()
            value = response.json()
        except (requests.RequestException, ValueError) as error:
            raise Deferred("error", "fence_observation", "Canonical lease outcome is unverified; preserve its binding and reconcile without a new mutation.") from error
        self.observe(owned)
        self.check_binding(value, owned, fence)
        return value

    @staticmethod
    def check_binding(value, owned, fence):
        expected = {"version": 1, "owner": "westicker", "generation": fence["generation"],
                    "studio_instance": owned["webapp"]["instance"],
                    "engine_instance": owned["comfyui"]["instance"]}
        if not isinstance(value, dict) or any(value.get(key) != item for key, item in expected.items()):
            raise Deferred("error", "fence_binding", "The canonical reply does not match the saved lease and runtime instances.")

    def claim(self, owned, fence, *, recover=False):
        self.policy("observe" if recover else "admit")
        result = self.fenced(owned, fence, "GET" if recover else "POST",
                             "/api/admission" if recover else "/api/admission/claim", payload={})
        if result.get("state") != "held":
            raise Deferred("busy", "fence_not_held", "Canonical submission ownership is not held by this batch.")

    def unload(self, owned, fence, maintenance, save, *, recover=False):
        self.policy("observe" if recover else "admit")
        try:
            if str(uuid.UUID(maintenance["id"])) != maintenance["id"]:
                raise ValueError("Invalid maintenance ID")
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            raise Deferred("error", "maintenance_binding", "The original maintenance identity needs owner reconciliation.") from error
        def observed(result):
            self.maintenance_status(result, maintenance)
            save()
            if maintenance["state"] == "failed":
                raise Deferred("error", "maintenance_failed", "The engine could not confirm unload completion; preserve the maintenance request.")
        if not recover:
            result = self.fenced(owned, fence, "POST", "/api/maintenance/unload",
                                 payload={"maintenance_id": maintenance["id"]})
            observed(result)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            result = self.fenced(owned, fence, "GET", "/api/maintenance/" + maintenance["id"])
            observed(result)
            if maintenance["state"] == "completed":
                # Completion is necessary but never replaces actual resources.
                env = self.environment()
                resources(env, {owned["comfyui"]["pid"]})
                self.command([str(self.root / "scripts/check_resources.sh")], env=env)
                self.ready(owned)
                self.claim(owned, fence, recover=True)
                return
            time.sleep(1)
        raise Deferred("busy", "maintenance_pending", "Unload completion is unverified; no next render is admitted.")

    @staticmethod
    def maintenance_status(result, maintenance):
        state = result.get("state")
        if result.get("maintenance_id") != maintenance["id"] or state not in {"queued", "running", "completed", "failed"}:
            raise Deferred("error", "maintenance_binding", "Unload acknowledgment does not match the original maintenance request.")
        maintenance["state"] = state

    def drain(self, owned, fence):
        self.policy("drain")
        result = self.fenced(owned, fence, "POST", "/api/admission/drain", payload={})
        if result.get("state") != "draining":
            raise Deferred("draining", "fence_not_draining", "Canonical mutations are not confirmed closed; no runtime was signalled.")

    def release(self, owned, fence):
        self.policy("drain")
        self.ports_free()
        result = self.command(["/usr/bin/python3", str(self.root / "scripts/runtime_admission.py"), "release"],
                              input=json.dumps(self.headers(owned, fence)))
        try:
            value = json.loads(result.stdout)
        except (TypeError, ValueError) as error:
            raise Deferred("draining", "release_unverified", "The canonical offline release was not confirmed.") from error
        self.check_binding(value, owned, fence)
        if value.get("state") != "released":
            raise Deferred("draining", "release_unverified", "The canonical offline release was not confirmed.")

    def start(self, record, save):
        self.policy()
        if self.identities():
            raise Deferred("busy", "existing_runtime", "A pre-existing runtime is not owned by this lifecycle.")
        self.ports_free()
        self.persisted_idle()
        env = self.environment()
        resources(env)
        self.command([str(self.root / "scripts/check_resources.sh")], env=env)
        record["state"] = "starting"
        record["expected_instances"] = {service: str(uuid.uuid4()) for service in PORTS}
        save()
        for service, key in (("comfyui", "H3_RUNTIME_INSTANCE"), ("webapp", "H3_WEBAPP_INSTANCE")):
            self.policy()
            self.command([str(self.root / f"scripts/start_{service}.sh")],
                         env=env | {key: record["expected_instances"][service]}, timeout=180)
            current = self.identities()
            for name, identity in current.items():
                if identity["instance"] != record["expected_instances"][name]:
                    raise Deferred("busy", "startup_race", "Another owner started the runtime; it will not be adopted or stopped.")
            record["owned"] = current
            save()
        record["state"] = "preparing"
        save()

    def stop(self, owned, fence=None):
        if not owned:
            return
        self.policy("drain")
        # Keep canonical Studio launches out while draining, then use its pidfd
        # identity helper because stop_webapp.sh has no expected-owner contract.
        with exclusive(self.root / "runtime/webapp-lifecycle.lock"):
            if self.identities() != owned:
                raise Deferred("draining", "ownership_changed", "Runtime ownership changed; nothing was signalled.")
            if set(owned) != set(PORTS):
                raise Deferred("draining", "partial_start", "Partial startup requires owner reconciliation; no broad cleanup.")
            idle(self.session)
            self.persisted_idle()
            self.drain(owned, fence)
            web = owned["webapp"]
            self.policy("drain")
            self.identity_command("webapp", "signal", "--expect-pid", str(web["pid"]),
                                  "--expect-instance", web["instance"], "--signal", "INT")
            deadline = time.monotonic() + 15
            while Path(f"/proc/{web['pid']}").exists() and time.monotonic() < deadline:
                time.sleep(0.25)
            if Path(f"/proc/{web['pid']}").exists():
                raise Deferred("draining", "still_running", "The owned Studio did not exit; no force or peer cleanup was attempted.")
            path = self.root / "runtime/webapp-state.json"
            if private_json(path) != web:
                raise Deferred("draining", "ownership_changed", "Studio state changed; the engine was preserved.")
            self.identity_command("webapp", "clear")
            engine = owned["comfyui"]
            self.policy("drain")
            self.command([str(self.root / "scripts/stop_comfyui.sh"), "--expect-pid", str(engine["pid"]),
                          "--expect-instance", engine["instance"]], timeout=60)
            self.ports_free()
            self.release(owned, fence)

    def after_boot(self, record):
        """Recover only pre-POST/finished work, never an uncertain provider job."""
        if (not record.get("boot_id") or record["boot_id"] == BOOT.read_text().strip()
                or record.get("state") not in {"offline", "idle", "preparing", "starting", "draining"}
                or record.get("provider") or record.get("fence")):
            return record
        if self.identities():
            raise Deferred("busy", "existing_runtime", "A live runtime must remain with its owner.")
        self.ports_free()
        self.persisted_idle()
        return {"version": 1, "state": "offline", "owned": {}, "attempt": None}


def read_record(path):
    record = private_json(path) if path.exists() else {"version": 1, "owned": {}}
    if (record.get("version") != 1 or not isinstance(record.get("owned"), dict)
            or record.get("state", "offline") not in
            {"offline", "idle", "preparing", "starting", "claiming", "maintenance", "submitting", "monitoring", "draining", "error"}):
        raise Deferred("error", "admission_record", "The saved admission record needs owner reconciliation.")
    return record


class Admission:
    def __init__(self, runtime, key, fingerprint, resume):
        self.runtime = runtime
        self.record = runtime.after_boot(read_record(runtime.path))
        prior = self.record.get("attempt")
        self.attempt = {"key": key, "fingerprint": fingerprint}
        if prior and prior != self.attempt:
            raise Deferred("busy", "reconcile_attempt", "The previous attempt still owns admission; reconcile its existing ID, never resubmit.")
        if resume and (prior != self.attempt or not self.record.get("owned")):
            raise Deferred("busy", "receipt_ownership", "The receipt has no matching managed runtime ownership; no replacement will be started or observed.")
        if self.record.get("state") in {"starting", "draining", "error"}:
            raise Deferred(self.record["state"], "reconcile_runtime", "The prior lifecycle operation needs owner reconciliation.")
        if prior and self.record.get("state") in {"submitting", "monitoring"} and not resume:
            raise Deferred("busy", "reconcile_attempt", "A submission may already exist; reconcile it before any new POST.")
        if not prior:
            self.record.pop("provider", None)
        self.record.update(attempt=self.attempt, state="monitoring" if resume else "preparing")
        self.save()

    def save(self):
        self.record["updated"] = time.time()
        self.record["boot_id"] = BOOT.read_text().strip()
        atomic_json(self.runtime.path, self.record)

    def prepare(self):
        if not self.record.get("owned"):
            self.runtime.start(self.record, self.save)
        fence = self.record.get("fence")
        if not fence or fence.get("state") != "held":
            recover = bool(fence)
            if not fence:
                fence = {"generation": str(uuid.uuid4()), "token": secrets.token_hex(32), "state": "claiming"}
                self.record["fence"] = fence
            self.record["state"] = "claiming"
            self.save()
            self.runtime.claim(self.record["owned"], fence, recover=recover)
            fence["state"] = "held"
            self.record["state"] = "preparing"
            self.save()
        if self.record.get("needs_unload"):
            maintenance = self.record.get("maintenance")
            recover = bool(maintenance)
            if not maintenance:
                maintenance = {"id": str(uuid.uuid4()), "state": "intent"}
                self.record["maintenance"] = maintenance
            self.record["state"] = "maintenance"
            self.save()
            def save_maintenance():
                # A confirmed unload is safe to drain if a later cold gate
                # fails. Pending/failed cleanup must retain its held state.
                if maintenance["state"] == "completed":
                    self.record["state"] = "preparing"
                self.save()
            self.runtime.unload(self.record["owned"], fence, maintenance, save_maintenance, recover=recover)
            self.record["needs_unload"] = False
            self.record.pop("maintenance", None)
        self.runtime.ready(self.record["owned"])
        self.record["state"] = "preparing"
        self.save()

    def submitting(self):
        if self.record["state"] != "preparing":
            raise Deferred("busy", "duplicate_post", "This lease cannot authorize another render POST.")
        self.runtime.ready(self.record["owned"])
        self.runtime.claim(self.record["owned"], self.record["fence"], recover=True)
        headers = self.mutation_headers()
        self.record["state"] = "submitting"
        self.save()
        return headers

    def mutation_headers(self):
        self.runtime.policy()
        self.runtime.observe(self.record["owned"])
        return self.runtime.headers(self.record["owned"], self.record.get("fence"))

    def receipt(self, provider):
        if self.record.get("provider", provider) != provider:
            raise Deferred("busy", "receipt_conflict", "The saved provider ID changed; reconcile without a new POST.")
        self.record.update(state="monitoring", provider=provider)
        self.save()

    def observe(self):
        if self.record["state"] != "monitoring" or not self.record.get("provider"):
            raise Deferred("busy", "receipt_required", "Observation requires the original provider receipt.")
        self.runtime.observe(self.record.get("owned", {}))

    def complete(self):
        if self.record["state"] == "monitoring":
            self.record["needs_unload"] = True
        self.record.pop("provider", None)
        self.record.update(state="idle", attempt=None)
        self.save()

    def close(self):
        if self.record["state"] == "preparing":
            self.complete()
        if self.record["state"] != "idle":
            return
        # Zero-second idle grace: no unattended supervisor or idle GPU daemon.
        self.record["state"] = "draining"
        self.save()
        try:
            self.runtime.stop(self.record.get("owned", {}), self.record.get("fence"))
            self.record.update(state="offline", owned={})
            for key in ("fence", "maintenance", "needs_unload"):
                self.record.pop(key, None)
        except Exception as error:
            self.record["cleanup"] = getattr(error, "status", {"state": "error", "code": "cleanup_unverified"})
        self.save()


class JobAdmission:
    """Keep one runtime and exclusive slot through serial items of a worker job."""

    def __init__(self, runtime, cfg):
        self.runtime = runtime
        self.cfg = cfg
        self.last = None
        self.active = False
        self.closed = False

    @contextmanager
    def item(self, cfg, key, fingerprint, *, resume=False):
        if cfg is not self.cfg or self.active or self.closed:
            raise Deferred("error", "job_lease", "The animation job lease is not available for this item.")
        self.runtime.policy("observe" if resume else "admit")
        lease = Admission(self.runtime, key, fingerprint, resume)
        self.last = lease
        self.active = True
        try:
            yield lease
        finally:
            self.active = False
            if lease.record["state"] == "preparing":
                lease.complete()

    def close(self):
        self.closed = True
        if self.last:
            self.last.close()


@contextmanager
def job_admission(cfg):
    runtime = Runtime(cfg)
    try:
        # The batch itself grants no submit authority; each new item rechecks
        # admission, while an original receipt can recover after closure.
        runtime.policy("observe")
        with exclusive(runtime.lock):
            batch = JobAdmission(runtime, cfg)
            try:
                yield batch
            finally:
                batch.close()
    finally:
        runtime.session.close()


@contextmanager
def admission(cfg, key, fingerprint, *, resume=False, batch=None):
    if batch is not None:
        with batch.item(cfg, key, fingerprint, resume=resume) as lease:
            yield lease
        return
    if resume and not cfg.get("local_video_runtime_root"):
        # Legacy receipts remain downloadable; this never grants a new POST/start.
        yield None
        return
    runtime = Runtime(cfg)
    try:
        runtime.policy("observe" if resume else "admit")
        with exclusive(runtime.lock):
            lease = Admission(runtime, key, fingerprint, resume)
            try:
                yield lease
            finally:
                lease.close()
    finally:
        runtime.session.close()


def status(cfg):
    """Read-only availability for a parent-owned API/status integration."""
    runtime = None
    try:
        runtime = Runtime(cfg)
        runtime.policy()
        with exclusive(runtime.lock, create=False) if runtime.lock.exists() else nullcontext():
            record = runtime.after_boot(read_record(runtime.path))
            if record.get("attempt") or record.get("state") in {"starting", "draining", "error"}:
                state = record.get("state")
                return {"state": state if state in {"starting", "draining", "error"} else "busy",
                        "code": "lease_pending", "can_submit": False,
                        "message": "An existing attempt/lifecycle operation needs observation."}
            if record.get("owned"):
                runtime.ready(record["owned"])
                return {"state": "ready", "code": "verified", "can_submit": True,
                        "message": "Ready for one leased submission; not a resource reservation."}
            if runtime.identities():
                raise Deferred("busy", "existing_runtime", "An existing runtime belongs to another owner.")
            runtime.ports_free()
            runtime.persisted_idle()
            resources(runtime.environment())
            return {"state": "available", "code": "on_demand", "can_submit": True,
                    "message": "The renderer is stopped and can start on demand."}
    except Deferred as error:
        return error.status
    except (OSError, ValueError, KeyError, TypeError, requests.RequestException):
        return {"state": "error", "code": "unverified", "can_submit": False,
                "message": "Runtime state could not be verified; no operation was attempted."}
    finally:
        if runtime:
            runtime.session.close()
