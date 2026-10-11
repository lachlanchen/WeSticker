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

**2026-10-11** · スタンプの閲覧はログイン不要です。Create は専用のログイン画面を経て、すっきりしたチャットに進みます。キャラクターと参考素材は Library、Account は最後のタブです。

[2026-10-11 · Public stickers / protected Create](../docs/protected-create-release-20261011.md) · [Native test builds](../docs/native-protected-create-20261011.md) · [Login qualification](../docs/social-auth-qualification-20261011.md) · [AgInTi qualification](../docs/aginti-images.md)

[2026-10-12 · Completion ledger](../docs/request-completion-ledger.md) · [Compact native builds](../docs/compact-native-release-20261012.md) · [Web subscription evidence](../docs/stripe-qualification.md)

![Chat studio](../docs/screenshots/compact-create-desktop.png)

## スタジオ

- 標準10パック、156種類のアニメーション、中国語・英語・日本語の文字版をすぐにプレビュー。
- 非公開の写真アップロード、再利用できる承認済みキャラクター、プラン上限内の下書き、文字編集、個別確認と ZIP 出力。
- 画像生成、ローカル動画化、販売審査、隔離ブラウザーでの WeChat 下書きアップロードは任意機能です。助手は下書き保存のみで、審査には提出しません。

## プラン

Web月額プランは利用可能です：Pocket $0.99 / 3クレジット、Creator $9.99 / 40、Studio $24.99 / 120。写真モードは無料です。各プランに標準コレクションの中国語・英語・日本語版ZIPを含みます。ネイティブアプリ内課金と任意の動画化・アップロード機能は個別に検証します。

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

バックエンドとブラウザーで公開閲覧、認証付きチャット、ログイン後の復帰、セッション期限切れ、参考素材、確認、書き出しを検証します。ネイティブ版の証拠は別途記録します。

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## リリース状況

制作機能の内部テスト版で、Web定期購入は稼働中です。商用リリース全体の完成を意味しません。LazyingArt経由のパスワード・Google・AppleログインとAgInTi画像生成は検証済みです。GitHubと直接のプロバイダー選択、アプリ内課金、公開動画化、クリエイター販売、利用者別に隔離したWeChatアップロードは完了リストで追跡しています。

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
