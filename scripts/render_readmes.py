"""Render synchronized profile READMEs from reviewed translation text."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
translations = json.loads((ROOT / "docs/readme-translations.json").read_text())
languages = [
    ("en", "English"),
    ("ar", "العربية"),
    ("es", "Español"),
    ("fr", "Français"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("vi", "Tiếng Việt"),
    ("zh-Hans", "中文 (简体)"),
    ("zh-Hant", "中文（繁體）"),
    ("de", "Deutsch"),
    ("ru", "Русский"),
]
start = """python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
npm ci
python3 scripts/configure_local.py
npm run build
python3 scripts/dev.py start"""
tests = """.venv/bin/pytest -q
node --test tests/wechat.test.mjs
npm run build
npm audit
npm run test:browser"""
citation = """@software{chen_westicker_2026,
  author = {Chen, Lachlan},
  title = {WeSticker: A Personal Sticker Creation Studio},
  year = {2026},
  url = {https://github.com/lachlanchen/WeSticker}
}"""
support = """| Donate | PayPal | Stripe |
| --- | --- | --- |
| [![Donate](https://img.shields.io/badge/Donate-LazyingArt-0EA5E9?style=for-the-badge&logo=kofi&logoColor=white)](https://chat.lazying.art/donate) | [![PayPal](https://img.shields.io/badge/PayPal-RongzhouChen-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/RongzhouChen) | [![Stripe](https://img.shields.io/badge/Stripe-Donate-635BFF?style=for-the-badge&logo=stripe&logoColor=white)](https://buy.stripe.com/aFadR8gIaflgfQV6T4fw400) |"""
for code, t in translations.items():
    root = code == "en"
    prefix = "" if root else "../"
    header = " · ".join(
        f"[{label}]({('README.md' if root else '../README.md') if lang == 'en' else ('i18n/' if root else '') + 'README.' + lang + '.md'})"
        for lang, label in languages
    )
    h = t["headings"]
    content = f"""{header}

[![LazyingArt banner](https://github.com/lachlanchen/lachlanchen/raw/main/figs/banner.png)](https://github.com/lachlanchen/lachlanchen/blob/main/figs/banner.png)

# WeSticker

*{t["tag"]}*

[![LazyingArt](https://img.shields.io/badge/LazyingArt-Project-0EA5E9)](https://lazying.art) [![Status](https://img.shields.io/badge/Status-Creator_beta-ED477A)]({prefix}docs/release-readiness.md) [![PWA](https://img.shields.io/badge/Open-Web_app-0EA5E9)](https://westicker.lazying.art) [![Sponsor](https://img.shields.io/badge/GitHub-Sponsors-F06595)](https://github.com/sponsors/lachlanchen)

{t["intro"]}

{support}

![WeSticker]({prefix}docs/screenshots/discover.png)

| Android / Compose | iOS / SwiftUI |
| --- | --- |
| ![Native Android]({prefix}docs/screenshots/native-android.png) | ![Native iOS]({prefix}docs/screenshots/animated-catalog-ios.png) |

[Native beta scope]({prefix}docs/native-catalog-beta.md) · [Creator roadmap]({prefix}docs/native-creator-plan.md) · [Bandwidth]({prefix}docs/catalog-bandwidth.md)

[Create / Agent beta update · 2026-10-10]({prefix}docs/creator-beta-20261010.md) · [Japanese LINE editions]({prefix}docs/line-japanese-editions.md)

[GIF playback, new icon and test-build evidence]({prefix}docs/native-playback-20261010.md)

**2026-10-11** · {t["creator_update"]}

[2026-10-11 · Public stickers / protected Create]({prefix}docs/protected-create-release-20261011.md) · [Native test builds]({prefix}docs/native-protected-create-20261011.md) · [Login qualification]({prefix}docs/social-auth-qualification-20261011.md) · [AgInTi qualification]({prefix}docs/aginti-images.md)

[2026-10-12 · Completion ledger]({prefix}docs/request-completion-ledger.md) · [Compact native builds]({prefix}docs/compact-native-release-20261012.md) · [Web subscription evidence]({prefix}docs/stripe-qualification.md)

![Chat studio]({prefix}docs/screenshots/compact-create-desktop.png)

<img src="{prefix}docs/screenshots/compact-create-ios.png" alt="Native iOS Create layout, authenticated test fixture" width="280">

[Native layout test scope]({prefix}docs/native-compact-toolbar-20261012.md)

## {h[0]}

{chr(10).join("- " + line for line in t["features"])}

## {h[1]}

{t["plans"]}

## {h[2]}

{t["start"]}

```bash
{start}
```

## {h[3]}

{t["inside"]}

| Path | Document |
| --- | --- |
| `src/`, `server/` | [Architecture]({prefix}docs/architecture.md) |
| `worker/`, `compose.yaml` | [Deployment]({prefix}docs/deployment.md) |
| `android/`, `apple/`, `macos/` | [Release readiness]({prefix}docs/release-readiness.md) |
| `server/auth.py`, `server/billing.py` | [Integration handoff]({prefix}docs/integration-handoff.md) |

## {h[4]}

{t["tests"]}

```bash
{tests}
```

## {h[5]}

{t["status"]}

## {h[6]}

{t["cite"]} [CITATION.cff]({prefix}CITATION.cff) · [MIT]({prefix}LICENSE) · [Artwork]({prefix}ARTWORK-LICENSE.md)

```bibtex
{citation}
```
"""
    dest = ROOT / ("README.md" if root else f"i18n/README.{code}.md")
    dest.parent.mkdir(exist_ok=True)
    dest.write_text(content)
print("Rendered 11 READMEs.")
