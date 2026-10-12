# Canonical WeSticker Entry

The sole public WeSticker entry is <https://westicker.lazying.art/>. AYA's
`/westicker` and `/westicker/` catalog deployment is retired. Keep AYA's shop,
media downloads, checkout, receipts and database independent and unchanged.

## Compatibility

- Redirect legacy GET/HEAD navigation with 308 to the canonical root. Old
  query parameters are not forwarded. Existing non-read method guards stay.
- Serve `deploy/legacy-catalog-retirement/sw.js` at the old exact service-worker
  URL as JavaScript with `Cache-Control: no-store`. Do not redirect this script:
  existing installed PWAs need an update before their cached shell disappears.
- The retirement worker removes only the old `westicker-shell-*` caches,
  unregisters only its exact legacy scope, and navigates only legacy windows.
  It does not clear cookies, local storage, IndexedDB or another app's caches.
- Existing offline installations migrate when online and the browser checks for
  a service-worker update. An offline device cannot receive an immediate update.
- Keep prior static releases as rollback artifacts, not a second live entrance.

`scripts/deploy_catalog_edge.py` now fails closed at its CLI entry point so
an old deployment command cannot restore the retired entrance. Its historical
implementation is retained for audit. Use the independent creator deployment.

## Scoped Rollout

Coordinate the shared Caddy owner. Install the small worker in a checksum-named
immutable directory, replace only the old AYA `/westicker` route using
`deploy/legacy-catalog-retirement/Caddyfile.fragment`, validate, then reload.
Back up the prior configuration and compare its hash immediately before apply.
Do not alter other virtual hosts, authentication, payments, firewall or tunnels.

Update AYA's Create my own link to the canonical domain through its existing
verified frontend-only release installer. Test both legacy root spellings,
legacy nested routes, script MIME/no-store, direct canonical health/catalog,
AYA health/catalog/media, and legacy-worker migration. Restore only the exact
owned delta if acceptance fails; never overwrite concurrent owner changes.
