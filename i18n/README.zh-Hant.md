[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*你的角色，日常的小表情。*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

獨立的貼圖創作工坊：可以欣賞阿芽與夥伴們的作品，也能建立自己的角色與貼圖系列。預設作品無需登入即可瀏覽，個人素材在私有工作區處理。既有 AYA 商店保持不變。

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

**2026-10-11** · https://westicker.lazying.art 已開放免登入訪客聊天。Characters（角色）位於 Library（作品庫）內，不再是獨立的主導覽入口。AgInTi 圖像生成（`nano-banana-2`）已通過真實服務商驗證並啟用；生成仍需帳號、授權同意及明確確認報價。

[2026-10-11 · 訪客聊天 / 導覽](../docs/clean-chat-release-20261011.md) · [AgInTi 圖像驗證](../docs/aginti-images.md) · [API / QA](../docs/chat-studio-20261011.md)

![Chat studio](../docs/screenshots/chat-studio-web.png)

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

77 項後端測試與 2 項瀏覽器代理安全測試通過。真實瀏覽器完成訪客下載、照片上傳、角色確認、照片貼圖生成、文字審核、ZIP 匯出與帳號刪除，並檢查桌面及行動寬度。這不代表真實付款或模型服務已驗證。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 發布狀態

內部測試版本: [iOS 1.0 (10)、macOS 1.0 (8)、Android 1.0 (9)](../docs/native-guest-chat-20261011.md). 一次本機動畫試運行已通過，但面向公眾的動畫生成仍保持離線，等待服務生命週期驗證。第三方社群登入、原生 App 內購買及網頁付款仍停用，等待端到端驗證通過。

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
