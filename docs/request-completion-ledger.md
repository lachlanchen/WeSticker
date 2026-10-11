# WeSticker Request Completion Ledger

Updated 2026-10-12. This is the current app request audit, not a claim that all
historical LALACHAN media jobs need to run again. Provider receipts, credentials,
customer content and runtime addresses remain in private handoffs.

| Owner requirement | Verified state | Work still required |
| --- | --- | --- |
| Default stickers visible without login | Live public catalog, 10 packs and 156 animations; three lettering languages | Preserve public access during creator changes |
| Compact pack list with GIFs immediately visible | Implemented and browser-tested; native GIF play/pause/resume pixel checks passed; compact PWA headers deployed | Native compact-header verification |
| Independent app and PWA | Independent HTTPS origin; native SwiftUI iOS/macOS and Compose Android | Keep platform parity; no WebView replacement |
| Test-build delivery | Android 12 internal; iOS 13 and macOS 10 in internal TestFlight | One cumulative successor after current changes qualify |
| One root login outside tabs | Implemented on web and native; intended destination and draft preserved | Retest after provider completion |
| Google, Apple, GitHub and LazyingArt login | LazyingArt and Google-through-LazyingArt verified end to end | Central Apple existing-account linking and GitHub/provider routing qualification |
| Create and Agent merged into chat | Conversation-first Create, references, editable revisioned sticker plan and explicit application | Keep chat uncluttered and complete real render delivery tests |
| Characters and generated work in Library | Account-scoped characters, references, collections and artifacts implemented | Ongoing cross-platform regression checks |
| Free single generation and bounded paid packs | Server tier limits and one-image trial; quote/idempotency guards implemented | Verify actual subscription-delivered limits on each payment lane |
| Real image generation | AgInTi real-provider canary passed; enabled | Preserve reference identity and per-user consent |
| Real animated sticker generation | Local provider canary passed | Qualify available runtime lifecycle before public activation |
| Web subscription payments | Live app-owned catalog/Portal/webhook and recovery timer active; web subscriptions enabled after actual sandbox lifecycle and live nonfinancial delivery tests | Ongoing monitoring; native IAP and advanced plan changes remain separate |
| Native subscriptions | StoreKit/Play UI and server verification implemented; fixtures passed | Real app-specific store setup, purchase/restore/lifecycle qualification |
| User-created packs for sale | Moderation and payout gates implemented | Verified creator onboarding and commercial operations before enabling sales |
| Optional WeChat draft uploader | Save-only safety contracts implemented | Customer-isolated browser/container lifecycle and live draft qualification |
| Clean, lively tab layouts | Compact PWA top-left headers, restrained motion and reviewed mobile/desktop screenshots deployed | Native cumulative candidate |
| Multilingual app | Three sticker-lettering languages; English interface | Interface localization remains distinct from 11-language README documentation |
| Commit, push, evidence and handoff | Previous verified source and release receipts retained | Update with each completed tested change; never label fixtures as live purchases |

## Completion Rules

- Inspect source, deployed behavior and provider receipts separately.
- Keep public catalog and already-working accounts available during changes.
- Share identity through the maintained issuer; app subscriptions remain app-owned.
- Preserve existing artifacts and submitted builds. A new build is distributed
  only after its cumulative feature set and relevant regression checks pass.
- Store review, a configured product, and successful payment delivery are
  different milestones. Record the actual state rather than substituting one.

## Evidence Index

- [Current release readiness](release-readiness.md)
- [Native test-build delivery](native-protected-create-20261011.md)
- [Social login qualification](social-auth-qualification-20261011.md)
- [Stripe qualification](stripe-qualification.md)
- [Chat-led studio](chat-studio-20261011.md)
- [Compact workspace evidence](compact-workspace-20261012.md)
