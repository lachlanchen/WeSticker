"""Loopback-only UI fixture: no accounts, tokens, model calls or store operations."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import threading


@contextmanager
def native_ui_fixture(port=18649):
    state = {"mode": "authenticated", "requests": [], "unexpected": [], "link_probes": []}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            state["requests"].append(self.path)
            status = 200
            if state["mode"] == "providers" and re.fullmatch(r"/auth/(google|apple|github|lazyingart)/start\?native_link=fixture-link", self.path):
                data = b"<!doctype html><title>Native cancellation fixture</title><h1>Native cancellation fixture</h1>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            elif self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            elif self.path.startswith("/__qa/") and self.path[6:] in ("authenticated", "expired", "unavailable", "providers"):
                state["mode"] = self.path[6:]
                body = {"mode": state["mode"]}
            elif self.path == "/api/bootstrap":
                body = {"user": {"id": "ui-fixture", "consented": True} if state["mode"] == "authenticated" else None,
                        "csrf": "ui-fixture", "providers": ([] if state["mode"] == "unavailable" else
                            ["google", "apple", "github", "lazyingart", "unknown", "google"] if state["mode"] == "providers" else ["lazyingart"]),
                        "capabilities": {"chat": True, "ai_images": False, "animation": False, "native_billing": False}}
            elif self.path == "/api/workspace" and state["mode"] == "authenticated":
                body = {"packs": [], "characters": [], "jobs": [], "limits": {
                    "plan": "free", "pack_size": 16, "packs": 1, "characters": 1,
                    "credits": 0, "trial_images": 0, "animation": False}}
            else:
                status, body = 404, {"error": "Unexpected UI fixture request"}
                state["unexpected"].append(self.path)
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if state["mode"] == "providers" and self.path == "/api/native/link":
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length)) if 0 < length <= 4096 else {}
                provider = request.get("provider")
                if (provider in ("google", "apple", "github", "lazyingart") and request.get("app_return") is True
                        and re.fullmatch(r"[A-Za-z0-9_-]{43}", request.get("challenge", ""))):
                    state["link_probes"].append({"provider": provider, "app_return": True, "valid_challenge": True})
                    body = {"id": "fixture-link", "url": state["origin"] + "/auth/" + provider + "/start?native_link=fixture-link", "expires": 600}
                    data = json.dumps(body).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            state["unexpected"].append("POST " + self.path)
            self.send_error(405, "This fixture never accepts mutations")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    state["origin"] = "http://127.0.0.1:" + str(server.server_port)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
