[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*你的角色，日常的小表情。*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Local_prototype-ED477A)](../docs/release-readiness.md) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

獨立的貼圖創作工坊：可以欣賞阿芽與夥伴們的作品，也能建立自己的角色與貼圖系列。預設作品無需登入即可瀏覽，個人素材在私有工作區處理。既有 AYA 商店保持不變。

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

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

React/Vite 前端、Python API 與工作程序、SQLite 資料庫、Capacitor Android/iOS 工程及 Mac Catalyst 設定。原始碼與私有執行資料分離。目前應用介面為英文，貼圖文字支援三種語言。

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `ios/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## 驗證結果

27 項後端測試與 2 項瀏覽器代理安全測試通過。真實瀏覽器完成訪客下載、照片上傳、角色確認、照片貼圖生成、文字審核、ZIP 匯出與帳號刪除，並檢查桌面及行動寬度。這不代表真實付款或模型服務已驗證。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 發布狀態

目前是可執行的本機原型，並非已上線服務。Android 偵錯 APK 已編譯，iOS/macOS 工程尚未建置。原生內購、正式登入付款驗證、生產審核營運及商店提交仍待完成。沒有向用戶收費，也沒有發布商店版本。

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
