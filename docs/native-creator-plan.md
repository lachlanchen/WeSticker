# Native creator and assistant: next milestone

Owner feedback, 2026-10-10: build 3 installed successfully, but creation and
the agent are absent. This is accurate. The shipped candidate is a catalog
beta, not the requested complete creator app. Cosmetic catalog changes do not
complete this milestone.

## Current boundary

- Public PWA and native beta: browse, preview, favorites, lettering language,
  animation pause and individual GIF download/share.
- Local web prototype: photo upload, reference approval, caption editing,
  photo-based exports, provider adapters and a draft-only WeChat worker.
- Not qualified end to end: live AI, four production login providers, native
  subscriptions, creator sales and customer-isolated WeChat automation.

## Native workflow

Use native screens and platform photo pickers in SwiftUI and Compose. Share
API contracts with the web app, not an embedded website.

1. **My studio:** resume drafts and show the exact generation state. Retain
   catalog browsing without login. Start with one character and eight expressions.
2. **Character:** select 3-5 photos, confirm rights, review a generated character
   sheet, and explicitly lock the reference before generating the pack.
3. **Expressions:** choose daily, couple, work or custom scenarios. An assistant
   proposes captions and actions as editable structured data.
4. **Generate:** display provider, cost and remaining quota before one deliberate
   submission. Persist the job ID; resume observation after app restarts. An
   uncertain response never starts another paid job automatically.
5. **Review:** a dense animated grid, per-sticker text/action edits, versions,
   approval, transparency/margin/text checks, and native ZIP/share export.
6. **Upload assistant:** a visible, account-isolated WeChat session. Show progress
   per field/file, handle expired login, save and verify the same draft. Final
   platform review submission remains with the user.

The assistant belongs beside the current task, with explicit proposed actions
and results. It must not be an unrelated chat screen or a hidden automation
that publishes without review. Keep the current pack and previews visible.

## Ordered implementation and acceptance

| Step | Existing foundation | Required evidence before release |
| --- | --- | --- |
| Account and upload | Web OAuth, ownership and consent API | Native system-browser return, secure session storage, cancellation, deletion, private uploads never in the catalog |
| Character and drafts | Web lock/review data model | Native draft lifecycle and photo picker on iOS/Android; restore state after relaunch |
| Generation | Image/local-animation adapters and durable jobs | One real authorized job, exact cost/receipt, progress, failure/resume and no duplicate charge |
| Review/export | Caption and package helpers | Native editing, retained originals, visual QA, valid ZIP and platform share/save |
| Billing | Server verification and prototype store bridges | Native StoreKit/Play Billing UI, actual sandbox purchase/restore/revoke/renewal matrix |
| WeChat assistant | Isolated Docker worker, save-only selectors | One consenting test account, draft readback, login expiry and crash recovery, no submit action |
| Marketplace | Review and entitlement model | Moderation, payout onboarding, refund/download tests and rights policy |

Build 4 should be described by what it actually delivers, not by this entire
roadmap. Expose actions only when their backend capability is verified. A mock
response, photo caption export, fixture purchase or queued request is not proof
of AI generation, payment or a successful WeChat upload.

## Efficiency

Generate and review a character first, then a small pack; reuse the approved
reference rather than re-generating it with every edit. Text-only changes use
post-processing. Poll only active jobs with backoff and pause on background;
use bounded, resumable uploads and thumbnails. Keep existing three-transfer
GIF concurrency and caches. Do not reload every pack when chatting.

Port the web grid's new small animated previews to native during the creator
update, keeping full original GIFs for save/share. Build 3 still uses original
GIFs in its native grid; the later PWA thumbnail improvement is not silently
claimed as present in that installed binary.
