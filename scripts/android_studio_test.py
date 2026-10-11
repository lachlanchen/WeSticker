"""Native UI + real local API/worker smoke test. Uses one disposable test account.

The test approves the app's S256 device link through that account's authenticated
API session. It does not represent a Google/Apple OAuth or paid-model test.
"""

import argparse
import json
import re
import sqlite3
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--apk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cfg = json.loads((root / ".config/local.json").read_text())
    assert cfg["local_accounts"] and cfg["origin"] == "http://127.0.0.1:18642"
    api = requests.Session()
    api.trust_env = False

    def request(path, data=None):
        csrf = api.get(cfg["origin"] + "/api/bootstrap").json().get("csrf") or ""
        r = api.post(
            cfg["origin"] + path,
            json=data,
            headers={"Origin": cfg["origin"], "X-CSRF-Token": csrf},
        )
        r.raise_for_status()
        return r.json()

    created = False
    process = None
    adb = str(args.sdk / "platform-tools/adb")
    serial = "emulator-5588"
    assert serial not in subprocess.check_output([adb, "devices"], text=True)
    args.out.mkdir(parents=True, exist_ok=True)

    def run(*parts):
        return subprocess.check_output([adb, "-s", serial, *parts], timeout=60)

    def tree(name=None):
        run("shell", "uiautomator", "dump", "/sdcard/westicker-studio.xml")
        raw = run("shell", "cat", "/sdcard/westicker-studio.xml")
        if name:
            (args.out / (name + ".xml")).write_bytes(raw)
            (args.out / (name + ".png")).write_bytes(run("exec-out", "screencap", "-p"))
        return ET.fromstring(raw)

    def tap(label, scroll=False):
        for _ in range(9 if scroll else 1):
            value = tree()
            for node in value.iter("node"):
                if node.get("text") == label or node.get("content-desc") == label:
                    x1, y1, x2, y2 = map(int, re.findall(r"\d+", node.get("bounds")))
                    run(
                        "shell",
                        "input",
                        "tap",
                        str((x1 + x2) // 2),
                        str((y1 + y2) // 2),
                    )
                    return
            run("shell", "input", "swipe", "540", "1650", "540", "650", "400")
            time.sleep(0.5)
        raise AssertionError("Missing control: " + label)

    try:
        request(
            "/api/auth/register",
            {
                "name": "Native QA",
                "email": f"native-qa-{uuid.uuid4().hex}@example.invalid",
                "password": uuid.uuid4().hex,
                "adult": True,
                "terms": True,
            },
        )
        created = True
        boot = api.get(cfg["origin"] + "/api/bootstrap").json()
        with (root / "public/icon-192.png").open("rb") as f:
            r = api.post(
                cfg["origin"] + "/api/assets",
                headers={"Origin": cfg["origin"], "X-CSRF-Token": boot["csrf"]},
                files={"file": ("reference.png", f, "image/png")},
                data={"rights": "yes"},
            )
            r.raise_for_status()
        char = request(
            "/api/characters",
            {"name": "Native QA friend", "style": "figurine", "refs": [r.json()["id"]]},
        )["id"]
        request(f"/api/characters/{char}/lock", {"approved": True})
        pack = request(
            "/api/packs", {"character": char, "title": "Native hello", "language": "en"}
        )["id"]
        with sqlite3.connect(Path(cfg["state"]) / "westicker.sqlite") as db:
            previous = {r[0] for r in db.execute("SELECT id FROM native_links")}
        with (args.out / "emulator.log").open("w") as log:
            process = subprocess.Popen(
                [
                    str(args.sdk / "emulator/emulator"),
                    "-avd",
                    "WeSticker_Review_API34",
                    "-port",
                    "5588",
                    "-no-window",
                    "-no-audio",
                    "-no-snapshot",
                    "-memory",
                    "2048",
                    "-cores",
                    "2",
                    "-gpu",
                    "swiftshader_indirect",
                    "-feature",
                    "-Bluetooth",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("Emulator exited")
            if (
                serial + "\tdevice"
                in subprocess.check_output([adb, "devices"], text=True)
                and run("shell", "getprop", "sys.boot_completed").strip() == b"1"
            ):
                break
            time.sleep(2)
        else:
            raise RuntimeError("Emulator timeout")
        run("shell", "svc", "bluetooth", "disable")
        run("shell", "pm", "disable-user", "--user", "0", "com.android.bluetooth")
        run("reverse", "tcp:18642", "tcp:18642")
        run("install", "-r", str(args.apk.resolve()))
        # The AVD is project-owned. Preserve installed-app state; use sign-in, not data clearing.
        run(
            "shell",
            "am",
            "start",
            "-n",
            "art.lazying.westicker.debug/art.lazying.westicker.MainActivity",
        )
        time.sleep(10)
        if any(
            n.get("text") == "Bluetooth keeps stopping" for n in tree().iter("node")
        ):
            tap("Close app")
        tap("Create")
        time.sleep(1)
        tap("Service settings")
        tap("HTTPS creator service")
        run("shell", "input", "text", cfg["origin"])
        run("shell", "input", "keyevent", "4")
        tree("01-create")
        tap("Continue with LazyingArt")
        time.sleep(4)
        with sqlite3.connect(Path(cfg["state"]) / "westicker.sqlite") as db:
            added = {r[0] for r in db.execute("SELECT id FROM native_links")} - previous
        assert len(added) == 1, "Native app must start exactly one link"
        approved = request(f"/api/native/link/{added.pop()}/approve", {"approved": True})
        run(
            "shell",
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-d",
            approved["return_url"],
            "art.lazying.westicker.debug",
        )
        time.sleep(2)
        tap("Library")
        time.sleep(1)
        tree("02-library")
        tap("Native hello")
        time.sleep(1)
        tap("Message your sticker assistant", True)
        run("shell", "input", "text", "change%s1%sto%sHowdy")
        run("shell", "input", "keyevent", "4")
        tap("Send message", True)
        time.sleep(2)
        run("shell", "input", "swipe", "540", "500", "540", "1650", "500")
        time.sleep(1)
        tap("Apply table", True)
        time.sleep(2)
        data = api.get(cfg["origin"] + "/api/workspace").json()
        p = next(p for p in data["packs"] if p["id"] == pack)
        assert p["items"][0]["label"] == "Howdy"
        tree("03-chat-and-plan")
        tap("Sticker plan")
        tap("Use uploaded photo", True)
        time.sleep(1)
        tap("Confirm generation", True)
        for _ in range(15):
            data = api.get(cfg["origin"] + "/api/workspace").json()
            if data["jobs"] and data["jobs"][0]["state"] == "review":
                break
            time.sleep(1)
        assert len(data["jobs"]) == 1 and data["jobs"][0]["state"] == "review"
        time.sleep(5)
        tree("04-generated-review")
        tap("Characters")
        time.sleep(1)
        tree("05-characters")
        assert any(n.get("text") == "Native QA friend" for n in tree().iter("node"))
        (args.out / "result.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "native_ui": "Compose",
                    "tested": [
                        "S256 link",
                        "account library",
                        "chat apply",
                        "photo job single submission",
                        "characters",
                    ],
                    "paid_render": False,
                },
                indent=2,
            )
        )
        print("Native Android chat, account linking and photo worker test passed.")
    finally:
        try:
            if created:
                request("/api/account/delete", {"confirmation": "DELETE"})
        finally:
            if process and process.poll() is None:
                try:
                    subprocess.run(
                        [adb, "-s", serial, "emu", "kill"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=15,
                        check=False,
                    )
                    process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=15)


if __name__ == "__main__":
    main()
