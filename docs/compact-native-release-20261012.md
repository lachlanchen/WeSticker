# Compact Native Test Release

The compact toolbar source is `f1848be`. This is an internal test release, not a
public store review or a claim that every payment/provider lane is active.

## Android 1.0 (14) Successor

Build 14 supersedes 13 in the same internal test track. Source `c1913d7` fixes
an actual sign-in defect that the earlier layout checks did not exercise:
clearing the callback inside its keyed Compose effect cancelled the suspended
exchange before credentials were saved. Callback consumption now follows the
exchange, coroutine cancellation is not displayed as a network error, and a
late browser-cancel result cannot replace an already received deep link.

The exact signed APK completed the normal system-browser authorization and
returned to native Account. After force-stop and relaunch, Account remained
signed in. Read-only backend evidence found one new session bound to the retained
owner and no new purchase, grant or Checkout. This is genuine native login and
persistence evidence, not a native purchase test; store product lookup remained
unavailable at this checkpoint and new sales were closed.

Play reports build 14 available to internal testers, with zero supported-device
losses and only the same nonblocking symbol/deobfuscation warnings as build 13.
The current APK and AAB are locally copied to Nutstore under the existing release
folder's `android-14/` subdirectory and their SHA-256 values match:

| Artifact | SHA-256 |
| --- | --- |
| APK | `b4aac557a229b9839e7c4a963eb9db91181572e49d9e679621b819320002ff8f` |
| AAB | `2f3c97638032a395111b632380fb1bc84fe0560963c3bb4243efc6957d487869` |

Private delivery evidence is `.runtime/releases/android-1.0-14/`; actual device
screenshots and read-only identity checks are under
`.runtime/native-billing-20261012/`. No earlier build or account was removed.
The full backend suite passed 448 tests, focused native/provider checks passed
62 tests, the web build passed, and isolated browser login/chat workflows passed.

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
