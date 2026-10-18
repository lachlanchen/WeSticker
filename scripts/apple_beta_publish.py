"""Upload an exact signed WeSticker artifact and attach it to internal testing.

Never creates an App Store submission or an external/public beta. Upload intent
is durable: an ambiguous upload must be reconciled, not automatically repeated.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlencode

from apple_release import Apple, BUNDLE, private_write


def existing_internal_group(api, app):
    groups = [g for g in api.list("betaGroups", app=app)
              if g["attributes"]["name"] == "WeSticker Internal"]
    if len(groups) != 1:
        raise RuntimeError("Expected one existing WeSticker Internal group; no group created")
    group = groups[0]
    if not group["attributes"]["isInternalGroup"] or api.call(
            "/v1/betaGroups/" + group["id"] + "/app")["data"]["id"] != app:
        raise RuntimeError("Wrong group")
    return group


def release_notes(action, path):
    if path is None:
        if action == "attach":
            raise ValueError("Attaching a beta requires --notes-file reviewed for this exact build")
        return None
    notes = path.read_text().strip()
    if not notes or len(notes) > 4000:
        raise ValueError("Release notes must contain 1-4000 characters")
    return notes


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["upload", "attach", "status"])
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--notes-file", type=Path, help="Reviewed release notes for this exact build")
    a = p.parse_args()
    notes = release_notes(a.action, a.notes_file)
    config = json.loads(a.config.expanduser().read_text())
    manifest = json.loads(a.manifest.expanduser().read_text())
    root = a.manifest.expanduser().parent
    if manifest["bundle"] != BUNDLE:
        raise RuntimeError("Not a WeSticker artifact")
    if manifest.get("native_ui") != "SwiftUI":
        raise RuntimeError("Only the native SwiftUI beta may be distributed")
    api = Apple(config)
    apps = api.list("apps", bundleId=BUNDLE)
    if len(apps) != 1:
        raise RuntimeError("Expected one existing WeSticker app")
    app = apps[0]["id"]
    expected = "IOS" if manifest["platform"] == "ios" else "MAC_OS"
    query = urlencode({"filter[app]": app, "filter[version]": manifest["build"], "include": "preReleaseVersion"})
    found = api.call("/v1/builds?" + query)
    versions = {v["id"]: v["attributes"] for v in found.get("included", [])}
    rows = [b for b in found["data"] if versions[b["relationships"]["preReleaseVersion"]["data"]["id"]]["platform"] == expected]
    if len(rows) > 1:
        raise RuntimeError("Ambiguous build match")
    if rows:
        v = versions[rows[0]["relationships"]["preReleaseVersion"]["data"]["id"]]
        if v["version"] != manifest["version"]:
            raise RuntimeError("Version mismatch")
    if a.action == "upload":
        if rows:
            print("Build already exists; upload not repeated.")
            return
        if (root / "upload-intent.json").exists():
            raise RuntimeError("Prior upload unresolved; inspect receipt and provider before any retry")
        artifact = Path(manifest["path"])
        if hashlib.sha256(artifact.read_bytes()).hexdigest() != manifest["sha256"]:
            raise RuntimeError("Artifact hash mismatch")
        for action in ("validate", "upload"):
            if action == "upload":
                private_write(root / "upload-intent.json", manifest)
            log = root / (action + ".log")
            fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                result = subprocess.run(["xcrun", "altool", "--" + action + "-app", "-f", str(artifact),
                    "-t", "ios" if expected == "IOS" else "macos", "--apiKey", config["key_id"],
                    "--apiIssuer", config["issuer_id"], "--output-format", "json"],
                    env=dict(os.environ, API_PRIVATE_KEYS_DIR=str(Path(config["key_file"]).expanduser().parent)),
                    stdout=f, stderr=subprocess.STDOUT)
            value = log.read_text()
            if result.returncode or any(s in value for s in ["UPLOAD FAILED", "VALIDATION FAILED", '"product-errors"', "ERROR:"]):
                raise RuntimeError("Provider did not accept " + action + "; see private log")
            if not any(s in value for s in ["UPLOAD SUCCEEDED", "VALIDATION SUCCEEDED", "No errors", '"success-message"']):
                raise RuntimeError("Provider result uncertain; reconcile")
            private_write(root / (action + "-accepted.json"), {"accepted": True, "sha256": manifest["sha256"]})
            print(action + " accepted: " + expected, flush=True)
        return
    if not rows:
        print("No processed build visible yet. No upload attempted.")
        return
    build = rows[0]
    bid = build["id"]
    state = build["attributes"]["processingState"]
    if a.action == "status" or state != "VALID":
        print(json.dumps({"platform": expected, "build": manifest["build"], "state": state}))
        return
    group = existing_internal_group(api, app)
    gid = group["id"]
    if build["attributes"].get("usesNonExemptEncryption") is None:
        api.call("/v1/builds/" + bid, {"data": {"type": "builds", "id": bid,
                 "attributes": {"usesNonExemptEncryption": False}}}, "PATCH")
    locs = api.call("/v1/builds/" + bid + "/betaBuildLocalizations")["data"]
    loc = next((v for v in locs if v["attributes"]["locale"] == "en-US"), None)
    if loc:
        api.call("/v1/betaBuildLocalizations/" + loc["id"], {"data": {"type": "betaBuildLocalizations", "id": loc["id"],
                 "attributes": {"whatsNew": notes}}}, "PATCH")
    else:
        api.call("/v1/betaBuildLocalizations", {"data": {"type": "betaBuildLocalizations",
            "attributes": {"locale": "en-US", "whatsNew": notes},
            "relationships": {"build": {"data": {"type": "builds", "id": bid}}}}})
    if not any(x["id"] == bid for x in api.call("/v1/betaGroups/" + gid + "/builds")["data"]):
        api.call("/v1/betaGroups/" + gid + "/relationships/builds", {"data": [{"type": "builds", "id": bid}]})
    result = {"app_id": app, "group_id": gid, "build_id": bid, "platform": expected, "processing": state,
              "group_contains_build": any(x["id"] == bid for x in api.call("/v1/betaGroups/" + gid + "/builds")["data"]),
              "tester_count": len(api.call("/v1/betaGroups/" + gid + "/betaTesters")["data"]),
              "beta_detail": api.call("/v1/builds/" + bid + "/buildBetaDetail")["data"]["attributes"],
              "public_submission": False}
    private_write(root / "testflight.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
