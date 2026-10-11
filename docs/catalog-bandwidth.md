# Public catalog bandwidth and operations

Current creator PWA: <https://westicker.lazying.art>. It has its own API, account
and billing boundary. The earlier catalog-only preview remains documented at
<https://aya.lazying.art/westicker/>; the AYA shop stays at that host's root.
The following October 10 deployment measurements describe the catalog-only
preview, not authenticated creator requests. Both retain lightweight grid previews
and original-quality download assets.

## Applied changes

| Surface | Change |
| --- | --- |
| Web grid | Small animated WebP derivatives, visible top-row priority, at most three transfers; cancel on unmount/pause, release stalled slots after 45 seconds |
| Original GIFs | Original quality and bytes retained for download, native share and full-size preview |
| Apple GIFs | Three HTTP transfers using an actor, shared in-flight requests, bounded memory/disk caches and request timeouts |
| Offline install | Shell plus selected posters, not every language poster; cache up to 160 additional viewed posters |
| Service worker | `/westicker/` scope; no API/auth caching; version includes source worker, scope and precache selection |
| Text assets | Caddy gzip/zstd negotiation; originals are not transcoded or overwritten |
| Hashed assets | One-year immutable cache; catalog/HTML/worker revalidate |
| Public artwork | One-day cache and conditional requests rather than repeated five-minute refetches |
| Avoidable requests | Cheap 404 for common secret/WordPress scans, 405 for writes to static paths |
| Hotlinking | Reject cross-site embedded GIF images; direct downloads, native clients, same-site embeds and loopback development previews remain allowed |

The measured catalog response was 13,419 bytes transferred versus 108,674
uncompressed (about 88% smaller). The initial offline set was 62 of 497 files,
about 1.11 MB versus 5.85 MB (about 81% less). These are transfer/cache metrics,
not a promise that every request is 81% faster. Original GIF payloads are unchanged.

The 468 grid-preview variants total 57,352,320 bytes, compared with 308,821,192
bytes for their original GIFs (81.4% less). This is an aggregate asset-size
comparison, not an initial page-load measurement. The new preview manifest is
generated locally; originals remain the save/share source.

`scripts/animated_previews.py APPROVED_PUBLIC_ROOT` produces ignored,
content-addressed 160-square, 10-fps WebP previews with quality 70. The build
merges their optional manifest into the deployed catalog only. The source
catalog and original GIF links remain unchanged; a build without derivatives
falls back to originals. These are lower-bandwidth grid previews, not a claim
of lossless conversion. Do not use them as the user's downloaded GIFs.

Hotlink checks rely on browser fetch metadata, which a non-browser client can
omit. They reduce casual bandwidth theft; they are not authentication or DDoS
protection. No evidence established a host-wide attack. No blanket IP/country
blocks, billing changes or firewall changes were applied.

## Deployment and rollback

Build with `WESTICKER_BASE=/westicker/ VITE_PUBLIC_CATALOG_ONLY=true npm run build`.
Archive only files under `dist/`; record SHA-256. The root-side
`scripts/deploy_catalog_edge.py` requires the archive hash and current Caddyfile
hash. Read the live file and its owner before using the tool on another host.

The tool checks the marked AYA block and preserves every other host. It stages
an immutable release, records the previous symlink/config, validates as the
Caddy service user, reloads without replacing the service, probes local TLS and
checks that the firewall is unchanged. A failed probe restores the previous
config and release. Repeated staging is accepted only for identical bytes.

For manual rollback, use the exact private deployment receipt: validate and
restore its saved Caddyfile, atomically retarget `current` to `previous.json`'s
release, reload the existing service and repeat probes. Never guess a previous
release or overwrite a config changed by another project after deployment.

Important implementation findings:

- Caddy directive sorting can put an isolated guard after a static handler.
  Guards and handlers therefore live in one explicit `route` block.
- Probe the existing TLS high port with local resolution during deployment.
  The edge host's own public-domain egress was not a reliable health route.
- HTTP/2 can multiplex many requests on one connection. Connection limits alone
  did not bound GIF transfers; the explicit queue did.
- Do not publish the full creator prototype under the shop's origin. The public
  build removes its auth/API/checkout controls and makes no backend requests.

## Checks

```bash
node --test tests/preview-queue.test.mjs
.venv/bin/pytest -q tests/test_native_catalog.py
node scripts/public_catalog_test.mjs
```

The live browser test covers 390/1360 widths, preview, offline shell, worker
scope and absence of API/auth requests. Also probe shop and PWA 200, direct and
same-site GIF 200, external image hotlink 403, static POST 405 and scanner 404.
Inspect genuine screenshots; a successful HTTP response is not layout evidence.

For full local creator UI regression, set `WESTICKER_QA_ART_ROOT` to the approved
shop public directory. This serves the same GIF bytes through a browser-test
route and avoids repeatedly downloading large files from the edge. Label that
run as fixture-backed; it does not replace the separate live PWA/edge tests.

References: [Caddy encode](https://caddyserver.com/docs/caddyfile/directives/encode),
[Caddy route](https://caddyserver.com/docs/caddyfile/directives/route).
