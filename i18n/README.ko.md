[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner — apps and four buddies](https://lazying.art/media/brand/lazyingart-intro.gif)](https://lazying.art)

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

**2026-10-11** · 스티커는 로그인 없이 볼 수 있습니다. Create는 별도 로그인 화면을 거쳐 깔끔한 채팅으로 돌아옵니다. 캐릭터와 참고 자료는 Library에, Account는 마지막 탭에 있습니다.

[2026-10-11 · Public stickers / protected Create](../docs/protected-create-release-20261011.md) · [Native test builds](../docs/native-protected-create-20261011.md) · [Login qualification](../docs/social-auth-qualification-20261011.md) · [AgInTi qualification](../docs/aginti-images.md)

[2026-10-12 · Completion ledger](../docs/request-completion-ledger.md) · [Compact native builds](../docs/compact-native-release-20261012.md) · [Web subscription evidence](../docs/stripe-qualification.md)

![Chat studio](../docs/screenshots/compact-create-desktop.png)

<img src="../docs/screenshots/compact-create-ios.png" alt="Native iOS Create layout, authenticated test fixture" width="280">

[Native layout test scope](../docs/native-compact-toolbar-20261012.md)

## 스튜디오

- 기본 10팩, 서로 다른 애니메이션 156개, 중국어·영어·일본어 문구 버전과 즉시 미리보기.
- 비공개 사진 업로드, 재사용 가능한 승인된 캐릭터, 요금제 한도 내 초안, 문구 편집, 개별 승인과 ZIP 내보내기.
- 선택형 이미지 생성, 로컬 애니메이션, 판매 검토, 격리된 WeChat 초안 업로드. 도우미는 초안만 저장하고 심사에 제출하지 않습니다.

## 요금제

웹 월 구독이 제공됩니다: Pocket $0.99 / 3크레딧, Creator $9.99 / 40, Studio $24.99 / 120. 사진 모드는 무료이며 기본 컬렉션의 중국어·영어·일본어 ZIP이 포함됩니다. 네이티브 인앱 결제와 선택형 애니메이션·업로드 기능은 별도로 검증합니다.

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

백엔드와 브라우저 테스트는 공개 탐색, 인증된 채팅, 로그인 복귀, 세션 만료, 참고 자료, 검토와 내보내기를 다룹니다. 네이티브 빌드 증거는 별도로 기록합니다.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## 출시 상태

웹 구독이 운영 중인 제작자 내부 테스트 베타이며 완성된 상용 출시가 아닙니다. LazyingArt를 통한 비밀번호·Google·Apple 로그인과 AgInTi 이미지 생성은 검증되었습니다. GitHub와 직접 제공자 선택, 네이티브 결제, 공개 애니메이션, 제작자 판매, 사용자별 격리 WeChat 업로드는 완료 목록에서 추적합니다.

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
