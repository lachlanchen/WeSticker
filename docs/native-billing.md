# Native subscriptions

Status: recovery adapters are implemented; **native consumer sales remain off**.
Actual app-owned catalog/authorization/notification setup is in progress. See the
[dated qualification record](native-billing-qualification-20261012.md) for real
provider results and remaining gates. Unit fixtures are not store transactions.

## Delivery and recovery

`server/native_billing.py` validates fresh provider state for the exact WeSticker
app, configured product/base plan, environment and immutable account binding.
Apple uses `appAccountToken`; Google uses the app-scoped `obfuscatedAccountId`.
Clients and notifications supply lookup hints, never entitlement facts.

`server/native_reconcile.py` encrypts minimal lookup material and queues verified
notification wakeups. Each recovery attempt takes the same nonblocking,
process-shared per-account lock as client Restore, then reads the provider again.
The single-host SQLite deployment also has one batch lock. There is no background
thread on module import, Flask creation or HTTP requests.

Delivery atomically persists the lookup, verified subscription, replacement
lineage and paid-order grant before Google acknowledgement. An acknowledgement
failure leaves recovery due; a later run retries without refilling spent credits.
Apple clients finish only after successful server delivery. Monthly credits reset
once per verified paid transaction, not per restore, notification or grace check.
Refund/revocation, hold and expiry remove the matching access, not saved work.
Cancellation remains active through the freshly verified paid-through date.

Google's fresh `linkedPurchaseToken` establishes predecessor/successor ownership.
Pending replacements do not retire paid predecessors. Active replacements retain
hashed ownership tombstones, including unknown predecessors; a delayed restore or
notification for an old token cannot restore the superseded tier. Cross-account,
conflicting and self-linked replacements fail closed. Unsupported deferred or
multi-line Google plans remain rejected by the verifier; this is not qualification
of every Google replacement mode.

Prepared/pending attempts and unresolved active/grace/hold/pending subscriptions
block a second purchase even after local access expires. Only fresh terminal
provider state establishes that a previously owned subscription has ended.
Closing new sales never disables Restore, Manage, notifications or reconciliation.

## Private configuration

The app identity is `art.lazying.westicker`. Keep both `purchase_enabled` flags
false until independently qualified. Product IDs, app records and test audiences
must belong to WeSticker. Google uses a dedicated app-scoped service account;
an authorized Apple team IAP key still requires exact WeSticker Server API proof.
Never borrow a sibling purchase token or treat an ASC upload key as IAP proof.

| Scope | Fields |
| --- | --- |
| `native_billing` | `key_file`: private lookup-encryption key; optional `reconcile_interval`: seconds, default 900, clamped to 60-3600 |
| `.apple` | `bundle_id`, numeric `app_id`, signing `key_file`, `key_id`, `issuer_id`, trusted DER `root_files`, `products` map to tier IDs, `accept_sandbox`, `sandbox_user_ids`, `purchase_enabled`, optional `purchase_user_ids`, `notifications_enabled` |
| `.google` | `package`, service-account `key_file`, `base_plan` (monthly), `products`, `accept_sandbox`, `sandbox_user_ids`, `purchase_enabled`, optional `purchase_user_ids`, `notifications_enabled`, `notifications` below |

Catalog product IDs remain visible when purchases are disabled. The response
includes Google's `base_plan` and a `purchase_disabled_reason` such as
`sales_closed`, `account_not_enabled`, or `recovery_unavailable`. Clients continue
using the existing per-provider `purchase_enabled` boolean.

When `purchase_user_ids` is present, only those exact immutable app accounts may
prepare a purchase, even if `purchase_enabled` is true. Empty or malformed lists
fail closed before intents or web-checkout side effects. Absence preserves the
explicit global sales flag's behavior; do not remove the list to run a pilot.
Restore and notification recovery do not consult this purchase allowlist.
Sandbox delivery independently requires `accept_sandbox` and membership in
`sandbox_user_ids`; it cannot grant ordinary accounts production credits. Keep
both lists empty in initial staging. Do not remove a sandbox delivery audience
while its test lineage still needs lifecycle reconciliation.

`native_billing.key_file` is distinct from both provider signing key files. The
operator provisions a URL-safe base64-encoded 32-byte random key in a regular,
non-symlink file owned by the service user, mode 0600 or stricter. Nothing generates,
prints, borrows or replaces this key automatically. New delivery fails closed
before provider work when it is absent, malformed or insecurely readable. Catalog
purchase capability is false and prepare is unavailable without a usable key;
configured products remain visible.

HKDF separates the encryption key by app and schema version; Fernet authenticates
the ciphertext. The encrypted envelope binds the app, owner, source, provider and
environment. Store references/order IDs are hashed in new database indexes, and
the raw Google token is never written outside ciphertext. Errors and batch output
contain only static error categories and aggregate counts. Do not enable HTTP
wire-debug logging or proxy request-body/Authorization logging for these routes.

Back up the key separately from the database with app-specific access controls.
Key loss or replacement is not a rotation procedure: it prevents decryption, does
not extend access and requires controlled recovery. No automatic re-encryption or
key-ring rotation is implemented. Account deletion removes active lookup rows and
associated inbox/lineage/bindings; operational backup retention remains the
operator's responsibility, not a claim of physical erasure of SQLite/WAL backups.

Legacy Apple references are encrypted and their source IDs hashed on startup when
the key is usable. Until then, pre-existing rows are left intact, not discarded.
Legacy grant IDs are hashed without losing duplicate-delivery protection. Old
Google rows never retained raw tokens: an authenticated Restore or authenticated
notification must supply them. Batch `missing_lookups` reports uncovered legacy
subscriptions; a zero-work batch is not proof that they are reconciled.

Google authenticated push requires all four exact, app-owned values:

```json
{
  "notifications": {
    "audience": "https://<westicker-api>/api/billing/native/notifications/google",
    "service_account_email": "<dedicated-push-account>",
    "service_account_subject": "<immutable-numeric-service-account-id>",
    "subscription": "projects/<project>/subscriptions/<subscription>"
  }
}
```

## Notification contract

Only these POST routes bypass browser session/Origin/CSRF checks:

- `/api/billing/native/notifications/apple`
- `/api/billing/native/notifications/google`

Both default to HTTP 503 until their `notifications_enabled` flag is set. Body
limit is 65536 bytes. Apple verifies the outer V2 JWS and nested transaction with
the official SDK, pinned operator-provided Apple roots and online certificate
checks. Production app ID, bundle and environment must match; optional Sandbox
fallback performs an independent complete verification. TEST is transport only.
Transaction-free summary/other-product notifications are not entitlement support.

Google uses the official Google-auth verifier for OIDC signature, timestamps,
audience and issuer, then requires the exact verified email, immutable subject,
Pub/Sub subscription and RTDN package. Invalid/missing identity is 401; malformed
or wrong-app events are 400; unavailable authentication/configuration is 503.
Subscription voids only trigger fresh lookup: an event's refund flag cannot revoke
a newer paid period. TEST and unsupported one-time-product events do not grant.

Accepted notifications persist an account-scoped, hashed-ID deduplication inbox
and wake a lookup in one transaction, returning 200 only after persistence. An
unknown reference first requires fresh provider ownership resolution; an unknown
or deleted account is ignored, never created. Client catalog/prepare/delivery
records account binding indexes, and startup backfills existing accounts. No raw
notification payload is retained. Provider/network failures return 503 for retry.
Duplicate events do not refill credits or reset retry scheduling. Wake versions
preserve a new event that arrives while a worker is verifying an older one.

## Parent integration hooks

`register_native_billing(app, cfg)` already initializes recovery tables, migrates
legacy metadata and registers notification routes. Do not register it twice.

1. In `app.py`'s request guard, import `NOTIFICATION_PATHS` and exempt exactly those
   paths from Origin/session/CSRF checks alongside the existing Stripe route.
   Before global JSON parsing, set `request.max_content_length = 65536` on these
   paths. Keep ordinary native prepare/outcome/verify authenticated and CSRF-bound.
2. Inside the existing account-deletion database transaction, before deleting the
   user, call `app.extensions["westicker"]["delete_native_account"](db, user["id"])`.
   This is also exported as `delete_native_account(db, owner)`. All recovery tables
   additionally use `ON DELETE CASCADE`; a late provider response cannot recreate
   the account. Store subscription cancellation is separate from account erasure
   and must remain explicit in the parent's deletion UI.
3. Run `reconcile_due(cfg, limit=25, budget_seconds=60)` from an explicit scheduler,
   or use `app.extensions["westicker"]["reconcile_native"]` with those keyword args.
   No `store.py` schema hook is required beyond normal foreign-key enforcement.

For a parent-managed timer using the same config/state/service user:

```bash
WESTICKER_CONFIG=/private/westicker/config.json \
  .venv/bin/python -m server.native_reconcile --limit 25 --budget-seconds 60
```

Run on an explicit timer and monitor `failed`, `busy`, `missing_lookups` and
worker exit status. Failed attempts back off from 60 seconds to six hours. A fresh
notification wakes the reference sooner. Successful references poll at the
configured interval, including inactive ones, to recover missed changes.
Known expiry is enforced even during provider/key outages. No outage extends the
provider's last verified paid-through date.

Each batch caps records at 100 and checks a monotonic budget (maximum 300 seconds)
between records. This is **not a hard interruption deadline** for an in-flight
verification: SDK API/OCSP/acknowledgement calls have 30-second network timeouts,
and Google OIDC certificate fetches use 10 seconds. Give the timer sufficient
shutdown allowance for the current record. Process-shared locks release on crash;
missed/interrupted work remains due. Multi-host deployments need a distributed
ordering/lease design before reuse.

## Verification and rollout

```bash
.venv/bin/pytest -q tests/test_native_billing.py tests/test_native_reconcile.py tests/test_native_catalog_provisioning.py
```

Recovery tests cover encrypted persistence/restart, key failure/tampering/scope,
renewal/duplicate grants, grace, hold, pending, refund/revocation and expiry;
acknowledgement retries, bounded batches/backoff/locks, wakeup races, deleted
accounts, Google replacement lineage, exact OIDC identities, and signed Apple
notifications. Local crypto fixtures use ephemeral test keys and test certificates,
with real signature validation. Apple's offline certificate checks are confined
to the fixture; runtime Apple verification retains online checks. No test proves
a real Apple sandbox purchase, Google license-test payment or delivered callback.

Before enabling a platform, the parent must provision and verify its actual
WeSticker products/keys/app permissions, authenticated notification transport,
explicit scheduler and backup policy; then exercise no-charge purchase, restart
restore, renewal, paid-through cancellation, expiry/refund, grace/hold, account
switching/deletion and relevant replacements. Store approval, TEST notifications
and synthetic fixtures are not payment lifecycle evidence. An App Store Connect
upload key is not automatically proof of App Store Server API authorization.

Provider references: [Apple signed-data verifier](https://apple.github.io/app-store-server-library-python/_modules/appstoreserverlibrary/signed_data_verifier.html),
[Google authenticated push](https://docs.cloud.google.com/pubsub/docs/authenticate-push-subscriptions),
[Google subscription replacement](https://developer.android.com/google/play/billing/subscriptions).
