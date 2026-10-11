import os

import pytest
from werkzeug.test import Client
from werkzeug.wrappers import Response

from server import ingress


def test_untrusted_non_ascii_relay_fails_closed():
    def target(environ, start):
        raise AssertionError("Untrusted request reached the app")
    client = Client(ingress.RelayGuard(target, "private", "app.example"), Response)
    response = client.get("/", headers={"Host": "app.example", "X-Westicker-Relay": "\u00e9"})
    assert response.status_code == 403


@pytest.mark.parametrize("kind", ["symlink", "public", "directory", "hardlink"])
def test_relay_secret_requires_private_owned_regular_file(tmp_path, monkeypatch, kind):
    path = tmp_path / "relay"
    path.write_text("a" * 64)
    path.chmod(0o600)
    if kind == "symlink":
        link = tmp_path / "link"
        link.symlink_to(path)
        path = link
    elif kind == "public":
        path.chmod(0o644)
    elif kind == "directory":
        path = tmp_path
    else:
        os.link(path, tmp_path / "second")
    monkeypatch.setenv("WESTICKER_RELAY_FILE", str(path))
    monkeypatch.setattr(ingress, "create_app", lambda: pytest.fail("Validated too late"))
    with pytest.raises(RuntimeError, match="protected regular file"):
        ingress.application()
