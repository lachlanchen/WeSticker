# WeSticker architecture

WeSticker is a separate creator product, not a replacement for AYA. Its bundle
identifier is `art.lazying.westicker`. Never reuse AYA Stripe product IDs, customer
databases, WeChat cookies, store records, or browser profiles.

## Product loop

1. Guests browse ten approved Aya/Lala/Sasa/Zhuangzi collections, 156 distinct
   animations and 468 Chinese/English/Japanese lettering variants. Local posters
   load first; original GIFs load on demand from the existing public AYA service.
2. Adults accept terms and confirm image permissions. The service normalizes
   uploads, strips metadata, and creates an account-scoped character record.
3. The user confirms reference identity, names the collection, and chooses eight
   everyday expressions. Previously locked characters are reusable.
4. Photo mode produces captioned static stickers without an AI call. Configured
   AI mode creates one or more expressions from the references. The optional
   LocalVideoGen adapter animates an approved still. These modes are distinct;
   a photo export is never represented as an AI animation.
5. The user edits lettering and approves each result. Export contains individual
   stickers, cover, banner, icon, appreciation artwork and metadata. Format
   helpers are not a guarantee of WeChat approval; inspect the current live form.
6. Creator sales require separate public/commercial consent, verified Stripe
   Connect payout onboarding, and operator review of the frozen export. Buyers
   receive access only after a verified payment event.
7. Studio can prepare a WeChat upload ticket. A dedicated browser requires the
   customer's login. The agent uploads to an empty album and clicks Save only.
   The customer remains responsible for final review submission.

## Components

| Path | Responsibility |
| --- | --- |
| `src/` | React catalog, preview, studio, review, plans, marketplace and account |
| `public/catalog.json`, `public/previews/` | Curated public default art, no customer originals |
| `server/app.py`, `store.py` | API, ownership, sessions, CSRF, SQLite WAL and job reservations |
| `server/worker.py` | Single worker, photo/image jobs, preserved outputs, uncertain-state recovery |
| `server/local_video.py` | Protected local animation adapter with intent and provider receipt |
| `server/auth.py` | Disabled-until-configured OAuth and custom LazyingArt PKCE adapters |
| `server/billing.py`, `market_billing.py` | App-specific Stripe subscriptions and Connect marketplace |
| `server/native_billing.py`, `src/NativePlans.tsx` | Account-bound Apple/Google verification and native-only purchase UI |
| `server/market.py` | Frozen reviewed exports, preview and entitlement-gated ZIPs |
| `server/wechat.py`, `worker/` | Draft-only ticket and isolated browser agent |
| `android/` | Native Kotlin/Jetpack Compose catalog beta |
| `apple/`, `macos/` | Shared SwiftUI source with separate native iOS and macOS targets |
| `ios/`, `prototype/` | Preserved earlier Capacitor prototype and billing bridges; not distributed as current native apps |

The public `/westicker/` PWA and native beta expose only the approved catalog,
preview, favorites and individual GIF save/share. The creator product loop
above is the separate local web prototype and planned native expansion, not
an assertion that all seven steps are available in build 3. See the
[native creator plan](native-creator-plan.md).

## Proposed subscriptions

| Monthly tier | USD | Image credits | Character slots | Additional access |
| --- | ---: | ---: | ---: | --- |
| Pocket | 0.99 | 3 | 2 | Default language ZIPs, private photo/caption workspace |
| Creator | 9.99 | 40 | 25 | Animation adapter, creator sales application |
| Studio | 24.99 | 120 | 100 | Optional isolated WeChat draft-upload assistant |

Photo mode consumes no AI credits. An image costs one internal credit; an
animation costs three. Credits are reserved transactionally, reset on a verified
paid billing period and do not roll over. Unknown provider outcomes retain their
reservation until reconciled. Pricing is a proposal, not a live offer or a claim
of profitable unit economics. Measure provider costs before enabling sales.
Marketplace prices are $0.99-$99.99; the proposed platform share is 15% before
payment-provider costs/taxes. Stripe Connect availability varies by territory.

## Data and recovery

SQLite is suitable for a single-instance pilot. Use a shared transactional store,
durable task leases and per-tenant quotas before horizontal scaling. The current
worker runs one task at a time under a file lock; a restart marks interrupted
jobs uncertain instead of resubmitting chargeable work. Keep `data/` private.

Generated images, videos, source GIFs and job receipts are retained as versions.
References expire after 30 days, excluding active/uncertain work. Generated
derivatives and provider-side uploads have separate retention; the current
retention script does not erase those. Account deletion removes owned local
media and cancels owned web subscriptions, but currently requires active jobs
and browser sessions to be resolved first. An asynchronous deletion workflow
and provider-token revocation are release gates, not completed features.

Original photos, provider tokens, browser profiles and payment identifiers are
not included in public previews or Git. Public default artwork is licensed
separately from source code; see `ARTWORK-LICENSE.md`.

## Safety and operational limits

- Adult-only creator pilot, explicit likeness/rights consent, private references.
- AI moderation before external generation; report and block entry points.
- Identity keyed by verified issuer and subject, never merged by email alone.
- Signed payment webhooks with provider re-fetch, replay guards and refund
  revocation; a checkout redirect alone never grants downloads or quota.
- One browser container per customer, local-bound VNC and CDP, no host cookie
  mounts. Never expose raw VNC/CDP to the Internet.
- At least 24 GiB available RAM and at most 75% swap usage before a local model
  submission. Existing provider jobs can be inspected without starting another.
- No review-submit selector is present in the WeChat agent. Changed pages stop
  with evidence rather than guessing at buttons.

Native IAP bridges and server verification are implemented but sales-disabled;
renewal/refund notification reconciliation and real store qualification remain.
Not yet implemented: native OAuth return plumbing, translated app UI,
automated marketplace review, dispute/tax
operations, multi-tenant browser orchestration, full animation QA and version
history browsing. The README languages describe the product; they are not app
UI localization.
