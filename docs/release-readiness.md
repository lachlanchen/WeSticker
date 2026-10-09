# Release readiness: 2026-10-10

**Status: local working prototype / integration foundation. Not publicly
deployed, not store-submitted, not ready to accept real customer payments.**

| Area | Evidence | Remaining gate |
| --- | --- | --- |
| Public default catalog | 10 packs, 156 animations, three lettering languages, local posters | Licensed production delivery and availability monitoring |
| Local creation | Real browser upload, lock, photo generation, edit/review, ZIP and deletion | Animation quality and model-provider qualification |
| Backend | 27 pytest cases, signed payment fixtures, private ownership checks | Load/concurrency audit, full abuse/privacy lifecycle |
| WeChat agent | Two Node safety tests; save-only source | Docker/live-page customer login and save verification |
| PWA | Vite build; offline browser reload keeps ten packs/posters and excludes API/auth caches | Installed physical-device review |
| Android | Gradle debug APK compiled, package art.lazying.westicker | Physical device, native auth/IAP, release signing, AAB and Play listing |
| iOS | Capacitor source, icons and privacy manifest | Xcode compile, signing, devices, IAP, App Store record/review |
| macOS | Mac Catalyst build settings | Mac compile, desktop UX, entitlement/signing and store review |
| OAuth | Google/Apple/GitHub/LazyingArt web adapters | Own client registrations and live callback/revoke tests |
| Stripe | Subscription/marketplace routes and webhook fixture tests | App-specific products, sandbox matrix, Connect/legal operations |
| App language | English UI; Chinese/English/Japanese stickers | App interface localization; 11 README languages are documentation only |

## Reproduce tests

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
node scripts/offline-test.mjs
```

Browser tests require the local demo runtime and Chromium. They create a
temporary account, use public approved artwork, and delete the test account.
Screenshots/results go into ignored `.runtime/browser-qa/`; selected clean
screenshots are copied into `docs/screenshots/`. They test 320/390/1440 widths,
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

Initial debug APK SHA-256:
`a717d693331af263bcce43f0ebb7398bccac1105ab4873329774b4186bb207d3`.
It is approximately 9.8 MiB. Rebuilding may change signing timestamps and hash.

## Store submission checklist

- Create separate WeSticker app records and required agreements, without editing
  the AYA shop or another app's release/review state.
- Implement and qualify native IAP/restore, server receipt verification and
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

Name: **WeSticker**. Subtitle: **Your character. Everyday expressions.**

Browse Aya and friends, turn your own photos into a personal sticker collection,
and review each expression before sharing. Creator tools preserve character
references and help prepare a consistent collection. Optional WeChat assistance
prepares a draft in your own account; you decide whether to submit it for review.

Do not advertise automatic approval, guaranteed earnings, unavailable AI/IAP or
platform affiliation. Do not submit a store listing until its claims match the
qualified release binary. WeChat names describe an optional integration and do
not imply endorsement.
