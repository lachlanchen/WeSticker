[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*나만의 캐릭터로 전하는 일상의 마음.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Aya와 친구들의 작품을 보고 나만의 캐릭터와 스티커를 만드는 독립 스튜디오입니다. 기본 작품은 로그인 없이 볼 수 있으며 개인 자료는 비공개 작업 공간에서 처리합니다. 기존 AYA 상점은 변경하지 않았습니다.

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

**2026-10-11** · https://westicker.lazying.art 에서 로그인 없이 게스트 채팅을 이용할 수 있습니다. Characters는 별도의 주요 메뉴가 아니라 Library 안에 있습니다. AgInTi 이미지 생성(`nano-banana-2`)은 실제 제공업체 검증을 통과해 활성화되었습니다. 생성에는 여전히 계정, 동의 및 견적에 대한 명시적 확인이 필요합니다.

[2026-10-11 · 게스트 채팅 / 탐색](../docs/clean-chat-release-20261011.md) · [AgInTi 이미지 검증](../docs/aginti-images.md) · [API / QA](../docs/chat-studio-20261011.md)

![Chat studio](../docs/screenshots/chat-studio-web.png)

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

백엔드 77개와 브라우저 에이전트 안전 테스트 2개를 통과했습니다. 실제 브라우저에서 다운로드, 업로드, 캐릭터 확인, 사진 스티커 생성, 문구 승인, ZIP 내보내기와 계정 삭제를 데스크톱·모바일 폭으로 확인했습니다. 실제 결제나 AI 제공업체 검증은 아닙니다.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 출시 상태

교체용 네이티브 빌드 후보: [iOS 1.0 (10), macOS 1.0 (8), Android 1.0 (9)](../docs/native-guest-chat-20261011.md). 스토어 처리 및 내부 배포 확인 기록이 확보되기 전까지 배포 여부는 확인되지 않은 상태입니다. 로컬 애니메이션 시험 1건은 성공했지만, 서비스 수명 주기 검증이 완료될 때까지 공개 애니메이션 생성은 오프라인 상태를 유지합니다. 소셜 로그인, 네이티브 앱 내 구매 및 웹 결제는 종단 간 검증을 통과할 때까지 비활성화 상태로 유지됩니다.

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
