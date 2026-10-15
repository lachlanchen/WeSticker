# Chat Agent And Docker

## Current Design

WeSticker owns authentication, account-scoped drafts, revisions, quotes,
generation, billing and uploads. Conversation and caption/action planning use
the **AgInTiFlow restricted application SDK with DeepSeek Flash**. This is a
real, pinned AgInTi integration, not the unrestricted CLI runner and not a
renamed direct LocalLLM call.

Each chat makes at most one text-only model request. The SDK validates a closed
proposal schema; WeSticker validates the resulting rows again. Applying a table
remains explicit. Chat cannot render, charge, publish, execute code, browse,
read files or select a different model. The existing image provider and local
animation pipeline are independent and retain their consent/quote gates.

Codex fallback is **disabled and not qualified**. The upstream maintainer found
that its existing CLI wrapper cannot guarantee an empty native tool set or
absence of ambient configuration. `codexFallback:true` deliberately refuses
startup. No Codex authentication, development session or home directory is
mounted. A future fallback requires a separately qualified transport, not a
prompt saying "read only". DeepSeek is sufficient for this ordinary workflow.

The selected AgInTi source is identified by commit and SHA-256 in
`agent/aginti.lock.json`; its unchanged npm version alone is not sufficient.

## Isolation And Limits

- One non-root, read-only agent container; no host Docker socket, home directory,
  app database, uploaded references or browser profiles.
- The model receives only the current draft's captions/actions and up to six
  authorized conversation exchanges. No asset paths, account IDs or credentials.
- One in-flight request globally, 60-second inference deadline, 3,500 output
  tokens, 64 KiB request/response bounds, 30 chat attempts per user/hour.
- Default global budget: 100 text requests/day; configurable independently of
  paid sticker credits. No retry or automatic fallback.
- Durable request fingerprints prevent repeat inference. A reused ID with
  changed input conflicts. Failed/interrupted requests stay held, including
  after restart; a new user attempt is explicit.
- The agent keeps replies privately for one day for response-loss recovery.
  Expired replies cannot replay; startup and minute-by-minute cleanup clear
  their content while retaining replay tombstones. This is logical deletion,
  not forensic erasure of SQLite/WAL or backups. It stores no raw prompts or
  transcripts. The app retains its existing conversation history.
- 256 MiB agent memory, 0.5 CPU, 64 PIDs; bounded logs and scratch storage.
  Separate app/worker/retention limits appear in Compose.

This contains an API-backed planner, not arbitrary customer code. Docker shares
the host kernel; it is not a VM or a guarantee against kernel vulnerabilities.
Egress is constrained by the fixed HTTPS transport in code, **not a network
firewall**. No user-supplied endpoint or redirect is accepted. Hardened Docker
configuration follows [Docker's security guidance](https://docs.docker.com/engine/security/).

DeepSeek supports JSON-object mode. The SDK performs schema validation locally;
this is not advertised as provider-enforced JSON Schema. See
[DeepSeek JSON output](https://api-docs.deepseek.com/guides/json_mode/).

## Build And Configure

Requires Docker Compose with additional build contexts, Node 22 and Python 3.12.
Private configuration remains outside images and git. The runtime UID is 1000;
protect config/token files with mode 0600 and matching ownership. Existing
Docker volumes from the previous UID-10001 pilot require an explicit ownership
migration while stopped; do not loosen secrets to world-readable.

```bash
python3 scripts/prepare_agent_source.py \
  --aginti-repo ../Agent/AgInTiFlow --output .runtime/aginti-source
node scripts/configure_agent.mjs \
  --deepseek-env /private/provider.env --output .config --daily-requests 100
docker compose -f compose.agent.yaml build
docker compose build web
docker compose -f compose.yaml -f compose.media.yaml build worker
```

The source exporter reads only the pinned tracked commit. It does not copy an
AgInTi working directory, `.env`, browser state or private session history.
Rebuilding source requires a new output directory or inspection of the existing
snapshot; it never deletes a previous snapshot automatically.

In private `.config/production.json`, use normal qualified app settings plus:

```json
{
  "origin": "https://westicker.example",
  "state": "/data",
  "local_accounts": false,
  "chat_provider": "aginti",
  "chat_agent_url": "http://agent:8001",
  "chat_agent_token_file": "/run/secrets/agent-token",
  "chat_agent_qualified": true
}
```

For the media worker, use `aginti_root:/opt/aginti` and `aginti_node:node`.
Transfer only the worker's approved image/moderation credentials to its private
`/data/.env` using the existing provider workflow. Never mount the full Agent
checkout or share the chat key with model-readable prompts. Image generation
and animation stay disabled until their container-side routes are qualified.
Host loopback GPU URLs need an explicit protected route on the destination;
`127.0.0.1` inside a container does not mean the workstation.

```bash
docker compose -f compose.yaml -f compose.agent.yaml -f compose.media.yaml config --quiet
docker compose -f compose.yaml -f compose.agent.yaml -f compose.media.yaml up -d
curl --fail http://127.0.0.1:18644/api/health
curl --fail http://127.0.0.1:18646/health
```

Only loopback ports are published. Route the public HTTPS origin through the
existing authenticated ingress. The current production ingress uses
`server.ingress:application()` and a private relay file; preserve that guard
when replacing its host process with a container. The default standalone image
serves `server.app:create_app()` behind an operator-managed reverse proxy.
It is not a drop-in replacement for the guarded production tunnel.

## Qualification And Rollout

```bash
python3 scripts/verify_docker_runtime.py --output .runtime/docker-web-check.json
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --memory 256m --pids-limit 64 \
  --mount type=bind,src="$PWD/tests",dst=/app/tests,readonly \
  westicker-agent:local node --test tests/chat-agent.test.mjs
python3 scripts/verify_chat_agent.py --live --token-file .config/agent-token \
  --output .runtime/agent-check.json
```

The last command makes exactly two real text requests, using synthetic local
accounts and no media generation. Inspect an existing receipt before another
run. Mocked security checks are separate from live provider qualification.

For a host-app/agent-container rollout, use `prepare_chat_runtime.py` to stage
private settings and `stage_creator_runtime.py` to snapshot the backend. Then
`activate_creator_runtime.py --config-candidate ...` installs both with idle
queue/chat checks and rollback. It preserves the previous config and release.
No native binary rebuild is required: PWA/iOS/macOS/Android already share this
authenticated chat endpoint.

For an agent-only update, close this app's admission while idle, confirm the
agent reports `busy:false`, recreate only its container, check `/health`, then
restore app admission. Preserve the `agent-state` volume. A 90-second stop
grace period exceeds the inference deadline; never force-kill an active request.

Qualification evidence and rollout scope: [2026-10-15 release](agent-release-20261015.md).

## Migration And Recovery

New deployments use portable `/data` state. Preserve app state, agent replay
state and private configuration separately from immutable images. Stop
admission and let generation/chat finish before stopping services or copying
state. Back up SQLite together with any WAL/SHM files and all asset/receipt
directories. Keep paid-outcome records and credentials private.

On another host, restore into new volumes, preserve UID/permissions, configure
provider/identity callbacks and the protected inference route, then verify with
the public origin still disconnected. Inventory absolute paths in old job
receipts before migrating legacy host state; do not blindly string-replace
customer content. Reconcile unfinished paid jobs manually rather than replaying.
Switch ingress only after authenticated chat, asset ownership, photo export,
provider readiness and billing callbacks pass. Keep the old stopped volumes and
image IDs for rollback. Restoring a backup must never grant fresh credits or
replay a completed image, payment or publication.

This release qualifies the agent container and app-container tests, not a live
full-data migration or new purchases. The live web/media services can remain on
their verified host runtime while the isolated chat agent runs in Docker.
