"""Exercise an exact signed APK in an owned, short-lived Android emulator."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET
import re
import hashlib
import uuid
from io import BytesIO
from PIL import Image
from urllib.request import urlopen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk", required=True, type=Path)
    p.add_argument("--apk", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--port", type=int, default=5588)
    p.add_argument("--creator", action="store_true")
    p.add_argument("--account", action="store_true", help="Check signed-out Account UI without signing in or purchasing")
    a = p.parse_args()
    if not a.apk.is_file():
        p.error("The selected APK does not exist")
    adb = str(a.sdk / "platform-tools/adb")
    serial = f"emulator-{a.port}"
    existing = subprocess.check_output([adb, "devices"], text=True)
    if serial in existing:
        raise RuntimeError("Test port already in use; no emulator replaced")
    a.out.mkdir(parents=True, exist_ok=True)
    def run(*args):
        return subprocess.check_output([adb, "-s", serial, *args], timeout=45)
    def capture(name):
        remote = "/data/local/tmp/westicker-qa-" + uuid.uuid4().hex + ".xml"
        for attempt in range(3):
            result = run("shell", "uiautomator", "dump", remote)
            if b"dumped to:" in result:
                break
            if attempt == 2:
                raise RuntimeError("No fresh UI hierarchy for " + name)
            time.sleep(2)
        xml = run("shell", "cat", remote)
        run("shell", "rm", "-f", remote)
        (a.out / (name + ".xml")).write_bytes(xml)
        (a.out / (name + ".png")).write_bytes(run("exec-out", "screencap", "-p"))
        return ET.fromstring(xml)
    def tap(tree, label, contains=False):
        for node in tree.iter("node"):
            text = node.get("text", "") or node.get("content-desc", "")
            if (label in text if contains else label == text):
                x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds", "")))
                run("shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2))
                return
        raise RuntimeError("Missing visible control: " + label)
    with urlopen("https://westicker.lazying.art/api/bootstrap", timeout=20) as response:
        configured = json.load(response).get("providers", [])
    provider_labels = {"google": "Google", "apple": "Apple", "github": "GitHub", "lazyingart": "LazyingArt"}
    expected = {"Continue with " + label for key, label in provider_labels.items() if key in configured}
    def assert_shared_login(name):
        for _ in range(10):
            tree = capture(name)
            texts = [n.get("text", "") or n.get("content-desc", "") for n in tree.iter("node")]
            if all(label in texts for label in expected) and (expected or "Sign-in is unavailable." in texts):
                break
            time.sleep(1)
        assert "Sign in to WeSticker" in texts and "Browse stickers" in texts
        assert {t for t in texts if t.startswith("Continue with ")} == expected
        assert all(texts.count(label) == 1 for label in expected)
        assert not any(t in texts for t in ("WeSticker Account", "Manage Play subscriptions", "Send message", "Library", "Characters"))
        assert not any("Stripe" in t or "Checkout" in t for t in texts)
        return tree
    with (a.out / "emulator.log").open("w") as log:
        proc = subprocess.Popen([str(a.sdk / "emulator/emulator"), "-avd", "WeSticker_Review_API34",
            "-port", str(a.port), "-no-window", "-no-audio", "-no-snapshot", "-memory", "2048",
            "-cores", "2", "-gpu", "swiftshader_indirect", "-feature", "-Bluetooth"], stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(120):
                if proc.poll() is not None:
                    raise RuntimeError("Owned emulator exited")
                if serial + "\tdevice" in subprocess.check_output([adb, "devices"], text=True):
                    if run("shell", "getprop", "sys.boot_completed").strip() == b"1":
                        break
                time.sleep(2)
            else:
                raise RuntimeError("Emulator boot timeout")
            # This owned API34 AVD's Bluetooth service can crash on a host with no adapter.
            run("shell", "svc", "bluetooth", "disable")
            run("shell", "pm", "disable-user", "--user", "0", "com.android.bluetooth")
            run("shell", "wm", "dismiss-keyguard")
            time.sleep(5)
            startup = capture("00-emulator")
            if any(n.get("text") == "Bluetooth keeps stopping" for n in startup.iter("node")):
                tap(startup, "Close app")
            run("install", "-r", str(a.apk.resolve()))
            run("shell", "am", "start", "-n", "art.lazying.westicker/.MainActivity")
            time.sleep(12)
            tree = capture("01-start")
            if any(n.get("text") == "Bluetooth keeps stopping" for n in tree.iter("node")):
                tap(tree, "Close app")
                tree = capture("01-start-cleared")
            tree = capture("01-catalog")
            texts = [n.get("text", "") or n.get("content-desc", "") for n in tree.iter("node")]
            if not any("Sticker collections" in t for t in texts):
                raise RuntimeError("Native catalog is not visible")
            if "Sign in" in texts or "Plans & credits" in texts:
                raise RuntimeError("Unqualified beta control is visible")
            if a.account:
                tap(tree, "Account")
                tree = assert_shared_login("account-to-login")
                tap(tree, "Browse stickers")
                tree = capture("account-return")
                assert any("Sticker collections" in n.get("text", "") for n in tree.iter("node"))
            if a.creator:
                tap(tree, "Create")
                tree = assert_shared_login("creator")
                tap(tree, "Browse stickers")
                tree = capture("creator-dismissed")
                tap(tree, "Library")
                tree = assert_shared_login("library-to-login")
                tap(tree, "Open saved local photo draft")
                tree = capture("local-photo-draft")
                assert any("Choose photo" in n.get("text", "") for n in tree.iter("node"))
                run("shell", "am", "force-stop", "art.lazying.westicker")
                run("shell", "am", "start", "-n", "art.lazying.westicker/.MainActivity")
                time.sleep(3)
                tree = capture("creator-reopened")
                assert any("Sticker collections" in n.get("text", "") for n in tree.iter("node"))
                tap(tree, "Library")
                tree = assert_shared_login("library-reopened")
                tap(tree, "Open saved local photo draft")
                tree = capture("creator-restored")
                assert any("Choose photo" in n.get("text", "") for n in tree.iter("node"))
                tap(tree, "Close local draft")
                tree = capture("catalog-return")
            tap(tree, "English")
            time.sleep(3)
            tree = capture("02-english")
            motion_node = next(n for n in tree.iter("node") if "Preview " in n.get("content-desc", ""))
            bounds = tuple(map(int, re.findall(r"\d+", motion_node.get("bounds", ""))))
            def motion_samples(name):
                values = set()
                for index in range(5):
                    frame = Image.open(BytesIO(run("exec-out", "screencap", "-p"))).crop(bounds).convert("RGB")
                    frame.save(a.out / f"{name}-{index}.png")
                    values.add(hashlib.sha256(frame.tobytes()).hexdigest())
                    time.sleep(0.27)
                return len(values)
            moving = motion_samples("playing")
            assert moving > 1, "The GIF pixels did not animate"
            tap(tree, "Pause animations")
            time.sleep(1)
            paused = motion_samples("paused")
            assert paused == 1, "Pause did not stop animation"
            tree = capture("paused-catalog")
            tap(tree, "Play animations")
            time.sleep(1)
            resumed = motion_samples("resumed")
            assert resumed > 1, "GIF did not resume"
            tree = capture("resumed-catalog")
            tap(tree, "Preview ", contains=True)
            time.sleep(3)
            tree = capture("03-preview")
            tap(tree, "Save GIF", contains=True)
            time.sleep(8)
            tree = capture("04-share")
            foreground = run("shell", "dumpsys", "activity", "activities").decode()
            if "ChooserActivity" not in foreground:
                raise RuntimeError("Native share sheet did not open")
            result = {"installed_exact_apk": str(a.apk), "catalog": True, "english": True,
                      "apk_sha256": hashlib.sha256(a.apk.read_bytes()).hexdigest(),
                      "account_signed_out_ui": a.account, "purchase_attempted": False,
                      "public_home_initial": True, "dedicated_create_login": a.creator,
                      "shared_authentication_route": a.creator and a.account,
                      "configured_provider_labels": sorted(expected),
                      "live_auth_attempted": False,
                      "motion_unique_frames": {"playing": moving, "paused": paused, "resumed": resumed},
                      "preview": True, "native_share_sheet": True, "physical_device": False,
                      "creator_navigation_and_local_editor_restore": a.creator, "gif_motion_pause_resume": True}
            (a.out / "result.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
        finally:
            try:
                run("emu", "kill")
            except Exception:
                proc.terminate()
            proc.wait(timeout=40)


if __name__ == "__main__":
    main()
