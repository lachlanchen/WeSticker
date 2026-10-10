# Native GIF Playback And Icon

The previous distributed Mac build still contained the earlier icon. The next
archive had the replacement artwork, but its installer export failed because
the existing installer signing keychain was locked. A source icon change alone
does not update an installed app.

## Internal Delivery

- macOS **1.0 (4)** is Apple-processed VALID and attached to the existing owner
  internal TestFlight group, with status IN_BETA_TESTING.
- iOS **1.0 (5)** is uploaded; processing/attachment is recorded in the private
  release handoff before it is described as available to testers.
- Android **1.0 (4)** is unchanged. This round verified the exact existing APK;
  it did not make a new Play submission.

## Changes

- macOS uses `GIFImageView`, an ImageIO frame player that respects each GIF's
  frame delay, loops, and stops its timer when detached or dismantled. Frames
  update the native image view directly rather than relying on implicit AppKit
  GIF animation inside SwiftUI.
- Apple platforms use Reduce Motion as the initial playback preference. The
  explicit Play button now overrides it; previously the UI could say Pause
  while Reduce Motion still forced the image to remain static.
- The light-blue Aya-and-Lala master is exported to every platform. The compiled
  Mac `AppIcon.icns` was extracted from the signed archive and visually checked.
- The release builder can reuse WeSticker's existing distribution identity.
  The installer keychain is unlocked only for export and restored afterward.

## Verification

![Compiled Mac icon](screenshots/mac-compiled-icon.png)

![Native iOS catalog during the playback test](screenshots/animated-catalog-ios.png)

- Native macOS view: eight different pixel captures while playing, one while
  paused, eight after resuming. This tests the actual renderer used by the app,
  not a browser GIF. The full Mac XCTest run could not establish its automation
  session and was stopped; it is not counted as a passing UI test.
- iOS simulator: the catalog's first sticker changes pixels, pauses, and resumes.
  `testGIFPlaybackPauseAndResume` passes, with saved screenshot attachments.
- Android signed 1.0 (4) APK: cropped sticker screenshots change while playing,
  remain identical while paused, and change again after resuming. Preview and
  the native share sheet also pass. No unchanged Android binary was rebuilt.
- Native physical-device playback was not tested in this round.

## Reproduce

On macOS, provide a downloaded public catalog GIF and an evidence directory:

```sh
swiftc apple/Sources/GIFImageView.swift scripts/macos_gif_smoke.swift -o /tmp/westicker-gif-smoke
/tmp/westicker-gif-smoke "$GIF" "$EVIDENCE"
```

Apple catalog UI coverage is in `apple/UITests/CatalogTests.swift`. Android's
`scripts/android_smoke.py` now checks motion, pause, resume and sharing against
an exact APK. Keep private signing configuration, build artifacts and provider
receipts out of Git. Internal TestFlight delivery is distinct from public review.

The AYA shop's localized **Create my own** button navigates to
<https://aya.lazying.art/westicker/>. Its independent shop router must not
intercept that link. Shop checkout, downloads and purchase records are unchanged.
