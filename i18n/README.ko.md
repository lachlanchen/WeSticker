[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*나만의 캐릭터로 전하는 일상의 마음.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Catalog_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://aya.lazying.art/westicker/) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Aya와 친구들의 작품을 보고 나만의 캐릭터와 스티커를 만드는 독립 스튜디오입니다. 기본 작품은 로그인 없이 볼 수 있으며 개인 자료는 비공개 작업 공간에서 처리합니다. 기존 AYA 상점은 변경하지 않았습니다.

| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |

![WeSticker](../docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android](../docs/screenshots/native-android.png) | ![Native iOS](../docs/screenshots/native-ios.png) |

[Native beta scope](../docs/native-catalog-beta.md) · [Creator roadmap](../docs/native-creator-plan.md) · [Bandwidth](../docs/catalog-bandwidth.md)

## 스튜디오

- 기본 10팩, 서로 다른 애니메이션 156개, 중국어·영어·일본어 문구 버전과 즉시 미리보기.
- 비공개 사진 업로드, 재사용 가능한 고정 캐릭터, 8가지 표현 초안, 문구 편집, 개별 승인과 ZIP 내보내기.
- 선택형 이미지 생성, 로컬 애니메이션, 판매 검토, 격리된 WeChat 초안 업로드. 도우미는 초안만 저장하고 심사에 제출하지 않습니다.

## 요금제

월 요금 제안: Pocket $0.99 / 이미지 3크레딧, Creator $9.99 / 40, Studio $24.99 / 120 및 선택형 업로드 지원. 사진 모드는 무료이며 애니메이션은 3크레딧입니다. 결제 연결과 검증 전에는 판매하지 않습니다.

## 로컬 실행

Python 3.12+, Node 22+, CJK 글꼴, 브라우저 테스트용 Chromium이 필요합니다. 다른 앱의 인증 정보를 빌리지 않고 독립된 비공개 데모 설정을 만듭니다. http://127.0.0.1:18642에서 열고 `python3 scripts/dev.py stop`으로 중지합니다.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## 구성

Android는 Kotlin/Jetpack Compose, iOS/macOS는 SwiftUI 네이티브 앱입니다. 별도 PWA는 React/Vite, 비공개 제작 시제품은 Python과 SQLite를 사용합니다. 화면은 영어이며 스티커 문구는 중국어·영어·일본어입니다.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## 검증

백엔드 46개와 브라우저 에이전트 안전 테스트 2개를 통과했습니다. 실제 브라우저에서 다운로드, 업로드, 캐릭터 확인, 사진 스티커 생성, 문구 승인, ZIP 내보내기와 계정 삭제를 데스크톱·모바일 폭으로 확인했습니다. 실제 결제나 AI 제공업체 검증은 아닙니다.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 출시 상태

공개 카탈로그 PWA는 https://aya.lazying.art/westicker/ 에서 운영됩니다. 네이티브 카탈로그는 Google Play 내부 테스트와 Apple TestFlight용입니다. 정확한 배포 상태와 검증 제한은 릴리스 기록을 확인하세요. AI 제작, 로그인, 구독과 판매는 베타에서 비활성화되어 있습니다.

## 인용

코드는 MIT이며 캐릭터와 그림은 별도 권리가 적용됩니다. 연구에 사용할 때 이 저장소를 인용해 주세요. [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
