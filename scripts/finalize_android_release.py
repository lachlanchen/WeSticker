"""Verify retained Android artifacts and write a manifest without rebuilding."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, type=Path)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--build", required=True, type=int)
    parser.add_argument("--version", default="1.0")
    args = parser.parse_args()
    out = args.dir.resolve()
    candidates = [p for p in (args.sdk / "build-tools").iterdir()
                  if re.fullmatch(r"\d+(\.\d+)+", p.name) and (p / "apksigner").is_file()]
    tools = max(candidates, key=lambda p: tuple(map(int, p.name.split("."))))
    apk = out / f"WeSticker-{args.version}-{args.build}.apk"
    aab = out / f"WeSticker-{args.version}-{args.build}.aab"
    badging = subprocess.check_output([str(tools / "aapt"), "dump", "badging", str(apk)], text=True)
    expected = f"package: name='art.lazying.westicker' versionCode='{args.build}' versionName='{args.version}'"
    if not badging.startswith(expected) or "uses-permission: name='com.android.vending.BILLING'" not in badging:
        raise RuntimeError("APK identity or Billing permission mismatch")
    signature = subprocess.check_output([str(tools / "apksigner"), "verify", "--verbose", "--print-certs", str(apk)], text=True)
    jar = subprocess.run(["jarsigner", "-verify", str(aab)], text=True, capture_output=True, check=True)
    if "jar verified." not in jar.stdout:
        raise RuntimeError("AAB signature missing")
    for name, value in [("apk-badging.txt", badging), ("apk-signature.txt", signature),
                        ("aab-signature.txt", jar.stdout + jar.stderr)]:
        path = out / name
        path.write_text(value)
        path.chmod(0o600)
    result = {"bundle": "art.lazying.westicker", "version": args.version, "build": args.build,
              "native_ui": "Jetpack Compose", "scope": "Native Account billing recovery; internal testing only",
              "billing_permission": True, "apk_signature_verified": True, "aab_signature_verified": True,
              "reused_existing_artifacts": True,
              "artifacts": [{"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                             "bytes": p.stat().st_size} for p in (apk, aab)]}
    manifest = out / "manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()) != result:
        raise RuntimeError("Existing manifest differs; do not overwrite")
    manifest.write_text(json.dumps(result, indent=2) + "\n")
    manifest.chmod(0o600)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
