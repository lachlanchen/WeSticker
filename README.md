[English](README.md) · [العربية](i18n/README.ar.md) · [Español](i18n/README.es.md) · [Français](i18n/README.fr.md) · [日本語](i18n/README.ja.md) · [한국어](i18n/README.ko.md) · [Tiếng Việt](i18n/README.vi.md) · [中文 (简体)](i18n/README.zh-Hans.md) · [中文（繁體）](i18n/README.zh-Hant.md) · [Deutsch](i18n/README.de.md) · [Русский](i18n/README.ru.md)

[![LazyingArt banner — apps and four buddies](https://lazying.art/media/brand/lazyingart-intro.gif)](https://lazying.art)

# WeSticker

*Your character. Everyday expressions.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

An independent sticker studio for Aya and friends, personal characters and creator collections. Browse the default artwork without signing in; use a private workspace to prepare your own. The existing AYA shop is unchanged.

<!-- support:start -->
[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsors-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)
[![LazyingArt Support](https://img.shields.io/badge/LazyingArt-Support-0EA5E9?style=for-the-badge)](https://chat.lazying.art/donate)
[![PayPal Support](https://img.shields.io/badge/PayPal-Support-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen)
[![Stripe Support](https://img.shields.io/badge/Stripe-Support-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400)
<!-- support:end -->

![WeSticker](docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android](docs/screenshots/native-android.png) | ![Native iOS](docs/screenshots/animated-catalog-ios.png) |

[Native beta scope](docs/native-catalog-beta.md) · [Creator roadmap](docs/native-creator-plan.md) · [Bandwidth](docs/catalog-bandwidth.md)

[Create / Agent beta update · 2026-10-10](docs/creator-beta-20261010.md) · [Japanese LINE editions](docs/line-japanese-editions.md)

[GIF playback, new icon and test-build evidence](docs/native-playback-20261010.md)

**2026-10-11** · Browse stickers without signing in. Create opens a separate sign-in screen, then a clean chat. Characters and references live in Library; Account is the last tab.

[2026-10-11 · Public stickers / protected Create](docs/protected-create-release-20261011.md) · [Native test builds](docs/native-protected-create-20261011.md) · [Login qualification](docs/social-auth-qualification-20261011.md) · [AgInTi qualification](docs/aginti-images.md)

[2026-10-12 · Completion ledger](docs/request-completion-ledger.md) · [Compact native builds](docs/compact-native-release-20261012.md) · [Web subscription evidence](docs/stripe-qualification.md)

![Chat studio](docs/screenshots/compact-create-desktop.png)

<img src="docs/screenshots/compact-create-ios.png" alt="Native iOS Create layout, authenticated test fixture" width="280">

[Native layout test scope](docs/native-compact-toolbar-20261012.md)

## The Studio

- 10 default packs, 156 animations, Chinese/English/Japanese sticker versions and instant previews.
- Private photo uploads, reusable approved characters, plan-limited drafts, editable captions, individual approval and ZIP export.
- Optional image generation, local animation, creator sales review and isolated WeChat draft uploads. The assistant saves drafts; it never submits review.

## Plans

Web monthly subscriptions are live: Pocket $0.99 / 3 credits, Creator $9.99 / 40 credits, Studio $24.99 / 120 credits. Photo mode is free. Plans include the default collection ZIPs in all three lettering languages. Native purchases and optional animation/upload services are qualified separately.

## Run Locally

Python 3.12+, Node 22+, a CJK font and Chromium for browser tests. The script creates a private local demo configuration; it does not borrow another app's credentials. Open http://127.0.0.1:18642. Stop with `python3 scripts/dev.py stop`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## Inside

Native Kotlin/Jetpack Compose Android and SwiftUI iOS/macOS catalog apps, plus a separate React/Vite PWA. The private creator prototype uses Python and SQLite. The interface is English; sticker lettering supports Chinese, English and Japanese.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](docs/deployment.md) |
| `agent/`, `compose.agent.yaml` | [AgInTi/DeepSeek chat and Docker](docs/agent-and-docker.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](docs/integration-handoff.md) |

## Verification

Backend and browser tests cover public browsing, protected chat, login return, expired sessions, references, review and export. Native build evidence is recorded separately.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Release Status

Internal-test creator beta with live web subscriptions, not a completed commercial release. Password, Google and Apple sign-in through LazyingArt and AgInTi image generation are verified. GitHub/direct-provider selection, native IAP, public animation, creator sales and customer-isolated WeChat uploads remain in the completion ledger.

## Citation

Code is MIT; artwork has separate rights. Cite this repository when using the software in research. [CITATION.cff](CITATION.cff) · [MIT](LICENSE) · [Artwork](ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
