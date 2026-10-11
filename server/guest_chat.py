"""A clear upgrade response for the retired anonymous-chat client."""

from flask import abort


def register_guest_chat(app, cfg):
    @app.post("/api/guest/chat")
    def guest_chat():
        # Older installed builds must not bypass the account-scoped chat flow.
        abort(410, description="Please update WeSticker and sign in to Create.")
