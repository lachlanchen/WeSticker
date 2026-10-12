"""Root-side static PWA deployment and scoped AYA bandwidth settings.

No application backend, login, payment, firewall or other hostname is changed.
The prior Caddyfile and PWA symlink are retained for rollback.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
from datetime import datetime, timezone

BEGIN, END = "# BEGIN AYALALA STICKERS", "# END AYALALA STICKERS"


def block(root):
    return f'''{BEGIN}
aya.lazying.art {{
    encode zstd gzip
    header X-Content-Type-Options nosniff
    header Referrer-Policy no-referrer
    header X-Frame-Options DENY
    request_body {{
        max_size 256KB
    }}
    route {{
    @scanner path /.env /.env/* /.git/* /wp-login.php /xmlrpc.php /wp-admin/*
    @hotlink {{
        path /media/* /westicker/motion/*
        header Sec-Fetch-Site cross-site
        header Sec-Fetch-Dest image
        not header_regexp Referer ^https?://(localhost|127[.]0[.]0[.]1)(:[0-9]+)?/
    }}
    @asset_write {{
        path /media/* /westicker/*
        not method GET HEAD
    }}
        respond @scanner 404
        respond @hotlink 403
        respond @asset_write 405
    redir /westicker /westicker/ 308
    handle_path /westicker/* {{
        root * {root}/current
        @versioned path /assets/* /motion/*.webp
        header @versioned Cache-Control "public, max-age=31536000, immutable"
        @art path /previews/* /icon-*.png
        header @art Cache-Control "public, max-age=86400"
        @fresh path / /index.html /sw.js /catalog.json /manifest.webmanifest /asset-manifest.json
        header @fresh Cache-Control "no-cache"
        file_server
    }}
    @media path /media/*
    handle @media {{
        root * /srv/ayalala/current/build/public
        header Cache-Control "public, max-age=86400"
        file_server
    }}
    @static path /style.css /app.js /catalog.json /i18n.json /support-i18n.json
    handle @static {{
        root * /srv/ayalala/current/build/public
        header Cache-Control "public, max-age=300"
        file_server
    }}
    handle {{
        reverse_proxy 127.0.0.1:18541 {{
            header_up X-Shop-Client {{remote_host}}
            header_up -Cookie
        }}
    }}
    }}
}}
{END}'''


def run(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def main():
    raise SystemExit(
        "The AYA /westicker/ catalog deployment is retired. "
        "Use the independent westicker.lazying.art creator deployment; "
        "see docs/legacy-entry-retirement.md. No changes were made."
    )


def historical_deploy():
    """Preserved for audit only; no CLI entry point restores the old catalog."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    p.add_argument("sha256")
    p.add_argument("--expected-caddy-sha256", required=True)
    p.add_argument("--config", type=Path, default=Path("/etc/lazystudio/Caddyfile"))
    p.add_argument("--root", type=Path, default=Path("/srv/westicker-catalog"))
    a = p.parse_args()
    assert os.geteuid() == 0
    assert hashlib.sha256(a.archive.read_bytes()).hexdigest() == a.sha256
    assert not a.config.is_symlink()
    with open("/run/lock/westicker-catalog.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        baseline = a.config.read_bytes()
        assert hashlib.sha256(baseline).hexdigest() == a.expected_caddy_sha256, "Ingress changed; inspect first"
        text = baseline.decode()
        assert text.count(BEGIN) == text.count(END) == 1
        before, rest = text.split(BEGIN)
        old_block, after = rest.split(END)
        assert "reverse_proxy 127.0.0.1:18541" in old_block
        updated = before + block(a.root) + after
        assert "admin 127.0.0.1:12019" in text and "https_port 18443" in text
        firewall = run("nft", "--stateless", "--numeric", "list", "ruleset")
        pid = run("systemctl", "show", "lazystudio-caddy", "--property=MainPID")
        release = a.root / "releases" / a.sha256[:16]
        release.mkdir(parents=True, exist_ok=True)
        total = 0
        with tarfile.open(a.archive, "r:gz") as archive:
            for member in archive:
                name = Path(member.name)
                assert member.isfile() and not name.is_absolute() and ".." not in name.parts
                assert member.size <= 8_000_000
                total += member.size
                assert total < 200_000_000
                target = release / name
                target.parent.mkdir(parents=True, exist_ok=True)
                data = archive.extractfile(member).read()
                if target.exists():
                    assert not target.is_symlink() and target.read_bytes() == data, "Staged release differs"
                else:
                    with target.open("xb") as f:
                        f.write(data)
                target.chmod(0o644)
        manifest = json.loads((release / "manifest.webmanifest").read_text())
        assert manifest["scope"] == "/westicker/" and manifest["start_url"] == "/westicker/"
        assert not (release / "api").exists()
        backup = a.root / "backups" / (a.sha256[:16] + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S"))
        backup.mkdir(parents=True, mode=0o700)
        (backup / "Caddyfile").write_bytes(baseline)
        current = a.root / "current"
        previous = current.resolve() if current.exists() else None
        (backup / "previous.json").write_text(json.dumps({"release": str(previous) if previous else None}))
        link = a.root / ".candidate"
        link.symlink_to(release)
        os.replace(link, current)
        candidate = a.config.with_name("Caddyfile.westicker-candidate")
        candidate.write_text(updated)
        st = a.config.stat()
        os.chown(candidate, st.st_uid, st.st_gid)
        candidate.chmod(st.st_mode & 0o777)
        installed = False
        def reload():
            run("runuser", "-u", "lazystudio", "--", "/usr/bin/caddy", "reload", "--config", str(a.config),
                "--adapter", "caddyfile", "--address", "127.0.0.1:12019")
        try:
            run("runuser", "-u", "lazystudio", "--", "/usr/bin/caddy", "validate", "--config", str(candidate), "--adapter", "caddyfile")
            assert a.config.read_bytes() == baseline, "Concurrent ingress edit"
            os.replace(candidate, a.config)
            installed = True
            reload()
            for path in ["/westicker/manifest.webmanifest", "/catalog.json"]:
                value = run("curl", "--noproxy", "*", "--fail", "--silent", "--show-error", "--max-time", "25",
                            "--resolve", "aya.lazying.art:18443:127.0.0.1", "https://aya.lazying.art:18443" + path)
                json.loads(value)
            assert pid == run("systemctl", "show", "lazystudio-caddy", "--property=MainPID")
            assert firewall == run("nft", "--stateless", "--numeric", "list", "ruleset")
            result = {"url": "https://aya.lazying.art/westicker/", "release": release.name,
                      "scope": "public catalog only", "firewall_unchanged": True, "backend_unchanged": True}
            (backup / "receipt.json").write_text(json.dumps(result, indent=2))
            print(json.dumps(result))
        except Exception:
            if installed and a.config.read_text() == updated:
                a.config.write_bytes(baseline)
                reload()
            if previous:
                link.symlink_to(previous)
                os.replace(link, current)
            elif current.is_symlink() and current.resolve() == release:
                current.unlink()
            raise
        finally:
            candidate.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
