# LocalVideoGen On-Demand Lifecycle

## Current Status

Implementation and CPU fixtures only. **Public animation remains off; the new
fenced lifecycle has not passed live GPU qualification.** No runtime startup,
render, policy installation, driver change or peer cleanup was performed by this
implementation task. The native billing worker currently owns the heavyweight
lane with Play-enabled emulator 5592. GPU qualification must wait for an explicit
handoff and fresh resource checks, not merely an apparently idle GPU.

This worker owns `server/local_video_lifecycle.py`, `server/local_video.py`,
`tests/test_local_video_lifecycle.py`, `tests/test_local_video_recovery.py`,
`tests/test_local_video_fence.py`, and this document. Parent owns worker/API
integration, public activation, native documentation and commits. The existing
LocalVideoGen owner is implementing the canonical changes in its own repository;
this worker has not modified that shared service's source or running processes.

## Durable Policy, Bounded Job

Installation approval is durable across time and reboots, not a daily or
boot-scoped operator grant. An app installation must explicitly configure
`local_video_runtime_root`, the canonical `http://127.0.0.1:8190` origin, and this
private owner-controlled file under the canonical root:

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
by the service UID, mode 0600, no symlink. All permission flags must be booleans.
Missing, malformed or non-private policy fails closed.

- New work requires `enabled`, `allow_start` and `allow_stop` all true.
- Closing `enabled` or `allow_start` blocks new work, not observation of an
  already-owned receipt or permitted cleanup.
- `allow_stop: false` explicitly revokes cleanup. Observation still works;
  cleanup records a draining/manual-handoff condition and sends no signal.
- Policy validation for observation does not probe free memory, deep readiness,
  model state or queue idleness. An original job may legitimately be running.

The worker holds a nonblocking `app-admission.lock` over a whole serial worker
job. Each item has its own fingerprint, durable submission intent and provider
receipt, with one render POST. Uncertainty retains these IDs; no expiry, new
lease generation or automatic render retry replaces them. The runtime remains
owned between items and drains once after the job, with no idle daemon.

## Exact Receipt Observation

Managed recovery requires the same saved attempt/fingerprint, provider ID and
complete captured process identities. Before and after every job GET and output
download, `Runtime.observe()` verifies both original services using canonical
identity checks and loopback listeners. A missing, partial or replaced runtime
is never adopted. A downloaded partial file is not promoted after an identity
mismatch. Recovery does not start a replacement runtime or perform a new POST.

`ready(new_submission=False)` is identity-only observation. Normal `ready()`
still applies all admission, resource, idle and deep-model checks. These paths
must not be interchanged to admit warm-model work.

Lost-claim and lost-unload GET recovery also use observation permission at entry.
A closed admission policy can still recover the original binding or persist a
matching unload acknowledgment, but cannot pass subsequent dispatch readiness.
The canonical owner's follow-up identified this additional boundary; both paths
have dedicated regressions and no new mutation authority.

Unmanaged historical receipts retain their prior read-only adapter behavior;
they do not authorize startup or submission. Managed receipts missing their
ownership journal fail closed. A fenced journal is not automatically cleared
across reboot: uncertain ownership requires reconciliation, not a new runtime
silently serving the original receipt.

## Canonical Fence And Unload

The caller's flock alone does not exclude raw Studio/engine writers. The
canonical owner is implementing actual mutation enforcement in Studio and
ComfyUI, with a separate shared/exclusive mutation lock. Canonical HTTP handlers
must never wait on the caller-held job flock.

The client persists a random batch generation and 256-bit token before claim.
Credentials stay in private state and request-local headers, never shared
session defaults, token-bearing argv, public status or tracked evidence:

```text
X-H3-Lease-Owner: westicker
X-H3-Lease-Generation: <canonical UUID>
X-H3-Lease-Token: <64 lowercase hex characters>
X-H3-Studio-Instance: <captured instance UUID>
X-H3-Engine-Instance: <captured instance UUID>
```

The client protocol is:

1. Start only through canonical scripts, capturing generated instance IDs before
   launch. Pre-existing runtimes are not adopted. Persist `claiming`, then send
   one `POST /api/admission/claim`. A lost reply recovers via same-binding
   `GET /api/admission`, never a new generation or automatic second claim POST.
   Claim precedes the post-start dispatch readiness check, allowing confirmed
   ownership to drain safely if first-item readiness subsequently fails. The
   unchanged startup resource checks still run before launching any process.
2. Carry the binding on reference upload and the item's sole render POST.
   Recheck resources, identity, queues, shared settings and held admission
   immediately before submission.
3. Between completed items, persist one maintenance ID before
   `POST /api/maintenance/unload`. Poll only
   `GET /api/maintenance/{id}` after a lost response. A 202 enqueue response,
   empty queue, HTTP 200 or increased free memory is not completion evidence.
4. Require an exact generation/instance/maintenance match and the engine
   worker's `completed` acknowledgment after unload, executor reset, garbage
   collection and allocator cleanup. Queued/running, failed, mismatched and
   unverified outcomes retain the original maintenance request and block the
   next render. The client wait is bounded to 60 seconds.
5. After matching completion, rerun both the client resource check and canonical
   `check_resources.sh`, unchanged. Then recheck identity, queues/settings,
   deep model readiness and held admission before the next item's one POST.
   If resources or new admission fail after confirmed completion, drain the
   exact owned idle runtime without submitting item two. Pending or failed
   maintenance is not treated as this safely completed case.
6. After the job, require `POST /api/admission/drain` to confirm `draining`
   before signalling any runtime. Only captured idle instances are stopped.
   After both exit and ports are free, invoke canonical
   `scripts/runtime_admission.py release` with the five-header JSON map on
   stdin. Validate the same-binding `released` receipt before clearing the
   client journal.

This is explicit unload between items, not an invented lower warm-resource
threshold. Processes remain running through the serial job, but model reload
cost still applies after unloading. Live timing, correctness and resource
behavior remain unqualified until the authorized two-item test.

## Gates And Cleanup

- GPU 0 and auxiliary GPU 0 only; at least 48 GiB available RAM, swap at most
  75%, and at least 20,000 MiB GPU0 free. Unknown NVML/identity or a foreign GPU0
  compute owner holds admission. No arbitrary threshold reduction.
- Strip inherited GPU/profile/loader overrides. An optional approved driver
  manifest checks loaded release, six hashes and existing library links. A
  repaired native stack supersedes that fallback. No global driver, symlink or
  loader changes.
- Verify captured identities, live queues and persisted jobs/series/settings
  before cleanup; hold Studio's canonical lifecycle lock; use its expected
  PID/instance pidfd helper and ComfyUI's expected-owner stop flags. Recheck
  drain permission immediately before each signal. No force/KILL or peer stop.
- Canonical drain must fail closed during uncertain maintenance. Failed or
  partial cleanup keeps the private journal and exact original identities for
  owner recovery; it is not labelled successful cleanup.

## API Integration

`server.local_video.lifecycle_status(cfg)` is the existing read-only preflight
surface. All results include `state`, `code`, `message`, `can_submit`. Only
`available` and `ready` return true; offline, disabled, busy, pending, resource,
starting/draining and unverifiable conditions return false. Public messages do
not expose credentials, private paths, process IDs or receipts.

Parent's quote/generation integration checks availability before reserving
credits and resolves existing attempts before new-work gating. A quote/status
is not a reservation: the job lease and final check remain authoritative. No
public bootstrap host probes were added. This worker did not edit `worker.py`,
`studio.py` or `app.py` in this correction.

## Test Evidence

Current focused fixtures: 135 passed in 6.60 seconds across lifecycle,
exact-instance recovery, canonical client fence, serial batch ownership and API
admission. Receipt: `.runtime/local-video-lifecycle-20261012/focused-fenced.xml`.
Final full checkout suite: 451 passed in 29.31 seconds. Receipt:
`.runtime/local-video-lifecycle-20261012/full-fenced.xml`.
These tests make no real provider calls and start no models or services.

The two-item adapter fixture asserts one start, one claim, one unload between
items, exactly two render POSTs and one final drain/release. Its failure variant
keeps the unchanged cold gate after acknowledgment and proves that item two is
not posted. Other fixtures cover stale identities before/after receipt I/O,
admission closure versus stop revocation, malformed bindings, lost claim/unload
responses, non-completion, failed acknowledgment persistence, release receipt
validation and private stdin credentials.

## Canonical Coordination And Live Hold

Implementation was dispatched through the supported queue to the existing
live canonical owner session, not a duplicate agent. The owner implemented
Studio/engine/series/direct-enqueue/shutdown guards and worker-authored unload
completion. Its initial handoff passed 27 focused/315 webapp tests, followed by
28/316 for permission/observation regressions. Its final actual claiming-fix and
CLI receipt confirms **32 focused and 320 total webapp tests passed**. The owner
also independently ran the actual-source client fixture successfully. Canonical
source remains owned by that session, with no deployment or live runtime change.

The CPU conformance fixture imports both the actual client and canonical module.
Its first run reproduced `parent_ownership_unverified`; the canonical owner then
added narrowly bound support for the durably journaled `claiming` state. The
second run **passes**: one claim, one unload, actual canonical worker-completion
logic with CPU stubs, two simulated submit boundaries, and one drain. No real
HTTP, process startup, GPU cleanup or model generation occurs in this fixture.
Canonical module SHA-256 at that pass:
`19c82cd5978f21e8088c514c182ae29766bf1765dc222b9f5805696e1b9da92f`.

Evidence under `.runtime/local-video-lifecycle-20261012/`:

- `canonical-contract-fixture.py`: cross-repository CPU fixture.
- `canonical-contract-attempt1.log`: preserved integration failure.
- `canonical-contract-attempt2.log`: corrected integration pass.
- `canonical-contract-final.log`: pass after the client's GET-recovery correction.
- `fenced-source-sha256.txt`: verified five-file client source/test snapshot.
- `focused-fenced.xml` and `full-fenced.xml`: client pytest receipts.

The canonical owner's interim manifest-mismatch note referred to the two latest
GET-recovery edits before retesting. The manifest is now refreshed after the
135/451 passes, and all five checksums verify; that interim mismatch is resolved.

Private source/test coordination and dispatch receipts are in
`OneTimeSync/WeSticker/LOCALVIDEO-IMPLEMENTATION-20261012.md` and
`LOCALVIDEO-CANONICAL-CONTRACT-20261012.md`. They are not live test receipts.

Parent authorizes one bounded two-item public-Aya qualification after source,
contract, fixture and real readiness checks, when the billing worker hands back
the heavyweight lane. The canonical owner's final coordination receipt approves
the single WeSticker managed adapter job as sole startup, submission and cleanup
executor, with the canonical owner retaining repo/policy ownership and read-only
runtime supervision. This avoids
adoption of a separately started runtime. Use one POST/item, fixed recorded
seeds, GPU0/aux0, 512-square five-second `quality_int8_offload` outputs; preserve
all artifacts and failures. No paid services, third attempt, automatic rerender
or broader public activation is authorized. Fresh 48 GiB/resource/identity
checks remain mandatory after the lane handoff.

## Staged Canary, Not Launched

Private runner:
`.runtime/local-video-lifecycle-20261012/stage_two_item_canary.py`.
Its default invocation only prints a plan, without importing the lifecycle,
probing resources, changing configuration, creating attempt state or making
provider calls. Staging/guard tests: **4 passed in 0.02 seconds**; receipt
`staged-canary-tests.xml`. The planned canary output folder does not yet exist.

The fixed job is `public-aya-lifecycle-20261012`; items are `wave-once-01` and
`nod-thanks-02`, with seeds 127970636 and 31307560. It pins the approved original
public Aya and historical normalized-reference hashes, the tested client source,
canonical fence and unchanged resource script. It refuses a second execution of
an existing canary folder. It never calls image generation, disables moderation,
installs policy or enables public animation.

Execution is deliberately gated behind `--execute`, an existing approved
private config, and a fresh private parent/James lane-release receipt. The
receipt is per-canary scheduling evidence, not a recurring installation grant.
The runner also refuses active 5592/5593 listeners and requires stopped/available
read-only lifecycle status before the actual job obtains its lease and rechecks
all live gates. Reference/source changes require reviewed restaging. No release
receipt, configuration or lifecycle policy has been fabricated or installed.

After future execution, preserve both original MP4s/GIFs, exact provider receipts,
requests, probes, contact sheets, maintenance snapshots and verified cleanup.
Rendered/decoded outputs remain marked as awaiting actual visual QA; no fixture
or successful HTTP response counts as identity/motion acceptance. Parent's
separate auth-only candidate `b5c8cdd2055b6752` uses committed source and keeps
these uncommitted lifecycle changes out of the live adapter until qualification.
That deliberate deployment boundary is not a rollback. Source/test hashes and
canonical conformance were rechecked for the final review/commit handoff; no
implementation changes followed the 135/451 passes. James's explicit AVD cleanup
handoff is still required before execution.

Historical one-item canaries and earlier 93/340-test receipts do not qualify this
new fenced batch protocol. Earlier review-only/no-owner-response notes and the
boot-scoped grant draft are superseded by this implementation status.
