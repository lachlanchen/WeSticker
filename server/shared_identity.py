"""Optional maintained LazyingArt adapter; app drafts and billing stay local.

Install the operator's pinned lazyingart-link SDK separately. No central
credentials or SDK sources are distributed in the native app or public repo.
"""

from pathlib import Path
import secrets
import threading
import time

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
        configured = cfg["providers"]["lazyingart"].get("selected_providers", [])
        if (not isinstance(configured, list)
                or any(not isinstance(p, str) or p not in {"google", "apple", "github", "lazyingart"} for p in configured)):
            raise ValueError("Invalid shared sign-in provider selection")
        self.selected = frozenset(configured)
        self._selection_cache = (0, ())
        self._selection_lock = threading.Lock()

    def selections(self):
        """Cache presentation only; the SDK rechecks discovery at authorization."""
        discover = getattr(self.client, "available_authorization_providers", None)
        if not self.enabled or not self.selected or not callable(discover):
            return ()
        with self._selection_lock:
            if time.monotonic() >= self._selection_cache[0]:
                try:
                    names = discover()
                    if (not isinstance(names, (list, tuple))
                            or any(not isinstance(p, str) or p not in {"google", "apple", "github", "lazyingart"} for p in names)):
                        raise self.error("discovery_not_qualified")
                    choices = tuple(p for p in ("google", "apple", "github", "lazyingart")
                                    if p in self.selected and p in names)
                except self.error:
                    choices = ()
                self._selection_cache = (time.monotonic() + 30, choices)
            return self._selection_cache[1]

    def start(self, provider=None):
        binding = secrets.token_urlsafe(32)
        try:
            if provider is not None:
                if provider not in self.selections():
                    abort(503, description="This sign-in method is currently unavailable.")
                target = self.client.authorize(self.store, binding, provider=provider, reuse_consent=True)
            elif "lazyingart" in self.selections():
                target = self.client.authorize(self.store, binding, provider="lazyingart", reuse_consent=True)
            else:
                target = self.client.authorize(self.store, binding)
            session["shared_browser"] = binding
            return redirect(target)
        except self.error:
            abort(503, description="Account service is unavailable. Your drafts are preserved.")

    def complete(self):
        binding = session.pop("shared_browser", "")
        try:
            callback = self.client.config.redirect_uri + "?" + request.query_string.decode("ascii")
            tokens, identity = self.client.complete(self.store, callback, binding)
            identifier = self.store.save_session(tokens, identity)
            return identity, identifier
        except self.error as exc:
            if exc.code == "authorization_cancelled":
                return None, None
            abort(401, description="Sign-in could not be completed. Start a fresh sign-in; your draft is preserved.")
        except UnicodeError:
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
            try:
                # Each login can leave an app-bound SDK session. Revoke all of
                # this subject's sessions before erasure, including older logins.
                with self.store.transaction() as db:
                    identifiers = [r[0] for r in db.execute(
                        "SELECT id FROM sessions WHERE subject=? AND state!='revoked'",
                        (row["subject"],),
                    )]
                for identifier in identifiers:
                    self.store.sign_out(self.client, identifier, expected_subject=row["subject"])
                self.store.erase_subject(row["subject"])
            except self.error:
                abort(503, description="Account deletion is waiting for sign-in revocation. Your data is preserved; please retry deletion shortly.")
