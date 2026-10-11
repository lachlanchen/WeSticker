[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Tu personaje. Tus expresiones de cada día.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Un estudio independiente para Aya y sus amigos, personajes personales y colecciones de creadores. Las obras predeterminadas se ven sin iniciar sesión; las fotos personales se procesan en privado. La tienda AYA existente no cambia.

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

**2026-10-11** · El chat de invitados está disponible en https://westicker.lazying.art sin iniciar sesión. Characters está dentro de Library, no como sección principal independiente. La generación de imágenes mediante AgInTi (`nano-banana-2`) superó la validación con el proveedor real y está habilitada; sigue requiriendo una cuenta, consentimiento y confirmación explícita del presupuesto.

[2026-10-11 · Chat de invitados / navegación](../docs/clean-chat-release-20261011.md) · [Validación de imágenes AgInTi](../docs/aginti-images.md) · [API / QA](../docs/chat-studio-20261011.md)

![Chat studio](../docs/screenshots/chat-studio-web.png)

## El estudio

- 10 paquetes, 156 animaciones distintas y versiones en chino, inglés y japonés con vista previa inmediata.
- Fotos privadas, personaje confirmado reutilizable, ocho expresiones, textos editables, aprobación individual y exportación ZIP.
- Generación de imágenes, animación local, revisión de ventas y carga aislada de borradores WeChat opcionales. El asistente guarda borradores; nunca los envía a revisión.

## Planes

Suscripciones mensuales propuestas: Pocket 0,99 USD / 3 créditos de imagen; Creator 9,99 USD / 40; Studio 24,99 USD / 120 y asistencia opcional. El modo foto es gratuito; una animación cuesta 3 créditos. Cobros desactivados hasta conectar y validar.

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

Pasan 77 pruebas backend y dos de seguridad del agente. Un navegador real verificó descarga, fotos, aprobación de personaje, generación fotográfica, textos, ZIP y eliminación de cuenta en tamaños móvil y escritorio. No son pruebas reales de pago ni del proveedor IA.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Estado de publicación

Compilaciones nativas candidatas de reemplazo: [iOS 1.0 (10), macOS 1.0 (8), Android 1.0 (9)](../docs/native-guest-chat-20261011.md). Su distribución no está confirmada hasta disponer de los comprobantes de procesamiento en las tiendas y de distribución interna. Una prueba piloto local de animación fue satisfactoria, pero la animación pública sigue fuera de servicio hasta validar el ciclo de vida del servicio. El inicio de sesión con proveedores sociales, las compras integradas en las aplicaciones nativas y los pagos web siguen deshabilitados hasta superar la validación de extremo a extremo.

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
