"""Run native release UI tests on the existing signing Mac, without store actions."""
import argparse
from pathlib import Path
import plistlib
import shutil
import subprocess


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
        with (out / "xctest.log").open("x") as log:
            subprocess.run(command, cwd=source, stdout=log, stderr=subprocess.STDOUT, check=True)
        print("Native XCTest passed: " + a.platform + " " + a.build, flush=True)
    finally:
        fixture.unlink()
        subprocess.run([xcodegen, "generate"], cwd=source, check=True, stdout=subprocess.DEVNULL)
        if ios:
            subprocess.run(["xcrun", "simctl", "shutdown", a.simulator], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
