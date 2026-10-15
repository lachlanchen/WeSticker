[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner — apps and four buddies](https://lazying.art/media/brand/lazyingart-intro.gif)](https://lazying.art)

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

**2026-10-11** · 貼圖瀏覽無需登入。Create 先進入獨立登入畫面，再返回簡潔的聊天。角色和參考素材放在 Library，Account 是最後一個標籤。

[2026-10-11 · Public stickers / protected Create](../docs/protected-create-release-20261011.md) · [Native test builds](../docs/native-protected-create-20261011.md) · [Login qualification](../docs/social-auth-qualification-20261011.md) · [AgInTi qualification](../docs/aginti-images.md)

[2026-10-12 · Completion ledger](../docs/request-completion-ledger.md) · [Compact native builds](../docs/compact-native-release-20261012.md) · [Web subscription evidence](../docs/stripe-qualification.md)

![Chat studio](../docs/screenshots/compact-create-desktop.png)

<img src="../docs/screenshots/compact-create-ios.png" alt="Native iOS Create layout, authenticated test fixture" width="280">

[Native layout test scope](../docs/native-compact-toolbar-20261012.md)

## 創作工坊

- 10 套預設作品、156 個獨立動畫，中英日三種文字版本，可直接預覽。
- 私有照片上傳、可重用的已確認角色、依方案限額的貼圖草稿、逐張改字與確認，最後匯出 ZIP。
- 可選影像生成、本機動畫、創作者銷售審核及隔離的微信草稿上傳。助手只儲存草稿，不提交審核。

## 訂閱方案

網頁月度訂閱已開放：Pocket $0.99 / 3 額度、Creator $9.99 / 40 額度、Studio $24.99 / 120 額度。照片模式免費，訂閱包含預設系列中英日三種文字版本的 ZIP。原生內購及可選動畫、上傳服務分別驗證。

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

後端與瀏覽器測試涵蓋公開瀏覽、受保護的聊天、登入返回、工作階段過期、參考素材、審核及匯出。原生版本證據另行記錄。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 發布狀態

目前為創作內部測試版，網頁訂閱已上線，並非完整商業發布。透過 LazyingArt 的密碼、Google 和 Apple 登入及 AgInTi 圖像生成已驗證。GitHub 與直接選擇供應商、原生內購、公開動畫、創作者銷售和使用者隔離的微信上傳仍列於完成清單。

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
