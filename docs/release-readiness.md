# Release readiness: 2026-10-10

**Status: local working prototype / integration foundation. Not publicly
deployed, not store-submitted, not ready to accept real customer payments.**

| Area | Evidence | Remaining gate |
| --- | --- | --- |
| Public default catalog | 10 packs, 156 animations, three lettering languages, local posters | Licensed production delivery and availability monitoring |
| Local creation | Real browser upload, lock, photo generation, edit/review, ZIP and deletion | Animation quality and model-provider qualification |
| Backend | 46 pytest cases, signed payment fixtures, private ownership checks | Load audit, full abuse/privacy lifecycle |
| WeChat agent | Two Node safety tests; save-only source | Docker/live-page customer login and save verification |
| PWA | Vite build; offline browser reload keeps ten packs/posters and excludes API/auth caches | Installed physical-device review |
| Android | Debug APK compiled with Billing Library 9.1.0 bridge; own Play record created | Native auth, real license-test purchases, release signing, AAB/internal upload |
| iOS | Xcode 26.3 simulator build passed with StoreKit 2 bridge; own app/bundle and signing profile created | Native auth, device/sandbox purchases, signed archive and TestFlight upload |
| macOS | Catalyst build attempted; pinned Capacitor/Cordova binaries lack a Catalyst slice | Source-framework or native Mac host decision, qualified desktop build and store review |
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

## Android debug artifact

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

## Apple build findings

The iOS simulator build passed for arm64 and x86_64 with Xcode 26.3, signing
disabled. This is compile evidence, not a device purchase or TestFlight upload.
The subsequent Catalyst build failed before app compilation because both
Capacitor and Cordova 8.5.1 XCFrameworks omit the Mac Catalyst platform. Source
is available in the installed Capacitor package, but switching dependency
managers or adding a dedicated Mac host has not been qualified. Do not relabel
the iOS-on-Mac build as a completed macOS distribution.

Store name: **WeSticker: Aya & Friends**. The shorter name was unavailable on
Apple. Provider IDs, signing routes and build logs stay in the private release
handoff. App records are not submitted releases.

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
