[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*Nhân vật của bạn. Cảm xúc mỗi ngày.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

Xưởng nhãn dán độc lập dành cho Aya cùng bạn bè và các nhân vật do người dùng tạo. Xem bộ mặc định không cần đăng nhập; ảnh cá nhân được xử lý trong không gian riêng. Cửa hàng AYA hiện tại không thay đổi.

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

**2026-10-11** · Trò chuyện dành cho khách đã hoạt động tại https://westicker.lazying.art mà không cần đăng nhập. Characters nằm trong Library, không phải mục điều hướng chính riêng biệt. Tạo ảnh qua AgInTi (`nano-banana-2`) đã được kiểm chứng với nhà cung cấp thực và được bật; việc tạo ảnh vẫn yêu cầu tài khoản, sự đồng ý và xác nhận rõ ràng báo giá.

[2026-10-11 · Trò chuyện dành cho khách / điều hướng](../docs/clean-chat-release-20261011.md) · [Kiểm chứng ảnh AgInTi](../docs/aginti-images.md) · [API / QA](../docs/chat-studio-20261011.md)

![Chat studio](../docs/screenshots/chat-studio-web.png)

## Xưởng sáng tạo

- 10 bộ, 156 hoạt ảnh riêng biệt, chữ Trung/Anh/Nhật và xem trước tức thì.
- Tải ảnh riêng tư, nhân vật đã xác nhận có thể dùng lại, tám biểu cảm, sửa chữ, duyệt từng ảnh và xuất ZIP.
- Tùy chọn tạo ảnh, hoạt ảnh cục bộ, duyệt bán và trình duyệt riêng để tải bản nháp WeChat. Trợ lý chỉ lưu nháp, không gửi xét duyệt.

## Gói dịch vụ

Giá tháng đề xuất: Pocket 0,99 USD / 3 tín dụng ảnh; Creator 9,99 USD / 40; Studio 24,99 USD / 120 và hỗ trợ tải lên tùy chọn. Chế độ ảnh miễn phí; hoạt ảnh tốn 3 tín dụng. Thanh toán chưa bật trước khi kết nối và kiểm chứng.

## Chạy cục bộ

Cần Python 3.12+, Node 22+, phông CJK và Chromium để kiểm thử. Lệnh tạo cấu hình demo riêng, không dùng thông tin đăng nhập của ứng dụng khác. Mở http://127.0.0.1:18642; dừng bằng `python3 scripts/dev.py stop`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## Cấu trúc

Android thuần Kotlin/Jetpack Compose, iOS/macOS dùng SwiftUI và PWA React/Vite riêng. Bản mẫu sáng tạo riêng tư dùng Python và SQLite. Giao diện tiếng Anh; chữ nhãn dán có tiếng Trung, Anh và Nhật.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## Kiểm thử

Đã qua 77 kiểm thử backend và hai kiểm thử an toàn agent. Trình duyệt thật đã kiểm tra tải xuống, tải ảnh, duyệt nhân vật, tạo ảnh nhãn dán, sửa chữ, ZIP và xóa tài khoản ở khổ máy tính lẫn di động. Đây không phải kiểm thử thanh toán hay nhà cung cấp AI thật.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## Trạng thái phát hành

Các bản thử nghiệm nội bộ: [iOS 1.0 (10), macOS 1.0 (8), Android 1.0 (9)](../docs/native-guest-chat-20261011.md). Một lần thử nghiệm hoạt ảnh cục bộ đã thành công, nhưng tính năng tạo hoạt ảnh công khai vẫn ngoại tuyến cho đến khi vòng đời dịch vụ được kiểm chứng. Đăng nhập qua mạng xã hội, mua hàng trong ứng dụng native và thanh toán web vẫn bị tắt cho đến khi vượt qua kiểm chứng đầu cuối.

## Trích dẫn

Mã nguồn MIT; hình ảnh có quyền riêng. Vui lòng trích dẫn kho mã khi dùng trong nghiên cứu. [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
