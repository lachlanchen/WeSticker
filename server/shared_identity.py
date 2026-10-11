"""Optional maintained LazyingArt adapter; app drafts and billing stay local.

Install the operator's pinned lazyingart-link SDK separately. No central
credentials or SDK sources are distributed in the native app or public repo.
"""

from pathlib import Path
import secrets

from flask import abort, redirect, request, session

from .store import database


class SharedIdentity:
    def __init__(self, cfg):
        from lazyingart_link import Client, LinkError, LinkStore
        from lazyingart_link.onboard import load_private

        self.error = LinkError
        self.cfg = cfg
        directory = Path(cfg["providers"]["lazyingart"]["private_directory"])
        options, key = load_private(directory)
        if options.redirect_uri != cfg["origin"] + "/auth/lazyingart/callback":
            raise ValueError("Shared identity callback does not match this deployment")
        self.client = Client(options)
        self.store = LinkStore(directory / "sessions.sqlite", options, key)
        self.enabled = options.enabled

    def start(self):
        binding = secrets.token_urlsafe(32)
        session["shared_browser"] = binding
        try:
            return redirect(self.client.authorize(self.store, binding))
        except self.error:
            abort(503, description="Account service is unavailable. Your drafts are preserved.")

    def complete(self):
        binding = session.pop("shared_browser", "")
        try:
            callback = self.client.config.redirect_uri + "?" + request.query_string.decode("ascii")
            tokens, identity = self.client.complete(self.store, callback, binding)
            identifier = self.store.save_session(tokens, identity)
            return identity, identifier
        except (self.error, UnicodeError):
            abort(401, description="Sign-in could not be completed. Start a fresh sign-in; your draft is preserved.")

    def associate(self, user_id, identity, identifier):
        with database(self.cfg) as db:
            db.execute(
                "INSERT OR REPLACE INTO shared_grants VALUES(?,?,?,?)",
                (user_id, identity.issuer, identity.subject, identifier),
            )

    def validate(self, user_id):
        with database(self.cfg) as db:
            row = db.execute("SELECT * FROM shared_grants WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return
        if not self.enabled:
            abort(503, description="Shared sign-in is currently disabled. Your draft is preserved.")
        try:
            try:
                tokens, identity = self.store.session(row["link_id"], expected_subject=row["subject"])
            except self.error as exc:
                if exc.code != "session_refresh_required":
                    raise
                tokens, identity = self.store.refresh(self.client, row["link_id"], expected_subject=row["subject"])
            # Every private request checks current issuer authority, not just a
            # valid local cookie. SDK refresh has single-flight/uncertain guards.
            if self.client.introspect(tokens.access_token, expected_subject=identity.subject) is None:
                abort(401, description="Please reconnect your LazyingArt account.")
        except self.error as exc:
            code = 503 if exc.code in {"issuer_unavailable", "issuer_response_invalid"} else 401
            abort(code, description="Account verification is unavailable. Reconnect when ready; your drafts are preserved.")

    def erase(self, user_id):
        with database(self.cfg) as db:
            row = db.execute("SELECT * FROM shared_grants WHERE user_id=?", (user_id,)).fetchone()
        if row:
            self.store.erase_subject(row["subject"])
