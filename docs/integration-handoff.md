# Independent account and payments handoff

## Ownership

Canonical checkout: `WeSticker` beside the existing `LALACHAN` project.
Owned files are this repository only. Existing AYA storefront, EchoMind identity,
Bunko adapters, store releases and billing products were not modified.
No WeSticker OAuth client, subscription product or store record was created.

## Central LazyingArt account owner

Request a **new** public PKCE client/audience for WeSticker after its production
origin is assigned. The web callback is `<origin>/auth/lazyingart/callback`.
General signup must not require an EchoMind invitation; application entitlements
remain local to WeSticker. Preserve central ownership and other client records.

The existing central service is a custom PKCE protocol, not assumed OIDC:
`/.well-known/lazyingart-account`, `/account/authorize`, `/account/token`,
POST `/account/profile`. This adapter validates exact issuer/endpoints, S256,
state, one-use callback and verified subject. Its local session is capped to the
600-second token lifetime; it does not retain a refresh token. Confirm token
revocation/deletion contract and any confidential-client requirement before
enabling. Native system-browser callbacks and universal links remain to build.

Latest inspected central account receipt reported password login active and
Google/Apple/GitHub not yet activated there. Do not infer that WeSticker social
login is live because an unrelated app has a login button.

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

Create three monthly USD products/prices for Pocket99c, Creator999c, Studio2499c.
Configure keys privately and set `stripe_prices` by tier ID. No live price was
created; amounts in source are proposed and must match provider records.
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
This implementation **does not contain native IAP**; Stripe buttons are disabled
in native shells. Do not enable them as a shortcut. Native sign-in and download
permissions also need physical-device tests. No submission has occurred.

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
