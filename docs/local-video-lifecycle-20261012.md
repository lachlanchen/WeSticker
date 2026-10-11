# LocalVideoGen On-Demand Lifecycle

## Current Scope

Implemented, fixture-tested, **not activated or live-start qualified**. No model
render, service startup/shutdown, policy installation, driver change or peer
cleanup was performed. Parent owns activation, API integration and any canary.

Owned files: `server/local_video.py`, `server/local_video_lifecycle.py`,
`tests/test_local_video_lifecycle.py`, and this document. Canonical LocalVideoGen
scripts and configuration remain unchanged. No commit by this worker.

## Durable Policy, Bounded Lease

The initial boot-bound 24-hour grant draft is superseded. Installation approval
is durable across time and reboots; no daily operator renewal is required.
An explicit app-owned installation supplies `local_video_runtime_root` and the
existing canonical loopback URL, then installs this private owner-controlled
file under the canonical root (no policy has been created by this work):

```json
{
  "version": 1,
  "owner": "westicker",
  "enabled": true,
  "exclusive": true,
  "root": "/absolute/canonical/LocalVideoGen",
  "allow_start": true,
  "allow_stop": true
}
```

Filename: `runtime/private/westicker-lifecycle-policy.json`, regular file owned
by the service UID, mode 0600, no symlink. `enabled: false` revokes admission.
`exclusive` records the installation's cooperating-owner arrangement, not a
claim that unmodified Studio/API writers automatically honor this lock. Those
writers must use the same admission protocol or be excluded during app work.
Canonical saved jobs, runnable series, shared prompt and live owners are checked
without adopting or modifying them. This is not a global scheduler.

The worker holds a nonblocking `app-admission.lock` across a complete serial
animation job, including the intervals between items. Each item still has its
own preparation, sole render POST, observation and output recovery. Its journal binds
attempt, fingerprint, provider receipt and exact process identities. Observation
is bounded to one hour; uncertainty retains the journal, not a stolen/expired
lease or automatic second POST. Original receipt recovery remains possible.

After a reboot, proven-dead pre-POST or finished leases can recover automatically
after canonical identity, port and persisted-work checks. Submitted/monitoring
or otherwise uncertain work remains bound to its original attempt. An expired
PID alone never authorizes signalling a replacement. Canonical startup clears
its own proven-dead state under its existing locks.

The worker now shares a `job_admission()` context across its serial items and
drains once after the job. Standalone item recovery retains its original behavior.
The context rejects nested items, other configuration objects and reuse after
closure. Uncertain items retain their original journal; remaining credits are not
refunded or another render submitted merely because a response was lost. A known
pre-submission failure refunds only unfinished items through the existing worker.

This removes per-item runtime restarts in the implementation, but **live warm-model
batch admission remains unqualified**. Resource checks still use the conservative
cold-start thresholds. Cached memory after the first item may hold a later item;
the canonical owner must supply or approve warm-state admission or safe unloading.
Do not reduce thresholds based only on fixture success. Public animation remains
off pending owner cooperation and a real lifecycle/batch test.

Batch handoff caveat: `Runtime.ready()` currently applies the same 48 GiB RAM
and 20,000 MiB GPU-free cold-start gates before each POST. An idle model cached
by this app may legitimately occupy those resources, so merely moving the lease
around a whole pack would cause later items to fail admission. The canonical
owner must define a verified warm-state gate or a supported exact-owner unload
between serial items, without repeatedly restarting the whole runtime. Do not
lower thresholds arbitrarily or treat any allocated GPU memory as app-owned.
Parent has taken ownership of both lifecycle modules and their tests for this
batch extension; this worker will make no further module/test changes.

## Gates And Cleanup

- GPU 0 and auxiliary GPU 0 only; at least 48 GiB available RAM, swap at most
  75%, and at least 20,000 MiB GPU0 free. Unknown NVML/identity is a hold.
- Inherited GPU/profile/loader overrides are stripped. An optional approved
  driver manifest checks loaded release, six file hashes and existing links.
  A repaired native driver stack supersedes that fallback after reboot. No
  system driver, loader settings, symlinks or global environment are changed.
- Canonical resource check and start scripts only; generated instance IDs are
  journaled before startup. Pre-existing runtimes are never adopted. Resources,
  identity, engine/jobs/series queues, shared prompt and deep model readiness are
  rechecked immediately before the sole POST. No automatic render retries.
- Cleanup verifies captured identities and idle state, holds Studio's canonical
  lifecycle lock, signals only its expected PID/instance through the canonical
  pidfd helper, then uses ComfyUI's expected-owner stop flags. No force/KILL.
  Partial, changed or unverifiable cleanup preserves evidence and shared work.

The current canonical `stop_webapp.sh` lacks expected-owner and job checks;
the helper uses its existing identity API instead. This exact cleanup sequence
is fixture-tested, not yet exercised against a newly launched live runtime.

## API Handoff

`server.local_video.lifecycle_status(cfg)` (also `local_video_lifecycle.status`)
is read-only: no lock-file creation, startup, render or state mutation.
All results contain `state`, `code`, `message`, `can_submit`. Only `available`
(stopped but installed and admissible) and `ready` return `can_submit: true`.
Offline setup/disabled policy, busy owners, pending leases, resource failures,
starting/draining and unverifiable state return false. Public messages contain
no private paths, process IDs or receipts.

Parent is integrating status into `server/studio.py` animation quotes and
`server/app.py` fresh generation preflight **before credit reservation**.
Existing attempt lookup comes first so closing availability does not prevent
recovery. No public bootstrap host probes are required. A quote/status is not a
resource reservation: the worker retains the exclusive admission and final
resource check. Resource changes between preflight and execution still require
the existing failure/refund handling. This worker did not edit either API file.

## Evidence And Remaining Qualification

Focused fixture suite: 93 passed; full checkout suite: 340 passed in 27.75s.
JUnit receipts are under
`.runtime/local-video-lifecycle-20261012/`. Tests cover policy revocation and
boot durability, pre-POST reboot recovery versus uncertain receipts, flock
exclusion, busy queues/saved work, resource boundaries, driver fallback, no
adoption, captured-ID cleanup, redirect rejection and one POST after a lost reply.
Fixtures never start a GPU runtime or contact a real provider.

Read-only observation at approximately 02:00 HKT, 2026-10-12: canonical
ports 8188/8190 and runtime identities were absent; saved work was idle. Default
NVML reported userspace 595.99 versus loaded 595.84. The previously qualified,
hash-verified process-local compatibility bundle reported GPU0 at 24,036 MiB
free and 0% utilization. The unmodified canonical resource gate held startup
because available RAM was about 46 GiB; swap was below 75%. GPU1 peers remained
untouched. This is historical observation, not an ongoing capacity guarantee.

A review-only message was queued to the discovered canonical runtime owner;
the private OneTimeSync lifecycle request records the exact thread/message.
No response or cooperating-owner installation approval is claimed. Remaining:
parent installation policy/owner agreement, warm-batch admission,
and one explicitly authorized live lifecycle qualification when the
resource lane is free. These are activation tasks, not recurring daily renewal.

Parent API integration validates draft/approval/tier/credit constraints before a
read-only availability probe, then revalidates under the credit-reservation
transaction. Existing attempts are resolved first, even if new generation has
been disabled. Fixtures include availability changing after a quote, unchanged
credit balances on holds, and prior-attempt replay without a new probe.
