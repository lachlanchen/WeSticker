# Native billing qualification, 12 October 2026

Scope: WeSticker store catalog, native backend and provider qualification only.
No source commit, native build, production review, real-money charge or refund by
this worker. A genuine Google no-charge test purchase is now qualified below.
Parent owns web/Stripe/deployment; the native UI worker owns Apple/Android sources
and cumulative builds. Nothing here authorizes changing another app's review.

## Build and backend handoff

No client change is required by this catalog or qualifier. Existing clients use
dynamic product IDs, Google's `base_plan`, immutable binding, verify and restore.
The parent may proceed with its cumulative Android13/iOS14/mac11 build independently
of these server/provider gates. A packaged build is not purchase qualification.
The later actual Android13 login test below found an independent native callback
cancellation defect. Parent fixed it in Android14; real login persistence and the
first no-charge purchase/restore now pass. No billing API change was needed.

Parent reports backend `d720d57b94b16f11` deployed with the sandbox delivery gate
and catalog diagnostics, native config still off, and a five-minute shared native/
Stripe reconciliation timer whose initial batch had zero errors. This worker's
later `purchase_user_ids` preparation gate needs the next parent backend snapshot.
No timer or live creator/Stripe configuration was changed by this worker.

Parent subsequently deployed `7ccf64903b559f57` with the exact native subtree and
`purchase_user_ids` gate. Both purchase flags were initially false and audiences
empty. Parent subsequently opened only the exact-owner Google pilot described
below; public native sales remain closed and web Checkout independently enabled.
The deployed native module's
SHA256 is `f6bfd3c4751fc2b5254af5bc0b50fae5528f3f71cc06c57c9ceb21b4d72346b7`.

Private `.config/native-billing.json` contains **only** `native_billing`. It has
three product IDs per provider, private lookup encryption, provider key references,
exact notification authentication, both purchase flags false, and both purchase/
sandbox account lists empty. Parent must merge just this subtree into the latest
creator configuration, preserving all `stripe_*` keys, then restart its service.
Notifications can be enabled without sales or sandbox entitlement delivery.

## Actual catalog

App identity: `art.lazying.westicker`; Apple app `6821157133`, subscription group
`22464274`. Prices below are the established PLANS contract, not new pricing.

| Tier | USD/month | Apple product | Google product |
| --- | --- | --- | --- |
| Pocket | 0.99 | `art.lazying.westicker.pocket.monthly` | `westicker_pocket_monthly` |
| Creator | 9.99 | `art.lazying.westicker.creator.monthly` | `westicker_creator_monthly` |
| Studio | 24.99 | `art.lazying.westicker.studio.monthly` | `westicker_studio_monthly` |

Apple API readback confirms all three one-month products and exact US prices.
Availability is USA only, with no automatic territory expansion. All three now
use App Store-only purchasing and disallow multiseat; Family Sharing remains off.
English names/descriptions, group localization and all three review-note drafts
are saved and independently reloaded. Products remain
`MISSING_METADATA` in the API / Prepare for Submission in Console. A genuine
native Account/Plans review screenshot is still needed; no mock was uploaded and
no product was submitted for review. First products accompany an app-version
review packet, not an unrelated application's review.

Google's dedicated Publisher API now independently confirms all three `monthly`
base plans **ACTIVE**, with exact USD0.99/9.99/24.99 prices, only regionUS available,
`P1M` billing, `P7D` grace, resubscribe inactive and next-billing-date proration.
The ordinary Console saved and activated them under the owner's authorization;
the app's backend purchase flags remain false. No territory expansion, new offer,
price migration or internal-release change occurred. Earlier Console save errors
and API PATCH403 intents remain preserved; their provider-side cause is not proven.
`provider-all-google-active.json` supersedes the earlier empty-base-plan readback.
All three English benefit lists and descriptions are saved; Creator and Studio
were independently reloaded after their successful metadata saves.

`scripts/provision_google_subscriptions.py` defaults to read-only, provisions
drafts with `--apply`, and permits exact validated US monthly-plan activation only
with `--apply --activate`. It validates the existing product/price/period/region,
writes a private intent before each mutation, and reconciles by fresh GET before
declaring success. Unresolved mutations are not blindly repeated. The observed
official regions-table version is `2026/01`; `--regions-version` avoids needing
the account-wide regional conversion operation. The helper never purchases,
refunds, changes a test track or enables backend sales.
Its default read-only audit accepts matching already-active plans without
mutation flags; the actual three-plan audit completed successfully.

## Actual authorization and transport

| Check | Observed result | What it does not prove |
| --- | --- | --- |
| Apple Sandbox notification history | HTTP200 | Purchase or production authorization |
| Apple Production notification history | HTTP401 | Production Server API is not qualified |
| Apple real Sandbox TEST | Exact bundle; official online signature verification and native adapter accepted | No purchase or credit grant |
| Apple public TEST delivery | Fresh TEST after `7ccf64903b559f57` reports `SUCCESS`; online signature and exact bundle/environment verified | Transport only, not purchase qualification |
| Google catalog read | HTTP200, three exact US monthly plans ACTIVE | A purchase, license-test sheet or entitlement |
| Google voided-purchase read | Initially401, now HTTP200 with empty history | Any real refund or payment |
| Google deliberately invalid non-purchase token | Initially401, now400 | A real token, acknowledgement or entitlement |
| Google RTDN | Real Console TEST send200 and exact authenticated push subscription reports `ack_200` | No purchase/renewal receipt or credit grant |

Apple Sandbox V2 URL is independently read back from ASC as
`https://westicker.lazying.art/api/billing/native/notifications/apple`;
production URL is untouched. The first TEST returned4040007 despite the saved URL.
After independent URL readback and propagation time, one separate recorded TEST
succeeded and its signature verified online. No unknown payment was retried.
The authorized team IAP key is distinct from the release-upload key, and uses
WeSticker-specific request/verifier identity. Production401 remains unresolved.
The earlier unsuccessful public delivery is preserved separately. The new real
TEST receipt is `release-7ccf64903b559f57/apple-test-status.json`. Read-only live
database counts after this delivery are zero for native subscriptions, lookups,
notifications, grants and intents. TEST does not create entitlement records.

A bounded production401 diagnostic verifies the signing key's local signature,
exact bundle/header, issuer equality with the app's ASC release configuration and
five-minute expiry. The official SDK token and a fresh token with explicit `iat`
both return Sandbox200 and Production401. No key was changed. Production access
remains unqualified; do not assert that app review/release will fix it without a
new successful provider check. Apple Sandbox purchase testing is independent.

Google uses a newly provisioned dedicated WeSticker Publisher identity and private
mode0600 credential, with no Cloud project roles. Normal runtime access is exactly
four app-only permissions: app information, app quality, financial data, orders/
subscriptions. Account permissions and groups are empty. Catalog editing uses
temporary WeSticker-only store-presence permission plus its Console-required policy
dependency, not app admin, release rights or sibling access. A later bounded PATCH
still returned403 with those rights saved; they were removed again. Catalog403
is not proof that runtime purchase-read permission is missing, nor is propagation
or the underlying provider-side cause established by these checks.

RTDN uses the separate WeSticker topic and subscription, a new **keyless** push
identity, exact audience equal to the Google callback URL, immutable subject and
subscription name pinned in staging. Google Play's system publisher was granted
Publisher on this topic only. The existing Cloud Pub/Sub service agent is inherited;
no project-wide token-creator or admin grant was added. Push payload wrapping stays
on, retry is10-600 seconds, acknowledgement deadline60 seconds, retention7 days.
Play receives subscription and voided-purchase notifications only. No other app's
topic, subscription, identity or settings were changed.

After the parent deployment, a deliberately observed Console test returned200 and
the visible `Test notification sent` confirmation. Cloud Monitoring's
`pubsub.googleapis.com/subscription/push_request_count`, filtered to exactly
`westicker-billing-push` and grouped by response code, has positive `ack_200`
delivery evidence. Earlier DNS and503 failures remain separately visible in the
one-hour history. The real TEST is transport-only; aggregate metrics do not map
an individual TEST ID to a callback log. Receipts are
`google-test-release7ccf-observed.json`, `google-public-push-metrics.json` and
`google-public-push-ack200-table.png`.

## Remaining purchase gates

1. Notification transport and the US Google catalog are now qualified as above.
   A zero-work reconciliation batch is still not purchase lifecycle evidence.
   Confirm separate recovery-key backup and monitoring before financial rollout.
2. Google signed-app product lookup/prices now pass. Genuine Apple Account/Plans
   lookup and review screenshot remain required using the existing TestFlight
   lane, coordinated with the current GUI owner; no billing API change is needed.
3. Google's exact-owner pilot and visible no-charge instrument now pass. Apple
   independently needs its native owner proof, exact-owner pilot and visible
   sandbox sheet. Internal-track membership alone never proves a free instrument.
4. Google initial purchase, once-only grant, acknowledgement, restart/explicit
   restore, one renewal, canceled paid-through access and actual expiry now pass.
   Relevant hold/grace/revocation and account-switch cases remain separate.
   Apple initial delivery is still unqualified. Deletion tests
   must use a separately authorized disposable account, never the permanent owner.
   Preserve the exact attempt after an unknown result. No real-money test is allowed.
5. Resolve Apple Production401 and applicable app/product review separately before
   production sales. Do not impose Google's gates on Apple's sandbox lane.

## Actual Android device continuation

After the parent released the native qualification lane, this worker reused the
existing saved `AiMemo_Billing_Play_API34` AVD on `emulator-5592`. Its maintained
handoff records real prior license testing; its current remembered Google account
privately matches WeSticker's already-enrolled license tester. No sibling app
token, account, subscription or data was reused as WeSticker proof. No AVD, SDK,
profile or userdata copy was made, and no account was signed out or reset.

WeSticker's exact internal invitation `4701650698244827462` was accepted normally;
the provider then displayed `You're a tester for art.lazying.westicker`. The Play
download listing still returned `Item not found`. The earlier generic package
testing URL was not the internal-track invitation and is not release evidence.
To continue without changing the track, the existing Android13 APK was sideloaded:
SHA256 `dcdd3be205d660058bdd8ff6745ac931cb2a0d22f81bb683ab4e578b5f27a624`,
APK signature verified. This is a genuine signed native app on the licensed Play
AVD, **not** a claimed Play-installed binary. Google explicitly supports license
tester sideloading; a visible test instrument is still required before purchase.

Actual native Account -> LazyingArt -> Google -> profile-only app consent ->
Connect device reached the existing retained owner. Read-only session comparison
found exactly two new sessions, both bound to the staged immutable owner; billing
lineage, intents, grants and Checkout counts stayed zero. However, the native
return displayed `The coroutine scope left the composition`. Force-stop/relaunch
of only WeSticker then showed Account still signed out. No successful native
bootstrap, store product sheet or purchase is claimed.

Source diagnosis for the native owner: `CreatorStudio.kt`'s callback
`LaunchedEffect(activity?.authResult, activity?.authCancelled)` clears its own key
before awaiting `cloud.finishLogin(uri)`. That can cancel the in-flight exchange
after the server creates a session and before local persistence. Native source
was not edited by this worker. Parent/Noether must fix callback consumption without
self-cancellation and qualify the corrected exact binary; no billing API change
is requested. Do not replay the consumed exchange or inject a session token.
The parent subsequently applied the callback fix, reported17 focused checks
passing, and began preparing Android14. No corrected-binary result is claimed yet.

Private evidence includes `google-avd-internal-enrolled.png`,
`google-native13-auth-consent.png`, `google-native13-return.png`,
`google-native13-account-after-relaunch.png`, `native-login-baseline.json` and
timestamped `native-login-check-*.json`. The web Connect device image is correctly
named `google-native13-web-connect-device.png`, not an Account/Plans capture.
`android13-native-auth-failure.json` records one consumed native link, both new
sessions bound to the retained owner, and the private filtered device log. No
matching API access-log entries existed for the exchange; its HTTP response status
is explicitly unknown. Database processing is not proof the client received it.
The exact AVD was then stopped without wiping/signing out while the parent builds
Android14; no worker emulator, tmux session or port5592/5593 remains resident.
The current Mac mini was not taken over:
read-only inventory found an active SHI process and no WeSticker in Applications.
The shared physical MIX2S was not installed onto or controlled.

## Exact pilot staging contract

Keep `.config/native-billing.json` unchanged as the closed notification baseline.
Parent alone owns the live creator configuration. Separate mode0600 native-only
candidates now exist at `.config/native-billing-apple-pilot.json` and
`.config/native-billing-google-pilot.json`. Each opens **only its named provider**:
`purchase_enabled: true`, `purchase_user_ids: [one verified owner ID]`,
`accept_sandbox: true`, and `sandbox_user_ids: [the same ID]`. All other fields and
the other provider's closed flags/lists are preserved. Parent merged only Google's
four fields after the correlated Android14 identity proof, not either whole file.
The exact identity comes from the permanent private owner handoff, verified by
local ID and original issuer/subject against WeSticker's read-only database, not
by matching email. The retained account has free-plan state and no native billing
lineage, Stripe subscription or Checkout. Its account/draft must not be deleted.

The parent accepted one fresh backend session bound to the immutable staged owner,
the corresponding native Account, and persistence across process restart as the
identity proof for this account-only pilot. No raw native session extraction or
decryption is needed or performed. Parent should merge only
the selected provider's four pilot fields into its latest config, preserving
Stripe and unrelated settings; the notification-only preparation helper correctly
refuses an open pilot. Do not merge both complete pilot candidates in succession.
The existing WeSticker internal owner is already present in a selected shared
Google license-test list; this was privately compared without changing any list.
That store identity alone did not match an app email, as expected for independent
app identity. No email link/merge or replacement account was attempted.
This allowlist controls accounts, not the store payment instrument; inspect the
real sandbox/license-test sheet before purchase. Closing the purchase flag after
testing must retain sandbox delivery membership for outstanding lineage.

An earlier direct Noether screenshot handoff was rejected by the official queue
because that spawned-agent thread was unloaded. Parent later transferred actual
device qualification to this worker; the Android continuation above supersedes
that earlier handoff dependency. Parent's SDK34 review emulator is stopped and is
not evidence of Play licensing. This worker did not install, launch or manipulate
the shared physical Android device. iOS14/mac11 upload receipts exist; genuine
Apple Account/Plans product lookup and review screenshot remain unqualified.

## Android14 genuine Google pilot

The exact signed Android14 APK SHA256
`b4aac557a229b9839e7c4a963eb9db91181572e49d9e679621b819320002ff8f`
was installed with `adb install -r` on the same saved Play-enabled AVD. Package
readback is versionCode14/versionName1.0. This remains a sideloaded binary, not a
claimed Play install; parent separately published internal14. One real system-
browser login created one fresh app session for the retained immutable owner.
Native Account stayed signed in after force-stop/relaunch. Parent accepted that
correlated identity proof and activated only the Google exact-owner pilot on
the existing `7ccf64903b559f57` API. No auth token was extracted or injected.

Initially the native Account had no returned eligible plans. The release client
collapses product-query errors/empty or filtered results into the same unavailable
message; no detailed BillingClient status was logged, so no specific error code
is claimed. Existing official Play Billing Lab was signed in normally with the
already-enrolled tester. It initially had no country override and response
simulation was off. Applying only its temporary United States test-country
setting immediately made all three real products visible at US$0.99, US$9.99 and
US$24.99 per month. Introductory-offer simulation stayed off. No actual payment
country, catalog territory or other application's subscription was changed.
The resulting Publisher purchase also independently reports region US. This
supports a test-region availability cause; the original payment country was not
read and is not inferred from device locale.

Pocket's actual Google sheet displayed `Test card, always approves` and the
explicit no-charge notice before one deliberate Subscribe confirmation. The
five-minute renewal shown is Google's accelerated monthly test schedule, not a
production price/period change. No real payment method was selected.

Independent app-owned Publisher GET after the normal native callback returned:
`testPurchase`, Sandbox, exact immutable owner binding, `westicker_pocket_monthly`,
base plan `monthly`, ACTIVE and ACKNOWLEDGED. Durable server state was one
subscription, one delivered intent, one grant and one real RTDN notification;
native Account showed Pocket with3 credits. Stripe Checkout count stayed zero.
Force-stop/relaunch changed only the WeSticker PID, and native Account restored
Pocket. Explicit Restore fetched fresh provider state again, with the same order
hash and exactly one grant/3 credits. Duplicate Subscribe was disabled for all
plans. No sibling token or fixture was used for these results.

Private evidence includes `google-lab-us-apply-result.png`,
`google-native14-us-products.png`, `google-native14-studio-products.png`,
`google-pocket-no-charge-preflight.png`, `google-pocket-delivered-account.png`,
`google-pocket-account-after-purchase-restart.png`, and timestamped
`google-initial-purchase-*`, `google-after-process-restart-*`,
`google-explicit-restore-*` JSON receipts. The private observer performs SQLite
read-only queries and Google GETs through the app's normal recovery-key adapter;
it does not acknowledge, deliver, mutate entitlements or print purchase tokens.

The first accelerated renewal produced a different successful-order hash and a
five-minute expiry extension. Its real RTDN was received; normal native foreground
revalidation delivered the new period. Exactly two grants now correspond to the
two paid test periods, still3 credits, not an accumulated6. A transient provider
read at the boundary extended expiry before the successful-order hash changed;
that intermediate read was not claimed as a completed renewal.

Native Manage opened the actual Play subscription manager. Only WeSticker Pocket
was canceled through its normal controls. Google then reported CANCELED with the
same renewed paid-through expiry, still ACKNOWLEDGED. A third RTDN was persisted.
Normal native restore retained Pocket/3 credits until that expiry, with no third
grant or new intent. Other applications' subscription entries were not touched.
Private `google-renewal-settlement-*`, `google-renewal-delivered-*`,
`google-cancelled-paid-through-*`, `google-cancelled-restore-*` and
`google-pocket-cancelled-ui.png` preserve this evidence.

At actual paid-through expiry, Google returned EXPIRED and a fourth real RTDN
arrived. Native explicit Restore revalidated the stored lookup and set the owner
back to Free with expiry0; subscription state is expired. The two historical
grants and3 unused credits remain under the existing retention contract; no
refund, deletion, third grant or second purchase was performed. Provider and
server proof is in `google-expiry-provider-*` and `google-expiry-restored-*`;
`google-pocket-expired-account.png` shows the actual native Free state.

The temporary Billing Lab US override was removed through its official control
and the dashboard readback returned to Add/no configuration, response simulation
off. The exact saved AVD was then stopped without wiping: emulator5592 absent,
tmux `westicker-google-play` absent, ports5592/5593 closed. Saved Android14,
account/Keystore state and all sibling data remain. Noether's heavy-job lane and
the parent's SDK/API cutover were explicitly released after this checkpoint.
Parent subsequently closed Google's new-purchase flag/audience; read-only config
confirms purchasefalse/audience0 with sandboxtrue/audience1 retained. Notification
config and encrypted historical lineage remain available for reconciliation.
Do not restore a stale whole creator configuration over current Stripe settings.

This qualifies one real Google no-charge Pocket sequence, not global native
sales or grace/hold/revocation/replacement/account-switch coverage. Apple remains
independent. The pinned existing Mini route and TestFlight are reachable; current
WeSticker iOS14/mac11 receipts are VALID/IN_BETA_TESTING. The SHI GUI owner was
directly queued for a bounded window/input lane; its active game was not stopped
or controlled. No WeSticker installation exists under that Mini's Applications
at the read-only probe. Normal TestFlight install/Account lookup and an app-only
review screenshot are the next actions after lane allocation, not a new-build or
assumed new-owner-login prerequisite. No connected physical iOS device appeared
in the Mini's inventory. A bounded check of the separate established iPad host
found its fleet endpoint refusing connections and its documented LAN fallback
failing strict host-key verification. The worker stopped that fallback without
changing pins, credentials, routes or device state. This is a concrete route/trust
condition, not a claim the iPad is off or requires a new owner login. The validly
pinned Mini remains preferred after its active owner returns or allocates a lane.
The current SHI binding and live player were rechecked without GUI input; an
explicit bounded response was requested, with no automatic takeover at expiry.

## Evidence and tests

Private evidence: `.runtime/native-billing-20261012/`. Relevant receipts include
`provider-recheck.json`, `after-url-readback/apple-test-status.json`, catalog intents,
permission reloads, product screenshots and RTDN subscription/Play reloads.
Raw TEST token and private credentials remain outside tracked documentation.
Some earlier screenshots predate permission-save confirmation; use the explicitly
reloaded receipts, not filenames that merely say "saved".

The focused native backend/recovery/catalog tests use explicit fixtures. They
cover sandbox delivery denial, account-scoped preparation without Stripe side
effects, catalog visibility with closed sales, encrypted recovery, exact provider
binding and idempotency. Activation tests validate intent/readback and refusal of
price mismatches; none is represented as a real store purchase.

Latest focused result: **90 passed**, including two new read-only active-catalog
regressions (86 backend/recovery/provisioning plus4 catalog checks rerun after
the real purchase). Parent's latest reported full result is **448 passed**, including
its thirteen one-provider pilot preparation tests. This supersedes the earlier
86-focused/361-full checkpoint and concurrent348/1 result; this worker
did not alter parent/Noether's video lifecycle or runtime preparation files.

Provider references: [Google app permissions](https://support.google.com/googleplay/android-developer/answer/9844686),
[base-plan activation](https://developers.google.com/android-publisher/api-ref/rest/v3/monetization.subscriptions.basePlans/activate),
[Google RTDN setup](https://developer.android.com/google/play/billing/getting-ready#configure-rtdn),
[license tester and sideloading rules](https://developer.android.com/google/play/billing/test),
[authenticated push](https://docs.cloud.google.com/pubsub/docs/authenticate-push-subscriptions),
[push delivery monitoring](https://docs.cloud.google.com/pubsub/docs/monitoring),
[Apple TEST](https://developer.apple.com/documentation/appstoreserverapi/request-a-test-notification),
[Apple JWT requirements](https://developer.apple.com/documentation/appstoreserverapi/generating-json-web-tokens-for-api-requests),
[first-product review](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-in-app-purchase/).
