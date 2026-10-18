# Monterey and Adaptive Apple Layouts

This candidate targets macOS 12.0 and preserves the existing iOS 16.0 baseline.
Compatibility source is prepared; native build and runtime qualification are
required before distributing it. Current internal builds remain iOS 1.0 (14)
and macOS 1.0 (11) until a new candidate is validated and processed.

## Implementation

`StudioCompatibility.swift` centralizes availability guards. On Monterey,
navigation uses NavigationView, photo import uses the system file picker with
scoped file access, multiline input uses TextEditor, and ZIP export uses the
system save panel. macOS 13 and later retain NavigationStack, PhotosPicker,
multiline TextField and ShareLink. No data format or account migration is needed.

The catalog uses the current scene's size and horizontal size class. AnyLayout
changes the pack list between a column and a row without replacing the sticker
content subtree. Search, selected preview, playback choice and the grid's scroll
state stay in their existing owners. Resizing does not submit work or purchases.
The bottom tabs can grow with larger text instead of clipping to a fixed height.

## Qualification

Local checks: 495 Python tests passed, 18 optional integrations skipped;
TypeScript/Vite passed; isolated browser catalog, photo draft and export checks
passed with approved local artwork. An initial public-edge GIF preview timed
out. The agent's nine isolated container security tests passed without model
calls. The native UI suite adds rotation/preview retention, enlarged text and
local-draft rotation to its existing GIF pixel, sharing and authentication tests.

The Apple signing host has Xcode 26.3, not 27.1. Apple requires Xcode 27.1/iOS
27.1 SDK for the new Duo full-screen experience. Ordinary iPhone rotation,
iPad size changes and browser resizing are useful regressions, not Duo hardware
or simulator qualification. Opening, closing, partial fold and reserved regions
remain untested until that toolchain/runtime is available. See Apple's
[preparation guidance](https://developer.apple.com/videos/play/tech-talks/111461/)
and [adaptive layouts guidance](https://developer.apple.com/videos/play/tech-talks/111463/).

A deployment target is not proof of a successful Monterey run. Record the
signed binary's minimum OS and architectures separately from testing on a real
12.x runtime. New SDK build-host requirements are also separate from deployment
support; see the [Xcode matrix](https://developer.apple.com/xcode/system-requirements).

## Internal Release Boundary

Use the existing native SwiftUI targets, registered bundle and WeSticker Internal
group. The publisher refuses absent, ambiguous, external or wrong-app groups.
Record exact artifact hash, upload acceptance, processing, group membership and
tester availability separately. No public release, price change or new tester
invitation is part of this compatibility candidate. Android and PWA sources are
unchanged; no duplicate Android package is needed.

The existing AppKit pixel helper accepts `--offscreen` for shared-host checks.
It can verify native GIF play/pause/resume without bringing a window forward;
that component check does not establish whole-app or Monterey runtime quality.
