[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Deine Figur. Kleine Gefühle für jeden Tag.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Local_prototype-ED477A)](../docs/release-readiness.md) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Ein unabhängiges Sticker-Studio für Aya und Freunde, eigene Figuren und Creator-Sammlungen. Standardmotive sind ohne Anmeldung sichtbar; persönliche Fotos bleiben im privaten Arbeitsbereich. Der bestehende AYA-Shop wird nicht verändert.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

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

React/Vite, Python-API und Worker, SQLite, Capacitor-Projekte für Android/iOS und Mac-Catalyst-Konfiguration. Quellcode und private Laufzeitdaten sind getrennt. Oberfläche derzeit Englisch, Stickertexte in drei Sprachen.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `ios/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## Prüfung

27 Backend- und zwei Agent-Sicherheitstests bestanden. Ein echter Browser prüfte Download, Upload, Figurenfreigabe, Fotogenerierung, Textprüfung, ZIP und Kontolöschung in Desktop- und Mobilbreiten. Keine Live-Zahlungs- oder KI-Anbietertests.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Veröffentlichungsstand

Funktionsfähiger lokaler Prototyp, kein veröffentlichter Dienst. Android-Debug-APK gebaut; iOS/macOS nicht gebaut. Native Käufe, OAuth-/Zahlungsqualifizierung, Produktionsmoderation und Store-Einreichung fehlen noch. Keine Kundenabbuchung oder Store-Veröffentlichung.

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
