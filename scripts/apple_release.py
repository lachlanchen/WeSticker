"""Scoped App Store Connect preflight and signing for WeSticker.

Run on the signing Mac with a private JSON config. No credentials are printed.
New app records must be created in App Store Connect's website.
"""

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

BUNDLE = "art.lazying.westicker"


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=")


def jwt(config):
    message = b".".join(
        b64(json.dumps(value).encode())
        for value in (
            {"alg": "ES256", "kid": config["key_id"], "typ": "JWT"},
            {"iss": config["issuer_id"], "iat": int(time.time()) - 20,
             "exp": int(time.time()) + 900, "aud": "appstoreconnect-v1"},
        )
    )
    signature = subprocess.check_output(
        ["openssl", "dgst", "-sha256", "-sign",
         str(Path(config["key_file"]).expanduser())], input=message
    )
    # P-256 signatures have two short ASN.1 integers; convert DER to JOSE.
    if signature[0] != 48 or signature[1] >= 128:
        raise ValueError("Unexpected signing signature")
    offset, parts = 2, []
    for _ in range(2):
        if signature[offset] != 2:
            raise ValueError("Unexpected signing integer")
        length = signature[offset + 1]
        offset += 2
        parts.append(int.from_bytes(signature[offset:offset + length], "big").to_bytes(32, "big"))
        offset += length
    return (message + b"." + b64(b"".join(parts))).decode()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError("Unexpected provider redirect")


class Apple:
    def __init__(self, config):
        self.token = jwt(config)
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def call(self, path, data=None, method=None):
        if not path.startswith("/v1/"):
            raise ValueError("Unsupported API scope")
        req = Request("https://api.appstoreconnect.apple.com" + path,
                      data=json.dumps(data).encode() if data is not None else None,
                      method=method,
                      headers={"Authorization": "Bearer " + self.token,
                               "Content-Type": "application/json"})
        try:
            with self.opener.open(req, timeout=60) as response:
                payload = response.read()
                return json.loads(payload) if payload else {}
        except HTTPError as exc:
            body = json.loads(exc.read())
            # Provider codes suffice for diagnosis; never emit raw transactions.
            codes = [item.get("code") for item in body.get("errors", [])]
            raise RuntimeError(f"Apple HTTP {exc.code}: {codes}") from None

    def list(self, resource, **filters):
        query = {f"filter[{key}]": value for key, value in filters.items()}
        query["limit"] = "200"
        result = self.call("/v1/" + resource + "?" + urlencode(query))
        if result.get("links", {}).get("next"):
            raise RuntimeError("Ambiguous paginated result; narrow the filter")
        return result["data"]


def private_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        os.fchmod(stream.fileno(), 0o600)
        json.dump(data, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "register-bundle", "profile", "certificates"])
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--platform", choices=["ios", "macos"], default="ios")
    args = parser.parse_args()
    config = json.loads(args.config.expanduser().read_text())
    root = Path(config["state"]).expanduser()
    api = Apple(config)
    if args.action == "certificates":
        print(json.dumps([{k: c["attributes"].get(k) for k in
                           ["certificateType", "expirationDate", "serialNumber"]} | {"id": c["id"]}
                          for c in api.list("certificates")], indent=2))
        return
    bundles = api.list("bundleIds", identifier=BUNDLE)
    apps = api.list("apps", bundleId=BUNDLE)
    if len(bundles) > 1 or len(apps) > 1:
        raise RuntimeError("Multiple matching records; refusing mutation")
    if args.action == "register-bundle" and not bundles:
        intent = root / "bundle-intent.json"
        if intent.exists():
            raise RuntimeError("An earlier registration is unresolved; reconcile first")
        private_write(intent, {"bundle": BUNDLE, "created": time.time()})
        result = api.call("/v1/bundleIds", {"data": {
            "type": "bundleIds", "attributes": {
                "identifier": BUNDLE, "name": "WeSticker", "platform": "IOS"}}})
        private_write(root / "bundle-receipt.json", result)
        bundles = api.list("bundleIds", identifier=BUNDLE)
    if args.action == "profile":
        if not bundles:
            raise RuntimeError("Register WeSticker's bundle first")
        certificate_id = config["certificate_id"]
        certificate = api.call("/v1/certificates/" + certificate_id)["data"]
        if certificate["attributes"]["certificateType"] != "DISTRIBUTION":
            raise RuntimeError("Expected an Apple Distribution certificate")
        profile_type = "IOS_APP_STORE" if args.platform == "ios" else "MAC_APP_STORE"
        name = "WeSticker App Store" if args.platform == "ios" else "WeSticker Mac App Store"
        profiles = api.list("profiles", name=name, profileType=profile_type)
        if not profiles:
            intent = root / ("profile-intent.json" if args.platform == "ios" else "mac-profile-intent.json")
            if intent.exists():
                raise RuntimeError("Earlier profile creation is unresolved")
            private_write(intent, {"bundle": BUNDLE, "created": time.time()})
            profile = api.call("/v1/profiles", {"data": {
                "type": "profiles", "attributes": {"name": name, "profileType": profile_type},
                "relationships": {"bundleId": {"data": {"type": "bundleIds", "id": bundles[0]["id"]}},
                                  "certificates": {"data": [{"type": "certificates", "id": certificate_id}]}}}})["data"]
        elif len(profiles) == 1:
            profile = profiles[0]
        else:
            raise RuntimeError("Multiple profile records")
        linked = api.call("/v1/profiles/" + profile["id"] + "/bundleId")["data"]
        if linked["attributes"]["identifier"] != BUNDLE:
            raise RuntimeError("Profile belongs to another app")
        if profile["attributes"]["profileState"] != "ACTIVE":
            raise RuntimeError("Profile is not active")
        private_write(root / ("profile.json" if args.platform == "ios" else "mac-profile.json"), profile)
        dest = root / (BUNDLE + (".mobileprovision" if args.platform == "ios" else ".provisionprofile"))
        dest.write_bytes(base64.b64decode(profile["attributes"]["profileContent"]))
        dest.chmod(0o600)
    summary = {"bundle": BUNDLE, "bundle_ids": [b["id"] for b in bundles],
               "apps": [{"id": a["id"], "name": a["attributes"]["name"]} for a in apps],
               "checked": time.time()}
    if apps:
        summary["builds"] = [{"id": b["id"], "version": b["attributes"]["version"],
                              "state": b["attributes"]["processingState"]}
                             for b in api.list("builds", app=apps[0]["id"])]
    private_write(root / "status.json", summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
