# Native Compact Toolbar

## Current State

2026-10-12: native source and source-level checks are ready for the parent's
single cumulative billing/auth/UI candidate. **New app builds, emulators and
uploads are held.** No version was incremented and no commit was made.

The delivered releases remain iOS 1.0 (13), Android 1.0 (12), and macOS 1.0 (10).
Their receipts are in [Native Protected Create](native-protected-create-20261011.md).
Those binaries and screenshots do not contain this compact-toolbar patch.

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

## Executed Checks

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

## Visual QA Still Required

No after screenshots or runtime layout pass are claimed. Retained iOS13 before
images under `.runtime/releases/ios-1.0-13/qa-images/`:

- Create: `4B5B95BD-A8E0-4F97-A7D2-067E3FA0EA9F.png`.
- Catalog: `5E893B1D-1998-43D4-9C5F-BCEF40DA04F3.png`.

The next coordinated candidate must capture all four tabs, root auth and the
empty/keyboard chat states at compact and wide sizes, including enlarged text
and reduced motion. XCTest now asserts one hittable leading title, compact
height, visible window bounds and same-row action separation. It retains
composer typing, keyboard clearance and tab-return checks; Android smoke now
checks catalog/login toolbar geometry. Inspect genuine captures before marking
the layout passed. Repeat GIF pause/resume and local-draft persistence.

No Gradle/xcodebuild, model call, live OAuth, store purchase or upload was run
for this patch. No GUI or server was started; unrelated shared processes remain.

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

No backend, web, configuration, README, translation or audit-ledger changes
were made by this native worker. Parent retains all commit/build coordination.
