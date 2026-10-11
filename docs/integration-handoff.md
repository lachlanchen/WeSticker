# Independent account and payments handoff

## Ownership

Canonical checkout: `WeSticker` beside the existing `LALACHAN` project.
Owned files are this repository only. Existing AYA storefront, EchoMind identity,
Bunko adapters, store releases and billing products were not modified.
Independent Apple and Google app records now exist. WeSticker Stripe test-mode
prices were provisioned without any customer charge. Provider identifiers and
receipts are private. Native catalog betas have now been uploaded; their exact
distribution status is in [release readiness](release-readiness.md).

## Central LazyingArt account owner

Client/audience `westicker` is registered on the live issuer and its exact callback
`https://westicker.lazying.art/auth/lazyingart/callback` is qualified and enabled.
The separate domain is deployed. The actual password signup/consent/callback,
native S256 return, cancellation, replay, logout and account deletion were tested
with one exact disposable account. See the [current release](login-chat-release-20261011.md).
Preserve this registration; do not create another client from an older handoff.
General signup must not require an EchoMind invitation; application entitlements
remain local to WeSticker. Preserve central ownership and other client records.

The central service is a custom PKCE protocol, not assumed OIDC. The app uses its
pinned maintained SDK for discovery, S256, browser-bound one-use state, subject
validation, encrypted token storage, serialized refresh and revocation. Native
system-browser login uses an independent one-use verifier and fixed callback;
no token is carried in the URL. Account deletion revokes every app-bound session
for that subject before SDK erasure and local deletion. Native purchases remain
independent of identity.

Current central discovery reports password, Google and Apple enabled; GitHub
remains disabled. Google has also passed the actual WeSticker round trip.
Apple reached an existing-account collision and needs explicit dual-proof linking.
The provider selector contract remains issuer-owned work. See
[dated provider evidence](social-auth-qualification-20261011.md); central enablement
alone does not qualify an app login button.

## Direct web providers

Each `providers.<name>` object uses `enabled`, `client_id`, `client_secret`.
Google and Apple use issuer discovery; GitHub uses its OAuth code exchange.
LazyingArt instead uses `issuer`, `client_id`, `audience`, `enabled`.
Register exact callbacks `/auth/google/callback`, `/auth/apple/callback`,
`/auth/github/callback` under WeSticker's own origin. Apple needs an independent
Services ID, domain verification and expiring signed client secret. Never copy
another app's secret, bundle identity or redirect URI without its owner's plan.

Before enablement test successful/cancelled login, state/nonce mismatch, replay,
expiry, fresh creator consent, logout, deletion and provider revoke behavior.
Existing local demo accounts are not automatically merged with social users.

## Stripe web pilot

Three monthly USD test-mode prices exist: Pocket99c, Creator999c, Studio2499c.
`scripts/provision_stripe.py` reconciles app-owned products and prices using
stable lookup/idempotency keys. It checks the expected merchant account, mode,
currency, period and amount before reuse; it creates no customer or charge.
Configure keys privately and set `stripe_prices` by tier ID. No live price was
created; production amounts remain proposed and must match provider records.
Webhook: POST `/api/billing/webhook`. Deliver invoice.paid,
customer.subscription.deleted, checkout.session.completed,
checkout.session.async_payment_succeeded, checkout.session.expired and
charge.refunded. Match exact event support in the pinned adapter before launch.

Connect Express onboarding, payouts and destination charges are separate from
subscription revenue. A verified buyer session, creator account, amount,
currency and app metadata must agree. Client success redirects grant nothing.
Full refunds revoke pack entitlements; partial refunds and disputes need an
operator policy and more tests. Configure the customer portal to prevent
unqualified proration/upgrade behavior until the lifecycle matrix passes.

Complete the Stripe sandbox matrix: new/duplicate/abandoned checkout, delayed
webhooks, renewal, failed payment, plan change, cancel/re-subscribe, replay,
refund, dispute, expired Connect onboarding and account deletion. HMAC fixture
tests in this repository are not a substitute for real test-mode checkout.

## Native stores

Use independent bundle/package `art.lazying.westicker` and store records. Apple
and Google digital-service purchases need qualified native IAP, server-verified
receipts, restore purchases, subscription management and store notifications.
Native StoreKit 2 and Play Billing bridges, a separate native plans UI and fresh
server verification now exist; see [native billing](native-billing.md).
Purchases remain disabled until actual store lifecycle tests pass. Stripe
checkout remains unavailable in native builds. Native SwiftUI and Compose now
include purchase/restore contracts and system-browser login with independent PKCE;
the old Capacitor bridge is historical, not the current host. Current internal
builds and their exact runtime test scope are recorded in
[native delivery](native-protected-create-20261011.md). Provider purchase lifecycle
tests remain necessary before enabling subscriptions.

## Sources checked

- [Apple review guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [Apple account deletion](https://developer.apple.com/support/offering-account-deletion-in-your-app/)
- [Google generative AI policy](https://support.google.com/googleplay/android-developer/answer/14094294?hl=en-EN)
- [Google payments policy](https://support.google.com/googleplay/android-developer/answer/10281818?hl=en)
- [Stripe subscription webhooks](https://docs.stripe.com/billing/subscriptions/webhooks)
- [Stripe Connect destination charges](https://docs.stripe.com/connect/destination-charges)
- [WeChat live sticker platform](https://sticker.weixin.qq.com/)

Policies and live forms are release-time authorities. Recheck them before store
submission rather than treating this handoff as permanent legal guidance.
