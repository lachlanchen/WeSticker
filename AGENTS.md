# WeSticker

Independent creator app. Do not mutate the AYA storefront, its orders or WeChat
works. Public default artwork is read-only; private uploads are account-scoped.
Use English for user-facing progress and explanations by default.
The owner requires native iOS and Android apps: SwiftUI/UIKit and Kotlin/Jetpack
Compose. WebView/Capacitor shells are not acceptable mobile test or store builds.
Keep the React app for the web/PWA only; share data/contracts, not a web UI shell.
Never commit credentials, browser profiles, customer photos, databases or builds.
Use apply_patch for source edits. Run backend tests, frontend typecheck/build and
browser tests before committing. Preserve other projects and active VMs.

Generation requires explicit consent, a locked character and an idempotent job.
Uncertain paid requests must not be retried automatically. Preview/export is not
AI generation. Never claim mocked billing, OAuth, native builds or store review
as live verification. WeChat automation saves drafts only, never submits review.

Native GIF checks must compare successive sticker pixels and exercise pause and
resume, not just assert that an image URL loaded. Respect reduced-motion defaults
while allowing explicit Play. Verify icons inside the compiled app and the exact
distributed build; changing source artwork alone does not update installed apps.

Keep subscriptions app-specific. Web Stripe checkout is not native IAP. Never
expose web checkout from native store builds before their applicable rules and
native purchase path are qualified. Creators cannot sell before moderation and
verified payout onboarding. Keep all candidate variants and actual provider IDs.
