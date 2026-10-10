[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*你的角色，日常的小表情。*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Catalog_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://aya.lazying.art/westicker/) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

獨立的貼圖創作工坊：可以欣賞阿芽與夥伴們的作品，也能建立自己的角色與貼圖系列。預設作品無需登入即可瀏覽，個人素材在私有工作區處理。既有 AYA 商店保持不變。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android](../docs/screenshots/native-android.png) | ![Native iOS](../docs/screenshots/native-ios.png) |

[Native beta scope](../docs/native-catalog-beta.md) · [Creator roadmap](../docs/native-creator-plan.md) · [Bandwidth](../docs/catalog-bandwidth.md)

[Create / Agent beta update · 2026-10-10](../docs/creator-beta-20261010.md) · [Japanese LINE editions](../docs/line-japanese-editions.md)

## 創作工坊

- 10 套預設作品、156 個獨立動畫，中英日三種文字版本，可直接預覽。
- 私有照片上傳、可重用的鎖定角色、8 張貼圖草稿、逐張改字與確認，最後匯出 ZIP。
- 可選影像生成、本機動畫、創作者銷售審核及隔離的微信草稿上傳。助手只儲存草稿，不提交審核。

## 訂閱方案

月費擬定為 Pocket $0.99 / 3 影像額度、Creator $9.99 / 40 額度、Studio $24.99 / 120 額度及可選上傳助手。照片模式免費，動畫消耗 3 額度。付款串接與驗證之前不開放收費。

## 本機執行

需要 Python 3.12+、Node 22+、中日韓字型及瀏覽器測試用 Chromium。腳本只建立本專案的私有示範設定，不借用其他應用憑證。開啟 http://127.0.0.1:18642；以 `python3 scripts/dev.py stop` 停止。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## 專案結構

Android 使用原生 Kotlin/Jetpack Compose，iOS/macOS 使用 SwiftUI，PWA 獨立使用 React/Vite。私人創作原型使用 Python 和 SQLite。介面為英文，貼圖文字支援中英日三種語言。

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## 驗證結果

46 項後端測試與 2 項瀏覽器代理安全測試通過。真實瀏覽器完成訪客下載、照片上傳、角色確認、照片貼圖生成、文字審核、ZIP 匯出與帳號刪除，並檢查桌面及行動寬度。這不代表真實付款或模型服務已驗證。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 發布狀態

公開目錄 PWA 已上線：https://aya.lazying.art/westicker/。原生目錄版本用於 Google Play 內部測試與 Apple TestFlight，具體可用狀態及測試限制見發布紀錄。測試版尚未開放 AI 創作、登入、訂閱與創作者銷售，並非完整創作服務上線。

## 引用

原始碼採用 MIT 授權，角色及美術資產另行授權。研究中使用本軟體時請引用本倉庫。 [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
