"""Optional explicit account linking and canonical, read-only LAC points.

The existing profile client remains profile-only. No reward producer, credit
conversion, purchased entitlement, wallet or financial route is registered here.
"""

import hashlib
from pathlib import Path
import secrets
import time

from flask import abort, jsonify, redirect, request, session
from werkzeug.security import check_password_hash

from .store import database, uid

ASSET = "lazyingart.fun-points.v1"
READ_SCOPE = "lac.points.balance.read"


def session_hash():
    # This browser-only consent path must not bind an unrelated native bearer.
    if request.headers.get("Authorization"):
        abort(409, description="Open account linking in the WeSticker web account page.")
    return hashlib.sha256(request.cookies.get("westicker_session", "").encode()).hexdigest()


class SharedAccount:
    def __init__(self, app, cfg):
        self.app, self.cfg = app, cfg
        self.profile = app.extensions.get("westicker_shared_identity")
        self.points = self.points_store = None
        self.unavailable = "disabled"
        directory = Path(cfg["providers"]["lazyingart"]["private_directory"]) if self.profile else None
        # Preserve revocation/cleanup access after reads are disabled; do not
        # create a new points store just by starting a profile-only deployment.
        if directory and (cfg.get("shared_points_read_enabled") is True or (directory / "points-sessions.sqlite").is_file()):
            try:
                from lazyingart_link import PointsClient, LinkStore
                from lazyingart_link.onboard import load_private
            except ImportError:
                self.unavailable = "sdk_unavailable"
            else:
                options, key = load_private(directory)
                self.points = PointsClient(options, scopes=(READ_SCOPE,), resource_origin="https://coin.lazying.art")
                self.points_store = LinkStore(directory / "points-sessions.sqlite", options, key)
                if not callable(getattr(self.points_store, "complete_pending", None)):
                    self.points = self.points_store = None
                    self.unavailable = "sdk_unavailable"

    def mapping(self, user_id):
        if not self.profile:
            return None
        with database(self.cfg) as db:
            row = db.execute("SELECT g.* FROM shared_grants g JOIN identities i ON i.user_id=g.user_id "
                             "AND i.issuer=g.issuer AND i.subject=g.subject WHERE g.user_id=?",
                             (user_id,)).fetchone()
        if row and row["issuer"] == self.profile.client.config.issuer:
            return dict(row)
        return None

    def ready(self):
        if not self.points or self.cfg.get("shared_points_read_enabled") is not True or not self.profile.enabled:
            return False
        try:
            self.points.discovery()
            return True
        except self.profile.error:
            return False

    def status(self, user):
        mapping = self.mapping(user["id"])
        ready = self.ready()
        with database(self.cfg) as db:
            connection = db.execute("SELECT state FROM shared_points_connections WHERE user_id=?",
                                    (user["id"],)).fetchone()
        return {
            "linked": mapping is not None,
            "can_link": bool(not mapping and user.get("password") and self.profile and self.profile.enabled
                             and callable(getattr(self.profile.store, "complete_pending", None))
                             and self.cfg.get("shared_account_linking_enabled") is True),
            "points": {"asset_id": ASSET, "available": ready,
                       "state": ("consented" if connection and connection["state"] == "ready" else "consent_required")
                       if ready and mapping else ("link_required" if ready else (
                           "disabled" if self.cfg.get("shared_points_read_enabled") is not True
                           else ("unavailable" if self.points else self.unavailable))),
                       "can_disconnect": connection is not None},
        }

    def start(self, purpose):
        user = self.app.extensions["westicker"]["current"]()
        self.app.extensions["westicker"]["throttle"]("shared-consent:" + user["id"], 10, 900)
        body = request.get_json() or {}
        if body.get("confirmed") is not True:
            abort(400, description="Confirm this account connection explicitly.")
        current_hash = session_hash()
        mapping = self.mapping(user["id"])
        if purpose == "link":
            if not self.status(user)["can_link"]:
                abort(409, description="Linking this account is not available. Existing accounts remain separate.")
            password = body.get("password")
            if not isinstance(password, str) or not 1 <= len(password) <= 200 or not check_password_hash(user["password"], password):
                abort(401, description="Verify your current WeSticker password.")
            client, store = self.profile.client, self.profile.store
        else:
            if not mapping or not self.ready():
                abort(503, description="Shared LAC points are not available for this account yet.")
            self.disconnect(user["id"], required=True)
            client, store = self.points, self.points_store
        binding = secrets.token_urlsafe(32)
        try:
            target = (client.authorize(store, binding, prompt="login", reuse_consent=False)
                      if purpose == "link" else client.authorize(store, binding))
        except self.profile.error:
            abort(503, description="Account connection is unavailable. Your creations are unchanged.")
        attempt = uid()
        with database(self.cfg) as db:
            db.execute("DELETE FROM shared_account_attempts WHERE created<?", (time.time() - 600,))
            db.execute("INSERT INTO shared_account_attempts VALUES(?,?,?,?,?,?)",
                       (attempt, user["id"], current_hash, purpose, mapping["subject"] if mapping else None, time.time()))
        session["shared_operation"] = {"id": attempt, "binding": binding}
        return jsonify(url=target)

    def complete(self):
        operation = session.pop("shared_operation", {})
        with database(self.cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            attempt = db.execute("SELECT * FROM shared_account_attempts WHERE id=?", (operation.get("id"),)).fetchone()
            db.execute("DELETE FROM shared_account_attempts WHERE id=?", (operation.get("id"),))
            live = db.execute("SELECT user_id FROM sessions WHERE token=? AND expires>?",
                              (session_hash(), time.time())).fetchone()
        if (not attempt or not live or attempt["created"] < time.time() - 300 or
                live["user_id"] != attempt["user_id"] or attempt["session_hash"] != session_hash()):
            abort(401, description="Account changed or connection expired. Start again from Account.")
        purpose = attempt["purpose"]
        client = self.profile.client if purpose == "link" else self.points
        store = self.profile.store if purpose == "link" else self.points_store
        if (not client or (purpose == "link" and self.cfg.get("shared_account_linking_enabled") is not True)
                or (purpose == "points" and self.cfg.get("shared_points_read_enabled") is not True)):
            abort(503, description="This account connection is disabled.")
        identifier = identity = completion_id = receipt_id = None
        accepted = False
        try:
            callback = client.config.redirect_uri + "?" + request.query_string.decode("ascii")
            completion_id, identity = store.complete_pending(client, callback, operation["binding"])
            if purpose == "link" and identity.authenticated_at < attempt["created"] - 30:
                abort(401, description="A fresh LazyingArt sign-in is required to link accounts.")
            if purpose == "points" and identity.subject != attempt["subject"]:
                abort(409, description="Use the LazyingArt identity already linked to this creator.")
            # Journal the cross-database adoption before it can create a ready
            # SDK session. Interrupted callbacks are revoked, never replayed.
            receipt_id = uid()
            with database(self.cfg) as db:
                db.execute("INSERT INTO shared_account_returns VALUES(?,?,?,?,?)",
                           (receipt_id, purpose, identity.subject, completion_id, time.time()))
            with database(self.cfg) as db:
                db.execute("BEGIN IMMEDIATE")
                # Recheck after network IO: logout, account deletion or mapping
                # changes cannot commit a late callback to another creator.
                live = db.execute("SELECT user_id FROM sessions WHERE token=? AND expires>?",
                                  (attempt["session_hash"], time.time())).fetchone()
                if not live or live["user_id"] != attempt["user_id"]:
                    abort(401, description="Sign-in changed. No connection was saved.")
                mapped = db.execute("SELECT user_id FROM identities WHERE issuer=? AND subject=?",
                                    (identity.issuer, identity.subject)).fetchone()
                prior = db.execute("SELECT issuer,subject FROM shared_grants WHERE user_id=?", (attempt["user_id"],)).fetchone()
                other_subject = db.execute("SELECT 1 FROM identities WHERE user_id=? AND issuer=? AND subject!=?",
                                           (attempt["user_id"], identity.issuer, identity.subject)).fetchone()
                if ((mapped and mapped["user_id"] != attempt["user_id"]) or
                        other_subject or (prior and tuple(prior) != (identity.issuer, identity.subject))):
                    abort(409, description="This identity belongs to another creator. No accounts were merged.")
                identifier = store.adopt_completion(completion_id, expected_subject=identity.subject)
                if purpose == "link":
                    db.execute("INSERT OR IGNORE INTO identities VALUES(?,?,?)", (identity.issuer, identity.subject, attempt["user_id"]))
                    db.execute("INSERT INTO shared_grants VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET link_id=excluded.link_id",
                               (attempt["user_id"], identity.issuer, identity.subject, identifier))
                else:
                    if not mapped or not prior:
                        abort(409, description="Account link changed. Start again from Account.")
                    db.execute("INSERT INTO shared_points_connections VALUES(?,?,?,?, 'ready','0') "
                               "ON CONFLICT(user_id) DO UPDATE SET link_id=excluded.link_id,state='ready'",
                               (attempt["user_id"], identity.issuer, identity.subject, identifier))
                db.execute("DELETE FROM shared_account_returns WHERE id=?", (receipt_id,))
            accepted = True
            return redirect(self.cfg["origin"] + "/?view=account&connection=complete")
        except self.profile.error as exc:
            if exc.code == "authorization_cancelled":
                return redirect(self.cfg["origin"] + "/?view=account&connection=cancelled")
            abort(401, description="Connection could not be verified. Your creations are unchanged.")
        except UnicodeError:
            abort(400)
        finally:
            if completion_id and not accepted:
                try:
                    if identifier:
                        store.sign_out(client, identifier, expected_subject=identity.subject)
                    else:
                        store.discard_completion(completion_id)
                    if receipt_id:
                        with database(self.cfg) as db:
                            db.execute("DELETE FROM shared_account_returns WHERE id=?", (receipt_id,))
                except self.profile.error:
                    pass

    def balance(self, user):
        if not self.points or self.cfg.get("shared_points_read_enabled") is not True:
            return {"state": self.unavailable, "asset_id": ASSET}
        mapping = self.mapping(user["id"])
        if not mapping:
            return {"state": "link_required", "asset_id": ASSET}
        with database(self.cfg) as db:
            row = db.execute("SELECT * FROM shared_points_connections WHERE user_id=?", (user["id"],)).fetchone()
        if not row or row["state"] != "ready":
            return {"state": "consent_required", "asset_id": ASSET}
        if (row["issuer"], row["subject"]) != (mapping["issuer"], mapping["subject"]):
            return {"state": "reconnect", "asset_id": ASSET}
        try:
            try:
                tokens, identity = self.points_store.session(row["link_id"], expected_subject=row["subject"])
            except self.profile.error as exc:
                if exc.code != "session_refresh_required":
                    raise
                tokens, identity = self.points_store.refresh(self.points, row["link_id"], expected_subject=row["subject"])
            snapshot = self.points.balance(tokens.access_token, expected_subject=identity.subject, minimum_revision=row["revision"])
            with database(self.cfg) as db:
                db.execute("BEGIN IMMEDIATE")
                current = db.execute("SELECT * FROM shared_points_connections WHERE user_id=?", (user["id"],)).fetchone()
                mapped = db.execute("SELECT 1 FROM identities i JOIN shared_grants g ON i.user_id=g.user_id "
                                    "AND i.issuer=g.issuer AND i.subject=g.subject WHERE i.user_id=? AND i.issuer=? AND i.subject=?",
                                    (user["id"], row["issuer"], row["subject"])).fetchone()
                if (not current or current["state"] != "ready" or current["link_id"] != row["link_id"] or
                        not mapped or int(snapshot["revision"]) < int(current["revision"])):
                    return {"state": "unavailable", "asset_id": ASSET}
                db.execute("UPDATE shared_points_connections SET revision=? WHERE user_id=?", (snapshot["revision"], user["id"]))
            return {"state": "ready", "asset_id": ASSET, "awarded_points": snapshot["awarded_points"],
                    "pending_points": snapshot["pending_points"], "as_of": snapshot["as_of"], "revision": snapshot["revision"]}
        except self.profile.error as exc:
            reconnect = exc.code in {"session_not_found", "session_reconnect_required", "invalid_token", "request_denied", "delegation_denied", "authorization_rejected"}
            return {"state": "reconnect" if reconnect else "unavailable", "asset_id": ASSET}

    def cleanup(self):
        """Operator-owned bounded cleanup; never starts login or a points read."""
        with database(self.cfg) as db:
            rows = db.execute("SELECT * FROM shared_account_returns WHERE created<? ORDER BY created LIMIT 10",
                              (time.time() - 300,)).fetchall()
        cleaned = 0
        for row in rows:
            client = self.profile.client if row["purpose"] == "link" and self.profile else self.points
            store = self.profile.store if row["purpose"] == "link" and self.profile else self.points_store
            if not client or not store:
                continue
            try:
                with store.transaction() as db:
                    sdk_row = db.execute("SELECT state,session_id FROM credential_returns WHERE id=?",
                                         (row["completion_id"],)).fetchone()
                if sdk_row and sdk_row[0] == "adopted":
                    store.sign_out(client, sdk_row[1], expected_subject=row["subject"])
                elif sdk_row:
                    store.discard_completion(row["completion_id"])
                with database(self.cfg) as db:
                    db.execute("DELETE FROM shared_account_returns WHERE id=?", (row["id"],))
                cleaned += 1
            except self.profile.error:
                continue
        returns = []
        for client, store in ((self.profile.client, self.profile.store), (self.points, self.points_store)) if self.profile else ():
            if store and callable(getattr(store, "cleanup_credentials", None)):
                returns.append(store.cleanup_credentials(client, limit=10))
        return {"reconciled": cleaned, "credential_returns": returns}

    def disconnect(self, user_id, required=False):
        with database(self.cfg) as db:
            row = db.execute("SELECT * FROM shared_points_connections WHERE user_id=?", (user_id,)).fetchone()
            if row:
                db.execute("UPDATE shared_points_connections SET state='held' WHERE user_id=?", (user_id,))
        if not row:
            return
        if not self.points:
            if required:
                abort(503, description="Points disconnection is pending. Your data is preserved.")
            return
        try:
            self.points_store.sign_out(self.points, row["link_id"], expected_subject=row["subject"])
        except self.profile.error:
            if required:
                abort(503, description="Points disconnection is pending. Please retry shortly.")
            return
        # Retain revision floor and immutable mapping across reconnects.
        with database(self.cfg) as db:
            db.execute("UPDATE shared_points_connections SET state='revoked' WHERE user_id=? AND link_id=?",
                       (user_id, row["link_id"]))


def register_shared_account(app, cfg):
    adapter = SharedAccount(app, cfg)
    app.extensions["westicker_shared_account"] = adapter
    current = app.extensions["westicker"]["current"]

    @app.get("/api/account/shared")
    def shared_status():
        return jsonify(adapter.status(current()))

    @app.post("/api/account/shared/link")
    def shared_link():
        return adapter.start("link")

    @app.post("/api/account/shared/points/consent")
    def shared_points_consent():
        return adapter.start("points")

    @app.get("/api/account/shared/points")
    def shared_points_balance():
        user = current()
        app.extensions["westicker"]["throttle"]("points-read:" + user["id"], 20, 60)
        return jsonify(adapter.balance(user))

    @app.post("/api/account/shared/points/disconnect")
    def shared_points_disconnect():
        adapter.disconnect(current()["id"], required=True)
        return jsonify(ok=True)
