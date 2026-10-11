[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*あなたのキャラクターで、毎日の気持ちを。*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

阿芽と仲間たちの作品を楽しみ、自分だけのキャラクターとスタンプを作る独立したスタジオです。標準作品はログインなしで閲覧でき、個人素材は非公開の作業領域で扱います。既存の AYA ショップは変更していません。

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

**2026-10-11** · https://westicker.lazying.art でログイン不要のゲストチャットを利用できます。Characters は独立したメイン項目ではなく、Library 内にあります。AgInTi の画像生成（`nano-banana-2`）は実プロバイダーでの検証に合格し、有効になっています。生成には引き続きアカウント、同意、見積もりの明示的な確認が必要です。

[2026-10-11 · ゲストチャット / ナビゲーション](../docs/clean-chat-release-20261011.md) · [AgInTi 画像生成の検証](../docs/aginti-images.md) · [API / QA](../docs/chat-studio-20261011.md)

![Chat studio](../docs/screenshots/chat-studio-web.png)

## スタジオ

- 標準10パック、156種類のアニメーション、中国語・英語・日本語の文字版をすぐにプレビュー。
- 非公開の写真アップロード、再利用できる固定キャラクター、8種類の表情、文字編集、個別確認と ZIP 出力。
- 画像生成、ローカル動画化、販売審査、隔離ブラウザーでの WeChat 下書きアップロードは任意機能です。助手は下書き保存のみで、審査には提出しません。

## プラン

月額案は Pocket $0.99 / 画像3クレジット、Creator $9.99 / 40、Studio $24.99 / 120 と任意のアップロード支援。写真モードは無料、アニメーションは3クレジット。決済の接続・検証までは販売しません。

## ローカル実行

Python 3.12+、Node 22+、CJK フォント、ブラウザーテスト用 Chromium が必要です。他アプリの認証情報は流用せず、専用の非公開デモ設定を作成します。http://127.0.0.1:18642 を開き、`python3 scripts/dev.py stop` で停止します。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## 構成

Android は Kotlin/Jetpack Compose、iOS/macOS は SwiftUI のネイティブ実装です。PWA は独立した React/Vite、非公開の制作試作版は Python と SQLite を使用。画面は英語、スタンプ文字は中国語・英語・日本語です。

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## 検証

バックエンド77件とブラウザーエージェント安全テスト2件に合格。実ブラウザーで閲覧・ダウンロード、写真アップロード、キャラクター確認、写真スタンプ生成、文字確認、ZIP 出力、アカウント削除をデスクトップとモバイル幅で検証しました。実決済や AI サービスの検証ではありません。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## リリース状況

差し替え用のネイティブビルド候補：[iOS 1.0 (10)、macOS 1.0 (8)、Android 1.0 (9)](../docs/native-guest-chat-20261011.md)。ストアでの処理と内部配布の確認記録が得られるまで、配布済みとは確認できません。ローカルのアニメーション試験は1件成功しましたが、サービスのライフサイクル検証が完了するまで一般向けアニメーション生成は停止したままです。ソーシャルログイン、ネイティブアプリ内課金、Web 決済は、エンドツーエンドの検証に合格するまで無効のままです。

## 引用

コードは MIT、キャラクターと画像は別の権利条件です。研究に利用する際は本リポジトリを引用してください。 [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
