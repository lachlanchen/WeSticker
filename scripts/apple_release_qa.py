"""Run native release UI tests on the existing signing Mac, without store actions."""
import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess
import json
from native_ui_fixture import native_ui_fixture


def clear_fixture_origin(data_root: Path) -> int:
    """Remove only this fixture's preference in the specified stopped simulator."""
    cleared = 0
    for prefs in data_root.glob("*/Library/Preferences/art.lazying.westicker.plist"):
        if prefs.is_symlink():
            raise RuntimeError("Unexpected simulator preference symlink")
        value = plistlib.loads(prefs.read_bytes())
        if value.get("studio-origin") == "http://127.0.0.1:18649":
            value.pop("studio-origin")
            prefs.write_bytes(plistlib.dumps(value))
            cleared += 1
    return cleared


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("platform", choices=["ios", "macos"])
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--build", required=True)
    p.add_argument("--simulator", default="83A61A5D-BF99-44A0-8277-0634A8D60A53")
    a = p.parse_args()
    root = a.root.expanduser().resolve()
    ios = a.platform == "ios"
    scheme = "WeStickerIOS" if ios else "WeStickerMac"
    out = root / "releases" / f"{a.platform}-1.0-{a.build}" / "qa"
    out.mkdir(parents=True, exist_ok=True)
    result = out / "NativeRelease.xcresult"
    if result.exists():
        raise RuntimeError("Existing QA result must be inspected, not overwritten")
    fixture = root / "source/apple/UITests/NativeAccountReleaseTests.swift"
    if fixture.exists():
        raise RuntimeError("Temporary QA fixture already exists; reconcile its owner")
    source = root / "source/apple"
    xcodegen = str(Path.home() / ".local/xcodegen-2.46.0/bin/xcodegen")
    archive = out.parent / "WeSticker.xcarchive/Products/Applications/WeSticker.app"
    info = plistlib.loads((archive / ("Info.plist" if ios else "Contents/Info.plist")).read_bytes())
    if info["CFBundleVersion"] != a.build or info["CFBundleIdentifier"] != "art.lazying.westicker":
        raise RuntimeError("Wrong release archive")
    shutil.copy2(Path(__file__).with_name("native_account_ui_qa.swift"), fixture)
    try:
        subprocess.run([xcodegen, "generate"], cwd=source, check=True, stdout=subprocess.DEVNULL)
        command = ["xcodebuild", "-project", "WeSticker.xcodeproj", "-scheme", scheme,
                   "-destination", "platform=iOS Simulator,id=" + a.simulator if ios else "platform=macOS",
                   "-derivedDataPath", str(root / ("CreatorQADerivedData" if ios else "MotionMacDerivedData")),
                   "-resultBundlePath", str(result), "-jobs", "1", "-parallel-testing-enabled", "NO",
                   "CODE_SIGNING_ALLOWED=NO", "CURRENT_PROJECT_VERSION=" + a.build, "test"]
        with native_ui_fixture() as state, (out / "xctest.log").open("x") as log:
            try:
                subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
            finally:
                (out / "fixture-requests.json").write_text(json.dumps(state, indent=2))
            if state["unexpected"]:
                raise RuntimeError("Unexpected requests reached the layout-only fixture")
            if [probe["provider"] for probe in state["link_probes"]] != ["google", "apple", "github", "lazyingart"]:
                raise RuntimeError("Expected one direct-link cancellation probe per configured provider")
        print("Native XCTest passed: " + a.platform + " " + a.build, flush=True)
    finally:
        fixture.unlink()
        subprocess.run([xcodegen, "generate"], cwd=source, check=True, stdout=subprocess.DEVNULL)
        if ios:
            # get_app_container fails after XCTest has already stopped the simulator.
            subprocess.run(["xcrun", "simctl", "shutdown", a.simulator], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            devices = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "--json"]))["devices"]
            owned = [device for group in devices.values() for device in group if device["udid"] == a.simulator]
            if len(owned) != 1 or owned[0]["state"] != "Shutdown":
                raise RuntimeError("Owned simulator is not stopped; preference cleanup deferred")
            data_root = Path.home() / "Library/Developer/CoreSimulator/Devices" / a.simulator / "data/Containers/Data/Application"
            print("Fixture origins cleared: " + str(clear_fixture_origin(data_root)), flush=True)


if __name__ == "__main__":
    main()
