from pathlib import Path
import importlib.util
import plistlib

ROOT = Path(__file__).resolve().parents[1]


def test_native_release_hosts_not_webviews():
    android = (ROOT / 'android/app/src/main/java/art/lazying/westicker/MainActivity.kt').read_text()
    apple = (ROOT / 'apple/Sources/WeStickerApp.swift').read_text()
    assert 'androidx.compose' in android and 'WebView' not in android
    assert 'import SwiftUI' in apple and 'WKWebView' not in apple
    assert 'UIActivityViewController' in apple and 'FileDocument' in apple
    assert 'DownloadSlots.shared.acquire()' in apple


def test_native_privacy_and_file_scope():
    privacy = plistlib.loads((ROOT / 'apple/PrivacyInfo.xcprivacy').read_bytes())
    assert not privacy['NSPrivacyTracking']
    assert any('CA92.1' in row['NSPrivacyAccessedAPITypeReasons']
               for row in privacy['NSPrivacyAccessedAPITypes'])
    files = (ROOT / 'android/app/src/main/res/xml/file_paths.xml').read_text()
    assert 'path="stickers/"' in files
    assert 'root-path' not in files and 'external-path' not in files


def test_edge_guards_precede_static_and_keep_checkout():
    spec = importlib.util.spec_from_file_location('edge', ROOT / 'scripts/deploy_catalog_edge.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    value = module.block('/srv/example')
    assert value.index('route {') < value.index('respond @hotlink') < value.index('handle_path')
    assert 'Sec-Fetch-Dest image' in value and 'localhost|127' in value
    assert 'reverse_proxy 127.0.0.1:18541' in value
    assert 'header_up -Cookie' in value
    assert 'max-age=31536000, immutable' in value
    assert 'not method GET HEAD' in value
