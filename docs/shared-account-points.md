# Optional Shared Account and LAC Points

WeSticker keeps local creators, private references, collections, purchases and
generation credits separate from its optional LazyingArt identity connection.
Shared LAC points are whole-integer, nonmonetary recognition: they cannot be
bought, transferred, spent, redeemed or converted to on-chain LAC here.

## Registration and Gates

The existing profile integration uses issuer `https://chat.lazying.art`, client
`westicker`, audience `westicker`, and exact callback
`https://westicker.lazying.art/auth/lazyingart/callback`. This is a custom
authorization-code/PKCE protocol, not OIDC. Profile permission alone does not
authorize points. The registration is retained for explicit operation consent.

The source implementation defaults both `shared_account_linking_enabled` and
`shared_points_read_enabled` to false. The points path additionally needs the
maintained SDK's `PointsClient` and `LinkStore.complete_pending` credential
lifecycle, qualified issuer discovery for this exact app, and a qualified Coin
read endpoint. Missing capabilities remain disabled or unavailable, not zero.

Only `lac.points.balance.read` is requested. The SDK pins contract
`app-lac-fun-points-v1`, audience `lazyingart-fun-points-api`, resource client
`lazyingart-fun-points-resource`, `https://coin.lazying.art`, and
`GET /api/points/v1/balance` with `X-Lac-Points-Token`.
No intent, reversal, award, policy, transfer or financial route is added.

## Identity and Consent

- A central `(issuer, subject)` maps to one local creator through the existing
  identities table. Email and display names are never linking evidence.
- Existing local password accounts may explicitly link after a current-password
  check and fresh central proof. A conflicting mapping fails without merging.
  Direct social-only local accounts lack a qualified dual-proof reauthentication
  path and cannot link through this new action yet.
- Existing shared-login creators can separately consent to a points read.
  Signed browser state, one-use SDK attempts, original creator/session binding,
  five-minute expiry, and the exact callback bind both operations. A changed
  central identity, local account switch or logout rejects the callback.
- Native bearer tokens cannot start this browser-only consent flow. Native
  points consent and presentation remain a separate qualification; existing
  native profile login and its independent S256 completion remain available.
- New sessions record their authentication source. Optional linking does not
  make independently authenticated local sessions depend on issuer uptime.
  Pre-migration sessions retain their previous validation behavior.

## Read and Recovery

The Account panel separates points from Plans & credits. It displays a balance
only after the SDK validates the exact asset, account, freshness and revision.
`awarded_points` is already net; it is neither reduced by reversed points again
nor added to another app's snapshot. The UI expires snapshots after 60 seconds
and clears old values on refresh/error. Server reads retain a revision floor
through disconnection and reconsent. Responses are no-store and rate limited.

New consent credentials are encrypted before post-exchange validation. The app
journals cross-database adoption so interrupted callbacks can be revoked without
retrying an uncertain code exchange. Logout holds points locally before remote
revocation; deletion waits when revocation cannot finish. Profile access remains
separate from points permission. The bounded maintenance command is:

```sh
WESTICKER_CONFIG=/private/westicker.json \
  .venv/bin/python scripts/cleanup_shared_credentials.py
```

Qualify and schedule this app-owned cleanup with the SDK rollout. It reconciles
up to ten interrupted adoptions, followed by bounded SDK cleanup; it does not
authenticate users, read points or produce rewards. Keep the existing SDK DB,
encryption key and app DB in the same private backup policy.

## Migration and Verification

Startup adds three app-owned tables (`shared_account_attempts`,
`shared_points_connections`, `shared_account_returns`) and `auth_kind` columns
to `sessions` and `native_links`. Existing account IDs, assets, packs, credits,
entitlements and billing rows are retained. Back up app and SDK state before
deployment; restore that backup for a full rollback, since older positional SQL
inserts are incompatible with the added columns. Production state was not migrated
during source qualification.

```sh
# Use the exact qualified SDK source path only in this isolated test process.
PYTHONPATH=/path/to/LazyingArtLinkPrivate \
  .venv/bin/python -m pytest -q tests/test_shared_account.py tests/test_shared_identity.py
npm run build
.venv/bin/python scripts/test_studio_isolated.py shared
```

The tests cover separate consent, fresh local/central proof, mapping collisions,
callback replay/cancellation, account switching, revocation, restart cleanup,
stale/foreign/malformed balances, revision rollback, preserved local credits and
entitlements, and unavailable-versus-zero UI at mobile and desktop widths.
Fixture success does not qualify live Coin access or a new native release.
