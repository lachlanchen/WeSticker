# Native purchase client handoff

Scope: SwiftUI `apple/` and the actual Compose host at `android/app/`.
There was no `native-android/` directory in this checkout. Neither the legacy
Capacitor billing bridge nor a WebView is used. No backend/config changes,
store mutations, purchases, heavy builds, signing, commits or uploads were
performed by the native purchase client worker.

## Parent build prerequisites

- Add `implementation 'com.android.billingclient:billing:8.3.0'` to the actual
  Compose app dependencies before the Android build. This client was typechecked
  against cached Billing 8.3.0; the dependency/build configuration is parent-owned.
- Apple `Sources` is already included recursively by `apple/project.yml`.
  Regenerate the Xcode project through the existing parent build workflow.
- Apple catalog IDs are supplied by `/api/billing/native/catalog`. The expected
  `art.lazying.westicker.{pocket,creator,studio}.monthly` products require no
  hard-coded client catalog change. Prices/descriptions come from StoreKit.
- Keep new sales disabled until the app-specific server/store qualification is
  complete. Current source is not proof of a store transaction or native build.

## Behavior

Account is a fifth native tab, with account plan/credit readback, localized store
plans, Subscribe, Restore, Manage, legal links and sign-out. No Stripe checkout
or payment link is exposed. Sign-in routes to the existing native login surface.

Requests capture an immutable service origin and bearer session. Every result
is checked against the active session and client generation before changing
account state, launching a sheet, finishing a transaction or saving recovery.
StoreKit uses the backend UUID in `appAccountToken`; Play uses the backend
binding in `setObfuscatedAccountId`. Mismatched store owners are rejected.

Recovery attempts are saved before prepare and before sheet presentation.
Keychain stores Apple journals; the existing Android Keystore-backed encrypted
store stores Play journals and fails closed on decryption/persistence failure.
Known receipt lookup references survive restart and logout, scoped to origin
and owner. Neither receipts nor session credentials are logged.

Only a preparation that has never presented a sheet can be deliberately resumed
with the same attempt ID. Pending, presented/unknown and unsent cancellation
outcomes block fresh payment. Confirmed cancellation is cleared only after its
server outcome succeeds. Empty store history is never proof of cancellation.
Unresolved lost callbacks or cancelled pending payments may still need backend
reconciliation; the clients never guess cancellation or mint a replacement ID.

Apple listens to transaction updates and restores current/unfinished transactions
and known references. It calls `finish()` only after successful authenticated
server verification and a final session check. Ordinary Restore does not call
`AppStore.sync`; the separate missing-purchase action does so deliberately.
Modern iOS/macOS purchases are scene/window-bound, with active-window checks for
the older OS fallback. Manage uses the App Store's native sheet on iOS and
official subscription URL on macOS.

Play maintains one root-owned BillingClient, queries purchases on foreground,
handles updates and restores encrypted known tokens. It never acknowledges or
consumes purchases locally; `/api/billing/native/verify` performs durable delivery
then acknowledgement. Only standard monthly auto-renewing base plans are offered;
trials, offer IDs, replacements and upgrades are not inferred. Product IDs are
catalog-driven, not restricted to Apple's bundle-style naming. Manage opens the
official Play subscription page for this package.

Store catalog metadata is loaded independently of receipt verification; a restore
failure keeps plans visible while blocking Subscribe. Account state comes from
server bootstrap readback, never from store success or a client entitlement flag.

## Verification

Lightweight, no-store checks:

```bash
.venv/bin/pytest -q tests/test_native_purchase_clients.py
ANDROID_HOME=/usr/local/echomind-formal-android-toolchain/android-sdk \
  bash tests/native_clients/check-kotlin.sh
git diff --check
```

The Kotlin runner executes 42 recovery checks, then typechecks the billing client
and Compose Account UI against cached Kotlin 2.2.20, Billing 8.3.0 and Compose
libraries. It uses a compile-only CloudStudio boundary, not an app shell. It
does not run Gradle, download SDKs, package an app, contact stores or purchase.

Swift recovery checks are provided for the parent's existing Mac toolchain:

```bash
swiftc apple/Sources/BillingRecovery.swift \
  tests/native_clients/BillingRecoveryTest.swift -o /tmp/westicker-billing-recovery
/tmp/westicker-billing-recovery
```

No Swift compiler is installed in this worker's Linux environment. Full native
builds, existing XCTest, screen captures, compact-width/dynamic-type review,
device account-switch/relaunch checks and actual provider lifecycle qualification
remain parent-owned. No StoreKit fixture or sandbox purchase was created.

The combined initial client/backend test run had 25 passes and one failure in
`tests/test_native_billing.py::test_google_acknowledgement_retry_does_not_double_grant`:
the second mocked verify returned 503 instead of 200 after the concurrent backend
added a required recovery cipher. That backend fixture was left untouched.

## Provider references

- [StoreKit finishing contract](https://developer.apple.com/documentation/storekit/transaction/finish())
- [Scene-bound purchase](https://developer.apple.com/documentation/storekit/product/purchase(confirmin:options:)-6dj6y)
- [Play Billing integration](https://developer.android.com/google/play/billing/integrate)
- [Billing 8 API migration](https://developer.android.com/google/play/billing/migrate-gpblv8)
