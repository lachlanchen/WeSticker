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

**2026-10-11** · Guest chat is live at https://westicker.lazying.art without signing in. Characters is inside Library, not a separate main destination. AgInTi image generation (`nano-banana-2`) passed real-provider qualification and is enabled; generation still requires an account, consent and explicit quote confirmation.

[2026-10-11 · Guest chat / navigation](docs/clean-chat-release-20261011.md) · [AgInTi image qualification](docs/aginti-images.md) · [API / QA](docs/chat-studio-20261011.md)

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

Backend and browser-agent safety tests pass. A real browser exercised guest download, upload, character approval, photo generation, caption review, ZIP export and deletion at desktop/mobile widths. These workflow checks are distinct from the real-provider evidence for [guest chat](docs/clean-chat-release-20261011.md) and [AgInTi images](docs/aginti-images.md); they do not qualify live payments or public animation.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Release Status

Replacement native build candidates: [iOS 1.0 (10), macOS 1.0 (8), Android 1.0 (9)](docs/native-guest-chat-20261011.md). Distribution is not confirmed until store-processing and internal distribution receipts are available. One local animation canary passed, but public animation remains offline pending service lifecycle qualification. Social-provider sign-in, native in-app purchases and web payments remain disabled pending end-to-end qualification.

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
