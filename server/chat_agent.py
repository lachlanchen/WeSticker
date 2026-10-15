"""Transport to the isolated, proposal-only AgInTi service."""

import json
from urllib.parse import urlsplit

import requests

from .generation import private_key


def available(cfg):
    if cfg.get("chat_provider") == "aginti":
        return bool(cfg.get("chat_agent_qualified") is True
                    and cfg.get("chat_agent_url") and cfg.get("chat_agent_token_file"))
    return bool(cfg.get("chat_api_key"))


def propose(cfg, pack, rows, text, maximum, history, request_id):
    if not available(cfg):
        raise ValueError("Chat agent has not been qualified")
    origin = cfg["chat_agent_url"].rstrip("/")
    url = urlsplit(origin)
    if (url.username or url.password or url.query or url.fragment or url.path
            or url.scheme not in {"http", "https"}
            or (url.scheme == "http" and url.hostname not in {"127.0.0.1", "::1", "agent"})):
        raise ValueError("Chat agent requires a fixed private endpoint")
    if not request_id or len(request_id) != 64:
        raise ValueError("Chat requires a durable request identity")
    messages = []
    for turn in history[-6:]:
        messages.append({"role": "user", "text": turn["text"][:2000]})
        previous = json.loads(turn["result"]) if turn.get("result") else None
        if previous and isinstance(previous.get("reply"), str):
            messages.append({"role": "assistant", "text": previous["reply"][:2000]})
    body = {
        "id": request_id,
        "title": pack["title"][:120],
        "language": pack["language"],
        "maximum": maximum,
        "items": [{"id": r["id"], "label": r["label"], "action": r.get("action", "")} for r in rows],
        "text": text,
        "history": messages,
    }
    with requests.Session() as session:
        session.trust_env = False
        with session.post(origin + "/propose", json=body,
                headers={"Authorization": "Bearer " + private_key(cfg["chat_agent_token_file"])},
                timeout=(3, 85), allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise ValueError("Chat agent did not complete this request")
            data = bytearray()
            for chunk in response.iter_content(8192):
                data.extend(chunk)
                if len(data) > 65536:
                    raise ValueError("Chat response exceeds its limit")
    result = json.loads(data)
    if (not isinstance(result, dict) or result.get("id") != request_id
            or result.get("engine") not in {"aginti-deepseek", "aginti-codex"}
            or not isinstance(result.get("proposal"), dict)):
        raise ValueError("Invalid chat agent response")
    return result
