# Stripe Subscription Qualification

Updated 2026-10-12. The owner's request to complete payments now includes activation
of the existing app-owned web subscription contract. Native external-payment links,
creator payouts, and other app catalogs remain outside this rollout.

## Contract And Configuration

Reused the existing WeSticker test catalog: monthly USD Pocket 99 cents,
Creator 999 cents, Studio 2499 cents. No products/prices, coupons, merchant-wide
settings, or other app objects were changed. Test credentials in
`.config/stripe-test.key` match the authorized private `../Stripe/.env` source.
The merchant was checked against `.config/stripe-account.json` through Stripe's
API. Keep these files and provider IDs private.

Required private backend configuration:

- `stripe_key`: backend-only key matching the explicitly selected mode.
- `stripe_account`: exact authorized merchant account.
- `stripe_mode`: `test` or `live`; use separate databases for separate modes.
- `stripe_prices`: allowlisted tier-to-price map from the app's existing catalog.
- `stripe_webhook_secret`: exact endpoint/mode signing secret, not another app's.
- `stripe_purchase_enabled`: defaults to **false**. Credentials do not open sales.
- `stripe_portal_configuration`: app-owned active portal configuration with
  `metadata.app=westicker` and subscription updates disabled. The adapter refuses
  the merchant-wide default or unqualified proration/upgrade controls.

The app initializes its additive `stripe_*` tables in `register_billing`; no
`store.py` or `app.py` migration edit is required. The database becomes bound to
one verified merchant/mode. Do not switch an existing database to another mode.

The parent owns the bootstrap capability integration. Its purchase predicate is:

```python
bool(
    cfg.get("stripe_purchase_enabled") is True
    and cfg.get("stripe_key")
    and cfg.get("stripe_webhook_secret")
    and cfg.get("stripe_account")
    and cfg.get("stripe_mode") in {"test", "live"}
    and all(cfg.get("stripe_prices", {}).get(p["id"]) for p in PLANS)
)
```

Catalog and verified access remain independent of this flag. Authenticated,
CSRF-protected `POST /api/billing/restore` reconciles the current user's customer;
it neither buys nor mints arbitrary client-supplied credits. Restore, management,
notifications and periodic reconciliation remain usable when new sales close.
Provider verification additionally checks actual customer, product, price, mode
and merchant ownership, not just the bootstrap predicate.

## Durable Lifecycle

- Verify the raw signed webhook before persisting a minimal immutable event
  envelope. Do not retain raw payment/customer payloads in application logs.
- Store the event before provider network I/O; deduplicate IDs and reject changed
  event bindings. Lease processing, preserve failure classes, and retry pending
  or expired leases. A crash after delivery cannot refill spent credits.
- Serialize Stripe reads/delivery across workers with the project database's
  `stripe.lock`. Keep provider truth and the delivery transaction ordered.
- Bind customer and subscription ownership immutably. A signed notification from
  a different mode/account cannot grant access. A foreign product is not an app
  subscription merely because it shares the merchant.
- Read current invoice, subscription, InvoicePayment/PaymentIntent and Charge
  state. Access ends at the paid invoice line's period, not a new unpaid period
  on the subscription. Failed renewals do not extend access or mint allowances.
- Grant a paid period once. Preserve the old `invoice:` marker during migration.
  Zero-paid/trial invoices, unsupported payment sources, and proration invoices
  cannot mint a monthly paid allowance. Plan changes need separate qualification.
- Cancellation retains paid-through access. Expiry removes this subscription's
  access and monthly quota; stale events cannot overwrite an active native or
  successor subscription.
- Full refunds revoke the affected current period and its remaining quota.
  Authoritative payment reads prevent an old paid event from restoring refunded
  access. Partial refunds preserve the existing period without minting credits.
  Disputed subscription charges hold access; dispute resolution policy is not qualified.
- Reserve Checkout before provider creation, and persist exact request parameters
  and idempotency key. Retry uncertain creation only with that same operation.
  Never recreate an unresolved operation after the key-retention safety window.
  Customer-scoped reconciliation discovers a successful but locally lost result.

The native parent can call
`app.extensions["westicker"]["close_stripe_checkouts"](user)` before reserving a
native intent. It expires confirmed-open app-owned Checkouts and rejects active
subscriptions or unresolved outcomes with 409. It replaces an age-only pending
Checkout guard; an unknown purchase does not become safe merely after 24 hours.
The Stripe slice does not alter native files or enable native web checkout.
Account deletion also closes owned open subscription Checkouts before canceling
owned subscriptions; unknown creation outcomes block deletion for reconciliation.

## Worker And Notifications

Run after the app initializes its database, using the same private configuration
and service user as the backend:

```bash
.venv/bin/python scripts/stripe_reconcile.py \
  --config /absolute/private/runtime-config.json
```

The parent's combined one-shot worker calls
`reconcile_stripe(cfg, limit=25, budget_seconds=45)`. No additional configuration
keys are needed; the existing merchant/mode/key/catalog and same private state
directory are required even when sales are closed. The webhook secret is needed
for incoming delivery, not for this read-only recovery worker.

Schedule every five minutes using the parent's service manager/timer only after
qualification. Each invocation attempts at most 25 total event/customer slots
(clamped to 1-100), alternating lanes with durable keyset cursors. Failed items
rotate too, including after process restart. Customer scans fetch at most five
Checkouts and five subscriptions per slot, persist each object cursor, and resume
across runs. Refund events stay pending until a full error-free customer sweep.
A separate batch lock prevents concurrent rotation races. A deleted provider
cursor resets just its own scan lane.

The time budget is checked before each provider call, not a hard process kill:
one in-flight request can finish after the deadline. Worker SDK retries are off
and the configured request timeout is at most 25 seconds. An invoice with more
than 100 payments fails closed for qualification rather than auto-paging without
a bound. Results retain `events`, `customers`, `errors` and add `checked`,
`deferred`, `busy`, `budget_exhausted`. Deferred pages and budget exhaustion are
normal continuation states; monitor oldest pending events and repeated failures.
The parent owns `python -m server.reconcile` and service/timer installation.

Recovery repairs missed renewals, failed payments, refunds and expiry without
creating purchases or refunds. Nonzero exit or `errors > 0` needs investigation; preserve the
original operation rather than submitting a replacement. An active lock prevents
overlapping delivery. Monitor pending inbox age/attempts and the worker exit code.

Configure a WeSticker-specific endpoint at `/api/billing/webhook` for at least:

```text
checkout.session.completed
checkout.session.async_payment_succeeded
checkout.session.async_payment_failed
checkout.session.expired
customer.subscription.created
customer.subscription.updated
customer.subscription.deleted
invoice.paid
invoice.payment_failed
invoice.payment_action_required
invoice.voided
invoice.marked_uncollectible
charge.refunded
refund.created
refund.updated
refund.failed
charge.dispute.created
charge.dispute.updated
charge.dispute.closed
```

Test actual provider delivery against the deployed endpoint before enabling sales.
Retries receive an error while processing remains incomplete; the durable inbox
also allows repair without waiting for provider redelivery. Never re-sign a local
fixture and describe it as a provider-delivered webhook.

## Evidence

Deterministic fixtures:

```bash
.venv/bin/python -m pytest -q tests/test_stripe_lifecycle.py tests/test_services.py
```

55 passed after the bounded-worker extension. Covers HMAC rejection, merchant/mode/owner
mismatches, durable failures and expired leases, concurrent-worker exclusion,
crash-after-delivery, duplicate/reordered notifications, renewal failure/recovery,
full/partial refunds, expiry, legacy grant deduplication, zero-paid invoices,
native-source isolation, and Checkout uncertainty/native-switch protection.
Includes legacy Checkout closure and app-scoped deletion cleanup.
Worker tests cover total slot limits, persistent customer/event rotation, poison
record fairness, alternating lanes, deadline checks, bounded provider pagination,
multi-pass refund recovery and concurrent batch exclusion.
These are fixtures, not provider purchases.

Real Stripe sandbox command:

```bash
.venv/bin/python scripts/stripe_sandbox_qa.py \
  --key-file .config/stripe-test.key \
  --account-file .config/stripe-account.json \
  --catalog .config/stripe-test-catalog.json \
  --output .runtime/stripe-qa/UNIQUE-RUN
```

The passing run is `.runtime/stripe-qa/20261011-qualification-03/`. It contains
0600 `evidence.json`, nine provider snapshots, the actual test refund, an isolated
app database, source hashes and exact provider identifiers. Eleven cases passed:
merchant/catalog validation; hosted Checkout creation/retry; abandonment/expiry;
initial test-clock payment; idempotent reconciliation; actual monthly renewal;
failed renewal without unpaid access; recovery; cancellation with paid-through
access; full test refund with durable revocation; canceled expiry. Hosted Checkout
was created and retrieved through Stripe, but not completed in a browser.

The test clock used Stripe's no-money Visa/declining instruments. The app's
reconciler was evaluated at the clock's frozen time; public APIs cannot supply
that override. Clock/simulation cleanup and closed Checkout were verified.
No production config, live charge/refund, creator sale, or other app product was
used. Earlier runs `01` and `02` remain private: they stopped on QA-script Refund
mode-field and Decimal-serialization assumptions, respectively, and cleaned up.

After the bounded-worker extension, the full shared backend suite passed
**202 tests in 24.42 seconds**. The final focused Stripe/service rerun passed
**55 tests in 8.37 seconds**. The parent still owns deployment and native
integration. No commit was made here.

### Actual Browser And Portal Qualification

Separate from the eleven API/test-clock cases, the private run
`.runtime/stripe-browser-qa/20261011-browser-01/` used a new synthetic identity,
isolated app database, separately built frontend, dedicated Chrome profile and
test-only app-owned Portal configuration. It contains provider snapshots,
screenshots, one-submit markers, source/evidence hashes and cleanup results.

- The actual web Plans Pocket button opened hosted Stripe **Sandbox** Checkout.
  One deliberate browser submission used Stripe's documented test Visa, not a
  real card. Provider state was `complete`, `paid`, USD 99 cents, `livemode=false`,
  with an active subscription and paid invoice. No money moved.
- The return alone left the app free, with zero grants and zero inbox entries.
  Clicking the actual app **Restore / check status** delivered Pocket and three
  credits. This is verified missed-webhook recovery, not webhook fulfillment.
- The actual app **Manage** button opened `billing.stripe.com` in Test mode with
  the dedicated "WeSticker sandbox billing" configuration, paid invoice and
  subscription. Subscription updates were disabled; no default merchant Portal
  configuration was changed.
- The Portal browser cancellation review showed paid-through November 11, 2026.
  One deliberate confirmation scheduled cancellation. The provider's `cancel_at`
  exactly matched the paid invoice period end, with reason
  `cancellation_requested`. Its `cancel_at_period_end` was false; do not mistake
  that one field for failure or fabricate a true value.
- The new bounded worker queried this real test subscription in 7.65 seconds:
  one checked customer, zero errors, no deferred work, one grant before/after.
  The large-account rotation/deadline assertions remain fixture evidence.
- The shared catalog's hosted heading is "WeSticker Creator" even for Pocket's
  99-cent Price. Amount, currency and ownership matched; this naming discrepancy
  remains for the parent's catalog review. No product or price was edited.

**Public webhook delivery did not pass.** No signed delivery reached the isolated
server; its inbox remained empty. The public exact-path POST probe returned 403,
while production `/api/health` returned 200. A dedicated test endpoint was created
and subsequently deleted; creating it is not proof of delivery. No payload was
locally re-signed and represented as Stripe delivery.

Cleanup verified the actual test subscription `canceled`, no open owned Checkouts,
dedicated webhook deleted, and dedicated Portal configuration inactive. The
isolated server, Chrome, Xvfb, VNC and noVNC processes were stopped. Synthetic
customer/history and private evidence remain; no production state was used.

Private helpers are `.runtime/stripe_browser_sidecar.py` and
`.runtime/stripe_browser_helper.mjs`. The API-only script now explicitly records
browser Checkout and Portal qualification as false to prevent evidence conflation.

### Exact Public Delivery Prerequisite

The parent must approve a temporary, POST-only exact path under
`https://westicker.lazying.art/api/stripe-sandbox/<new-run>/webhook` to a separate
loopback-only sidecar tunnel. The existing production tunnel must stay unchanged.
The relevant shared file is `/etc/westicker-creator/Caddyfile.site`, imported by
`/etc/lazystudio/Caddyfile`; no edits were made to either. Preserve the baseline,
validate/reload with the existing deployment procedure, and restore exact bytes
after qualification. The temporary handler must precede the ordinary `/api/*`
handler and forward the unchanged raw body and `Stripe-Signature` header.

Use a fresh isolated run's private `config.json` for its app-owned endpoint secret,
test credentials and Portal configuration. The completed run's endpoint and Portal
were cleaned up and are not reusable active configuration. Before a new sandbox
purchase, verify invalid-signature rejection at the exact public path, then prove
genuine signed provider receipt, durable inbox completion and one entitlement
grant **before** any Restore or worker call. No shared route edit is authorized
merely by this documented prerequisite.

### October 12 Public Delivery Follow-Up

The isolated HTTPS webhook route is now qualified. This supersedes the earlier
403 result for that test route, not the separate production activation gate.

- One temporary, POST-only exact path on the WeSticker hostname forwarded to a
  separate loopback tunnel and isolated database. Production routing, accounts,
  firewall and static release were preserved.
- Missing signatures returned 400; GET returned 405; production health stayed 200.
- Stripe delivered genuine test-mode `invoice.paid` and
  `customer.subscription.created` events. Raw bodies and signing headers passed
  unchanged. No event was locally re-signed or injected as provider delivery.
- The invoice granted Pocket and three credits exactly once before any Restore
  or manual reconciliation call. The simultaneous subscription notification
  initially returned 503 after durable capture; Stripe retried it successfully.
  Both inbox entries ended `done`, with one grant after all three deliveries.
- The subscription was created through Stripe's API with its no-money test Visa.
  This is public delivery evidence, not a new browser Checkout or real payment.
- The owned test subscription was canceled, endpoint deleted and temporary Portal
  configuration disabled. The exact site bytes were restored; root ingress and
  firewall were unchanged. Local and remote test ports were verified closed.

Private evidence is under `.runtime/stripe-browser-qa/20261012-public-webhook-01/`,
including `public-delivery-result.json`, delivery receipts, route install/restore
hashes and cleanup. The private `stripe_webhook_probe.py` and
`stripe_webhook_edge.py` helpers preserve the exact-run and rollback guards.
No production credential or sales flag changed.

## Current Production State

### October 12 Production Preparation

`scripts/prepare_stripe_runtime.py` now prepares only this app's three monthly
Prices, dedicated Portal and exact webhook endpoint, recording the signing secret
in a private receipt. It refuses an existing endpoint whose secret is unavailable
instead of creating duplicates. Staged configuration keeps new sales closed and
preserves unrelated authentication/native settings. The actual live preparation
completed without creating customers, subscriptions or charges.

The shared Product is named **WeSticker**, not **WeSticker Creator** for every
tier. Checkout now states the selected plan and allowance explicitly. New Checkout
attempts use the qualified card lane; pending attempts retain their original
durable parameters. Prices and existing subscription terms do not change.

`scripts/install_billing_reconciler.py` installs an app-owned bounded five-minute
recovery timer. It does not create purchases and refuses to overwrite a different
existing unit. The actual timer is active and its initial recovery completed with
zero errors. Installation verifies active state, not just the enable command.

Live web sales are now enabled for the existing USD monthly Pocket/Creator/Studio
contract. The ordinary bootstrap reports `web_checkout=true`; native sales are
unchanged. The live merchant reports charges and payouts enabled. Configuration
was merged only for `stripe_*` keys, preserving authentication and native settings.

The exact production webhook was separately tested with a genuine Stripe-signed
**live `product.updated` event**, using only a temporary metadata marker on the
app-owned Product. Its durable inbox reached `done`, with zero grants. Temporary
event subscription/metadata were restored. This proves live signature and routing,
not a live financial purchase. Paid initial/renewal/refund behavior is supported by
the earlier actual **sandbox** evidence; no real card was charged for testing.

Checkout and Portal returns open Account. A successful-return URL triggers server
reconciliation, never grants based on the URL itself. Browser fixtures cover paid,
unpaid, cancelled and Portal returns, with zero new Checkout requests. Previously
reserved operations preserve their original parameters and identity.

Backend snapshot `d720d57b94b16f11`, static release `1988216d324926fb`. Private
activation, rollback and nonfinancial delivery receipts remain under
`.runtime/creator-deploy/` and `.runtime/stripe-live-route/`.

Remaining qualification is separate: native IAP, creator sales, subscription
proration/plan changes and dispute-resolution policy. New web Checkouts currently
use cards only; Portal plan changes remain disabled. Rollback closes
`stripe_purchase_enabled` without removing verification, management, recovery,
customer bindings or existing paid access.

Provider references: [webhooks](https://docs.stripe.com/webhooks),
[idempotency](https://docs.stripe.com/api/idempotent_requests),
[InvoicePayments](https://docs.stripe.com/api/invoice-payment/list),
[test clocks](https://docs.stripe.com/billing/testing/test-clocks/api-advanced-usage),
and [test instruments](https://docs.stripe.com/testing?testing-method=payment-methods).
