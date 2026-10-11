# Social Sign-In Qualification

Updated 11 October 2026, 20:12 UTC (12 October locally). Public Stickers and the separate,
authenticated Create workflow remain app-owned. This investigation changed no
application source, provider configuration, activation flag or store release.

## Current App Selector Acceptance

The app owner activated official SDK `4eb95cfa`, then release
`a0299f0024990686` and the four-provider selection. The public login screen now
offers Google, Apple, GitHub and LazyingArt through the existing shared client
and callback. All four have actual retained-owner web app acceptance. Earlier
LA-only, three-provider and deployment-pending statements below describe
historical checkpoints, not the current app.

The initial retained-owner acceptance passed for the first three buttons:
Apple and Google each went directly from one app provider click to the real
external provider, without a second central provider chooser or button. Normal
Apple authentication/confirmation and Google's remembered-account choice each
returned through the real WeSticker callback to authenticated bootstrap 200 with
the original app-local ID. After another normal app sign-out, LazyingArt reused
central SSO and returned the same account. All three opened the app Account
destination (`view=account`); these are not synthetic or intercepted callbacks.

Existing profile consent was reused; these checks do not claim a new first-time
registration or consent flow. External provider authentication may still require
interaction. Read-only checks confirmed the original issuer/subject mapping,
one retained draft, zero render jobs, zero checkouts and zero upload tickets.
No new chat, generation, purchase, account creation, merge or deletion occurred.

Issuer `db3129d1` is live. Its owner's separate public checks now pass automatic
same-origin CSRF POST continuation and cancellation for Google, Apple and GitHub.
Those issuer checks are distinct from the actual app acceptance above. The
earlier public-probe failure was diagnostic redirect interception, not an app
acceptance result. GitHub's real linking and app callback are recorded below;
native system-browser completion remains a separate qualification boundary.

Local evidence: `.runtime/auth-qualification/selector-login-20261012.png` and
`selector-app-acceptance-20261012.json`. The login screenshot contains no account
identity. Private records retain exact identifiers; no credentials or tokens are
included in public documentation.

## GitHub Link And App Acceptance

At 20:06 UTC, the normal central GitHub link journey completed using the retained
owner and original authorized browser profile. Real GitHub authentication opened
the existing-account continuation. Fresh Google proof for the original account
and a second fresh GitHub proof led to an initially unchecked Link confirmation.
The exact displayed username matched the private retained-owner record before
explicit confirmation. The issuer then returned to its normal account page.
No duplicate signup, email-based merge, direct database link or account deletion
was used. Central immutable-subject readback was requested from its owner.

After parent enabled GitHub, the four-button screen was observed in a signed-out
app browser. Clicking GitHub returned through the actual shared callback to
authenticated bootstrap 200 and the original app-local ID, reusing the freshly
linked central session and existing profile permission.

A second independent app flow signed out only this profile's central browser
session, then signed out of WeSticker normally. One app GitHub click produced the
real sequence: issuer authorization, automatic CSRF-protected GitHub start POST,
GitHub OAuth authorization, real issuer GitHub callback, and automatic profile
permission reuse POST. No second central provider or Continue button was clicked.
The existing authorized GitHub session needed no further external interaction.
The actual app returned to Account (`view=account`) with authenticated bootstrap
200. The navigation observer ended after the issuer reuse POST; app completion
was independently verified from the resulting browser UI and fresh bootstrap,
not inferred from a provider hostname or an intercepted callback.

Read-only exact-account checks verified the original local ID, unchanged
immutable `(issuer, subject)` and unique mapping, one retained draft, zero jobs,
zero checkouts and zero upload tickets. No new chat, render, purchase or upload
was requested. The permanent account remains intact. These are real browser and
provider outcomes, not fixtures; they do not claim native system-browser or a
new GitHub provider-denial test.

Evidence under `.runtime/auth-qualification/`: `github-link-20261012.json`,
`github-app-acceptance-20261012.json`, `four-provider-login-20261012.png` and
`github-app-account-redacted-20261012.png`. Identity was hidden only for the final
screenshot and restored immediately; account/profile content was not changed.
The temporary recovered GitHub browser was closed normally after evidence;
its original profile and the existing shared browser/app session were preserved.

## Live Readiness

The live [account discovery](https://chat.lazying.art/.well-known/lazyingart-account)
returned HTTP 200 at 19:11 UTC with password, Google, Apple and GitHub enabled.
The issuer owner's earlier Google/Apple qualification recorded two real callbacks
with stable subjects, cancellation and consumed-state rejection. GitHub's later
proofs and cancellation limitation are recorded separately below. Central proofs
are distinct from a completed WeSticker login.

| Path | Verified result | Remaining boundary |
| --- | --- | --- |
| LazyingArt password | Existing app signup, consent, callback and session qualification is retained. Fresh app authorization uses client/audience `westicker`, scope `profile`, the exact app callback, state and S256. | This investigation did not repeat password signup or revive the erased test account. |
| Google through LazyingArt | Normal first-sign-in registration, real Google callback, profile-only app consent, WeSticker callback/session, creator consent and Create workspace all passed. | The permanent owner account is retained. Fresh provider reauthentication and Apple linking are separate checks. |
| LazyingArt SSO reuse | After app logout, a new consent round-trip reused the exact local account and opened Create. Cancellation returned to the dedicated login screen; consumed app callback replay returned 401 without invalidating the current session. | No new password or forced refresh test was performed in this continuation. |
| Apple through LazyingArt | Explicit linking, independent Apple login and the live selected Apple app-button flow all returned the original local account and immutable central mapping. | Permanent account retained; native system-browser return is separate. |
| GitHub through LazyingArt | Dedicated registration, real central callback/replay checks, explicit dual-proof linking, selected app session reuse and a fresh GitHub-to-WeSticker round-trip passed with the original immutable mapping. | Native completion and real provider-denial testing are separate; no duplicate account or email merge was used. |

The completed Google round-trip returned HTTP 200 bootstrap with an authenticated
user; normal app creator consent was accepted and the actual Create workspace
opened. The original central subject and local account ID are recorded privately
as permanent owner data. Normal app logout returned `user: null`; subsequent SSO
returned that same account. That earlier app used `providers: ["lazyingart"]`;
the current four choices still share that single client and callback, not
separate direct-provider clients. These are real browser outcomes, not
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
worked when completed. The central owner subsequently deployed normal explicit
registration continuation and dual-proof linking as `a0433e39`. Its registration
form tests used synthetic provider transport; those do not claim another real
owner registration. The actual Apple linking and login acceptance below did use
the real provider and retained permanent account.

Apple's earlier account collision is now resolved through the deployed explicit
issuer linking flow, not by email matching, alternate signup or direct database
insertion. The exact target account was confirmed before linking, preserving its
original identifiers and draft.

The app should retain its existing LazyingArt client and callback. Central
Google/Apple readiness does not authorize enabling unconfigured direct app
OAuth clients or copying another app's credentials. Complete the remaining
GitHub account/callback and remaining lifecycle checks; native system-browser completion
needs its own receipt. Billing and store publication remain separate.

## Actual Apple Acceptance

At 18:07-18:09 UTC, real Apple authentication opened **Use your existing account**
instead of the old raw collision. The normal journey then required fresh sign-in
with the account's original Google identity, a second fresh Apple proof, and an
unchecked Link confirmation. Its displayed target username was compared to the
retained private account record before explicitly confirming. The original app
permission remained separate; completing it returned to WeSticker authenticated.

A new app sign-out/login then independently proved Apple-only sign-in. No Google
request, registration, collision or Link screen appeared in this second flow.
At 18:11 UTC, bootstrap returned 200 with the same local account ID. Read-only
checks confirmed the original central issuer/subject mapping, one retained draft,
zero render jobs, zero checkouts and zero upload tickets. The Account view
rendered and every owned auth/password-manager tab was closed. No new chat,
generation, upload, purchase or account creation/deletion occurred.

Because central SSO initially opened app consent, qualification used the existing,
source-supported central reauthentication page with the original app authorization
preserved. This is not a new provider-selection API or an app-level Apple button.
The app still exposes LazyingArt only; explicit social entry points need the
supported selector/SDK contract. Its base contract is deployed and the public
readiness method is now delivered; single-entry issuer rollout and actual
new-contract app acceptance remain pending. GitHub-to-WeSticker remains unqualified. These results
do not claim native system-browser acceptance.

## Preservation

All owned anonymous contexts, password-manager tabs and the final QA tab were
closed after evidence capture. The shared browser/profile and other projects'
tabs were preserved. The saved
Apple password was used in memory through the authorized browser password manager;
no credential, cookie, token or callback code was copied into files or logs.
The new owner account is permanent, not disposable. No account cleanup, merge or
deletion was attempted. No subscription, purchase, reference upload or render was
submitted during login qualification. The single chat reply is not image or
animation qualification and does not itself qualify Apple's app login or native
return; the later independent Apple evidence is recorded above.

## Provider Selection Contract

The issuer actively accepted this work at 18:18 UTC and delivered an implementation
receipt at 18:33 UTC. Its latest 18:35 update reports browser fixtures passing and
a cancellation-race fix underway before deployment. The canonical owner has one
confirmed active writer; no competing owner agent or runtime edit was started.
Earlier queued-only status is superseded by this actual implementation work.

The source SDK now defines the additive interface:

```python
client.authorize(store, browser_binding,
                 provider="google", reuse_consent=True)
```

Allowed selections are `google`, `apple`, `github`, and `lazyingart`. Optional
single prompts are `login`, `select_account`, and `consent`; ordinary login need
not force a prompt. Unchanged calls retain the legacy request. The SDK requires
fresh pinned discovery with the exact `provider-select-v1` capability and enabled
selected-provider readiness before creating an attempt. Allowed names are not
availability flags. No disabled-provider fallback, guessed hint or direct social
start GET is supported.

Fresh public discovery at 18:37 UTC still lacked this extension and marked GitHub
disabled. Source implementation is therefore not a deployed contract or a passed
new-selector app callback. The parent integration packet identifies the SDK call,
existing shared adapter, bootstrap readiness, neutral-session reuse and native
return boundaries; it does not authorize copying central provider credentials or
enabling the app's separate direct OAuth clients. State, S256, browser binding,
the exact registered shared callback and explicit consent remain required.

Independent SDK fixture runs from its source checkout passed:

- `python -m pytest -q tests/test_authorization_extension.py tests/test_client.py`:
  163 passed.
- `python -m pytest -q`: 245 passed, 3 optional source-integration suites skipped.

These runs used the existing project Python environment and did not modify a
runtime. They cover strict options/discovery, disabled-provider refusal, legacy
shape, browser binding, S256, cancellation and replay. They are not real-provider
or deployment evidence. The permanent owner's previously qualified Google/Apple
account and app session are retained; GitHub's retained-account app callback is
still required before claiming all four app methods work.

An independent source review found that this implementation still requires a
second central login click after the app selects a social provider. Its browser
fixture explicitly clicks the app's Google choice and then the central Google
button. Filtering the central chooser is not the requested single-entry journey.
The issuer owner received the exact finding and a request for nonce-protected,
same-origin CSRF POST continuation to the selected provider, with a no-JavaScript
fallback and explicit registration/link/first-permission consent preserved.
That repair and a browser assertion without the second click remain required.

At 18:42 UTC the issuer reported guarded-write and legacy regression tests
passing, preparation of a backed-up deployment, and active GitHub provisioning
work using the recovered dedicated registration. It confirmed live GitHub client
credentials remain absent and will keep that provider disabled until a real
callback succeeds. This is active work, not an all-provider completion receipt.
At 18:46 UTC, read-only browser metadata confirmed the original recovered profile
had reopened on the existing registration's credential settings page. No page
contents or credential values were inspected by this sidecar. The issuer's active
browser remains untouched; this observation is not proof of secret creation or
a completed GitHub callback.

The issuer's 18:48 update reports source and SDK committed/pushed as `371ff01f`
and `03e021cb`, respectively, with candidate validation before cutover. The
independently tested SDK source fingerprints match the committed version.
Public discovery at 18:49 still lacked the extension and marked GitHub disabled.
GitHub provisioning reached a real **Confirm access** challenge; its owner is
trying the normal recovery path without account-security changes. The committed
selector still requires the second central click described above. Deployment,
that UX repair and actual GitHub callback qualification remain open, not passed.

The 18:57 owner readback supersedes the Confirm access blocker: normal email
verification succeeded and the dedicated credential is now stored privately.
Structured evidence confirms one code submission, the original owner/application
and cleared protected-action challenge; the sidecar inspected no code or credential
values. The issuer is checking deployment and real callbacks before activation.
Credential provisioning is progress, not a completed GitHub-to-WeSticker login.

The parent requested a public SDK `available_authorization_providers()` method
for bootstrap readiness without creating attempts or duplicating private protocol
validation. That additive method is requested, not present in `03e021cb`.
UI-only caching may be brief; each authorization must still fetch fresh discovery.

At 19:03 UTC, independent public discovery returned 200 with the exact
`provider-select-v1` extension, including its integer 30-day consent lifetime.
Google, Apple and password were enabled; GitHub remained disabled. This supersedes
the earlier deployment-pending discovery results. Parent app adapters are prepared
but not activated; the public SDK availability method, second-click correction
and actual provider-specific app acceptance still remain separate gates.

At 19:11 UTC GitHub also became enabled in public discovery. Independent receipt
comparison confirms two real HTTPS GitHub callbacks with the same verified
identity/client and distinct state, plus rejection of the first callback replay.
These are central proof-only results, not a WeSticker login. The separate public
browser cancellation check passed a same-origin 303 return with original
state/issuer, `access_denied`, no code and no account writes. It expressly did not
perform an app roundtrip or external-provider proof. GitHub offered no Cancel
control after existing approval; that external flow was abandoned without an
account change, and an actual provider Deny result is not claimed.

The existing SDK worker received a follow-up, but the public availability method
and automatic selected-provider POST have not yet been delivered in the inspected
source. The parent requested a safe Google/Apple increment independently of
GitHub work. No extra owner approval or account proof is required for these fixes.

At 19:21 UTC, the issuer's complete rollout receipt confirms `371ff01f` live,
the narrow migration, all four central availability flags, and the GitHub proofs
described above. It also records normal cleanup of its temporary GitHub browser,
preserving the profile and shared browsers. The SDK remains clean at `03e021cb`
without the requested public readiness method; the selected-provider second-click
gap remains in issuer source. Prepared app `5922d81` is still unactivated and
pinned to the older SDK. Neither central deployment nor previous legacy app
acceptance proves the requested single-click provider-specific app flow.

At 19:30 UTC, official SDK `4eb95cfa03f810924b6594ed493f7c01e57861f5` was
independently confirmed committed and pushed. Its public
`Client.available_authorization_providers()` validates one fresh pinned discovery
response and returns an enabled-name tuple without creating an attempt. This
supersedes the missing-getter status above. Independent verification passed:

- SDK suite: 347 passed, 3 optional integration modules skipped.
- SDK lint and formatting checks passed, retaining the documented E721 exception.
- WeSticker shared-identity suite with the new SDK: 30 passed.
- Actual public HTTPS getter returned LazyingArt, Google, Apple and GitHub.
- An isolated adapter probe using the real getter and `authorize` passed UI-only
  caching, shared callback/S256, fresh disabled-provider refusal and cache refresh.

The app tests/probe used synthetic issuer transport and temporary state; the live
getter performed public discovery only. None is a real new-selector app login.
The issuer owner retained and implemented automatic selected-provider POST in
working source; browser/deployment proof is still required before app activation.
No concurrent issuer/SDK source edit was made by this sidecar.

## Repeated Consent Diagnosis

The app-owned session-reuse fix is now independently verified in the real retained
owner browser. At 16:54 UTC, bootstrap returned 200 with an authenticated account;
`/auth/lazyingart/start?view=library` returned 302 directly to the app Library
destination (`view=library`), without visiting issuer authorization or consent.
The trace retained host, path and `view`, not the complete query string; it does
not establish the presence or absence of other parameters such as `welcome=1`.
The subsequent bootstrap returned 200 with the same nonempty local
account ID. A separate settled-page check confirmed the visible Library heading,
Library tabs and creation library, with no login screen. Both owned tabs closed;
the retained account/session and other owners' tabs were preserved. No new OAuth
exchange, account, chat, render or purchase was needed. This closes the unnecessary
redirect for a currently valid app session; it does not qualify expired-session
login, provider selection or issuer consent reuse.

Before that fix, the 16:27 UTC real-browser trace found:

1. App bootstrap returned 200 with an authenticated user.
2. An explicit visit to `/auth/lazyingart/start` returned 302.
3. Central `/account/authorize` returned 200 and displayed "Continue to westicker"
   with Continue/Cancel. No external-provider login was needed.
4. Client/audience were `westicker`, scope `profile`, callback exactly
   `https://westicker.lazying.art/auth/lazyingart/callback`, with state and S256.
5. Returning to the app without submitting the form preserved the existing app
   account/session. The owned trace tab was closed; no exchange remains active.

That reproduced repeated consent, not a redirect loop or lost cookie. The active
issuer's profile authorization GET unconditionally renders consent after checking
the central session; it does not consult a reusable profile-consent grant. The
old app start also created a new authorization attempt whenever invoked. The
parent's deployed fix now avoids that unnecessary start for a valid session.

Remembering consent requires issuer-owned durable grants and qualification, not
auto-clicking Continue or skipping authentication. A proposed implementation must
bind the decision to the exact subject, client, audience and scopes; require new
consent for new/expanded, revoked or expired grants; preserve revocation and
account-switch behavior; and continue issuing fresh one-use codes with the new
state/S256 binding. The new issuer implementation explicitly defines a 30-day,
exact subject/client/audience/callback/profile grant with first approval, no
expiry extension on reuse, and a same-origin CSRF POST for code issuance. Its
deployment and real-browser acceptance remain separate from this source contract.
At that earlier checkpoint, registration continuation and explicit dual-proof
Apple linking were unresolved. The subsequent deployed repair and genuine Apple
acceptance are recorded above; no repeated known-collision attempts were made.

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
used. The issuer handoff records the exact recovered browser/profile for recovery;
no current blanket owner-login blocker is claimed. Separate XYQ and preserved
OnlyIdeas profile checks reached sign-in, and their temporary inspection windows
were closed. The recovered owner browser was subsequently closed normally at
the bounded-watch deadline; its saved profile and reopen instructions remain
preserved privately. No provider contract or callback
qualification is inferred from that recovered console access.

At 17:00 UTC discovery still reported GitHub disabled and no provider-selection
extension. Read-only inspection of the existing dedicated GitHub registration
also confirmed an enabled new-client-secret control. No secret was generated:
issuer delegation and a private credential destination were requested, not
received. This is console capability evidence, not credential provisioning or a
passed code exchange; a protected action could still require normal Confirm
access. A source-informed, explicitly proposed integration plan is prepared
privately for the issuer. No proposed selector field is a supported contract.

The bounded handoff watch ended at 17:22 UTC without a supported contract,
explicit implementation/provisioning delegation or issuer response file. The
consolidated pickup request remains in the issuer's actual shared queue; queued
is not acknowledged or implemented. With no observed active pickup, only the
reopened browser was closed, and its process exit and closed port were verified.
Other browsers, the shared desktop, saved profiles and permanent owner account
were preserved. No additional account, chat, render or payment call occurred.

Related evidence: [original app login qualification](login-chat-release-20261011.md)
and [integration ownership](integration-handoff.md). Private central-owner and
app-attempt receipts remain outside the repository.
