# Native Protected Create

Current unified-auth and compact-toolbar delivery, 2026-10-12. This supersedes
the anonymous-chat entry policy and interim tab-level login UI, not their
historical receipts.
These build-delivery checks did not include formal review, purchases or sales activation.

## Current Delivery

| Platform | Current Build | Verified Delivery | Receipt under `.runtime/releases/` |
| --- | --- | --- | --- |
| Android | 1.0 (13) | Available to internal testers; not reviewed | `android-1.0-13/play-receipt.json` and `.png` |
| iOS | 1.0 (14) | VALID / IN_BETA_TESTING; WeSticker Internal, one tester | `ios-1.0-14/testflight.json` |
| macOS | 1.0 (11) | VALID / IN_BETA_TESTING; WeSticker Internal, one tester | `macos-1.0-11/testflight.json` |

These are the current compact candidates; all three are internally available.
Prior qualification is explicitly historical below. Provider discovery changes
do not require another binary.

## Current Qualification and Evidence

[Native Compact Toolbar](native-compact-toolbar-20261012.md) records the exact
artifact hashes, reviewed current screenshot paths, preserved first iOS14
failure and Apple GUI limitations. Source checkpoint `f1848be` plus the tested
three-file Apple title/harness correction is the final native input; its hashes
are in `.runtime/native-compact-toolbar-20261012/apple-corrected-source-sha256.txt`.

Current checks: 33 native source contracts passed; Android13 exact-APK QA passed
with GIF 5/1/5; corrected iOS14 passed six simulator XCTest cases with zero
failures in 263.863 seconds. macOS11 passed universal archive/export, signatures
and the bounded native GIF component test (8/1/8). A full macOS layout pass is
not claimed because peer keychain dialogs obstruct the shared GUI session.

Current artifacts are locally copied and hash-verified in
`Share/WeSticker/2026-10-12-compact-workspace/`, not the older unified-auth or
protected-create folders. Cloud synchronization is not independently confirmed.
Current iOS captures are under `ios-1.0-14/qa-images/`; Android captures are under
`android-1.0-13/qa/`. Four-provider and authenticated Apple fixture screenshots
are labelled fixtures, not live issuer qualification.
The owned simulator, fixture and GIF helper are stopped; existing signing
keychains are locked again. Shared browser, VM and peer GUI state are preserved.

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

## Historical Unified-Auth Qualification

The remainder of this section records Android12/iOS13/macOS10, before compact
toolbars. These receipts and screenshots are retained, not current UI evidence.

Historical source checkpoint: `052f2f0de78660ba2b51ef46fe5cfbded4b2d240`.
Native input hashes: `.runtime/native-shared-auth-20261012/source-sha256-052f2f0.txt`.
The older checksum snapshot is retained for held-candidate provenance only.

Shared-route source checks: 28 passed across protected entry, native catalog,
native purchase contracts, fixture discovery and stopped-simulator cleanup.
Receipt: `.runtime/native-shared-auth-20261012/source-contracts.xml`.
Kotlin recovery42 and the cached-SDK Compose Account typecheck passed. Swift root,
cloud and release-test parser checks passed. These checks are not runtime UI or
live OAuth receipts. That round's final candidates were Android12, iOS13 and
macOS10; all three were internally available. Additional qualified providers are a
server-discovery change and do not require another binary.

Android12's exact signed APK passed the shared-root public navigation, dismissal,
saved local draft restart, preview, native sharing and GIF pause/resume checks.
GIF unique frames were 5/1/5. The live LazyingArt-only auth and public catalog
captures were visually reviewed; the owned emulator was stopped. Receipt:
`android-1.0-12/qa/result.json`. Play readback confirms build12 available to
internal testers, released 2026-10-12 01:05 HKT, not reviewed. Receipts:
`android-1.0-12/play-receipt.json` and `.png`. Only missing deobfuscation/debug
symbols were recommended; no release errors or supported-device losses.
The held Android11 draft was discarded while retaining its uploaded bundle in
the provider library and its local upload/QA evidence.

Android12 APK SHA-256:
`75ec7cec58f920050af9dc78604aa888d9a1cf0bc0e0b29b37ddca354483ae02`.
Android12 AAB SHA-256:
`2b8a263faed46fd37e8921e500ced4eac2fd43c178e97f7b6d130dc50a306eee`.
That round's reviewed captures: `android-1.0-12/qa/creator.png` (live root auth),
`qa/01-catalog.png` (public starting view), and `qa/library-to-login.png`.

iOS13 is archived/exported from the final source. All six XCTest cases passed
with zero failures (227.568 seconds): catalog/GIF/share, saved draft persistence,
visible/hittable composer typing and keyboard/tab return, expiry/unavailable
discovery, live shared-route entry and fixture destination/provider cancellation.
Each configured fixture provider sent its selected name and valid S256 challenge;
all four system-auth consent cancellations returned to the hittable public catalog
before browser navigation. This does not prove a real issuer round trip.
The fixture recorded no unexpected requests, real authentication or model/store
actions. The simulator was shut down and its fixture-origin preference cleared.
IPA SHA-256:
`a329dd677de6008bdd29c28eb4783d38ac11cd408eb4fa1786d9ce3285fef541`.
Apple validation/upload succeeded. Readback confirms iOS13 VALID and
IN_BETA_TESTING in the existing WeSticker Internal group with one tester.
Receipt: `ios-1.0-13/testflight.json`; build/delivery ID
`5d390e0c-f993-462e-b6e9-07eb10d254ee`. No external or formal review was submitted.

macOS10's universal arm64/x86_64 archive/export passed. The app's deep/strict
signature and the existing Apple-issued Mac installer signature were verified.
PKG SHA-256:
`fc3075a59847748541b01d345a7904189c24f7c6bfab7c296b4a310a77050705`.
Apple validation/upload succeeded, delivery ID
`88e5edb1-9fc7-42ff-a936-95ee0e93e6fb`. Readback confirms VALID and IN_BETA_TESTING
in WeSticker Internal with one tester; receipt `macos-1.0-10/testflight.json`.
No new Mac GUI-pass claim: the existing
SSH AppKit/SwiftUI capture limitation remains, without another probe or redesign.
Both existing app and installer keychains are locked again.

## Historical Unified-Auth Screenshots

Android12's reviewed root auth, catalog and Library-entry captures are under
`android-1.0-12/qa/` as listed above. Historical iOS13 captures, visually reviewed
under `ios-1.0-13/qa-images/`:

- Live shared root auth: `E5C0E5F5-495D-4345-857D-2FB1224A0BC5.png`.
- Public starting catalog: `5E893B1D-1998-43D4-9C5F-BCEF40DA04F3.png`.
- Authenticated fixture composer: `4B5B95BD-A8E0-4F97-A7D2-067E3FA0EA9F.png`.
- Fixture keyboard, typed but unsent: `E54EC562-74BB-4DE5-BEE3-3CC48F9E5770.png`.
- Four-provider layout, fixture only: `6D399C47-02F5-42E2-9492-489D7CB9CDE9.png`.
- Fixture cancellation to catalog: `9E5069EC-3FE0-46B8-BD5A-A58DBC823374.png`.

Live discovery advertised LazyingArt only at capture. Four-provider and
authenticated layout screenshots are not live OAuth qualification receipts.

## Historical Unified-Auth Sync and Cleanup

The Android12 APK/AAB, iOS13 IPA and macOS10 PKG were copied and hash-verified
in the owner's `Share/WeSticker/2026-10-12-unified-auth/` Nutstore folder, alongside
per-platform evidence. This proves local folder contents, not completed cloud
synchronization. Final provider receipts are included in each release folder.

Android5588, the owned iOS simulator and loopback fixture are stopped. Temporary
iOS QA source was removed and its fixture-origin preference cleared. Existing
app and installer keychains are locked. No owned build, app, emulator, simulator
or fixture server remains running. Shared store browser/VM and other projects
are preserved. Final host check: 56 GiB available RAM; swap70/135 GiB.

That round's source hashes and both 28-test JUnit receipts are under
`.runtime/native-shared-auth-20261012/`; the final repeat passed in 1.77 seconds.
Reviewed capture hashes are in `reviewed-screenshots-sha256.txt` there.

```sh
.venv/bin/python -m pytest -q tests/test_native_login_gate.py tests/test_native_ui_fixture.py tests/test_native_purchase_clients.py tests/test_native_catalog.py
```

That round's UI runners: `scripts/android_smoke.py --creator --account` against the
exact Android12 APK, and `scripts/apple_release_qa.py ios --build 13` against the
source-matched Apple candidate. Complete logs and artifact manifests are retained
under `.runtime/releases/<platform>-1.0-<build>/`.

No real OAuth account, model call or purchase was used for this release QA. The
previous disposable native identity was already deleted. Parent owns social
qualification, web/backend, README/translations and all commits. The close-out
for that round changed only this tracked delivery doc after `052f2f0`; subsequent
compact-toolbar changes and their test evidence are linked above. Runtime
receipts remain private and no worker commit was made.

## Historical Held Candidates

Android11 and iOS12 were signed/exported once before the final browser-cancel
routing fix. Android11 passed exact-APK release smoke, with GIF counts 5/1/5,
and its AAB was uploaded to a Play draft only, not internally released. That
owned draft is now discarded, with the uploaded bundle retained in the library. iOS12
is not uploaded: five of six XCTest cases passed, including root navigation,
intended Create/Library/Account restoration and the four-provider fixture. Two
assertions in the expiry case failed because the test omitted the explicit
Library refresh; the corrected harness subsequently passed against iOS13. Its visible composer
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
relaxed and no binary rebuilt. The release smoke was rerun on the same APK without
that unsupported fixture; iOS provides the separate four-provider fixture scope.
The rerun passed after a separate startup-only /sdcard readiness failure; both
failed attempts are retained. UI dumps now use fresh task-unique temporary paths.

## Historical Interim Delivery

These accepted binaries predate the shared-route correction. Their screenshots
remain interim evidence, not proof of the current source's unified authentication.

| Platform | Historical Build | State Recorded at Interim Delivery |
| --- | --- | --- |
| Android | 1.0 (10) | Exact-APK QA passed; available to Play internal testers, not reviewed |
| iOS | 1.0 (11) | Five XCTest cases and visual review passed; VALID and IN_BETA_TESTING in WeSticker Internal |
| macOS | 1.0 (9) | Universal archive/export and signatures passed; VALID and IN_BETA_TESTING in WeSticker Internal; GUI limitation below |

The interim suite had 21 passing source checks, with Kotlin42/Swift37 recovery
checks and cached Compose Account typecheck. Its 21-test JUnit receipt remains
under `.runtime/native-protected-create-20261011/`; this is not the current suite.

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

Historical macOS9 GUI QA had the disclosed SSH AppKit/SwiftUI capture limitation;
its failed probe is retained, not relabeled as a product failure or GUI pass.
The old `Share/WeSticker/2026-10-12-protected-create/` Nutstore folder contains
only that earlier Android10/iOS11/macOS9 delivery. It is not the current folder.

## Historical Unified-Auth Source Scope

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
