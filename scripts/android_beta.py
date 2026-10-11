"""Build one signed WeSticker test APK/AAB using a private, stable upload key."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=int, required=True)
    parser.add_argument("--version", default="1.0")
    parser.add_argument("--scope", default="catalog beta")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = root / ".config/android-signing"
    config.mkdir(parents=True, exist_ok=True, mode=0o700)
    key, password = config / "upload.jks", config / "upload.pass"
    if key.exists() and not password.exists():
        raise RuntimeError("Existing key has no password file; do not replace it")
    if not password.exists():
        fd = os.open(password, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_hex(32))
    env = dict(os.environ, WESTICKER_KEYSTORE=str(key),
               WESTICKER_STORE_PASSWORD=password.read_text().strip(),
               WESTICKER_BUILD=str(args.build), WESTICKER_VERSION=args.version)
    env.pop("ANDROID_SDK_ROOT", None)
    java = Path(env["JAVA_HOME"]) / "bin"
    if not (java / "javac").is_file():
        raise RuntimeError("JAVA_HOME must name a complete JDK, including javac")
    build_tools = Path(env["ANDROID_HOME"]) / "build-tools"
    candidates = [p for p in build_tools.iterdir()
                  if all(x.isdigit() for x in p.name.split(".")) and (p / "apksigner").is_file()]
    if not candidates:
        raise RuntimeError("ANDROID_HOME must contain installed Android build tools")
    apksigner = max(candidates, key=lambda p: tuple(map(int, p.name.split(".")))) / "apksigner"
    if not key.exists():
        subprocess.run([str(java / "keytool"), "-genkeypair", "-keystore", str(key),
                        "-alias", "westicker-upload", "-keyalg", "RSA", "-keysize", "3072",
                        "-validity", "10000", "-dname", "CN=WeSticker, O=LazyingArt",
                        "-storepass:env", "WESTICKER_STORE_PASSWORD",
                        "-keypass:env", "WESTICKER_STORE_PASSWORD"], env=env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        key.chmod(0o600)
    out = root / ".runtime/releases" / f"android-{args.version}-{args.build}"
    out.mkdir(parents=True, exist_ok=True)
    if (out / "manifest.json").exists() or list(out.glob("*.aab")) or list(out.glob("*.apk")):
        raise RuntimeError("Artifacts exist; inspect them rather than overwrite")
    with (out / f"build-{time.time_ns()}.log").open("x") as log:
        subprocess.run(["./gradlew", "--no-daemon", "--max-workers=2",
                        "-Dorg.gradle.jvmargs=-Xmx2g",
                        "-Dorg.gradle.java.installations.paths=" + env["JAVA_HOME"],
                        "assembleRelease", "bundleRelease"], cwd=root / "android", env=env,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    artifacts = []
    for kind, source in [("apk", "apk/release/app-release.apk"),
                         ("aab", "bundle/release/app-release.aab")]:
        target = out / f"WeSticker-{args.version}-{args.build}.{kind}"
        shutil.copy2(root / "android/app/build/outputs" / source, target)
        if kind == "apk":
            subprocess.run([str(apksigner),
                            "verify", "--verbose", str(target)], check=True,
                           stdout=subprocess.DEVNULL)
        else:
            result = subprocess.run([str(java / "jarsigner"), "-verify", str(target)],
                                    check=True, capture_output=True, text=True)
            if "jar verified" not in result.stdout:
                raise RuntimeError("Bundle signature missing")
        artifacts.append({"path": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest()})
    result = {"bundle": "art.lazying.westicker", "version": args.version, "native_ui": "Jetpack Compose",
              "build": args.build, "scope": args.scope, "artifacts": artifacts}
    (out / "manifest.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
