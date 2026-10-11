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

**2026-10-11** · https://westicker.lazying.art 已开放免登录访客聊天。Characters（角色）位于 Library（作品库）内，不再是独立的主导航入口。AgInTi 图像生成（`nano-banana-2`）已通过真实服务商验证并启用；生成仍需账号、授权同意和明确确认报价。

[2026-10-11 · 访客聊天 / 导航](../docs/clean-chat-release-20261011.md) · [AgInTi 图像验证](../docs/aginti-images.md) · [API / QA](../docs/chat-studio-20261011.md)

![Chat studio](../docs/screenshots/chat-studio-web.png)

## 创作工坊

- 10 套默认作品、156 个独立动画，中英日三种文字版本，打开即可预览。
- 私有照片上传、可复用的锁定角色、8 张表情草稿、逐张改字与确认，最后导出 ZIP。
- 可选图像生成、本地动画、创作者销售审核和隔离的微信草稿上传。助手只保存草稿，不提交审核。

## 订阅方案

月费拟定为 Pocket $0.99 / 3 图像额度、Creator $9.99 / 40 额度、Studio $24.99 / 120 额度及可选上传助手。照片模式免费，动画消耗 3 额度。支付接入与验证之前不开放收费。

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

77 项后端测试及 2 项浏览器代理安全测试通过。真实浏览器完成访客下载、照片上传、角色确认、照片表情生成、文字审核、ZIP 导出和账号删除，并检查桌面与移动宽度。这不代表真实支付或模型服务已经验证。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 发布状态

内部测试版本: [iOS 1.0 (10)、macOS 1.0 (8)、Android 1.0 (9)](../docs/native-guest-chat-20261011.md). 一次本地动画试运行已通过，但面向公众的动画生成仍保持离线，等待服务生命周期验证。第三方社交登录、原生应用内购买和网页支付仍禁用，等待端到端验证通过。

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
