# Native catalog beta

## Build scope

| Platform | Candidate | Implementation | Distribution |
| --- | --- | --- | --- |
| Android | 1.0 (3) | Kotlin / Jetpack Compose | Google Play internal testing, owner tester selected |
| iOS/iPad | 1.0 (3) | SwiftUI and native image/share views | Internal TestFlight; owner reports successful installation |
| macOS | 1.0 (2) | SwiftUI, AppKit image view and native save panel | Internal TestFlight group; provider reports in beta testing |
| Web | Public catalog | React PWA | <https://aya.lazying.art/westicker/> |

Available: guest catalog, collection search, favorites, EN/JA/ZH lettering,
animated GIFs, pause, preview and native save/share. Originals and names are
from the approved public catalog. No private photos are bundled.

Not in these binaries: creation, AI assistant, accounts, purchases, creator
sales or WeChat upload. Existing implementation work for those features is in
the local web prototype; it is not automatically available to native users.
See the [next milestone](native-creator-plan.md).

## Reproducible source

- `android/`: independent Compose Activity, Coil GIF decoding and restricted
  FileProvider cache. No WebView or packaged HTML release UI.
- `apple/project.yml`: XcodeGen targets `WeStickerIOS` and `WeStickerMac`.
  Both use `apple/Sources/WeStickerApp.swift`, not Catalyst or a web host.
- `scripts/sync_native_catalog.py`: copy curated catalog/posters into the two
  native targets. These reproducible copies are ignored by Git.
- `scripts/android_beta.py`: stable protected upload key, signed APK/AAB,
  explicit build number and SHA-256 artifact receipt. Refuses overwrite.
- `scripts/apple_beta_build.py`: separate signed archives, profile/keychain
  handling and exact artifact manifests; resumes export without a new build.
- `scripts/apple_beta_publish.py`: validate, one-shot upload intent, status,
  existing-app/internal-group attachment and readback. No public submission.

Use `--help` for signing/build commands; private credential paths are supplied
explicitly and never included in the repository. App Store IPA/PKG exports are
not general sideload installers; testers use TestFlight. The Android APK can
be installed directly and is signed separately from Play's app-signing key.

## Verification record

Android build 3 passed the owned API34 emulator test: catalog, English lettering,
preview and system share. The emulator was stopped afterward. iOS passed a real
XCTest run on an owned simulator: no web views, native catalog, preview and
`ActivityListView` share sheet. The simulator was shut down after capture.

The Mac target compiled, signed and launched a populated native window. Its
XCTest run was interrupted after the shared desktop's unrelated keychain and
authorization dialogs prevented progress. These dialogs and other projects
were not dismissed or changed. A clean Mac UI/save-panel test remains open;
compilation and Apple processing are not claimed as that missing test.

Public PWA checks cover mobile/desktop fit, live preview, direct GIF link,
offline shell, worker scope and absence of backend requests. Tests of the
prototype's billing UI are fixtures, not live purchase qualification.

## Artifact hashes

| Artifact | SHA-256 |
| --- | --- |
| Android APK 1.0 (3) | `0cc3cdc2a75ce0f2d7f1f7875e5d4d4a5a8afcc42b1459b919f7672254718a84` |
| Android AAB 1.0 (3) | `402560be595399a4085e385ae4f0148aee1f10935e892b4796c5dc8d703d8863` |
| iOS IPA 1.0 (3) | `37239ce6e43eefeca61af8c92ad123a2072c04728ae7bdacbd84a8f624f82f3e` |
| macOS PKG 1.0 (2) | `deac0ded24f4ba3216c33cfea97a33dc6bf2b0a0c572a1fbcac5f6ec74251a82` |

Retain older artifacts without distributing obsolete wrappers. Beta-provider
receipts, tester addresses and signing details stay in the private handoff.

## Findings carried forward

- Native GIF transfer concurrency needs an explicit queue even with HTTP/2
  connection limits. Public artwork quality is retained, not recompressed.
- In SwiftUI, hosted image views must not intercept the containing button's
  touch events. Preview/save flows are verified, not only screenshots.
- A root iOS bundle folder named `Resources` caused signing ambiguity; use
  `CatalogAssets` and verify both resource lookup and archive signing.
- Native UserDefaults use is declared in the Apple privacy manifest. Review
  declarations again when login, uploads or analytics are introduced.
- Preserve shared signing/browser/VM state and stop only exact owned tests.
