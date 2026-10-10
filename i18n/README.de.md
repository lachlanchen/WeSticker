[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Deine Figur. Kleine Gefühle für jeden Tag.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Catalog_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://aya.lazying.art/westicker/) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Ein unabhängiges Sticker-Studio für Aya und Freunde, eigene Figuren und Creator-Sammlungen. Standardmotive sind ohne Anmeldung sichtbar; persönliche Fotos bleiben im privaten Arbeitsbereich. Der bestehende AYA-Shop wird nicht verändert.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android](../docs/screenshots/native-android.png) | ![Native iOS](../docs/screenshots/native-ios.png) |

[Native beta scope](../docs/native-catalog-beta.md) · [Creator roadmap](../docs/native-creator-plan.md) · [Bandwidth](../docs/catalog-bandwidth.md)

[Create / Agent beta update · 2026-10-10](../docs/creator-beta-20261010.md) · [Japanese LINE editions](../docs/line-japanese-editions.md)

## Das Studio

- 10 Pakete, 156 eigenständige Animationen, chinesische, englische und japanische Beschriftungen mit sofortiger Vorschau.
- Private Fotos, wiederverwendbare bestätigte Figur, acht Ausdrücke, bearbeitbare Texte, Einzelprüfung und ZIP-Export.
- Optionale Bilderzeugung, lokale Animation, Verkaufsprüfung und isolierter WeChat-Entwurfsupload. Der Assistent speichert nur Entwürfe und reicht nichts zur Prüfung ein.

## Tarife

Monatliche Preisvorschläge: Pocket 0,99 USD / 3 Bild-Credits; Creator 9,99 USD / 40; Studio 24,99 USD / 120 und optionaler Upload-Assistent. Fotomodus kostenlos, Animation 3 Credits. Abrechnung bleibt bis zur Anbindung und Prüfung deaktiviert.

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

46 Backend- und zwei Agent-Sicherheitstests bestanden. Ein echter Browser prüfte Download, Upload, Figurenfreigabe, Fotogenerierung, Textprüfung, ZIP und Kontolöschung in Desktop- und Mobilbreiten. Keine Live-Zahlungs- oder KI-Anbietertests.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Veröffentlichungsstand

Die öffentliche Katalog-PWA ist unter https://aya.lazying.art/westicker/ verfügbar. Native Katalogversionen sind für interne Google-Play-Tests und Apple TestFlight vorgesehen. Verfügbarkeit und Testgrenzen stehen im Release-Protokoll. KI-Erstellung, Anmeldung, Abonnements und Verkauf bleiben in diesen Betas deaktiviert.

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
