# Native Guest Chat And Navigation

Delivered internal releases: iOS 1.0(10), macOS 1.0(8), Android 1.0(9).
The preceding iOS/Android 8 UI is superseded. No formal review or purchases.

## Actual Delivery

- Android 1.0(9): available to internal testers. Exact signed APK smoke passed;
  genuine guest composer and nested Characters screenshots reviewed. GIF pixels
  changed/paused/resumed (5/1/5 unique frames), preview/share and local restore passed.
- iOS 1.0(10): signed archive/export, four XCTest cases and screenshot review
  passed. Actual typing, keyboard clearance, visible bounds and Account-tab return
  were exercised without sending chat. Apple reports VALID, IN_BETA_TESTING,
  present in WeSticker Internal, one tester. No formal review was submitted.
- iOS 1.0(9): uploaded before screenshot review found the composer occluded despite
  passing existence assertions. Provider readback confirms it is not in the
  internal group. Preserve the failed artifact; local source changes do not fix it.
- macOS 1.0(8): corrected source archived/exported and installer signature verified;
  Apple reports VALID, IN_BETA_TESTING, present in WeSticker Internal, one tester.
  The existing installer credential resolved the locked keychain without replacing
  any identity or changing security. Desktop GUI QA is unqualified:
  XCTest previously stalled and a bounded source-matched probe could not capture
  its window in the SSH GUI session. Failed probe evidence is preserved; it is
  not evidence of a product rendering defect. No app redesign was made for it.

Evidence is under `.runtime/releases/{android-1.0-9,ios-1.0-10,macos-1.0-8}`.
Apple artifacts and full XCTest results are also retained on the existing build
Mac under `~/Projects/WeSticker-build/releases`. No physical-device qualification
or native purchase was performed in this round.
All four binaries (APK, AAB, IPA, PKG) were copied to the owner's existing
`Share/WeSticker/2026-10-11-clean-chat` sync folder and their hashes verified.
This establishes local sync-folder copies, not independent cloud acknowledgement.
Owned native build/test processes and simulators are stopped; shared store-browser
sessions and other projects' devices remain untouched.

## Native Scope

- Four top-level destinations: Stickers, Create, Library, Account. Create opens first.
- Library owns the Creations/Characters tabs and retained local photo draft.
- Guest Create has a composer immediately, without login or account creation.
- Account and the cloud library retain explicit system-browser sign-in. Cloud
  references, saved projects, consent, render quotes and confirmation stay on
  the existing authenticated routes. Account shows sign-in progress/errors;
  purchase and recovery logic is unchanged.
- Authenticated Chat/Sticker plan remain mutually exclusive panes. Service
  configuration is a sheet/dialog, not always-visible chat content.
- Apple uses explicit scroll/composer/navigation rows, avoiding nested bottom
  safe-area insets. Release QA requires a visible, hittable composer, unsent text
  entry, keyboard clearance and the same checks after returning from Account.

## Guest Contract

`POST /api/guest/chat` on the configured native creator-service origin:

```json
{"message":"Hello","history":[{"role":"user","content":"Earlier question"},{"role":"assistant","content":"Earlier reply"}],"locale":"en"}
```

The response is `{ "reply": "..." }`. Non-2xx `detail` or `error` strings are
displayed as failures. The clients do not replay failed requests automatically.
Messages are limited to 2,000 characters; history contains up to six completed
pairs, at most 12 turns and 16,000 characters. Pending/failed turns are excluded.

Guest transcripts and drafts are session-only, not uploaded as cloud projects or
persisted to disk. A separate anonymous transport sends no bearer token, CSRF,
cookies or stored HTTP credentials and refuses redirects. A new conversation,
origin change or authentication/consent transition invalidates pending replies.
Ordinary bootstrap refresh does not erase guest conversation. Cancelled/failed
messages remain editable; no generation, tools or account calls originate from
the guest transport.

## Checks

- `pytest -q tests/test_native_guest_chat.py tests/test_native_purchase_clients.py`
- `ANDROID_HOME=<existing-sdk> bash tests/native_clients/check-kotlin.sh`
- On the existing Mac: compile `apple/Sources/GuestChat.swift` with
  `tests/native_clients/GuestChatTest.swift` using `swiftc`, then run the binary.
- `apple/UITests/CatalogTests.swift` checks no-login Create, nested Characters,
  retained local drafts, catalog sharing, and changing/paused/resumed GIF pixels.
- Release-only Account XCTest and `scripts/android_smoke.py --creator --account`
  never open authentication or purchase sheets and never send live guest chat.

Protocol fixture tests and source-contract checks are not live-provider or
physical-device evidence. Build hashes, actual UI captures and internal-store
receipts belong to each private release directory. No backend, web or store
configuration is changed by this native revision.
