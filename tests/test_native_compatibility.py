"""Source safeguards, supplemented by real Apple builds and native UI tests."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "apple/Sources"


def test_deployment_baselines_and_guarded_fallbacks():
    project = (ROOT / "apple/project.yml").read_text()
    assert 'iOS: "16.0"' in project
    assert 'macOS: "12.0"' in project
    compat = (SOURCES / "StudioCompatibility.swift").read_text()
    for old, new in [("NavigationView", "NavigationStack"), ("TextEditor", "axis: .vertical"),
                     ("fileImporter", "PhotosPicker"), ("fileExporter", "ShareLink")]:
        assert old in compat and new in compat
    assert '@available(macOS 13.0, *)' in compat
    assert compat.count('if #available(macOS 13.0, *)') >= 5
    assert "startAccessingSecurityScopedResource" in compat
    assert "stopAccessingSecurityScopedResource" in compat
    for file in SOURCES.glob("*.swift"):
        if file.name != "StudioCompatibility.swift":
            assert "NavigationStack {" not in file.read_text()


def test_adaptive_catalog_keeps_one_content_branch_and_scene_size():
    app = (SOURCES / "WeStickerApp.swift").read_text()
    compat = (SOURCES / "StudioCompatibility.swift").read_text()
    assert "horizontalSizeClass == .regular" in app
    assert "usesSidebar(width: geometry.size.width)" in app
    assert "} content: { content }" in app
    assert "AnyLayout(HStackLayout" in compat and "AnyLayout(VStackLayout" in compat
    assert "UIScreen.main" not in app + compat
    assert "onChange(of: geometry" not in app
    assert "@State private var preview" in app
    assert "@AppStorage(\"catalog-language\")" in app
    assert '.frame(minHeight: 50)' in (SOURCES / "CreatorStudio.swift").read_text()
    scene = app.split("struct WeStickerApp: App", 1)[1].split("struct CatalogView", 1)[0]
    assert scene.count("WindowGroup {") == 1
    assert "if #available" not in scene
    assert ".frame(idealWidth: 1120, idealHeight: 800)" in scene


def test_resize_and_accessibility_are_native_runtime_scenarios():
    qa = (ROOT / "apple/UITests/CatalogTests.swift").read_text()
    assert "testRotationPreservesPreviewSearchAndPlayback" in qa
    assert "testLargeTextKeepsCatalogControlsReachable" in qa
    assert "landscapeLeft" in qa and "portrait" in qa
    assert "UICTContentSizeCategoryAccessibilityXXXL" in qa
    assert "Save GIF" in qa


def test_optional_close_is_conditional_view_not_conditional_toolbar_item():
    creator = (SOURCES / "CreatorStudio.swift").read_text()
    toolbar = creator.split('.compactStudioHeader("Create")', 1)[1].split('.onChange', 1)[0]
    assert '.toolbar {\n                    ToolbarItem(placement: .primaryAction) {\n                        if let close {' in toolbar
    assert 'Button(action: close)' in toolbar
    assert '.accessibilityLabel("Close local draft")' in toolbar
