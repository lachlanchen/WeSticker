# Native Compact Toolbar

## Current State

2026-10-12: the cumulative compact candidates are Android13, corrected iOS14
and macOS11. Each Apple artifact was uploaded once after qualification. No
formal review, real OAuth, model call or store purchase was performed by this
worker. Parent owns commits and Android distribution.

| Platform | Build | Current Delivery | Private Receipt |
| --- | --- | --- | --- |
| Android | 1.0 (13) | Available to internal testers; not reviewed | `android-1.0-13/play-receipt.json` |
| iOS | 1.0 (14) | VALID / IN_BETA_TESTING; WeSticker Internal, one tester | `ios-1.0-14/testflight.json` |
| macOS | 1.0 (11) | VALID / IN_BETA_TESTING; WeSticker Internal, one tester | `macos-1.0-11/testflight.json` |

Receipt paths are relative to `.runtime/releases/`. Final Apple readbacks
confirm both builds attached to the existing internal group. No external beta
or formal review was submitted. Both accepted uploads occurred exactly once.

Earlier iOS13/Android12/macOS10 receipts remain in
[Native Protected Create](native-protected-create-20261011.md); those binaries
do not contain the compact-toolbar patch.

## Candidate Correction

The first unuploaded iOS14 candidate is preserved under
`.runtime/releases/ios-1.0-14-title-clipped/`, with its failed six-case XCTest
result and original IPA. Visual inspection caught the leading title truncated
to `Cr...` despite available space. `StudioChrome.swift` now supplies the title's
intrinsic horizontal size. XCTest additionally checks the measured full headline
width. The separate welcome-height failure was a harness assumption: SwiftUI
exposes the 44-point icon and headline as one 76-point accessibility group.
Its bound now checks the full compact group, not a text-only 44-point frame.
The composer was visible, hittable and typed in the preserved first capture.

Corrected iOS14 IPA SHA-256:
`b8c0c22867422b191500177cda0a730a37c44f1687b302ec4aab81e422f3c905`.
The original `e8b051f3...` artifact is never to be uploaded. Build14 was not
uploaded before this correction, so the final candidate retains that number.
Native source contracts reran: 33 passed (`corrected-title-contracts.xml`).
The final post-delivery repeat also passed 33 checks in 1.78 seconds
(`final-source-contracts.xml`); all final Apple input hashes still match.
Final Apple input hashes: `apple-corrected-source-sha256.txt` in the evidence
directory below. No Android rebuild is needed for this SwiftUI-only correction.

## Changes

- One reusable, compact leading toolbar title on each tab, in the actions row.
  SwiftUI uses an inline navigation bar; Compose uses the small top app bar.
  Duplicate Account and Android catalog body headings are removed.
- Empty chat uses a 44-point/dp app icon and a small centered welcome in the
  available scroll area. The explicit SwiftUI scroll/composer VStack and
  Compose keyboard insets remain intact.
- One-shot 220 ms welcome entry, 150 ms send-readiness feedback, and 160 ms
  collection/selection feedback. SwiftUI checks Reduce Motion; Compose uses
  the system animator duration scale. No looping decoration or new timers.
- Root authentication, dynamic provider discovery, direct provider selection,
  expiry/cancellation routing, intended-tab restoration, GIF playback and
  local drafts are unchanged. No anonymous transport was added.
- Native billing changes are header layout only: the shared Account toolbar
  and removal of its duplicate heading. No purchase, restore, verification,
  finish/acknowledgement, ownership or catalog contract changes. Backend/store
  work stays with James; web/auth integration stays with the parent.

## Initial Source Checks

Evidence: `.runtime/native-compact-toolbar-20261012/`.

| Check | Actual Result | Evidence |
| --- | --- | --- |
| Focused Python native contracts/fixtures | 33 passed | `source-contracts.xml` |
| Offline Kotlin billing recovery | 42 checks passed | `kotlin-typecheck.log` |
| All Compose sources, cached SDK/compiler | Typecheck passed; no app package | `kotlin-typecheck.log` |
| Offline Swift billing recovery | 37 checks passed | `swift-billing-recovery.log` |
| All SwiftUI sources, iOS simulator SDK | Typecheck passed | `swift-ios-typecheck.log` |
| All SwiftUI sources, macOS SDK | Typecheck passed | `swift-macos-typecheck.log` |
| Catalog and account XCTest sources, iOS/macOS | Typecheck passed; not executed | `swift-ui-tests-typecheck.log`, `swift-macos-ui-tests-typecheck.log` |
| Python syntax, shell syntax, scoped diff whitespace | Passed | `validation.json` |

Swift app checks retain warnings on unchanged PhotosPicker actor-isolation
expressions. Kotlin checks retain existing Send/Logout icon deprecations.
The first direct XCTest typecheck omitted the SDK's Swift XCTest overlay;
`swift-ui-tests-missing-overlay.log` preserves that harness failure. Adding the
existing SDK module search path passed without changing app or test behavior.

```sh
.venv/bin/python -m pytest -q tests/test_native_compact_chrome.py tests/test_native_login_gate.py tests/test_native_purchase_clients.py tests/test_native_ui_fixture.py tests/test_native_catalog.py
ANDROID_HOME=/usr/local/echomind-formal-android-toolchain/android-sdk PATH=/usr/local/echomind-formal-android-toolchain/jdk-21/bin:$PATH bash tests/native_clients/check-kotlin.sh --ui
```

Apple source checks used `swiftc -typecheck -parse-as-library -swift-version 5`
with the existing iOS simulator/macOS SDKs on the authorized Mac. A separate
`~/Projects/WeSticker-build/ui-check-20261012/` snapshot was used; the delivered
release source/artifacts were not replaced. Source hashes and exact check scopes
are in `source-sha256.txt` and `validation.json` beside the logs.

## Visual QA Scope

Corrected iOS14 passed all six source-matched simulator XCTest cases, zero
failures in 263.863 seconds. Evidence: `ios-1.0-14/qa/xctest.log`,
`qa/NativeRelease.xcresult` and `qa/fixture-requests.json`. Coverage includes
catalog/native sharing, GIF pixel pause/resume, saved draft restart, full-width
leading titles, visible/hittable composer typing, keyboard clearance, tab
return, expiry and provider-discovery failure, shared root auth, intended-tab
restoration and system-auth cancellation. All four selected-provider fixture
link requests carried a valid PKCE challenge; no unexpected requests occurred.
This is not a live four-provider round trip.

Reviewed corrected captures under `.runtime/releases/ios-1.0-14/qa-images/`:

| View | Capture | Scope |
| --- | --- | --- |
| Catalog | `DB5BA0A8-452C-47C6-9F27-F26110911CF2.png` | Live public artwork |
| Create | `F4C12FDB-B75A-4F4A-8324-222219839312.png` | Authenticated fixture |
| Restored Create, parent approved | `36CF3D38-88F2-40AD-9CBC-0F6D8A410B03.png` | Authenticated fixture, intended destination |
| Keyboard | `5352EEB7-6A32-4ECE-A222-1F3A3FAFEB52.png` | Fixture, typed but unsent |
| Library / Characters | `B410553C-44BE-45B5-A330-6DC238FD734C.png` | Authenticated fixture |
| Account | `6DF14036-1905-4B95-B24B-3214C65F079D.png` | Fixture, no purchase |
| Root auth | `4B33BA3F-18FB-4339-8739-623CCC215F24.png` | Live LazyingArt-only discovery |
| Four-provider selector | `ECAB71E0-76D9-47D9-B16D-563E0E4C0E5C.png` | UI fixture only |

Capture hashes: `.runtime/native-compact-toolbar-20261012/reviewed-ios-sha256.txt`.
Parent Android13 exact-APK QA passed with GIF unique frames 5/1/5, root gates,
compact toolbar geometry, local draft and sharing. See
`android-1.0-13/qa/result.json`, `qa/creator.png` and `qa/01-catalog.png`.

macOS11's universal arm64/x86_64 archive/export and deep/strict app and installer
signature checks passed. Its bounded native AppKit GIF test passed 8/1/8
playing/paused/resumed frames: `macos-1.0-11/motion-qa/result.json`. This tests the
current native GIF component, not the complete packaged application's layout.
Full Mac Create/Library/Account/keyboard capture remains unqualified: existing
shared desktop keychain dialogs obstruct GUI automation. A private read-only
desktop capture is retained; no peer dialog was dismissed or security setting
changed. Wide-window, enlarged-text and reduced-motion runtime coverage is not
claimed for this release. Do not relabel the earlier failed Mac probe as a pass.

Retained iOS13 **before** images under `.runtime/releases/ios-1.0-13/qa-images/`:

- Create: `4B5B95BD-A8E0-4F97-A7D2-067E3FA0EA9F.png`.
- Catalog: `5E893B1D-1998-43D4-9C5F-BCEF40DA04F3.png`.

## Exact Artifacts

| Artifact | SHA-256 |
| --- | --- |
| Android13 APK | `dcdd3be205d660058bdd8ff6745ac931cb2a0d22f81bb683ab4e578b5f27a624` |
| Android13 AAB | `8c0edced9aa8721197e4dd281bcb8e6b3656d71490082080d18b366da5d6c594` |
| Corrected iOS14 IPA | `b8c0c22867422b191500177cda0a730a37c44f1687b302ec4aab81e422f3c905` |
| macOS11 PKG | `a5fd4a1f19667ff155c4f65700574e7b9618c97cea927024f2a31d71cfdef229` |

iOS upload delivery ID: `6c252eee-bc54-4e91-b589-b8e6a4615548`.
macOS upload delivery ID: `e7ba2c9f-b866-46cb-be10-1371e66c001a`.
These are also the final provider build IDs in the respective TestFlight receipts.
The four artifacts are hash-verified in the owner's local Nutstore folder
`Share/WeSticker/2026-10-12-compact-workspace/`. This proves local copies, not
completed cloud synchronization. Archives and the failed first iOS14 candidate
remain preserved separately; neither is duplicated into the share folder.

## Cleanup

The owned iOS simulator and loopback fixture are stopped; the temporary test
source and fixture-origin preference were removed by the runner. The AppKit GIF
helper exited after capture. No owned native build/upload or app is running.
Both existing app and installer signing keychains are locked again; the existing
search list is restored. Shared Mac VM, Simulator.app, peer dialogs and the
existing store browser are preserved. The host had 47 GiB available RAM and
67/135 GiB swap used at final checks; ports 8188, 8190, 5588 and 18649 were free.

## Exact Owned Files

- `apple/Sources/StudioChrome.swift` (new)
- `apple/Sources/WeStickerApp.swift`
- `apple/Sources/CloudStudio.swift`
- `apple/Sources/CreatorStudio.swift`
- `apple/Sources/NativeBilling.swift` (header only)
- `apple/UITests/CatalogTests.swift`
- `android/app/src/main/java/art/lazying/westicker/StudioChrome.kt` (new)
- `android/app/src/main/java/art/lazying/westicker/MainActivity.kt`
- `android/app/src/main/java/art/lazying/westicker/CloudStudio.kt`
- `android/app/src/main/java/art/lazying/westicker/CreatorStudio.kt`
- `android/app/src/main/java/art/lazying/westicker/BillingAccountScreen.kt` (header only)
- `scripts/android_smoke.py`
- `scripts/native_account_ui_qa.swift`
- `tests/native_clients/check-kotlin.sh`
- `tests/test_native_compact_chrome.py` (new)
- `docs/native-compact-toolbar-20261012.md` (new)

The compact checkpoint is `f1848be`. The only subsequent native source/test
adjustments are `StudioChrome.swift`, `CatalogTests.swift` and
`scripts/native_account_ui_qa.swift`, described above. Final input hashes still
match the tested artifacts. This release also updates
`docs/native-protected-create-20261011.md` to label earlier delivery historical.
No backend, web, configuration, README, translation or audit-ledger changes
were made during this Apple delivery. The earlier bounded lifecycle work has
been handed back; parent owns its batch extension and activation.
