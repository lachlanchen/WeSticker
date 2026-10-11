# Native Protected Create

Owner correction, started 2026-10-11; interim internal delivery completed 2026-10-12.
This supersedes the anonymous-chat entry policy, not the preserved historical
build receipts. No formal review, purchases or sales activation are authorized.

## Current Source

- Public Stickers is the initial view. Four tabs: Stickers, Create, Library,
  Account. Characters and the saved local photo draft remain inside Library.
- Signed-out Create, Library and Account open one app-level authentication
  sheet/dialog outside the tabs. There are no separate tab-level login forms.
  Dismissal returns to browsing; completion restores the intended destination.
  The Library gate retains the offline saved-photo draft action.
- Provider buttons are derived from bootstrap `providers`: Google, Apple,
  GitHub and LazyingArt are supported, but only advertised methods are shown.
  Native link requests always include the selected provider. The returned direct
  URL, explicit browser device approval and PKCE completion contract are retained.
  Empty discovery shows retry; a successful `user: null` bootstrap clears the
  stale native bearer and private workspace. A 503 is not treated as sign-out.
- Existing system-browser authentication and independent one-use native PKCE
  completion are preserved. Authenticated Create retains consent, cloud drafts,
  reference approval, quotes and render safeguards.
- Retired anonymous transports and their fixtures are removed from SwiftUI and
  Compose. No native call targets the retired anonymous endpoint.
- The explicit SwiftUI scroll/composer VStack and Compose keyboard insets remain.
  There is no native Stripe checkout link. Native sales remain disabled.

## Qualification

Shared-route source checks: 28 passed across protected entry, native catalog,
native purchase contracts, fixture discovery and stopped-simulator cleanup.
Receipt: `.runtime/native-shared-auth-20261012/source-contracts.xml`.
Kotlin recovery42 and the cached-SDK Compose Account typecheck passed. Swift root,
cloud and release-test parser checks passed. These checks are not runtime UI or
live OAuth receipts. The final candidates are Android12, iOS13 and macOS10;
delivery and new visual QA are pending. Additional qualified providers are a
server-discovery change and do not require another binary.

Android11 and iOS12 were signed/exported once before the final browser-cancel
routing fix. Android11 passed exact-APK release smoke, with GIF counts 5/1/5,
and its AAB is uploaded to a Play draft only, not internally released. iOS12
is not uploaded: five of six XCTest cases passed, including root navigation,
intended Create/Library/Account restoration and the four-provider fixture. Two
assertions in the expiry case failed because the test omitted the explicit
Library refresh; the harness is corrected for the next run. Its visible composer
and four-provider fixture captures were reviewed, but the suite is not a pass.
These two candidates are preserved and do not represent the final cancellation
behavior: cancelling the system browser now clears the root gate and returns
to the public catalog. The final iOS fixture also exercises four selected-provider
link requests and cancellation against inert loopback pages, never real issuers.

Android11's first QA run reached
the shared live login/local-draft checks, then failed an experimental loopback HTTP
provider fixture because the release APK correctly blocks cleartext HTTP. Failed
evidence is preserved in `android-1.0-11/qa-http-fixture-blocked/`; it is not a
four-provider screenshot or a passed release run. No app security policy was
relaxed and no binary rebuilt. The release smoke is rerun on the same APK without
that unsupported fixture; iOS provides the separate four-provider fixture scope.
The rerun passed after a separate startup-only /sdcard readiness failure; both
failed attempts are retained. UI dumps now use fresh task-unique temporary paths.

The interim delivery below had 21 passing checks across protected entry, native catalog,
native purchase contracts and the layout fixture. These are not provider receipts.
Retained recovery suites also passed: Kotlin 42 checks and Swift 37 checks,
without store/network access. The cached-SDK Compose Account typecheck passed.

Release UI tests distinguish live public bootstrap/navigation from a loopback-only
authenticated layout fixture. That fixture has no credentials or model/store
operations; composer typing remains unsent. It tests visible/hittable input,
keyboard clearance, tab return, expired-session refresh and unavailable provider
presentation. It is not evidence of a new live OAuth round trip.

The previously qualified disposable live native identity was deleted. No new
identity or owner-account authentication is performed by this release worker.
Central provider qualification remains with its owner.

## Interim Candidates

These accepted binaries predate the shared-route correction. Their screenshots
remain interim evidence, not proof of the current source's unified authentication.

| Platform | Candidate | Current State |
| --- | --- | --- |
| Android | 1.0 (10) | Exact-APK QA passed; available to Play internal testers, not reviewed |
| iOS | 1.0 (11) | Five XCTest cases and visual review passed; VALID and IN_BETA_TESTING in WeSticker Internal |
| macOS | 1.0 (9) | Universal archive/export and signatures passed; VALID and IN_BETA_TESTING in WeSticker Internal; GUI limitation below |

Android10's exact signed APK passed public initial Home, protected Create,
Account-to-login, nested Characters, local-draft restart, preview and native
sharing checks. GIF unique frame counts were 5 playing, 1 paused, 5 resumed.
The owned API34 software-rendered emulator was stopped after QA. Play readback
shows build10 available to internal testers, released 2026-10-12 00:06 HKT,
not reviewed. Receipt: `android-1.0-10/play-receipt.json` and `.png`.

iOS11's five source-matched simulator XCTest cases passed with zero failures.
Input was tapped and typed into, with hittability, nonzero frame, window bounds,
keyboard clearance and tab-return assertions. The fixture recorded only bootstrap,
workspace and local fixture-control GETs; no unexpected requests. The simulator
was shut down and the temporary test target source removed. Screenshots were
visually reviewed before upload, not accepted merely because controls existed.
Apple's readback confirms iOS11 in the existing internal group with one tester;
no formal or external-beta submission. Receipt: `ios-1.0-11/testflight.json`.
macOS9 also passed Apple validation/upload and is VALID, IN_BETA_TESTING in the
same internal group with one tester. Receipt: `macos-1.0-9/testflight.json`.
Its app executable contains arm64 and x86_64; archive and installer signatures
were verified. Existing signing identities were reused, with no security reset.

Android10 APK SHA-256:
`8ebd5872f560daa5dd44c4e56d1bd6ad66305e725cf817480155576971dacd23`.
Android10 AAB SHA-256:
`2d1a6b8501042ce5442144682b073b6162bb34c45983fe4508af1a87e40a28f1`.
iOS11 IPA SHA-256:
`2af5da306791b30bd4b4806d0d078d5a4dced9606ac2821a293a4d6e99e1eb17`.
macOS9 universal PKG SHA-256:
`12e2f5cce6e9bff78a695b5b6692497c45b7bafb7ab7cf648320ece8b1c8300a`.

Manifests, logs, screenshots and provider receipts are retained privately under
`.runtime/releases/<platform>-1.0-<build>/`. Prior guest-chat captures
are historical and must not be presented as current protected-entry evidence.

Reviewed interim captures, relative to `.runtime/releases/`:

- Android public catalog: `android-1.0-10/qa/01-catalog.png`.
- Android protected Create: `android-1.0-10/qa/creator.png`.
- Android Library: `android-1.0-10/qa/library-characters.png`.
- iOS public initial catalog: `ios-1.0-11/qa-images/5933C407-6B5F-4AF9-8074-7CFA5509CAE8.png`.
- iOS protected Create, live provider availability: `ios-1.0-11/qa-images/1CDDE82D-6E6C-44A2-8028-0DA2724AE618.png`.
- iOS authenticated fixture chat: `ios-1.0-11/qa-images/B5E2779E-CF33-4117-82E6-346ECA6D6659.png`.
- iOS fixture keyboard: `ios-1.0-11/qa-images/B66D4D36-CB63-4CD6-AF97-0EE97F7ED1AD.png`.
- iOS fixture tab return: `ios-1.0-11/qa-images/6B0D73D8-714B-4C87-952F-32B17619F72D.png`.

Do not label fixture chat as a fresh live authentication or model response.

macOS GUI qualification retains the previously disclosed SSH capture/accessibility
limitation. No repeated GUI probe or product redesign is planned to work around
that test-host limitation; compile, signature and source checks are separate.
There is no new macOS GUI-pass claim and no old guest-chat screenshot presented
as a current Mac capture. iOS authenticated layout evidence is a fixture, while
Android's current exact-APK smoke covers signed-out navigation and local use.

No commits are made by this worker. Parent owns the cumulative commit, public web,
backend, README/translations and general auth coordination.

All four binaries were copied into the existing owner's local Nutstore folder
`Share/WeSticker/2026-10-12-protected-create/`; copied hashes match the release
artifacts. Local folder verification does not independently establish cloud sync.
Android5588, the owned iOS simulator and the loopback fixture are stopped. Existing
app and installer keychains are locked again. The central owner's shared store
browser/VM and other projects were preserved.

Focused verification command:

```sh
.venv/bin/python -m pytest -q tests/test_native_login_gate.py tests/test_native_ui_fixture.py tests/test_native_purchase_clients.py tests/test_native_catalog.py
```

Native UI runners: `scripts/android_smoke.py --creator --account` against the
exact Android10 APK, and `scripts/apple_release_qa.py ios --build 11` against the
source-matched Apple candidate. Their SDK/root/artifact paths and complete logs
are retained in private release evidence. The final source file hashes and
21-test JUnit receipt are under `.runtime/native-protected-create-20261011/`.

Exact cumulative worker file scope (20 paths, including removals):

```text
android/app/src/main/java/art/lazying/westicker/CloudStudio.kt
android/app/src/main/java/art/lazying/westicker/CreatorStudio.kt
android/app/src/main/java/art/lazying/westicker/BillingAccountScreen.kt
android/app/src/main/java/art/lazying/westicker/GuestChat.kt (deleted)
apple/Sources/CloudStudio.swift
apple/Sources/CreatorStudio.swift
apple/Sources/NativeBilling.swift
apple/Sources/GuestChat.swift (deleted)
apple/UITests/CatalogTests.swift
scripts/android_smoke.py
scripts/apple_release_qa.py
scripts/native_account_ui_qa.swift
scripts/native_ui_fixture.py
tests/native_clients/GuestChatTest.kt (deleted)
tests/native_clients/GuestChatTest.swift (deleted)
tests/native_clients/check-kotlin.sh
tests/test_native_guest_chat.py (deleted)
tests/test_native_login_gate.py
tests/test_native_ui_fixture.py
docs/native-protected-create-20261011.md
```
