[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Ваш персонаж. Эмоции на каждый день.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Catalog_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://aya.lazying.art/westicker/) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Независимая студия стикеров Aya и друзей, личных персонажей и авторских наборов. Стандартные работы доступны без входа; личные фотографии обрабатываются в закрытой рабочей области. Существующий магазин AYA не изменён.

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

## Студия

- 10 наборов, 156 отдельных анимаций, китайские, английские и японские подписи с быстрым просмотром.
- Закрытая загрузка фото, повторно используемый подтверждённый персонаж, восемь эмоций, редактирование текста, проверка каждого стикера и ZIP.
- Опциональные генерация изображений, локальная анимация, проверка продаж и изолированная загрузка черновиков WeChat. Помощник только сохраняет черновик, не отправляя его на модерацию.

## Тарифы

Предлагаемые месячные тарифы: Pocket $0.99 / 3 кредита изображений; Creator $9.99 / 40; Studio $24.99 / 120 и дополнительная помощь с загрузкой. Фоторежим бесплатен, анимация стоит 3 кредита. Оплата отключена до подключения и проверки.

## Локальный запуск

Нужны Python 3.12+, Node 22+, шрифт CJK и Chromium для тестов. Скрипт создаёт закрытые настройки демо без чужих учётных данных. Откройте http://127.0.0.1:18642; остановка: `python3 scripts/dev.py stop`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## Архитектура

Нативный Android на Kotlin/Jetpack Compose, iOS/macOS на SwiftUI и отдельная PWA на React/Vite. Закрытый прототип создания использует Python и SQLite. Интерфейс английский; тексты стикеров на китайском, английском и японском.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## Проверки

Пройдены 46 серверных тестов и два теста безопасности агента. Реальный браузер проверил скачивание, загрузку фото, подтверждение персонажа, фоторежим, тексты, ZIP и удаление аккаунта на мобильной и настольной ширине. Это не проверка реальной оплаты или AI-сервиса.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Статус выпуска

Публичная PWA каталога доступна: https://aya.lazying.art/westicker/. Нативные версии предназначены для внутренних тестов Google Play и Apple TestFlight; точный статус и ограничения указаны в журнале выпуска. Создание с ИИ, вход, подписки и продажи в этих бета-версиях отключены.

## Цитирование

Код MIT; права на изображения отдельные. При исследовательском использовании ссылайтесь на репозиторий. [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
