"""Bounded, stateless conversation. Anonymous chat cannot invoke creator tools."""

import threading

import requests
from flask import abort, jsonify, request


def register_guest_chat(app, cfg):
    slots = threading.BoundedSemaphore(2)
    throttle = app.extensions["westicker"]["throttle"]

    @app.post("/api/guest/chat")
    def guest_chat():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            abort(400, description="Send a message object.")
        message, history = body.get("message"), body.get("history", [])
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2000:
            abort(400, description="Write a message of up to 2,000 characters.")
        if not isinstance(history, list) or len(history) > 12:
            abort(400, description="Conversation history is too long.")
        turns = []
        for turn in history:
            if (
                not isinstance(turn, dict)
                or turn.get("role") not in {"user", "assistant"}
                or not isinstance(turn.get("content"), str)
                or not 1 <= len(turn["content"]) <= 6000
            ):
                abort(400, description="Invalid conversation history.")
            turns.append({"role": turn["role"], "content": turn["content"]})
        if sum(len(t["content"]) for t in turns) > 16000:
            abort(400, description="Start a new conversation to continue.")
        if not cfg.get("chat_api_key"):
            abort(503, description="Chat is temporarily unavailable. Please try later.")
        # Keep client-supplied proxy headers out of the rate-limit identity.
        throttle("guest-chat:" + (request.remote_addr or "unknown"), 30, 3600)
        throttle("guest-chat:total", 240, 3600)
        if not slots.acquire(blocking=False):
            abort(429, description="Aya is busy. Please try again in a moment.")
        try:
            response = requests.post(
                cfg.get("chat_api_origin", "https://api.deepseek.com/v1").rstrip("/")
                + "/chat/completions",
                headers={"Authorization": "Bearer " + cfg["chat_api_key"]},
                json={
                    "model": cfg.get("chat_model", "deepseek-chat"),
                    "max_tokens": 1200,
                    "messages": [
                        {"role": "system", "content": (
                            "You are Aya, a friendly, concise creative assistant in WeSticker. "
                            "Chat naturally in the user's language and follow their intent. "
                            "Help brainstorm characters, everyday expressions and natural sticker gestures. "
                            "Use a short readable caption/action table when requested, otherwise converse normally. "
                            "Chat does not require an account. You have no tools in this conversation: "
                            "never claim to generate, upload, save or charge. Private cloud references, "
                            "saving and image generation are separate user-confirmed actions. "
                            "Do not ask for login just to discuss an idea."
                        )},
                        *turns,
                        {"role": "user", "content": message.strip()},
                    ],
                },
                timeout=(5, 55),
                allow_redirects=False,
            )
            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"]
            if not isinstance(reply, str) or not reply.strip():
                raise ValueError("Missing reply")
        except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
            abort(503, description="Aya could not reply just now. Your message is still here.")
        finally:
            slots.release()
        return jsonify(reply=reply.strip()[:6000])
