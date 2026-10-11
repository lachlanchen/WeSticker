[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Votre personnage, vos petites expressions du quotidien.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Un studio indépendant pour Aya et ses amis, vos personnages et vos collections. Les créations par défaut sont visibles sans connexion ; les photos personnelles restent dans un espace privé. La boutique AYA existante est inchangée.

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

**2026-10-11** · Consultez les stickers sans connexion. Create ouvre une connexion distincte, puis un chat épuré. Personnages et références sont dans Library ; Account est le dernier onglet.

[2026-10-11 · Public stickers / protected Create](../docs/protected-create-release-20261011.md) · [Native test builds](../docs/native-protected-create-20261011.md) · [Login qualification](../docs/social-auth-qualification-20261011.md) · [AgInTi qualification](../docs/aginti-images.md)

[2026-10-12 · Completion ledger](../docs/request-completion-ledger.md) · [Compact native builds](../docs/compact-native-release-20261012.md) · [Web subscription evidence](../docs/stripe-qualification.md)

![Chat studio](../docs/screenshots/compact-create-desktop.png)

## Le studio

- 10 collections, 156 animations distinctes, versions chinoise, anglaise et japonaise avec aperçu immédiat.
- Photos privées, personnages validés réutilisables, brouillons limités par formule, textes modifiables, validation individuelle et export ZIP.
- Génération d’images, animation locale, examen des ventes et envoi de brouillons WeChat isolé en option. L’assistant enregistre seulement les brouillons, sans soumettre à examen.

## Formules

Les abonnements web mensuels sont disponibles : Pocket 0,99 USD / 3 crédits, Creator 9,99 USD / 40, Studio 24,99 USD / 120. Le mode photo est gratuit. Les formules incluent les ZIP des collections par défaut dans les trois langues. Les achats natifs et les services facultatifs d’animation et d’envoi sont validés séparément.

## Exécution locale

Python 3.12+, Node 22+, police CJK et Chromium pour les tests navigateur. Le script crée une configuration de démonstration privée, sans emprunter les identifiants d’une autre application. Ouvrez http://127.0.0.1:18642. Arrêtez avec `python3 scripts/dev.py stop`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## Architecture

Android natif en Kotlin/Jetpack Compose, iOS/macOS en SwiftUI et PWA séparée en React/Vite. Le prototype privé de création utilise Python et SQLite. Interface anglaise, textes des stickers en chinois, anglais et japonais.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## Vérification

Les tests couvrent consultation publique, chat protégé, retour de connexion, expiration, références, validation et export. Les preuves natives sont documentées séparément.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## État de publication

Bêta interne de création avec abonnements web actifs, et non lancement commercial complet. Les connexions par mot de passe, Google et Apple via LazyingArt et la génération AgInTi sont vérifiées. GitHub, la sélection directe du fournisseur, les achats natifs, l’animation publique, les ventes de créateurs et les envois WeChat isolés par utilisateur restent suivis dans le registre d’achèvement.

## Citation

Code sous MIT ; illustrations sous droits distincts. Citez ce dépôt pour un usage scientifique. [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
