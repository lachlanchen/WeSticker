[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*你的角色，日常的小表情。*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

独立的表情创作工坊：可以欣赏阿芽与伙伴们的作品，也能创建自己的角色与表情系列。默认作品无需登录即可浏览，个人素材在私有工作区处理。已有 AYA 商店保持不变。

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

**2026-10-11** · 表情浏览无需登录。Create 先进入独立登录界面，再返回简洁的聊天。角色和参考素材放在 Library，Account 是最后一个标签。

[2026-10-11 · Public stickers / protected Create](../docs/protected-create-release-20261011.md) · [Native test builds](../docs/native-protected-create-20261011.md) · [Login qualification](../docs/social-auth-qualification-20261011.md) · [AgInTi qualification](../docs/aginti-images.md)

[2026-10-12 · Completion ledger](../docs/request-completion-ledger.md) · [Compact native builds](../docs/compact-native-release-20261012.md) · [Web subscription evidence](../docs/stripe-qualification.md)

![Chat studio](../docs/screenshots/compact-create-desktop.png)

<img src="../docs/screenshots/compact-create-ios.png" alt="Native iOS Create layout, authenticated test fixture" width="280">

[Native layout test scope](../docs/native-compact-toolbar-20261012.md)

## 创作工坊

- 10 套默认作品、156 个独立动画，中英日三种文字版本，打开即可预览。
- 私有照片上传、可复用的已确认角色、按方案限额的表情草稿、逐张改字与确认，最后导出 ZIP。
- 可选图像生成、本地动画、创作者销售审核和隔离的微信草稿上传。助手只保存草稿，不提交审核。

## 订阅方案

网页月度订阅已开放：Pocket $0.99 / 3 额度、Creator $9.99 / 40 额度、Studio $24.99 / 120 额度。照片模式免费，订阅包含默认系列中英日三种文字版本的 ZIP。原生内购及可选动画、上传服务分别验证。

## 本地运行

需要 Python 3.12+、Node 22+、中日韩字体及浏览器测试用 Chromium。脚本只生成本项目的私有演示配置，不借用其他应用凭据。打开 http://127.0.0.1:18642；用 `python3 scripts/dev.py stop` 停止。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## 项目结构

Android 使用原生 Kotlin/Jetpack Compose，iOS/macOS 使用 SwiftUI，PWA 独立使用 React/Vite。私有创作原型使用 Python 和 SQLite。界面为英文，表情文字支持中英日三种语言。

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## 验证结果

后端和浏览器测试覆盖公开浏览、受保护的聊天、登录返回、会话过期、参考素材、审核及导出。原生版本证据单独记录。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 发布状态

当前为创作内部测试版，网页订阅已上线，并非完整商业发布。通过 LazyingArt 的密码、Google 和 Apple 登录及 AgInTi 图像生成已验证。GitHub 与直接选择提供商、原生内购、公开动画、创作者销售和用户隔离的微信上传仍列在完成清单中。

## 引用

源代码采用 MIT 协议，角色及美术资产单独授权。研究中使用本软件时请引用本仓库。 [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
