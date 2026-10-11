[English](README.md) · [العربية](i18n/README.ar.md) · [Español](i18n/README.es.md) · [Français](i18n/README.fr.md) · [日本語](i18n/README.ja.md) · [한국어](i18n/README.ko.md) · [Tiếng Việt](i18n/README.vi.md) · [中文 (简体)](i18n/README.zh-Hans.md) · [中文（繁體）](i18n/README.zh-Hant.md) · [Deutsch](i18n/README.de.md) · [Русский](i18n/README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Your character. Everyday expressions.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

An independent sticker studio for Aya and friends, personal characters and creator collections. Browse the default artwork without signing in; use a private workspace to prepare your own. The existing AYA shop is unchanged.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android](docs/screenshots/native-android.png) | ![Native iOS](docs/screenshots/animated-catalog-ios.png) |

[Native beta scope](docs/native-catalog-beta.md) · [Creator roadmap](docs/native-creator-plan.md) · [Bandwidth](docs/catalog-bandwidth.md)

[Create / Agent beta update · 2026-10-10](docs/creator-beta-20261010.md) · [Japanese LINE editions](docs/line-japanese-editions.md)

[GIF playback, new icon and test-build evidence](docs/native-playback-20261010.md)

**2026-10-11** · LazyingArt password sign-in and chat-first creation are live at https://westicker.lazying.art. Start a conversation, add references later and review editable sticker plans. Internal test builds: iOS 1.0 (7), macOS 1.0 (6), Android 1.0 (7). Social-provider login, AI image/animation rendering and payments are not yet enabled.

[2026-10-11 · Login / chat / test builds](docs/login-chat-release-20261011.md) · [API / QA](docs/chat-studio-20261011.md)

![Chat studio](docs/screenshots/chat-studio-web.png)

## The Studio

- 10 default packs, 156 animations, Chinese/English/Japanese sticker versions and instant previews.
- Private photo uploads, a reusable locked character, eight-expression drafts, editable captions, individual approval and ZIP export.
- Optional image generation, local animation, creator sales review and isolated WeChat draft uploads. The assistant saves drafts; it never submits review.

## Plans

Proposed monthly subscriptions: Pocket $0.99 / 3 image credits; Creator $9.99 / 40 credits; Studio $24.99 / 120 credits and optional upload assistance. Photo mode is free; animation uses 3 credits. Billing is disabled until connected and qualified.

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
| `android/`, `apple/`, `macos/` | [Release readiness](docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](docs/integration-handoff.md) |

## Verification

77 backend tests and two browser-agent safety tests pass. A real browser exercised guest download, upload, character approval, photo generation, caption review, ZIP export and deletion at desktop/mobile widths. These are not live payment or AI-provider tests.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Release Status

LazyingArt password sign-in and chat-first creation are live at https://westicker.lazying.art. Start a conversation, add references later and review editable sticker plans. Internal test builds: iOS 1.0 (7), macOS 1.0 (6), Android 1.0 (7). Social-provider login, AI image/animation rendering and payments are not yet enabled.

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
