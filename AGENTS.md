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

Create is the shared chat/artifact workspace; do not restore a separate global
Agent tab. Chat proposes a revisioned caption/action table, and the user applies
it explicitly. All renders require a quote and stable attempt ID. Keep tier
limits in the backend contract, preserve older drafts after expiry, and keep
the saved on-device photo workflow accessible without uploading its references.
The assistant is conversation-first: users can chat before choosing references;
questions need not produce a sticker table. Attach an approved character to the
same draft later. Native login uses a system browser and automatic, one-use PKCE
return, never a manual "I connected" button. Shared-account deletion revokes the
app-bound SDK sessions before erasure and must allow interrupted cleanup retries.
Stickers is the public starting tab. Create requires sign-in: signed-out users
see one app-level login screen outside the tabs, then return to their intended
workspace after authentication. Do not duplicate login forms inside Create,
Library or Account. Native provider selection opens its authorization directly,
without another PWA login screen. Chat itself is a clean conversation surface, not a login or
billing panel. There is no anonymous chat endpoint. Characters belong inside
Library, not a separate global navigation tab; Account is the last tab. Private
references and generation retain consent and quote requirements.
Use `scripts/test_studio_isolated.py` for repeat browser QA; do not relax signup
limits or borrow paid-provider credentials to make tests pass.

Normal chat uses the pinned AgInTi restricted application SDK with DeepSeek in
an isolated, proposal-only container. Keep this lightweight: one bounded text
request, no model-executable tools, account-scoped history and explicit table
application. Generation remains in the existing quote/consent/job pipeline.
Do not mount Codex homes, active developer sessions or the Docker socket into
customer chat. Codex fallback is unqualified and disabled; a preference for
AgInTi does not authorize using its unrestricted CLI wrapper. See
`docs/agent-and-docker.md` for qualification, migration and rollback.

Native GIF checks must compare successive sticker pixels and exercise pause and
resume, not just assert that an image URL loaded. Respect reduced-motion defaults
while allowing explicit Play. Verify icons inside the compiled app and the exact
distributed build; changing source artwork alone does not update installed apps.

Keep subscriptions app-specific. Web Stripe checkout is not native IAP. Never
expose web checkout from native store builds before their applicable rules and
native purchase path are qualified. Creators cannot sell before moderation and
verified payout onboarding. Keep all candidate variants and actual provider IDs.
