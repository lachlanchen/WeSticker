"""Generation readiness and fail-closed moderation shared by both workers."""

import os
import base64
from pathlib import Path
import stat
from urllib.parse import urlsplit
import requests


def private_key(path):
    target = Path(path).expanduser()
    info = target.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077
            or info.st_uid != os.getuid() or info.st_nlink != 1):
        raise ValueError("Provider key must be an owner-only regular file.")
    value = target.read_text().strip()
    if not value or len(value) > 8192 or any(c.isspace() for c in value):
        raise ValueError("Invalid provider key file.")
    return value


def load_keys(cfg):
    for name in ("image_api_key", "moderation_api_key"):
        if cfg.get(name + "_file"):
            if cfg.get(name):
                raise ValueError("Choose exactly one source for each provider key.")
            cfg[name] = private_key(cfg[name + "_file"])
    return cfg


def provider_origin(value):
    parsed = urlsplit(value)
    if (parsed.username or parsed.password or parsed.query or parsed.fragment
            or not parsed.hostname or (parsed.scheme != "https" and not
            (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}))):
        raise ValueError("Provider requires HTTPS or a protected loopback endpoint.")
    return value.rstrip("/")


def safety_credentials(cfg):
    key = cfg.get("moderation_api_key") or cfg.get("image_api_key")
    if not key:
        raise ValueError("Safety provider is not connected.")
    origin = provider_origin(cfg.get("moderation_api_origin") or
                             cfg.get("image_api_origin", "https://api.openai.com/v1"))
    return origin, key


def capabilities(cfg):
    aginti = (cfg.get("image_provider") == "aginti" and cfg.get("aginti_root")
              and cfg.get("aginti_qualified") is True)
    safety = bool(cfg.get("moderation_api_key") or cfg.get("image_api_key") or aginti)
    return {
        "ai_images": bool(cfg.get("image_generation_enabled") is True
                          and (aginti or (cfg.get("image_provider", "openai") == "openai"
                              and cfg.get("image_api_key"))) and safety),
        "animation": bool(cfg.get("animation_enabled") is True
                          and cfg.get("local_video_url") and safety),
    }


def check_moderation(payload):
    results = payload.get("results") if isinstance(payload, dict) else None
    if (not isinstance(results, list) or not results
            or any(not isinstance(x, dict) or type(x.get("flagged")) is not bool
                   for x in results)):
        raise ValueError("Safety response was incomplete. Nothing was submitted.")
    if any(x["flagged"] for x in results):
        raise ValueError("This expression needs a safety review. Nothing was submitted.")


def moderate(cfg, text, paths):
    if cfg.get("image_provider") == "aginti":
        from .aginti import moderate as aginti_moderate
        return check_moderation(aginti_moderate(cfg, text, paths))
    origin, key = safety_credentials(cfg)
    result = requests.post(origin + "/moderations", headers={"Authorization": "Bearer " + key},
        json={"model": cfg["moderation_model"], "input": [
            {"type": "text", "text": text},
            *[{"type": "image_url", "image_url": {"url": "data:image/png;base64," +
                base64.b64encode(Path(p).read_bytes()).decode()}} for p in paths],
        ]}, timeout=60, allow_redirects=False)
    result.raise_for_status()
    check_moderation(result.json())
