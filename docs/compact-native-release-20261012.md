# Compact Native Test Release

The compact toolbar source is `f1848be`. This is an internal test release, not a
public store review or a claim that every payment/provider lane is active.

## Android 1.0 (13)

Available to the existing Google Play internal testers:
<https://play.google.com/apps/internaltest/4701650698244827462>.

- The exact signed APK passed catalog, root login, intended-tab navigation,
  local draft reopening, GIF preview and the native share sheet checks.
- Pixel checks found 5 different playing frames, 1 paused frame and 5 resumed
  frames. Leading toolbar titles and same-row actions did not overlap.
- The visible provider at capture time was LazyingArt. This does not claim
  four-provider live login or a native purchase test.
- The owned emulator was stopped after testing. The existing physical device
  and other projects were not changed.
- Play accepted the AAB and reports build 13 available to internal testers.
  Nonblocking warnings concern missing deobfuscation/native debug symbols;
  there were no supported-device losses.

| Artifact | SHA-256 |
| --- | --- |
| APK | `dcdd3be205d660058bdd8ff6745ac931cb2a0d22f81bb683ab4e578b5f27a624` |
| AAB | `8c0edced9aa8721197e4dd281bcb8e6b3656d71490082080d18b366da5d6c594` |

Private evidence is in `.runtime/releases/android-1.0-13/`: signed artifacts,
`qa/result.json`, reviewed screenshots, upload intent and Play receipt. The first
QA invocation pointed at the build-only SDK without an emulator; that harness
failure is preserved separately. Testing then reused the installed full SDK,
without downloading or duplicating an SDK.

## Apple

iOS 1.0 (14) and macOS 1.0 (11) are VALID and IN_BETA_TESTING in the existing
internal group. Corrected iOS 14 passed six simulator XCTest cases, zero
failures, including full leading-title width and the visible chat composer.
macOS 11 passed universal build/signature checks and its AppKit GIF pixel test
(8 playing / 1 paused / 8 resumed); full packaged-window QA remains unqualified.

| Artifact | SHA-256 |
| --- | --- |
| iOS 14 IPA | `b8c0c22867422b191500177cda0a730a37c44f1687b302ec4aab81e422f3c905` |
| macOS 11 PKG | `a5fd4a1f19667ff155c4f65700574e7b9618c97cea927024f2a31d71cfdef229` |

Receipts are in `.runtime/releases/ios-1.0-14/testflight.json` and
`macos-1.0-11/testflight.json`. The same verified artifacts are locally copied
to Nutstore `Share/WeSticker/2026-10-12-compact-workspace/`. Provider delivery,
local copying and cloud synchronization are distinct checks.

See [the implementation and source checks](native-compact-toolbar-20261012.md),
[previous delivery](native-protected-create-20261011.md), and
[the completion ledger](request-completion-ledger.md).
