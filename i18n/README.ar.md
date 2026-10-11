[English](../README.md) · [العربية](README.ar.md) · [Español](README.es.md) · [Français](README.fr.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Tiếng Việt](README.vi.md) · [中文 (简体)](README.zh-Hans.md) · [中文（繁體）](README.zh-Hant.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*شخصيتك، وتعابيرك الصغيرة كل يوم.*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)](../docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

استوديو مستقل لملصقات Aya وأصدقائها ولشخصيات المستخدمين ومجموعاتهم. يمكن مشاهدة الأعمال الافتراضية دون تسجيل الدخول، بينما تُعالج الصور الشخصية في مساحة خاصة. متجر AYA الحالي لم يتغير.

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

**2026-10-11** · يتوفر تسجيل الدخول بكلمة مرور LazyingArt والإنشاء عبر المحادثة على https://westicker.lazying.art. ابدأ المحادثة ثم أضف الصور المرجعية وعدّل خطة الملصقات. إصدارات الاختبار الداخلي: iOS 1.0 (7)، macOS 1.0 (6)، Android 1.0 (7). تسجيل الدخول عبر الخدمات الاجتماعية وتوليد الصور والرسوم المتحركة بالذكاء الاصطناعي والدفع غير مفعلة بعد.

[2026-10-11 · Login / chat / test builds](../docs/login-chat-release-20261011.md) · [API / QA](../docs/chat-studio-20261011.md)

![Chat studio](../docs/screenshots/chat-studio-web.png)

## الاستوديو

- 10 مجموعات و156 حركة مستقلة، مع نصوص صينية وإنجليزية ويابانية ومعاينة فورية.
- رفع صور خاصة، وشخصية مؤكدة قابلة لإعادة الاستخدام، وثمانية تعابير، وتحرير النصوص، وموافقة لكل ملصق وتصدير ZIP.
- توليد صور وتحريك محلي ومراجعة بيع ورفع مسودات WeChat في متصفح معزول كخيارات إضافية. يحفظ المساعد المسودات فقط ولا يرسلها للمراجعة.

## الخطط

الاشتراكات الشهرية المقترحة: Pocket بسعر 0.99 دولار و3 أرصدة صور؛ Creator بسعر 9.99 و40 رصيداً؛ Studio بسعر 24.99 و120 رصيداً مع مساعدة رفع اختيارية. وضع الصور مجاني والتحريك يستهلك 3 أرصدة. الدفع معطل حتى الربط والتحقق.

## التشغيل محلياً

يتطلب Python 3.12+ وNode 22+ وخط CJK وChromium لاختبارات المتصفح. ينشئ البرنامج إعداد عرض خاصاً دون استعارة بيانات اعتماد تطبيق آخر. افتح http://127.0.0.1:18642 وأوقفه عبر `python3 scripts/dev.py stop`.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start
```

## البنية

تطبيق Android أصلي باستخدام Kotlin/Jetpack Compose وتطبيقا iOS/macOS باستخدام SwiftUI، مع PWA منفصلة بـ React/Vite. نموذج الإنشاء الخاص يستخدم Python وSQLite. الواجهة بالإنجليزية ونصوص الملصقات بالصينية والإنجليزية واليابانية.

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture](../docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment](../docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness](../docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff](../docs/integration-handoff.md) |

## التحقق

نجح 77 اختباراً للخادم واختبارا أمان للوكيل. تحقق متصفح حقيقي من التنزيل والرفع وتأكيد الشخصية وإنشاء ملصقات الصور ومراجعة النص وZIP وحذف الحساب على أحجام الهاتف والحاسوب. ليست هذه اختبارات دفع فعلي أو مزود ذكاء اصطناعي حي.

```bash
.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser
```

## حالة الإصدار

يتوفر تسجيل الدخول بكلمة مرور LazyingArt والإنشاء عبر المحادثة على https://westicker.lazying.art. ابدأ المحادثة ثم أضف الصور المرجعية وعدّل خطة الملصقات. إصدارات الاختبار الداخلي: iOS 1.0 (7)، macOS 1.0 (6)، Android 1.0 (7). تسجيل الدخول عبر الخدمات الاجتماعية وتوليد الصور والرسوم المتحركة بالذكاء الاصطناعي والدفع غير مفعلة بعد.

## الاستشهاد

الكود بترخيص MIT، والرسوم لها حقوق منفصلة. يرجى الاستشهاد بالمستودع عند استخدامه في البحث. [CITATION.cff](../CITATION.cff) · [MIT](../LICENSE) · [Artwork](../ARTWORK-LICENSE.md)

```bibtex
@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}
```
