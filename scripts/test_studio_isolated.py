"""Run browser QA against a fresh local database without relaxing live rate limits."""

import argparse
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from server.app import create_app
from server.worker import work_once


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "test", choices=["chat", "browser", "local", "billing", "login", "downloads"], default="chat", nargs="?"
    )
    args = parser.parse_args()
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    os.environ.pop("WESTICKER_CONFIG", None)
    script = {
        "chat": "chat_studio_test.mjs",
        "browser": "browser-test.mjs",
        "local": "local_studio_test.mjs",
        "billing": "web-billing-ui-test.mjs",
        "login": "login_entry_test.mjs",
        "downloads": "collection_download_test.mjs",
    }[args.test]
    with tempfile.TemporaryDirectory(prefix="westicker-qa-") as state:
        app = create_app(
            {"state": state, "origin": "http://127.0.0.1", "local_accounts": True}
        )
        cfg = app.config["WESTICKER"]
        # Never inherit paid endpoints or credentials from an operator environment.
        for key in (
            "image_api_key",
            "chat_api_key",
            "local_video_url",
            "stripe_key",
            "providers",
        ):
            cfg.pop(key, None)
        server = make_server("127.0.0.1", 0, app, threaded=True)
        origin = f"http://127.0.0.1:{server.server_port}"
        cfg["origin"] = origin
        stop = threading.Event()

        def worker():
            while not stop.is_set():
                work_once(cfg)
                stop.wait(0.2)

        http_thread = threading.Thread(target=server.serve_forever, daemon=True)
        job_thread = threading.Thread(target=worker, daemon=True)
        http_thread.start()
        job_thread.start()
        try:
            env = os.environ | {
                "WESTICKER_TEST_URL": origin,
                "WESTICKER_URL": origin,
                "WESTICKER_PUBLIC_URL": origin,
            }
            result = subprocess.run(
                ["node", str(ROOT / "scripts" / script)],
                cwd=ROOT,
                env=env,
                timeout=300,
                check=False,
            )
            return result.returncode
        finally:
            stop.set()
            job_thread.join(10)
            server.shutdown()
            http_thread.join(10)
            server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
