"""App-local sessions; provider identity is issuer + subject, never email."""

import base64
import hashlib
import secrets
import re
import time
from urllib.parse import urlencode

from authlib.integrations.flask_client import OAuth
from flask import abort, redirect, request, session
from werkzeug.exceptions import HTTPException
import requests

from .store import database, uid


def provider_choices(cfg, shared=None):
    selected = shared.selections() if shared else ()
    return [p for p in ("google", "apple", "github", "lazyingart")
            if p in selected or (cfg.get("providers", {}).get(p, {}).get("enabled")
                                and not (shared and p != "lazyingart" and p in shared.selected))]


def register_auth(app, cfg):
    oauth = OAuth(app)
    providers = cfg.get("providers", {})
    shared = None
    if providers.get("lazyingart", {}).get("private_directory"):
        from .shared_identity import SharedIdentity
        shared = SharedIdentity(cfg)
        app.extensions["westicker_shared_identity"] = shared
        providers["lazyingart"]["enabled"] = shared.enabled
    for name, options in providers.items():
        if not options.get("enabled") or name == "lazyingart" or (shared and name in shared.selected):
            continue
        common = {
            "client_id": options["client_id"],
            "client_secret": options["client_secret"],
            "client_kwargs": {
                "scope": "openid email profile",
                "code_challenge_method": "S256",
            },
        }
        if name == "google":
            oauth.register(
                name,
                server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
                **common,
            )
        elif name == "apple":
            oauth.register(
                name,
                server_metadata_url="https://appleid.apple.com/.well-known/openid-configuration",
                **(
                    common
                    | {
                        "client_kwargs": {
                            "scope": "openid",
                            "code_challenge_method": "S256",
                        }
                    }
                ),
            )
        elif name == "github":
            oauth.register(
                name,
                access_token_url="https://github.com/login/oauth/access_token",
                authorize_url="https://github.com/login/oauth/authorize",
                api_base_url="https://api.github.com/",
                **(
                    common
                    | {
                        "client_kwargs": {
                            "scope": "read:user",
                            "code_challenge_method": "S256",
                        }
                    }
                ),
            )

    def return_to_app(response=None):
        intent = session.pop("native_intent", None)
        query = {"welcome": "1"}
        destination = session.pop("web_destination", None)
        if destination:
            query["view"] = destination
        if intent and intent["expires"] > time.time():
            query.pop("view", None)
            query["native_link"] = intent["id"]
            if intent["return"]:
                query["native_return"] = "1"
        target = cfg["origin"] + "/?" + urlencode(query)
        if response is None:
            return redirect(target)
        response.status_code = 302
        response.headers["Location"] = target
        return response

    def activate(issuer, subject, name, ttl=86400 * 14, grant=None):
        if not subject or len(subject) > 256:
            abort(400)
        with database(cfg) as db:
            row = db.execute(
                "SELECT user_id FROM identities WHERE issuer=? AND subject=?",
                (issuer, subject),
            ).fetchone()
            if row:
                id = row["user_id"]
            else:
                id = uid()
                db.execute(
                    "INSERT INTO users(id,name,created) VALUES(?,?,?)",
                    (id, str(name or "Creator")[:60], time.time()),
                )
                db.execute(
                    "INSERT INTO identities VALUES(?,?,?)", (issuer, subject, id)
                )
        if grant:
            shared.associate(id, *grant)
        response = app.extensions["westicker"]["login_user"](id, ttl=ttl)
        return return_to_app(response)

    @app.get("/auth/<provider>/start")
    def start(provider):
        keys = ("web_destination", "native_intent", "shared_browser")
        previous = {key: session[key] for key in keys if key in session}
        try:
            return start_checked(provider)
        except Exception:
            # An unavailable second choice must not break a pending callback.
            for key in keys:
                session.pop(key, None)
            session.update(previous)
            raise

    def start_checked(provider):
        # Only app-owned tabs may be restored; this is not an open redirect.
        session.pop("web_destination", None)
        destination = request.args.get("view")
        if destination in {"create", "library", "account"}:
            session["web_destination"] = destination
        session.pop("native_intent", None)
        link = request.args.get("native_link", "")
        if link:
            if not re.fullmatch(r"[a-f0-9]{32}", link):
                abort(400)
            with database(cfg) as db:
                row = db.execute("SELECT expires FROM native_links WHERE id=? AND used=0 AND expires>?", (link, time.time())).fetchone()
            if not row:
                abort(410, description="Sign-in expired. Return to WeSticker and try again.")
            session["native_intent"] = {"id": link, "expires": row["expires"], "return": request.args.get("native_return") == "1"}
        options = providers.get(provider, {})
        selected_shared = shared and provider != "lazyingart" and provider in shared.selected
        if ((selected_shared and not shared.enabled)
                or (not options.get("enabled") and not selected_shared)):
            abort(503, description="This sign-in provider is not connected yet.")
        app.extensions["westicker"]["throttle"](
            "oauth:" + request.remote_addr, 20, 3600
        )
        callback = cfg["origin"] + "/auth/" + provider + "/callback"
        if selected_shared:
            # Social choices still return through the single shared callback and
            # stable issuer/subject. Explicit choice never reuses a local cookie.
            return shared.start(provider)
        if provider == "lazyingart":
            if shared:
                try:
                    user = app.extensions["westicker"]["current"](False)
                except HTTPException as exc:
                    if exc.code != 401:
                        raise
                    user = None
                # Validate issuer authority, then reuse this exact app session.
                # Choosing a different social provider must not take this path.
                if user:
                    with database(cfg) as db:
                        linked = db.execute("SELECT 1 FROM shared_grants WHERE user_id=?", (user["id"],)).fetchone()
                    if linked:
                        return return_to_app()
                return shared.start()
            issuer = options["issuer"].rstrip("/")
            if not issuer.startswith("https://"):
                abort(503)
            discovery = requests.get(
                issuer + "/.well-known/lazyingart-account", timeout=15
            ).json()
            expected = {
                "authorization_endpoint": "/account/authorize",
                "token_endpoint": "/account/token",
                "profile_endpoint": "/account/profile",
            }
            if discovery.get("issuer") != issuer or any(
                discovery.get(k) != issuer + v for k, v in expected.items()
            ):
                abort(503, description="Identity service discovery failed.")
            verifier = secrets.token_urlsafe(48)
            state = secrets.token_urlsafe(32)
            session["lazyingart"] = {
                "state": state,
                "verifier": verifier,
                "created": time.time(),
            }
            challenge = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .rstrip(b"=")
                .decode()
            )
            return redirect(
                issuer
                + "/account/authorize?"
                + urlencode(
                    {
                        "response_type": "code",
                        "client_id": options["client_id"],
                        "audience": options["audience"],
                        "scope": "profile",
                        "redirect_uri": callback,
                        "state": state,
                        "code_challenge": challenge,
                        "code_challenge_method": "S256",
                    }
                )
            )
        return oauth.create_client(provider).authorize_redirect(callback)

    @app.get("/auth/<provider>/callback")
    def callback(provider):
        options = providers.get(provider, {})
        if not options.get("enabled") or (shared and provider != "lazyingart" and provider in shared.selected):
            abort(404)
        if provider == "lazyingart":
            if shared:
                identity, identifier = shared.complete()
                if identity is None:
                    session.pop("native_intent", None)
                    query = {"login": "cancelled"}
                    destination = session.pop("web_destination", None)
                    if destination:
                        query["view"] = destination
                    return redirect(cfg["origin"] + "/?" + urlencode(query))
                return activate(identity.issuer, identity.subject, identity.display_name,
                                grant=(identity, identifier))
            flow = session.pop("lazyingart", None)
            issuer = options["issuer"].rstrip("/")
            if (
                not flow
                or time.time() - flow["created"] > 600
                or not secrets.compare_digest(
                    request.args.get("state", ""), flow["state"]
                )
                or request.args.get("iss") != issuer
            ):
                abort(
                    400,
                    description="Expired or invalid sign-in. Your draft is still saved.",
                )
            if request.args.get("error"):
                return redirect(cfg["origin"] + "/?login=cancelled")
            # A one-use code exchange is never retried after an uncertain response.
            result = requests.post(
                issuer + "/account/token",
                json={
                    "grant_type": "authorization_code",
                    "code": request.args.get("code"),
                    "code_verifier": flow["verifier"],
                    "client_id": options["client_id"],
                    "audience": options["audience"],
                    "redirect_uri": cfg["origin"] + "/auth/lazyingart/callback",
                },
                timeout=20,
            )
            if result.status_code != 200:
                abort(
                    401,
                    description="Sign-in could not be completed. Please try a fresh sign-in.",
                )
            token = result.json()
            response = requests.post(
                issuer + "/account/profile",
                headers={"Authorization": "Bearer " + token["access_token"]},
                json={
                    "client_id": options["client_id"],
                    "audience": options["audience"],
                },
                timeout=15,
            )
            if response.status_code != 200:
                abort(401)
            profile = response.json()
            if (
                profile.get("client_id") != options["client_id"]
                or profile.get("account_status") != "active"
            ):
                abort(403)
            return activate(
                issuer,
                profile["subject"],
                profile["display_name"],
                ttl=min(int(token.get("expires_in", 600)), 600),
            )
        client = oauth.create_client(provider)
        try:
            token = client.authorize_access_token()
            if provider == "github":
                profile = client.get("user", token=token).json()
                return activate(
                    "https://github.com",
                    str(profile["id"]),
                    profile.get("name") or profile["login"],
                )
            profile = token.get("userinfo")
            if not profile:
                abort(401)
            issuer = (
                "https://accounts.google.com"
                if provider == "google"
                else "https://appleid.apple.com"
            )
            if profile.get("iss") != issuer:
                abort(401)
            return activate(issuer, str(profile["sub"]), profile.get("name", "Creator"))
        except (ValueError, KeyError):
            abort(401, description="Provider identity could not be verified.")
