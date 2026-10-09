[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Ваш персонаж. Эмоции на каждый день.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Local_prototype-ED477A)](../docs/release-readiness.md) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Независимая студия стикеров Aya и друзей, личных персонажей и авторских наборов. Стандартные работы доступны без входа; личные фотографии обрабатываются в закрытой рабочей области. Существующий магазин AYA не изменён.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

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

React/Vite, Python API и worker, SQLite, проекты Capacitor Android/iOS и настройки Mac Catalyst. Код отделён от закрытых данных. Интерфейс пока английский, тексты стикеров доступны на трёх языках.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `ios/` | [Release readiness](../docs/release-readiness.md) |
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

Рабочий локальный прототип, не запущенный сервис. Сборки Android debug и симулятора iOS проходят. Адаптеры встроенных покупок реализованы, но продажи отключены. Mac Catalyst заблокирован отсутствием нужных бинарных зависимостей. Созданы отдельные записи магазинов и тестовый каталог Stripe. Рабочий вход, жизненный цикл платежей, модерация и отправка в магазины ещё не проверены. Списаний и публикаций в магазинах не было.

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
