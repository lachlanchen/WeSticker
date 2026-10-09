[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Votre personnage, vos petites expressions du quotidien.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Local_prototype-ED477A)](../docs/release-readiness.md) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Un studio indépendant pour Aya et ses amis, vos personnages et vos collections. Les créations par défaut sont visibles sans connexion ; les photos personnelles restent dans un espace privé. La boutique AYA existante est inchangée.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

## Le studio

- 10 collections, 156 animations distinctes, versions chinoise, anglaise et japonaise avec aperçu immédiat.
- Photos privées, personnage validé réutilisable, brouillons de huit expressions, textes modifiables, validation individuelle et export ZIP.
- Génération d’images, animation locale, examen des ventes et envoi de brouillons WeChat isolé en option. L’assistant enregistre seulement les brouillons, sans soumettre à examen.

## Formules

Abonnements mensuels proposés : Pocket 0,99 $ / 3 crédits image ; Creator 9,99 $ / 40 ; Studio 24,99 $ / 120 et assistance d’envoi facultative. Le mode photo est gratuit ; une animation coûte 3 crédits. Aucun paiement avant connexion et validation.

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

React/Vite, API et worker Python, SQLite, projets Capacitor Android/iOS et configuration Mac Catalyst. Code et données privées sont séparés. L’interface est actuellement anglaise ; les textes des stickers existent en trois langues.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `ios/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## Vérification

27 tests backend et deux tests de sécurité de l’agent passent. Un vrai navigateur a vérifié téléchargement, photos, validation du personnage, génération photo, révision, ZIP et suppression de compte aux tailles mobile et bureau. Ce ne sont pas des tests de paiement réel ou de fournisseur IA.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## État de publication

Prototype local fonctionnel, pas un service lancé. APK Android de débogage compilé ; iOS/macOS non compilés. Achats natifs, qualification OAuth/paiements, modération de production et soumission aux boutiques restent à faire. Aucun client facturé ni publication en boutique.

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
