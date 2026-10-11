# Social Sign-In Qualification

Updated 11 October 2026, 16:45 UTC (12 October locally). Public Stickers and the separate,
authenticated Create workflow remain app-owned. This investigation changed no
application source, provider configuration, activation flag or store release.

## Live Readiness

The live [account discovery](https://chat.lazying.art/.well-known/lazyingart-account)
returned HTTP 200 with password, Google and Apple enabled; GitHub was disabled.
The issuer owner's earlier qualification recorded two real callbacks per enabled
social provider with stable subjects, cancellation and consumed-state rejection.
Those central proofs are distinct from a completed WeSticker login.

| Path | Verified result | Remaining boundary |
| --- | --- | --- |
| LazyingArt password | Existing app signup, consent, callback and session qualification is retained. Fresh app authorization uses client/audience `westicker`, scope `profile`, the exact app callback, state and S256. | This investigation did not repeat password signup or revive the erased test account. |
| Google through LazyingArt | Normal first-sign-in registration, real Google callback, profile-only app consent, WeSticker callback/session, creator consent and Create workspace all passed. | The permanent owner account is retained. Fresh provider reauthentication and Apple linking are separate checks. |
| LazyingArt SSO reuse | After app logout, a new consent round-trip reused the exact local account and opened Create. Cancellation returned to the dedicated login screen; consumed app callback replay returned 401 without invalidating the current session. | No new password or forced refresh test was performed in this continuation. |
| Apple through LazyingArt | Normal first-time registration fields, terms/age consent, saved Apple authentication and ordinary Apple Continue reached the real central callback. | The callback returned `account_exists_use_sign_in`. No successful Apple-to-WeSticker session is claimed; explicit linking must preserve the existing Google-created owner account. |
| GitHub through LazyingArt | Latest discovery reports disabled. Expanded browser recovery found actual authenticated owner settings access and confirmed the existing dedicated central registration with both callbacks. | Issuer owner has the exact retained browser/tab for credential recovery and real callback qualification. Do not duplicate the registration. Console access is not working GitHub app login. |

The completed Google round-trip returned HTTP 200 bootstrap with an authenticated
user; normal app creator consent was accepted and the actual Create workspace
opened. The original central subject and local account ID are recorded privately
as permanent owner data. Normal app logout returned `user: null`; subsequent SSO
returned that same account. The app continues to use `providers: ["lazyingart"]`,
not separate direct-provider clients. These are real browser outcomes, not
fixtures or central-only proof checks.

One ordinary chat request in that same authenticated Create UI returned HTTP 200
and a visible reply with a proposed caption/action table. The table was not
applied and no generation was requested. Read-only checks of the exact retained
account found one draft, zero render jobs, zero checkouts, zero upload tickets,
the free plan and zero credits. The account and generic brainstorm draft are
retained, not erased as test fixtures.

## Exact Next Boundary

The initial Google and Apple attempts left the collapsed first-time registration
section unfilled and returned the raw `registration_consent_required` error.
That historical outcome is superseded for Google: the owner expressly authorized
ordinary registration and terms/age consent, and the existing first-time form
worked when completed. The central owner has received the UX defect: a new user
needs a clear, explicit registration continuation rather than a raw error page.

Apple encountered an actual account collision after registration consent. Use
an explicit issuer-owned linking flow with fresh proof of both identities;
never link by matching email or create an alternate account to avoid the
collision. The central owner reports no enabled general linking UI at the last
checkpoint. The exact collision and retained-account record have been sent to
that owner. Direct database insertion is not an acceptable workaround. Provider
access and console setup already work; another password request is not the fix.

The app should retain its existing LazyingArt client and callback. Central
Google/Apple readiness does not authorize enabling unconfigured direct app
OAuth clients or copying another app's credentials. Complete the remaining
provider-specific account/callback and refresh checks; native system-browser completion
needs its own receipt. Billing and store publication remain separate.

## Preservation

All owned anonymous contexts, password-manager tabs and the final QA tab were
closed after evidence capture. The shared browser/profile and other projects'
tabs were preserved. The saved
Apple password was used in memory through the authorized browser password manager;
no credential, cookie, token or callback code was copied into files or logs.
The new owner account is permanent, not disposable. No account cleanup, merge or
deletion was attempted. No subscription, purchase, reference upload or render was
submitted during login qualification. The single chat reply is not image or
animation qualification and does not qualify Apple's app login or native return.

## Provider Selection Contract

The currently inspected SDK exposes `Client.authorize(store, browser_binding)`
with no provider-selection argument. It sends only `response_type`, `client_id`,
`audience`, `redirect_uri`, `scope`, `state`, `code_challenge` and
`code_challenge_method`. Fresh discovery at 16:27 UTC advertises contract v1 but
no provider-selection or remembered-consent capability.

Read-only inspection of the issuer's active mounted source confirms that the
authorization handler does not implement a provider hint. Extra query fields
being carried into its hidden form do not give those fields selection semantics.
The actual provider start is a CSRF-protected POST to
`/account/provider/{google,apple,github}/start`, not an app-linkable GET route.
Do not invent `provider=`, `login_hint`, `prompt` or direct provider-start links.

The supported path remains the pinned LazyingArt SDK authorization followed by
central provider selection. Explicit app social buttons need an additive,
documented issuer/SDK contract, including exact allowed values, unavailable and
cancel behavior, preservation through registration/reauthentication, and fresh
proof of the selected provider rather than silently using a different session.
State, S256, browser binding, the exact callback and app consent remain required.
The issuer owner has received this request; no deployed extension or completed
repair receipt was available at this checkpoint. The parent owns the unified
app login route and must not treat this requested contract as implemented.

## Repeated Consent Diagnosis

A fresh real-browser trace with the retained authenticated app session found:

1. App bootstrap returned 200 with an authenticated user.
2. An explicit visit to `/auth/lazyingart/start` returned 302.
3. Central `/account/authorize` returned 200 and displayed "Continue to westicker"
   with Continue/Cancel. No external-provider login was needed.
4. Client/audience were `westicker`, scope `profile`, callback exactly
   `https://westicker.lazying.art/auth/lazyingart/callback`, with state and S256.
5. Returning to the app without submitting the form preserved the existing app
   account/session. The owned trace tab was closed; no exchange remains active.

This reproduces repeated consent, not a redirect loop or lost cookie. The active
issuer's profile authorization GET unconditionally renders consent after checking
the central session; it does not consult a reusable profile-consent grant. The
app start also creates a new authorization attempt whenever invoked. The parent
can avoid unnecessary starts when the intended app session is already valid.

Remembering consent requires issuer-owned durable grants and qualification, not
auto-clicking Continue or skipping authentication. A proposed implementation must
bind the decision to the exact subject, client, audience and scopes; require new
consent for new/expanded, revoked or expired grants; preserve revocation and
account-switch behavior; and continue issuing fresh one-use codes with the new
state/S256 binding. These are acceptance requirements, not current capabilities.
First-time registration continuation and explicit dual-proof Apple linking remain
separate unresolved issuer work. No further Apple collision retries were made.

The subsequent bounded GitHub inventory checked the documented EchoMind/AiMemo
endpoints. CDP9485 and9497 identify the same live browser; historical9484,
AiMemo9493 and the documented separate9294 endpoint were unavailable. A fresh
read-only developer-settings visit in the live profile redirected to GitHub
sign-in. Stopped saved profiles were not relaunched or declared unauthenticated.
The historical central receipt identifies an existing dedicated registration;
runtime credentials being absent is not a reason to register another client.
All existing tabs were preserved and the single temporary inspection tab closed.

That initial bounded result is superseded by the expanded authorized inventory:
normal reopening of an inactive, previously owner-selected saved profile reached
authenticated GitHub developer settings and the existing central application's
actual settings page. Both expected callbacks were present. No profile/cookie
copy, token injection, MFA bypass, registration or secret-generation action was
used. The issuer owner received the exact retained browser/tab for recovery;
no current blanket owner-login blocker is claimed. Separate XYQ and preserved
OnlyIdeas profile checks reached sign-in, and their temporary inspection windows
were closed. The recovered owner browser is retained solely for issuer recovery,
with its cleanup ownership recorded privately. No provider contract or callback
qualification is inferred from that recovered console access.

Related evidence: [original app login qualification](login-chat-release-20261011.md)
and [integration ownership](integration-handoff.md). Private central-owner and
app-attempt receipts remain outside the repository.
