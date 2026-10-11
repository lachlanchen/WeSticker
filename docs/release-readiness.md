# Release Readiness

Current web release: [public Stickers and protected Create](protected-create-release-20261011.md).
The [native internal test builds](native-protected-create-20261011.md) track native
builds separately. The independent HTTPS creator origin has qualified password,
Google and Apple-through-LazyingArt sign-in, with login outside the conversation.
Apple linking and a separate Apple-only login preserve the original app account.
AgInTi image generation passed
one real-provider qualification and is enabled. A local animation canary passed,
but public animation remains disabled until its runtime lifecycle is available.
Social-provider app qualification is recorded [separately](social-auth-qualification-20261011.md).
Web subscriptions are now enabled; actual Stripe sandbox Checkout, Portal and
lifecycle tests passed, followed by genuine live nonfinancial signed webhook
delivery and app-owned production activation. Native IAP remains gated pending its
own store qualification. The tables below preserve
the earlier October 10 release record, not the current build numbers or gates.

**Status: public catalog, protected creator beta and live web subscriptions.
Native IAP, public animation and creator marketplace are not yet fully qualified.**

The [completion ledger](request-completion-ledger.md) is the current cross-feature
audit. Android 14, iOS 14 and macOS 11 are available to internal testers with
compact toolbars. Subscriber language-ZIP downloads now remain in
WeSticker instead of redirecting to the independent AYA checkout. Native signed
notification handling is deployed with purchase flags closed; genuine Apple
Sandbox TEST delivery succeeded. Financial sandbox qualification is separate.
Android 14 additionally fixes the callback self-cancellation found in an actual
system-browser login; native sign-in and persistence after restart are verified.

## Current Entry Flow

Public Stickers opens first. Create requires sign-in on its own screen and then
opens the conversation. Characters are nested in Library; Account is the last
tab. Web, SwiftUI and Compose follow this organization. The old anonymous chat
endpoint is retired. Current provider evidence and internal delivery receipts
are in the linked qualification notes above.

## Historical October 10 Baseline

The owner previously installed iOS build 3. Creation and the assistant were intentionally
not claimed as available in that binary. The table records that baseline only;
it is not the feature list or build number of the new protected-Create release.

| Area | Evidence | Remaining gate |
| --- | --- | --- |
| Public default catalog | 10 packs, 156 animations, three lettering languages, local posters; live at `aya.lazying.art/westicker/` | Installed-device monitoring |
| Local creation | Real browser upload, lock, photo generation, edit/review, ZIP and deletion | Animation quality and model-provider qualification |
| Backend and release contracts | 49 pytest cases, signed payment fixtures, private ownership checks | Load audit, full abuse/privacy lifecycle |
| WeChat agent | Two Node safety tests; save-only source | Docker/live-page customer login and save verification |
| PWA | Public static deployment; 390/1360 browser checks, offline shell, scoped worker, no API/auth requests | Physical installed-PWA review |
| Android | Native Compose 1.0 (3), signed APK/AAB, emulator catalog/preview/share smoke passed; Play internal track active with owner tester | Creator features, auth and real store purchases |
| iOS | Native SwiftUI 1.0 (3), signed upload processed, internal TestFlight group; catalog/preview/share XCTest passed; owner reports installation | Creator features, auth and real store purchases |
| macOS | Native SwiftUI 1.0 (2), universal signed package in internal TestFlight; native window launches | Shared Mac dialogs blocked automated UI/save-panel test; creator features and store purchases |
| OAuth | Four web adapters; disabled LazyingArt onboarding files staged privately | Own live registrations, native callback/session delivery and revoke tests |
| Stripe | App-specific test-mode catalog provisioned; webhook fixtures pass | Actual sandbox checkout matrix, live catalog/webhook, Connect/legal operations |
| Native subscriptions | Account-bound provider verification, serialized restore, durable quota grants, purchase/restore/manage UI; six UI fixture scenarios | Notifications, periodic reconciliation, replacement lineage, real provider lifecycle matrix; sales remain disabled |
| App language | English UI; Chinese/English/Japanese stickers | App interface localization; 11 README languages are documentation only |

## Reproduce tests

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
node scripts/offline-test.mjs
node scripts/native-billing-ui-test.mjs
```

Browser tests require the local demo runtime and Chromium. They create a
temporary account, use public approved artwork, and delete the test account.
Screenshots/results go into ignored `.runtime/browser-qa/`; selected clean
screenshots are copied into `docs/screenshots/`. Layout tests cover 320 through 1440 widths,
not native devices. Nothing invokes a paid image/video provider.

## Native Artifacts

See [protected Create builds](native-protected-create-20261011.md) for current
delivery and qualification. The [native catalog beta](native-catalog-beta.md)
preserves the earlier build history. Android is Compose; iOS/macOS are SwiftUI.
WebView/Capacitor wrappers are not the current test releases. Public App Store
or Play Production review has not been requested for these catalog candidates.

## Historical prototype findings

The following debug/Catalyst findings describe the earlier prototype, preserved
as evidence. They do not describe the current native release path.

### Earlier Android debug artifact

```bash
npm run native:sync
cd android
./gradlew --no-daemon --max-workers=2 -Dorg.gradle.jvmargs=-Xmx2g assembleDebug
```

Requires Android SDK36 and a full JDK21, not a JRE. The APK appears at
`android/app/build/outputs/apk/debug/app-debug.apk` and is intentionally ignored.
The built-in guest catalog can open without a backend; private creation and
payments are not configured in this debug native build.

2026-10-10 native-billing debug APK SHA-256:
`def6731fcae9a52dc2f8476995e5ccce183caf03b6b1e121a6d7d27917412375`.
Rebuilding may change bundled web files, signing timestamps and hash.

### Earlier Apple build findings

The iOS simulator build passed for arm64 and x86_64 with Xcode 26.3, signing
disabled. This is compile evidence, not a device purchase or TestFlight upload.
The subsequent Catalyst build failed before app compilation because both
Capacitor and Cordova 8.5.1 XCFrameworks omit the Mac Catalyst platform. Source
is available in the installed Capacitor package, but switching dependency
managers or adding a dedicated Mac host has not been qualified. Do not relabel
the iOS-on-Mac build as a completed macOS distribution.

Store name: **WeSticker: Aya & Friends**. The shorter name was unavailable on
Apple. Provider IDs, signing routes and build logs stay in the private release
handoff. At that earlier stage app records alone were not submitted releases;
current internal distribution is recorded above.

## Store submission checklist

- Complete the existing WeSticker app records and required agreements, without
  creating duplicate records or editing another app's release/review state.
- Qualify native IAP/restore and server receipt verification; implement and test
  refund/revocation/subscription notification handling.
- Complete native system-browser login and return links; verify Apple login and
  account/token deletion requirements.
- Add a non-blocking deletion request workflow for active jobs and provider-side
  data/token cleanup. Publish legal entity, support, privacy, retention and terms.
- Staff content reporting, copyright requests, creator moderation, refunds and
  appeals; qualify safeguards against impersonation and prohibited content.
- Test animation fidelity, transparent edges, text fit and export file limits.
- Validate iOS/macOS/Android on devices, permissions, share sheets, accessibility,
  offline behavior, crashes, purchases and age declarations.
- Build signed releases and supply real screenshots, store metadata, review
  credentials and accurate privacy/data-safety declarations.

## Suggested store positioning

Name: **WeSticker: Aya & Friends**. Subtitle: **Your character. Everyday expressions.**

Browse Aya and friends, turn your own photos into a personal sticker collection,
and review each expression before sharing. Creator tools preserve character
references and help prepare a consistent collection. Optional WeChat assistance
prepares a draft in your own account; you decide whether to submit it for review.

Do not advertise automatic approval, guaranteed earnings, unavailable AI/IAP or
platform affiliation. Do not submit a store listing until its claims match the
qualified release binary. WeChat names describe an optional integration and do
not imply endorsement.
