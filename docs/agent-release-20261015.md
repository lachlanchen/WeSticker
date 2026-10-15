# Restricted Chat Release - 2026-10-15

The live WeSticker backend now routes normal chat and caption/action proposals
through the pinned AgInTi restricted SDK and DeepSeek Flash. This fulfills the
lightweight API option; it does not start a coding agent for each message.

## Verified

- Full Python backend suite: 464 passed.
- Real restricted-SDK tests inside the hardened agent container: 9 passed.
  Transport is mocked in these security tests; no model spend is claimed here.
- App tests inside the read-only web container: 29 passed, including photo
  sticker export. Explicit CJK and Latin font dependencies are installed.
- Actual Gunicorn image startup, public catalog, signed-out bootstrap, HTML,
  non-root/read-only settings and owned-container cleanup passed with synthetic
  state. No production database or provider keys were mounted for this check.
- The separate media image builds and imports its pinned AgInTi media module
  as a non-root user; FFmpeg is available. This is a dependency/startup check,
  not a new live image or GPU-animation qualification inside Docker.
- TypeScript typecheck, production build and isolated chat/browser QA passed.
  General gallery QA used the existing approved local artwork mirror to avoid
  treating remote artwork latency as an app failure.
- Two real DeepSeek text requests completed through authenticated Flask routes
  and the Docker service: one conversational response, one sticker-table
  proposal. No images, animations, purchases or publication were triggered.
- The conversation response replayed without another provider request. A test
  initially expected `Hello` exactly, while the valid proposal said `Hello!`;
  the assertion was corrected without repeating either paid inference. The
  second replay is covered by isolated tests, not claimed as a live replay.

Security checks cover private histories, request limits, invalid/tool-bearing
responses, single-flight admission, daily cap, durable replay, held interrupted
attempts and reply expiry. Agent idle memory was approximately 20 MiB against a
256 MiB cap, with 0.5 CPU and 64 PIDs configured. This is an idle measurement,
not a load or latency benchmark.

## Deployment Scope

The Docker agent is live behind the existing protected backend at
<https://westicker.lazying.art>. App and media workers remain on their existing
verified host runtime; this release does not claim a completed full-data Docker
migration. Separate web/media Docker images and migration instructions are
provided. The local GPU service remains external.

Activation preserved image/animation, identity and billing configuration. The
previous release and private settings were retained for rollback. Public health
and advertised capabilities were checked after activation. No native binary,
store review, OAuth flow or purchase was resubmitted or newly qualified here.

Codex fallback remains disabled: the upstream maintainer has not qualified a
CLI transport with no native tools or ambient developer context. Customer chat
does not receive developer sessions, home directories, uploads or Docker access.

Private provider receipts, runtime IDs and settings backups are kept outside git
under the operator's ignored runtime/config directories. See the
[runbook](agent-and-docker.md) for reproducible checks and migration boundaries.
