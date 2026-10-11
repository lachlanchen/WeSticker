"""Archive/export WeSticker on its signing Mac, without changing other apps.

Signing inputs are private files. Existing archives are reused only after their
bundle/version/build and signature are checked; they are never overwritten.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import secrets
import shlex
import subprocess

from apple_release import BUNDLE, private_write


def checked_profile(path, platform):
    value = plistlib.loads(subprocess.check_output(
        ["security", "cms", "-D", "-i", str(path)], stderr=subprocess.DEVNULL))
    team = value["TeamIdentifier"][0]
    ent = value["Entitlements"]
    identity = ent.get("application-identifier", ent.get("com.apple.application-identifier"))
    if identity != team + "." + BUNDLE or ent.get("get-task-allow", False):
        raise ValueError("Wrong app or development profile")
    destination = Path.home() / "Library/MobileDevice/Provisioning Profiles" / (value["UUID"] + path.suffix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(path.read_bytes())
    destination.chmod(0o600)
    return value, team


def chains():
    return shlex.split(subprocess.check_output(["security", "list-keychains", "-d", "user"], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=["ios", "macos"])
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--p12", type=Path, help="Import a distribution identity; omit to reuse the app's keychain")
    parser.add_argument("--p12-password-file", type=Path)
    parser.add_argument("--version", default="1.0")
    parser.add_argument("--build", default="1")
    parser.add_argument("--scope", default="catalog beta")
    parser.add_argument("--installer-keychain", type=Path)
    parser.add_argument("--installer-password-file", type=Path)
    args = parser.parse_args()
    if bool(args.p12) != bool(args.p12_password_file):
        parser.error("--p12 and --p12-password-file must be supplied together")
    root = args.root.expanduser().resolve()
    signing = root / "store-signing"
    chain, password_file = signing / "westicker-release.keychain-db", signing / "keychain.pass"
    if not password_file.exists():
        fd = os.open(password_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    password = password_file.read_text().strip()
    commands = []
    def command(*parts):
        commands.append(" ".join(shlex.quote(str(p)) for p in parts))
    if not chain.exists():
        command("create-keychain", "-p", password, chain)
    command("unlock-keychain", "-p", password, chain)
    command("set-keychain-settings", "-lut", "14400", chain)
    if args.p12:
        command("import", args.p12.expanduser(), "-k", chain, "-P",
                args.p12_password_file.expanduser().read_text().strip(),
                "-T", "/usr/bin/codesign", "-T", "/usr/bin/security")
    command("set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", password, chain)
    # security -i echoes commands; capture and never publish that output.
    response = subprocess.run(["security", "-i"], input="\n".join(commands) + "\n",
                              text=True, capture_output=True)
    if response.returncode:
        raise RuntimeError("Private signing keychain setup failed")
    identity = subprocess.check_output(["security", "find-identity", "-v", "-p", "codesigning", str(chain)], text=True)
    if "1 valid identities found" not in identity:
        raise RuntimeError("Expected one valid distribution signing identity")
    del password, commands, response
    suffix = ".mobileprovision" if args.platform == "ios" else ".provisionprofile"
    profile, team = checked_profile(signing / (BUNDLE + suffix), args.platform)
    out = root / "releases" / f"{args.platform}-{args.version}-{args.build}"
    out.mkdir(parents=True, exist_ok=True)
    archive, export = out / "WeSticker.xcarchive", out / "export"
    old = chains()
    added = str(chain) not in old
    installer_added = False
    installer_ref, installer_locked = None, False
    sec = None
    try:
        if added:
            subprocess.run(["security", "list-keychains", "-d", "user", "-s", str(chain), *old], check=True)
        ios = args.platform == "ios"
        cwd = root / "source/apple"
        subprocess.run([str(Path.home() / ".local/xcodegen-2.46.0/bin/xcodegen"), "generate"], cwd=cwd, check=True)
        if not archive.exists():
            cmd = ["xcodebuild", "-project", "WeSticker.xcodeproj",
                   "-scheme", "WeStickerIOS" if ios else "WeStickerMac", "-configuration", "Release",
                   "-destination", "generic/platform=iOS" if ios else "generic/platform=macOS",
                   "-derivedDataPath", str(root / ("NativeReleaseDerivedData" if ios else "NativeMacDerivedData")),
                   "-archivePath", str(archive), "-jobs", "1", "archive",
                   "CURRENT_PROJECT_VERSION=" + args.build, "MARKETING_VERSION=" + args.version,
                   "DEVELOPMENT_TEAM=" + team, "CODE_SIGN_STYLE=Manual",
                   "CODE_SIGN_IDENTITY=Apple Distribution", "OTHER_CODE_SIGN_FLAGS=--keychain " + str(chain)]
            cmd.append("WESTICKER_PROFILE=" + profile["Name"])
            if not ios:
                cmd += ["ARCHS=arm64 x86_64", "ONLY_ACTIVE_ARCH=NO"]
            with (out / "archive.log").open("w") as log:
                subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)
        app = archive / "Products/Applications/WeSticker.app"
        info = plistlib.loads((app / ("Info.plist" if ios else "Contents/Info.plist")).read_bytes())
        if (info["CFBundleIdentifier"], info["CFBundleShortVersionString"], info["CFBundleVersion"]) != (BUNDLE, args.version, args.build):
            raise RuntimeError("Archive identity mismatch")
        subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], check=True)
        signing_hash = re.findall(r"\b([A-Fa-f0-9]{40})\b", identity)[0]
        opts = {"method": "app-store-connect", "destination": "export", "teamID": team,
                "signingStyle": "manual", "signingCertificate": signing_hash,
                "provisioningProfiles": {BUNDLE: profile["Name"]}, "manageAppVersionAndBuildNumber": False}
        if not ios:
            if args.installer_keychain and args.installer_password_file:
                installer_path = str(args.installer_keychain.expanduser())
                if installer_path not in chains():
                    subprocess.run(["security", "list-keychains", "-d", "user", "-s",
                                    str(chain), installer_path,
                                    *[x for x in chains() if x != str(chain)]], check=True)
                    installer_added = True
                sec = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
                sec.SecKeychainOpen.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]
                sec.SecKeychainGetStatus.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
                sec.SecKeychainUnlock.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_bool]
                sec.SecKeychainLock.argtypes = [ctypes.c_void_p]
                installer_ref = ctypes.c_void_p()
                if sec.SecKeychainOpen(str(args.installer_keychain.expanduser()).encode(), ctypes.byref(installer_ref)):
                    raise RuntimeError("Installer keychain not available")
                status = ctypes.c_uint32()
                if sec.SecKeychainGetStatus(installer_ref, ctypes.byref(status)):
                    raise RuntimeError("Cannot inspect installer keychain")
                installer_locked = not bool(status.value & 1)
                if installer_locked:
                    secret = args.installer_password_file.expanduser().read_bytes().strip()
                    if sec.SecKeychainUnlock(installer_ref, len(secret), secret, True):
                        raise RuntimeError("Installer keychain unlock failed")
                    del secret
            installed = subprocess.check_output(["security", "find-identity", "-v",
                *([str(args.installer_keychain.expanduser())] if args.installer_keychain else [])], text=True)
            installers = [line for line in installed.splitlines()
                          if "3rd Party Mac Developer Installer:" in line and team in line]
            if len(installers) != 1:
                raise RuntimeError("Expected one existing Mac installer identity")
            opts["installerSigningCertificate"] = re.findall(r"\b([A-Fa-f0-9]{40})\b", installers[0])[0]
        (out / "ExportOptions.plist").write_bytes(plistlib.dumps(opts))
        extension = "*.ipa" if ios else "*.pkg"
        if not list(export.glob(extension)):
            with (out / "export.log").open("w") as log:
                subprocess.run(["xcodebuild", "-exportArchive", "-archivePath", str(archive),
                                "-exportOptionsPlist", str(out / "ExportOptions.plist"),
                                "-exportPath", str(export)], stdout=log, stderr=subprocess.STDOUT, check=True)
        files = list(export.glob(extension))
        if len(files) != 1:
            raise RuntimeError("Expected one exported artifact")
        artifact = files[0]
        result = {"platform": args.platform, "bundle": BUNDLE, "version": args.version,
                  "build": args.build, "path": str(artifact),
                  "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                  "sdk": info.get("DTSDKName"), "scope": args.scope, "native_ui": "SwiftUI"}
        private_write(out / "manifest.json", result)
        print(json.dumps(result, indent=2))
    finally:
        if installer_ref and installer_locked and sec:
            sec.SecKeychainLock(installer_ref)
        if added:
            subprocess.run(["security", "list-keychains", "-d", "user", "-s",
                            *[x for x in chains() if x != str(chain)]], check=True)
        if installer_added:
            subprocess.run(["security", "list-keychains", "-d", "user", "-s",
                            *[x for x in chains() if x != str(args.installer_keychain.expanduser())]], check=True)
        subprocess.run(["security", "lock-keychain", str(chain)], check=True)


if __name__ == "__main__":
    main()
