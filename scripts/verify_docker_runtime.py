"""Start the built web image with disposable state, check it, and remove only it."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen
import uuid


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="westicker:local")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        raise SystemExit("Preserve the previous receipt; choose a new output path.")
    name = "westicker-runtime-qa-" + uuid.uuid4().hex[:12]
    created = False
    with tempfile.TemporaryDirectory(prefix="westicker-docker-qa-") as folder:
        config = Path(folder) / "config.json"
        config.write_text(json.dumps({"state": "/data", "origin": "http://localhost",
                                      "local_accounts": False}))
        # Synthetic settings only; no account/provider secrets enter this test.
        config.chmod(0o644)
        try:
            docker("run", "-d", "--name", name, "--init", "--read-only",
                   "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                   "--pids-limit", "96", "--memory", "512m", "--cpus", "1",
                   "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
                   "--tmpfs", "/data:rw,noexec,nosuid,size=32m,uid=1000,gid=1000,mode=700",
                   "--mount", f"type=bind,src={config},dst=/run/secrets/westicker.json,readonly",
                   "-p", "127.0.0.1::8000", args.image)
            created = True
            info = json.loads(docker("inspect", name))[0]
            port = info["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"]
            origin = "http://127.0.0.1:" + port
            def read(path):
                with urlopen(origin + path, timeout=3) as response:
                    return json.load(response)
            for attempt in range(30):
                try:
                    health = read("/api/health")
                    break
                except (URLError, OSError):
                    if attempt == 29:
                        raise
                    time.sleep(0.5)
            assert health.get("ok") and health.get("app") == "westicker"
            boot = read("/api/bootstrap")
            assert boot["user"] is None
            assert not boot["capabilities"]["chat"]
            assert not boot["capabilities"]["ai_images"]
            catalog = read("/api/catalog")
            assert catalog["packs"]
            with urlopen(origin + "/", timeout=3) as response:
                assert b"<html" in response.read(100000).lower()
            host = info["HostConfig"]
            assert host["ReadonlyRootfs"] and "ALL" in host["CapDrop"]
            assert info["Config"]["User"] == "westicker"
            result = {"ok": True, "image": info["Image"], "packs": len(catalog["packs"]),
                      "non_root": True, "read_only": True, "ai_requests": 0,
                      "temporary_container": name}
        finally:
            if created:
                docker("rm", "-f", name)
    result["temporary_container_removed"] = True
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as output:
            json.dump(result, output, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
