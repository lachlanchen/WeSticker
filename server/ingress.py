"""Loopback-only worker ingress for a separately authenticated edge relay."""

from pathlib import Path
import hmac
import os
import stat

from .app import create_app


class RelayGuard:
    def __init__(self, app, secret, host):
        self.app, self.secret, self.host = app, secret, host

    def __call__(self, environ, start_response):
        relay = environ.pop("HTTP_X_WESTICKER_RELAY", "")
        if environ.get("HTTP_HOST") != self.host or not hmac.compare_digest(relay.encode(), self.secret.encode()):
            start_response("403 Forbidden", [("Content-Type", "text/plain"), ("Cache-Control", "no-store")])
            return [b"Forbidden"]
        # The edge overwrites this namespace. External Authorization is never
        # forwarded as an upstream/service credential.
        environ["HTTP_AUTHORIZATION"] = environ.pop("HTTP_X_WESTICKER_CLIENT_AUTHORIZATION", "")
        environ["REMOTE_ADDR"] = environ.pop("HTTP_X_WESTICKER_CLIENT_IP", "") or "unknown"
        return self.app(environ, start_response)


def application():
    path = Path(os.environ["WESTICKER_RELAY_FILE"])
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise RuntimeError("Relay secret requires a protected regular file")
    secret = path.read_text().strip()
    if len(secret) < 48:
        raise RuntimeError("Invalid relay secret")
    app = create_app()
    return RelayGuard(app, secret, "westicker.lazying.art")
