"""Compact native chrome source contracts; screenshot QA requires the next build."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APPLE = ROOT / "apple/Sources"
ANDROID = ROOT / "android/app/src/main/java/art/lazying/westicker"


def test_shared_leading_toolbar_has_no_large_title():
    swift = (APPLE / "StudioChrome.swift").read_text()
    kotlin = (ANDROID / "StudioChrome.kt").read_text()
    assert "return .navigationBarLeading" in swift
    assert "return .navigation" in swift
    assert '.navigationTitle("")' in swift
    assert ".navigationBarTitleDisplayMode(.inline)" in swift
    assert "Text(title).font(.headline).lineLimit(1)" in swift
    assert "TopAppBar(title =" in kotlin
    assert "MaterialTheme.typography.titleMedium" in kotlin
    assert "maxLines = 1" in kotlin and "TextOverflow.Ellipsis" in kotlin
    for source in (swift, kotlin):
        assert '"studio-toolbar-title"' in source


def test_every_tab_uses_the_compact_header():
    for filename, call in (
        ("WeStickerApp.swift", '.compactStudioHeader("WeSticker")'),
        ("CloudStudio.swift", '.compactStudioHeader(section == 2 ? "Library" : "Create")'),
        ("NativeBilling.swift", '.compactStudioHeader("Account")'),
    ):
        source = (APPLE / filename).read_text()
        assert call in source
        assert ".navigationTitle(" not in source
    for filename, call in (
        ("MainActivity.kt", 'CompactStudioTopBar("WeSticker"'),
        ("CloudStudio.kt", 'CompactStudioTopBar(if(section==2) "Library" else "Create"'),
        ("BillingAccountScreen.kt", 'CompactStudioTopBar("Account")'),
    ):
        source = (ANDROID / filename).read_text()
        assert call in source
        assert "TopAppBar(" not in source
    assert 'Text("Sticker collections"' not in (ANDROID / "MainActivity.kt").read_text()
    assert 'Text("WeSticker Account"' not in (ANDROID / "BillingAccountScreen.kt").read_text()
    assert 'Section("WeSticker Account")' not in (APPLE / "NativeBilling.swift").read_text()


def test_small_welcome_is_balanced_in_available_scroll_space():
    chrome = (APPLE / "StudioChrome.swift").read_text()
    swift = (APPLE / "CloudStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    assert "frame(width: 44, height: 44)" in chrome
    assert 'Text("What shall we make?").font(.headline)' in chrome
    assert "viewport.size.height - 32" in swift
    assert "Modifier.size(44.dp)" in kotlin
    assert "contentAlignment=Alignment.Center" in kotlin
    assert "maxHeight-32.dp" in kotlin
    assert "heightIn(min=welcomeHeight)" in kotlin
    for source in (chrome, kotlin):
        assert '"chat-welcome"' in source


def test_motion_is_bounded_and_respects_platform_settings():
    chrome = (APPLE / "StudioChrome.swift").read_text()
    swift = (APPLE / "CloudStudio.swift").read_text()
    root = (APPLE / "CreatorStudio.swift").read_text()
    kotlin = (ANDROID / "CloudStudio.kt").read_text()
    for source in (chrome, swift, root):
        assert "accessibilityReduceMotion" in source
        assert "reduceMotion ? nil" in source
        assert "repeatForever" not in source
    assert "animateFloatAsState" in kotlin
    assert "system animator duration scale" in kotlin
    assert "rememberInfiniteTransition" not in kotlin
    assert "tween(220)" in kotlin and "tween(150)" in kotlin
    assert "canSend" in swift and "canSend" in kotlin


def test_next_ui_run_asserts_real_toolbar_geometry_and_composer():
    catalog = (ROOT / "apple/UITests/CatalogTests.swift").read_text()
    fixture = (ROOT / "scripts/native_account_ui_qa.swift").read_text()
    smoke = (ROOT / "scripts/android_smoke.py").read_text()
    assert "label.frame.midY - button.frame.midY" in catalog
    assert "label.frame.maxX, button.frame.minX" in catalog
    assert "visible.count, 1" in catalog
    for title in ("Create", "Library", "Account", "Sign in"):
        assert 'assertCompactHeader("' + title + '"' in fixture
    assert 'assert_toolbar(tree, "WeSticker", "About this beta")' in smoke
    assert 'assert_toolbar(tree, "Sign in", "Service settings")' in smoke
    assert "welcome.frame.maxY, input.frame.minY" in fixture
    assert 'input.tap(); input.typeText("A friendly sticker idea")' in fixture
