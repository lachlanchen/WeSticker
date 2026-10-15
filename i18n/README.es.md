[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner — apps and four buddies](https://lazying.art/media/brand/lazyingart-intro.gif)](https://lazying.art)

# WeSticker

*Tu personaje. Tus expresiones de cada día.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Un estudio independiente para Aya y sus amigos, personajes personales y colecciones de creadores. Las obras predeterminadas se ven sin iniciar sesión; las fotos personales se procesan en privado. La tienda AYA existente no cambia.

<!-- support:start -->
[![GitHub Sponsors](https://img.shields.io/badge/GitHub-Sponsors-EA4AAA?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/lachlanchen)
[![LazyingArt Support](https://img.shields.io/badge/LazyingArt-Support-0EA5E9?style=for-the-badge)](https://chat.lazying.art/donate)
[![PayPal Support](https://img.shields.io/badge/PayPal-Support-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen)
[![Stripe Support](https://img.shields.io/badge/Stripe-Support-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400)
<!-- support:end -->

![WeSticker](../docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android](../docs/screenshots/native-android.png) | ![Native iOS](../docs/screenshots/animated-catalog-ios.png) |

[Native beta scope](../docs/native-catalog-beta.md) · [Creator roadmap](../docs/native-creator-plan.md) · [Bandwidth](../docs/catalog-bandwidth.md)

[Create / Agent beta update · 2026-10-10](../docs/creator-beta-20261010.md) · [Japanese LINE editions](../docs/line-japanese-editions.md)

[GIF playback, new icon and test-build evidence](../docs/native-playback-20261010.md)

**2026-10-11** · Explora stickers sin iniciar sesión. Create abre un acceso independiente y después un chat limpio. Los personajes y referencias están en Library; Account es la última pestaña.

[2026-10-11 · Public stickers / protected Create](../docs/protected-create-release-20261011.md) · [Native test builds](../docs/native-protected-create-20261011.md) · [Login qualification](../docs/social-auth-qualification-20261011.md) · [AgInTi qualification](../docs/aginti-images.md)

[2026-10-12 · Completion ledger](../docs/request-completion-ledger.md) · [Compact native builds](../docs/compact-native-release-20261012.md) · [Web subscription evidence](../docs/stripe-qualification.md)

![Chat studio](../docs/screenshots/compact-create-desktop.png)

<img src="../docs/screenshots/compact-create-ios.png" alt="Native iOS Create layout, authenticated test fixture" width="280">

[Native layout test scope](../docs/native-compact-toolbar-20261012.md)

## El estudio

- 10 paquetes, 156 animaciones distintas y versiones en chino, inglés y japonés con vista previa inmediata.
- Fotos privadas, personajes aprobados reutilizables, borradores limitados por plan, textos editables, aprobación individual y exportación ZIP.
- Generación de imágenes, animación local, revisión de ventas y carga aislada de borradores WeChat opcionales. El asistente guarda borradores; nunca los envía a revisión.

## Planes

Las suscripciones web mensuales están activas: Pocket 0,99 USD / 3 créditos, Creator 9,99 USD / 40, Studio 24,99 USD / 120. El modo foto es gratuito. Los planes incluyen los ZIP de las colecciones predeterminadas en los tres idiomas. Las compras nativas y los servicios opcionales de animación y carga se validan por separado.

## Ejecución local

Python 3.12+, Node 22+, fuente CJK y Chromium para pruebas. El script crea una configuración privada de demostración sin reutilizar credenciales ajenas. Abre http://127.0.0.1:18642. Detén con `python3 scripts/dev.py stop`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## Estructura

Android nativo con Kotlin/Jetpack Compose, iOS/macOS con SwiftUI y PWA separada con React/Vite. El prototipo privado de creación usa Python y SQLite. Interfaz en inglés; textos en chino, inglés y japonés.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## Verificación

Las pruebas cubren exploración pública, chat protegido, regreso tras el acceso, sesiones caducadas, referencias, revisión y exportación. La evidencia nativa se documenta por separado.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Estado de publicación

Beta interna de creación con suscripciones web activas, no un lanzamiento comercial completo. Se verificaron el acceso por contraseña, Google y Apple mediante LazyingArt y la generación AgInTi. GitHub, la selección directa del proveedor, las compras nativas, la animación pública, las ventas de creadores y las cargas WeChat aisladas por usuario siguen en el registro de tareas.

## Cita

Código MIT; ilustraciones con derechos separados. Cita el repositorio si lo usas en investigación. [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
