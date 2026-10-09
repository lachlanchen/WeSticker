# Local preview and deployment

## Reproducible local preview

Requires Python 3.12+, Node 22+, a CJK font, and Chromium for browser tests.
FFmpeg is required only by the optional animation adapter.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

Open `http://127.0.0.1:18642`. The demo supports local account creation; it does
not grant subscription credits or enable external providers. Set a temporary
password used nowhere else. Stop this project's three owned processes with:

```bash
python3 scripts/dev.py status
python3 scripts/dev.py stop
```

Local account registration is a loopback demo facility. It has no email
verification/recovery. Use qualified identity providers before public service.
Do not run a second copy against the same state directory.

## Configuration

`WESTICKER_CONFIG` selects a private JSON file. `config.example.json` contains
safe defaults. `.config/`, `.env*`, `data/` and `.runtime/` are ignored. Never
paste secret configuration into a handoff, README, screenshot or issue.

| Setting | Meaning |
| --- | --- |
| `origin` | Exact externally visible origin, HTTPS in production |
| `state` | Private persistent state directory; `/data` in Docker |
| `local_accounts` | Demo only; false in production |
| `font` | Installed CJK font file for captions and packaging |
| `providers` | App-specific provider registrations; see integration handoff |
| `image_api_key`, `image_api_origin`, `image_model` | Image provider; disabled without credentials |
| `moderation_model` | Safety model used before image/animation requests |
| `local_video_url` | Optional protected localhost LocalVideoGen service |
| `stripe_key`, `stripe_webhook_secret`, `stripe_prices` | WeSticker-only billing and tier price IDs |
| `creator_sales_enabled` | Open only after Connect and moderation operations qualify |
| `wechat_worker_enabled` | Open only after isolated draft-upload qualification |
| `default_artifacts` | Optional read-only artifact root containing `artifacts.json` and `downloads/`, for subscriber ZIP delivery |

Artifact records must be from the matching catalog release. Never
point the import at Downloads, a personal photo folder, or all project media.

## Docker pilot

Prepare `.config/production.json` with the production origin, state `/data` and
demo accounts disabled. The image runs as UID/GID 10001; arrange the **private**
config mount permissions so that this UID can read it, without world-readable
secrets. The named volume is initialized by the image. Back up the database and
private assets together before migrations.

```bash
docker compose config --quiet
docker compose build
docker compose up -d
curl --fail http://127.0.0.1:18644/api/health
```

Docker build/runtime has not been qualified in the initial implementation.
TLS ingress must preserve Host/Origin, allow bounded 21 MB image requests, and
route both `/api/` and `/auth/` to the same application. Do not share AYA's
origin, database or cookies. LazyEdge may provide the protected tunnel/HTTPS
edge after an independent domain is chosen; no new public route was installed.
LocalVideoGen on host localhost is not reachable from an ordinary bridge
container. Keep that optional adapter disabled until a protected route is
explicitly designed and tested; do not solve it by exposing a public GPU API.

## Isolated WeChat browser

This is an operator-assisted draft workflow, not a platform approval API.
The user logs into their own browser and opens a new blank album. Production
needs authenticated per-user VNC proxying and session lifecycle controls.

```bash
docker build -t westicker-wechat:local worker
WESTICKER_CONFIG=.config/production.json .venv/bin/python scripts/wechat_container.py start TICKET_ID
WESTICKER_CONFIG=.config/production.json .venv/bin/python scripts/wechat_container.py upload TICKET_ID
WESTICKER_CONFIG=.config/production.json .venv/bin/python scripts/wechat_container.py stop TICKET_ID
```

Use a tunnel to the loopback VNC URL, not a raw public port. The password stays
in the private runtime receipt. The script refuses a second container for the
same customer. It stages one ticket, takes screenshots, clicks Save, then
reloads to verify. Preserve receipts and reconcile uncertain saves before any
retry. Static/animated platform controls require live qualification. Copyright,
pricing and appreciation fields may still require user input on the live page.
The app never submits a WeChat album for review.

## Review and retention

```bash
WESTICKER_CONFIG=.config/production.json .venv/bin/python scripts/moderate.py PACK_ID approve --rights-checked --reason "Reviewed the frozen export and rights"
WESTICKER_CONFIG=.config/production.json .venv/bin/python scripts/retention.py
```

The operator inspects every expression, rights, labels and packaging first.
Report handling, appeals, backups, refund/dispute handling and deletion requests
need named operators before launch. Run retention hourly and verify its receipt.
