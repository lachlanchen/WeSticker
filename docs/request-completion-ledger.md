# WeSticker Request Completion Ledger

Updated 2026-10-12. This is the current app request audit, not a claim that all
historical LALACHAN media jobs need to run again. Provider receipts, credentials,
customer content and runtime addresses remain in private handoffs.

| Owner requirement | Verified state | Work still required |
| --- | --- | --- |
| Default stickers visible without login | Live public catalog, 10 packs and 156 animations; three lettering languages | Preserve public access during creator changes |
| Compact pack list with GIFs immediately visible | Implemented and browser-tested; native GIF play/pause/resume pixel checks passed; compact PWA and native headers delivered | Full installed macOS window QA remains separate from its native GIF component test |
| Independent app and PWA | Independent HTTPS origin; native SwiftUI iOS/macOS and Compose Android | Keep platform parity; no WebView replacement |
| Test-build delivery | Android 15 available to internal testers after exact APK cumulative UI/GIF checks; iOS 14 and macOS 11 VALID and in internal TestFlight with compact toolbars | Ongoing service qualification, not public store approval |
| One root login outside tabs | Implemented on web and native; Android 14 fixes an actual callback cancellation defect and remains signed in after restart; Android 15 preserves the root route | Keep native system-browser and public web qualification distinct |
| Google, Apple, GitHub and LazyingArt login | All four selected web app callbacks passed with the original immutable account mapping, without a second central provider chooser; GitHub uses explicit dual-proof linking | Each native system-browser provider path remains a separate qualification, not inferred from web results |
| Create and Agent merged into chat | Conversation-first Create, references, editable revisioned sticker plan and explicit application | Keep chat uncluttered and complete real render delivery tests |
| Characters and generated work in Library | Account-scoped characters, references, collections and artifacts implemented | Ongoing cross-platform regression checks |
| Free single generation and bounded paid packs | Server tier limits and one-image trial; quote/idempotency guards implemented | Verify actual subscription-delivered limits on each payment lane |
| Real image generation | AgInTi real-provider canary passed; enabled | Preserve reference identity and per-user consent |
| Real animated sticker generation | Two real sequential items passed the managed start, unload, drain and stop lifecycle; enabled on the live service | Prompt/visual acceptance remains per result; the canary is not a publication-ready pack |
| Web subscription payments | Live app-owned catalog/Portal/webhook and recovery timer active; web subscriptions enabled after actual sandbox lifecycle and live nonfinancial delivery tests | Ongoing monitoring; native IAP and advanced plan changes remain separate |
| Subscriber default sticker downloads | Deployed app-owned access routing; all three language ZIPs, guest/expiry and network errors tested; 30 production archives pass CRC checks; live mobile login route verified | Keep AYA orders independent |
| Native subscriptions | Google Play no-charge purchase, restart, restore, real renewal, cancellation, paid-through access and expiry verified; one grant per period. Apple signed Sandbox TEST delivery succeeded | Apple native product/purchase qualification and production API authorization; broader native sales remain closed. TEST is not a purchase |
| User-created packs for sale | Moderation and payout gates implemented | Verified creator onboarding and commercial operations before enabling sales |
| Optional WeChat draft uploader | Save-only safety contracts implemented | Customer-isolated browser/container lifecycle and live draft qualification |
| Clean, lively tab layouts | Compact top-left headers, restrained motion and reviewed PWA/Android/iOS screenshots; exact Android APK and six iOS XCTest cases passed | Full installed macOS layout capture; preserve platform parity |
| Multilingual app | Three sticker-lettering languages; English interface | Interface localization remains distinct from 11-language README documentation |
| Commit, push, evidence and handoff | Previous verified source and release receipts retained | Update with each completed tested change; never label fixtures as live purchases |

The current checkout passes 458 backend tests, a production web build and isolated
chat/login browser checks. Android 15 also verifies current About copy, three
configured provider labels at capture time, local draft persistence, share and
GIF pixel changes (5 playing / 1 paused / 5 resumed). Provider visibility can
change through qualified service configuration without rebuilding the app.

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
- [Compact native successor](compact-native-release-20261012.md)
- [Social login qualification](social-auth-qualification-20261011.md)
- [Stripe qualification](stripe-qualification.md)
- [Subscriber collection downloads](subscriber-downloads-20261012.md)
- [Native payment qualification](native-billing-qualification-20261012.md)
- [Chat-led studio](chat-studio-20261011.md)
- [Compact workspace evidence](compact-workspace-20261012.md)
