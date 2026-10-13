[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner — apps and four buddies](https://github.com/lachlanchen/LazyingArtWebsite/raw/main/media/brand/lazyingart-intro.gif)](https://lazying.art)

# WeSticker

*Deine Figur. Kleine Gefühle für jeden Tag.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Ein unabhängiges Sticker-Studio für Aya und Freunde, eigene Figuren und Creator-Sammlungen. Standardmotive sind ohne Anmeldung sichtbar; persönliche Fotos bleiben im privaten Arbeitsbereich. Der bestehende AYA-Shop wird nicht verändert.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android](../docs/screenshots/native-android.png) | ![Native iOS](../docs/screenshots/animated-catalog-ios.png) |

[Native beta scope](../docs/native-catalog-beta.md) · [Creator roadmap](../docs/native-creator-plan.md) · [Bandwidth](../docs/catalog-bandwidth.md)

[Create / Agent beta update · 2026-10-10](../docs/creator-beta-20261010.md) · [Japanese LINE editions](../docs/line-japanese-editions.md)

[GIF playback, new icon and test-build evidence](../docs/native-playback-20261010.md)

**2026-10-11** · Sticker lassen sich ohne Anmeldung ansehen. Create öffnet eine separate Anmeldung und anschließend einen aufgeräumten Chat. Figuren und Referenzen liegen in Library; Account ist der letzte Tab.

[2026-10-11 · Public stickers / protected Create](../docs/protected-create-release-20261011.md) · [Native test builds](../docs/native-protected-create-20261011.md) · [Login qualification](../docs/social-auth-qualification-20261011.md) · [AgInTi qualification](../docs/aginti-images.md)

[2026-10-12 · Completion ledger](../docs/request-completion-ledger.md) · [Compact native builds](../docs/compact-native-release-20261012.md) · [Web subscription evidence](../docs/stripe-qualification.md)

![Chat studio](../docs/screenshots/compact-create-desktop.png)

<img src="../docs/screenshots/compact-create-ios.png" alt="Native iOS Create layout, authenticated test fixture" width="280">

[Native layout test scope](../docs/native-compact-toolbar-20261012.md)

## Das Studio

- 10 Pakete, 156 eigenständige Animationen, chinesische, englische und japanische Beschriftungen mit sofortiger Vorschau.
- Private Fotos, wiederverwendbare bestätigte Figuren, tarifabhängige Entwürfe, bearbeitbare Texte, Einzelprüfung und ZIP-Export.
- Optionale Bilderzeugung, lokale Animation, Verkaufsprüfung und isolierter WeChat-Entwurfsupload. Der Assistent speichert nur Entwürfe und reicht nichts zur Prüfung ein.

## Tarife

Web-Monatsabos sind verfügbar: Pocket 0,99 USD / 3 Credits, Creator 9,99 USD / 40, Studio 24,99 USD / 120. Der Fotomodus ist kostenlos. Alle Tarife enthalten die ZIPs der Standardsammlungen in drei Beschriftungssprachen. Native Käufe und optionale Animations- und Uploaddienste werden getrennt qualifiziert.

## Lokal starten

Python 3.12+, Node 22+, CJK-Schrift und Chromium für Browsertests. Das Skript erstellt eine private Demo-Konfiguration ohne fremde App-Zugangsdaten. http://127.0.0.1:18642 öffnen; mit `python3 scripts/dev.py stop` beenden.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## Aufbau

Native Android-App mit Kotlin/Jetpack Compose, iOS/macOS mit SwiftUI und separate React/Vite-PWA. Der private Erstellungsprototyp nutzt Python und SQLite. Oberfläche Englisch; Stickertexte Chinesisch, Englisch und Japanisch.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## Prüfung

Tests prüfen öffentliches Stöbern, geschützten Chat, Anmelderückkehr, abgelaufene Sitzungen, Referenzen, Freigabe und Export. Native Nachweise werden separat dokumentiert.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Veröffentlichungsstand

Interne Creator-Beta mit aktiven Web-Abos, kein vollständig abgeschlossener kommerzieller Release. Passwort-, Google- und Apple-Anmeldung über LazyingArt sowie AgInTi-Bilderzeugung sind geprüft. GitHub, direkte Anbieterauswahl, native Käufe, öffentliche Animation, Creator-Verkäufe und nutzerisolierte WeChat-Uploads werden weiterhin im Aufgabenregister verfolgt.

## Zitieren

Code unter MIT; Bildmaterial mit eigenen Rechten. Bei wissenschaftlicher Nutzung bitte dieses Repository zitieren. [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
