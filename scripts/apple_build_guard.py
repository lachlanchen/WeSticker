"""Protocol-1 shared Mac guard for an already admitted bounded operation.

This is not a scheduler. The caller must first obtain an explicit predecessor
handback, supply fresh resource/process checks, and verify any owned QA cleanup.
There is deliberately no context-manager, EXIT trap, TTL, or recovery command.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import subprocess


GUARD_PATH = Path("/tmp/lazyingart-apple-build.lock")


class PreflightConflict(RuntimeError):
    """A verified conflict before starting a child, not an uncertain probe."""


class GuardRetained(RuntimeError):
    """Explicit owner recovery is needed; never remove a peer's guard."""


class AppleBuildGuard:
    def __init__(self, *, owner, checkout, operation, handoff, path=GUARD_PATH):
        if not all(str(value).strip() for value in (owner, checkout, operation, handoff)):
            raise ValueError("Owner, checkout, bounded operation and actual handoff are required")
        self.path = Path(path)
        self.owner = owner
        self.checkout = str(checkout)
        self.operation = operation
        self.handoff = str(handoff)
        self.identity = None
        self.record = None
        self.children = []
        self.uncertain = False
        self.released = False

    def acquire(self):
        if self.identity is not None:
            raise RuntimeError("A guard instance may acquire only once")
        self.path.mkdir(mode=0o700)
        info = self.path.lstat()
        self.identity = (info.st_dev, info.st_ino)
        if not stat.S_ISDIR(info.st_mode):
            raise GuardRetained("Acquired path is not a directory")
        # A failed/partial metadata write remains occupied for explicit recovery.
        self.record = {
            "protocol": 1, "app": "WeSticker", "owner": self.owner,
            "host": socket.gethostname(), "token": secrets.token_hex(24),
            "wrapperPid": os.getpid(),
            "wrapperStarted": subprocess.check_output(
                ["ps", "-p", str(os.getpid()), "-o", "lstart="], text=True).strip(),
            "acquiredUTC": datetime.now(timezone.utc).isoformat(),
            "checkout": self.checkout, "operation": self.operation,
            "handoff": self.handoff,
        }
        fd = os.open(self.path / "owner.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(self.record, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        self._verify_identity()

    def _verify_identity(self):
        if self.identity is None or self.released:
            raise GuardRetained("No active owned guard")
        info = self.path.lstat()
        if not stat.S_ISDIR(info.st_mode) or (info.st_dev, info.st_ino) != self.identity:
            raise GuardRetained("Guard directory identity changed")
        if {item.name for item in self.path.iterdir()} != {"owner.json"}:
            raise GuardRetained("Unexpected or partial guard contents")
        metadata = self.path / "owner.json"
        if not stat.S_ISREG(metadata.lstat().st_mode):
            raise GuardRetained("Owner metadata is not a regular file")
        if json.loads(metadata.read_text()) != self.record:
            raise GuardRetained("Guard metadata or ownership changed")

    def _verify_children(self):
        if self.uncertain:
            raise GuardRetained("Interrupted or uncertain child state")
        for child in self.children:
            if child.poll() is None:
                raise GuardRetained("Owned child has not exited")
            try:
                os.killpg(child.pid, 0)
            except ProcessLookupError:
                continue
            except OSError as error:
                raise GuardRetained("Cannot establish owned process-group cleanup") from error
            raise GuardRetained("Owned process group still exists")

    def run(self, command, *, cwd, log, timeout):
        """Run one foreground child; detached services require caller cleanup checks."""
        self._verify_identity()
        self._verify_children()
        if timeout <= 0:
            raise ValueError("A positive bounded timeout is required")
        # Mark uncertain before launch, including Popen failure or signal races.
        self.uncertain = True
        child = subprocess.Popen(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        self.children.append(child)
        code = child.wait(timeout=timeout)
        self.uncertain = False
        self._verify_children()
        return code

    def release(self, *, cleanup_verified):
        if cleanup_verified is not True:
            raise GuardRetained("Owned QA/descendant cleanup has not been verified")
        self._verify_children()
        self._verify_identity()
        (self.path / "owner.json").unlink()
        self.path.rmdir()
        self.released = True


def run_guarded(guard, command, *, cwd, log, timeout, preflight, verify_cleanup):
    """Acquire only after preflight; rerun checks while holding the common guard.

    preflight must raise PreflightConflict for a proven resource/process conflict.
    A failed/unknown probe, exception, signal or timeout retains the guard. After
    a timeout the caller must reconcile its exact child/descendants, not retry.
    verify_cleanup must check all operation-owned resources, including any
    simulator or detached QA helper. False/unknown retains the guard.
    """
    preflight()
    guard.acquire()
    try:
        preflight()
    except PreflightConflict:
        guard.release(cleanup_verified=True)  # No child or QA resource was started.
        raise
    code = guard.run(command, cwd=cwd, log=log, timeout=timeout)
    guard.release(cleanup_verified=verify_cleanup())
    return code
