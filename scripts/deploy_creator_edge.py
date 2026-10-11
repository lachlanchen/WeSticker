"""Install the WeSticker-only static root, restricted tunnel and HTTPS site.

Run as root on the reviewed edge. Private inputs arrive in a protected config
file. Preserve existing TLS/firewall/app sites; validate and roll back the exact
Caddy mutation if reload fails. Does not activate identity or generation.
"""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import tarfile
import time


def run(*args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT, text=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, type=Path)
    a = p.parse_args()
    assert os.geteuid() == 0 and not a.input.is_symlink()
    assert a.input.stat().st_mode & 0o077 == 0
    cfg = json.loads(a.input.read_text())
    root = Path("/srv/westicker-creator")
    conf = Path("/etc/westicker-creator")
    caddy = Path("/etc/lazystudio/Caddyfile")
    site = conf / "Caddyfile.site"
    archive = Path(cfg["archive"])
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert digest == cfg["sha256"]
    relay = cfg["relay"]
    key = cfg["public_key"].strip()
    assert len(relay) == 64 and relay.isalnum()
    assert key.startswith("ssh-ed25519 ") and "\n" not in key
    with open("/run/lock/westicker-creator.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        baseline = caddy.read_bytes()
        assert hashlib.sha256(baseline).hexdigest() == cfg["caddy_sha256"], "Concurrent ingress edit"
        assert "admin 127.0.0.1:12019" in baseline.decode()
        assert "https_port 18443" in baseline.decode()
        firewall = run("nft", "--stateless", "--numeric", "list", "ruleset")
        root.mkdir(exist_ok=True)
        conf.mkdir(mode=0o750, exist_ok=True)
        owner = pwd.getpwnam("lazystudio")
        os.chown(conf, 0, owner.pw_gid)
        release = root / "releases" / digest[:16]
        release.mkdir(parents=True, exist_ok=True)
        total = 0
        with tarfile.open(archive) as src:
            for entry in src:
                name = Path(entry.name)
                assert entry.isfile() and not name.is_absolute() and ".." not in name.parts
                assert entry.size < 8_000_000
                total += entry.size
                assert total < 200_000_000
                dst = release / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                value = src.extractfile(entry).read()
                if dst.exists():
                    assert not dst.is_symlink() and dst.read_bytes() == value
                else:
                    with dst.open("xb") as f:
                        f.write(value)
                dst.chmod(0o644)
        assert (release / "index.html").is_file()
        username = "westicker-tunnel"
        try:
            account = pwd.getpwnam(username)
        except KeyError:
            run("useradd", "--create-home", "--shell", "/bin/false", username)
            account = pwd.getpwnam(username)
        ssh = Path(account.pw_dir) / ".ssh"
        ssh.mkdir(mode=0o700, exist_ok=True)
        os.chown(ssh, account.pw_uid, account.pw_gid)
        authorized = ssh / "authorized_keys"
        line = 'restrict,port-forwarding,permitlisten="127.0.0.1:18644",command="/bin/false" ' + key + "\n"
        if authorized.exists():
            assert authorized.read_text() == line, "Existing tunnel identity differs"
        else:
            authorized.write_text(line)
        authorized.chmod(0o600)
        os.chown(authorized, account.pw_uid, account.pw_gid)
        policy = Path("/etc/ssh/sshd_config.d/91-westicker-tunnel.conf")
        policy_text = "Match User westicker-tunnel\n    AuthenticationMethods publickey\n    PasswordAuthentication no\n    AllowTcpForwarding remote\n    PermitListen 127.0.0.1:18644\n    GatewayPorts no\n    PermitTTY no\n    X11Forwarding no\n    AllowAgentForwarding no\nMatch all\n"
        if policy.exists():
            assert policy.read_text() == policy_text
        else:
            policy.write_text(policy_text)
            run("sshd", "-t")
            run("systemctl", "reload", "ssh")
        backup = root / "backups" / str(time.time_ns())
        backup.mkdir(parents=True, mode=0o700)
        (backup / "Caddyfile").write_bytes(baseline)
        oldsite = site.read_bytes() if site.exists() else None
        if oldsite:
            (backup / "site").write_bytes(oldsite)
        content = f'''westicker.lazying.art {{
    encode zstd gzip
    header X-Content-Type-Options nosniff
    header Referrer-Policy no-referrer
    header X-Frame-Options DENY
    header Strict-Transport-Security "max-age=31536000"
    request_body {{
        max_size 21MB
    }}
    route {{
    @scanner path /.env /.git/* /wp-login.php /xmlrpc.php
    respond @scanner 404
    @service {{
        path /api/* /auth/*
        method GET HEAD POST PATCH
    }}
    handle @service {{
        reverse_proxy 127.0.0.1:18644 {{
            header_up Host westicker.lazying.art
            header_up X-Westicker-Relay {relay}
            header_up X-Westicker-Client-Authorization {{http.request.header.Authorization}}
            header_up X-Westicker-Client-IP {{remote_host}}
            header_up -Authorization
            header_up -Forwarded
            header_up -X-Real-IP
            transport http {{
                dial_timeout 2s
                response_header_timeout 150s
                read_timeout 150s
                write_timeout 150s
                max_conns_per_host 6
            }}
        }}
    }}
    @private_namespace path /api/* /auth/*
    respond @private_namespace 405
    @read method GET HEAD
    handle @read {{
        root * {release}
        @immutable path /assets/* /motion/*
        header @immutable Cache-Control "public, max-age=31536000, immutable"
        @fresh path / /index.html /sw.js /asset-manifest.json /catalog.json
        header @fresh Cache-Control "no-cache"
        file_server
    }}
    handle {{
        respond "Not found" 404
    }}
    }}
}}
'''
        site.write_text(content)
        site.chmod(0o640)
        os.chown(site, 0, owner.pw_gid)
        include = "import /etc/westicker-creator/Caddyfile.site"
        updated = baseline if include.encode() in baseline else baseline + ("\n# WeSticker independent creator service\n" + include + "\n").encode()
        candidate = caddy.with_name("Caddyfile.westicker-stage")
        candidate.write_bytes(updated)
        os.chown(candidate, caddy.stat().st_uid, caddy.stat().st_gid)
        candidate.chmod(caddy.stat().st_mode & 0o777)
        def reload():
            run("runuser", "-u", "lazystudio", "--", "caddy", "reload", "--config", str(caddy), "--adapter", "caddyfile", "--address", "127.0.0.1:12019")
        try:
            run("runuser", "-u", "lazystudio", "--", "caddy", "validate", "--config", str(candidate), "--adapter", "caddyfile")
            assert caddy.read_bytes() == baseline
            os.replace(candidate, caddy)
            reload()
            assert run("nft", "--stateless", "--numeric", "list", "ruleset") == firewall
        except BaseException:
            if oldsite:
                site.write_bytes(oldsite)
            else:
                site.unlink(missing_ok=True)
            caddy.write_bytes(baseline)
            reload()
            raise
        finally:
            candidate.unlink(missing_ok=True)
        print(json.dumps({"host": "westicker.lazying.art", "release": digest[:16], "backup": str(backup), "firewall_unchanged": True}))


if __name__ == "__main__":
    main()
