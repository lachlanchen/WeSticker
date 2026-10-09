# Native subscriptions

Status: implemented adapters and fixture-tested UI, not enabled sales or real
store qualification. Android debug and iOS simulator builds compile. Native
system-browser authentication and production API access are separate gates.

## Responsibilities

- `ios/App/App/WeStickerBilling.swift`: StoreKit 2 prices, bound purchase,
  transaction updates, restore, subscription management and explicit finish.
- `android/app/src/main/java/art/lazying/westicker/WeStickerBillingPlugin.java`:
  Play Billing 9.1.0 prices, bound purchase, pending states and restore.
- `src/NativePlans.tsx`: native-only plans, store-localized prices, account-switch
  guards and server verification before finishing delivery. Web keeps Stripe.
- `server/native_billing.py`: fresh provider lookup, exact app/product/environment
  checks, immutable user binding and transactional credit grants.

Apple binds a WeSticker UUID via `appAccountToken`; Google binds the app-scoped
hash via `obfuscatedAccountId`. Client claims, redirects and receipt text alone
never grant access. Google acknowledgement follows durable server delivery;
Apple finish follows a successful server response. Uncertain results keep the
purchase for restore instead of issuing a second purchase.

The API serializes provider lookup and delivery per user using a nonblocking
process-shared lock. A concurrent restore receives 409, without another provider
read. This matches the current single-host SQLite pilot, not a distributed lock.
Monthly credits reset once per verified paid transaction. Restoring that same
transaction neither refills spent credits nor adds rollover credits.

## Configuration

`config.example.json` leaves both product maps empty and purchases disabled.
Only populate them from verified WeSticker provider records. Private options:

| Provider | Fields |
| --- | --- |
| Apple | `bundle_id`, numeric `app_id`, `key_file`, `key_id`, `issuer_id`, DER `root_files`, `products` map to tier IDs, `accept_sandbox`, `purchase_enabled` |
| Google | `package`, service-account `key_file`, `base_plan` (monthly), `products` map to tier IDs, `accept_sandbox`, `purchase_enabled` |

The app identity is `art.lazying.westicker`. Product maps are app-specific; do
not copy another app's subscriptions. Sandbox acceptance is explicit. Closing
new sales does not disable verification, Restore or Manage.

## Tests and evidence

```bash
.venv/bin/pytest -q tests/test_native_billing.py
node scripts/native-billing-ui-test.mjs
npm run native:sync
```

Backend fixtures exercise wrong app/environment/owner/product, grace, expiry,
revocation, cancelled-but-paid-through, hold, renewal quota, concurrent restore,
CSRF, duplicate intents and acknowledgement transport failure after delivery.
UI fixtures cover success, cancellation, pending payment, server unavailability,
closed sales with restore still available, and a late purchase result after
leaving the plans screen. These tests use no payment card
and do not prove an Apple sandbox or Google license-test transaction.

## Before accepting payments

1. Configure the independent API origin and native authentication return/session
   transport. Verify cancellation, account switching, logout and account deletion.
2. Reconcile app-owned subscription products and their visible localized prices.
3. Implement authenticated provider notifications and periodic revalidation,
   including refund/revocation, grace/hold, renewals and Google replacement-token
   lineage. Preserve durable lookup material privately for that process.
4. Exercise purchase, restore after restart, renewal, cancellation, refund,
   provider outage and pending approval with actual sandbox/license-test accounts.
5. Verify cross-account rejection and repeat delivery without a duplicate charge
   or quota grant. Resolve prepared/pending intents from provider evidence.
6. Enable the qualified platform separately. Store listing approval is not a
   substitute for billing evidence; one platform does not gate the other's build.

Current restore can reconcile when the app is open. Background subscription
reconciliation is not yet implemented, so sales must remain disabled.
