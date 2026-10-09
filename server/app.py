import hashlib
import io
import json
from pathlib import Path
import secrets
import shutil
import time

from flask import Flask, abort, g, jsonify, request, send_file, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from .store import ROOT, PLANS, THEMES, audit, database, initialize, settings, uid


class PaymentRequired(HTTPException):
    code = 402
    description = "An active plan or purchase is required."


def create_app(override=None):
    cfg = settings() | (override or {})
    initialize(cfg)
    state = Path(cfg["state"])
    (state / "assets").mkdir(exist_ok=True, mode=0o700)
    secret = state / "session-secret"
    if not secret.exists():
        with secret.open("x") as stream:
            stream.write(secrets.token_hex(32))
        secret.chmod(0o600)
    app = Flask(__name__, static_folder=None)
    app.aborter.mapping[402] = PaymentRequired
    app.config.update(
        SECRET_KEY=secret.read_text(),
        MAX_CONTENT_LENGTH=21 * 1024 * 1024,
        SESSION_COOKIE_NAME="westicker_oauth",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=cfg["origin"].startswith("https:"),
        SESSION_COOKIE_SAMESITE="Lax",
    )
    app.config["WESTICKER"] = cfg

    def throttle(key, limit=60, window=60):
        now = time.time()
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM rate_limits WHERE key=?", (key,)).fetchone()
            if row and row["starts"] > now - window:
                if row["count"] >= limit:
                    abort(429, description="Please wait a moment and try again.")
                db.execute("UPDATE rate_limits SET count=count+1 WHERE key=?", (key,))
            else:
                db.execute(
                    "INSERT OR REPLACE INTO rate_limits VALUES(?,?,1)", (key, now)
                )

    def current(required=True):
        if not hasattr(g, "user"):
            token = request.cookies.get("westicker_session", "")
            with database(cfg) as db:
                row = db.execute(
                    "SELECT u.*,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?",
                    (hashlib.sha256(token.encode()).hexdigest(), time.time()),
                ).fetchone()
                g.user = dict(row) if row else None
        if required and not g.user:
            abort(401, description="Sign in to keep your creations private.")
        if (
            required
            and not g.user["consented"]
            and request.path
            not in {"/api/account/consent", "/api/account/delete", "/api/auth/logout"}
        ):
            abort(
                403, description="Confirm the creator terms and age before continuing."
            )
        return g.user

    def user_info(user):
        return (
            {
                k: user[k]
                for k in (
                    "id",
                    "name",
                    "plan",
                    "credits",
                    "expires",
                    "payout_ready",
                    "consented",
                )
            }
            if user
            else None
        )

    def owned(table, object_id):
        assert table in {"assets", "characters", "packs", "jobs"}
        user = current()
        with database(cfg) as db:
            row = db.execute(
                f"SELECT * FROM {table} WHERE id=? AND user_id=?",
                (object_id, user["id"]),
            ).fetchone()
        if not row:
            abort(404)
        return dict(row)

    def login_user(user_id, ttl=86400 * 14):
        raw = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(24)
        with database(cfg) as db:
            db.execute(
                "INSERT INTO sessions VALUES(?,?,?,?)",
                (
                    hashlib.sha256(raw.encode()).hexdigest(),
                    user_id,
                    csrf,
                    time.time() + ttl,
                ),
            )
        result = jsonify(ok=True)
        result.set_cookie(
            "westicker_session",
            raw,
            httponly=True,
            secure=cfg["origin"].startswith("https:"),
            samesite="Lax",
            max_age=ttl,
        )
        return result

    app.extensions["westicker"] = {
        "current": current,
        "owned": owned,
        "login_user": login_user,
        "throttle": throttle,
    }

    @app.before_request
    def protect():
        if (
            request.path.startswith("/api/")
            and request.is_json
            and request.method not in {"GET", "HEAD", "OPTIONS"}
        ):
            if not isinstance(request.get_json(silent=True), dict):
                abort(400, description="Expected a JSON object.")
        if (
            request.path.startswith("/api/")
            and request.method not in {"GET", "HEAD", "OPTIONS"}
            and request.path != "/api/billing/webhook"
        ):
            if request.headers.get("Origin") != cfg["origin"]:
                abort(403, description="Origin rejected.")
            user = current(False)
            if user and not secrets.compare_digest(
                request.headers.get("X-CSRF-Token", ""), user["csrf"]
            ):
                abort(403, description="Session changed. Refresh and try again.")

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob: https://aya.lazying.art; style-src 'self' 'unsafe-inline'; font-src 'self'; connect-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.path.startswith(("/api", "/auth")):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(HTTPException)
    def error(exc):
        return jsonify(error=exc.description), exc.code

    @app.get("/api/health")
    def health():
        return jsonify(ok=True, app="westicker", version="0.1.0")

    @app.get("/api/bootstrap")
    def bootstrap():
        user = current(False)
        return jsonify(
            user=user_info(user),
            csrf=user["csrf"] if user else None,
            plans=PLANS,
            themes=THEMES,
            providers=[
                p
                for p in ["google", "apple", "github", "lazyingart"]
                if cfg.get("providers", {}).get(p, {}).get("enabled")
            ],
            local_accounts=cfg["local_accounts"],
            capabilities={
                "ai_images": bool(cfg.get("image_api_key")),
                "animation": bool(
                    cfg.get("local_video_url") and cfg.get("image_api_key")
                ),
                "web_checkout": bool(
                    cfg.get("stripe_key")
                    and cfg.get("stripe_webhook_secret")
                    and cfg.get("stripe_prices")
                ),
                "native_billing": False,
                "creator_sales": bool(cfg.get("creator_sales_enabled")),
                "wechat_worker": bool(cfg.get("wechat_worker_enabled")),
            },
        )

    @app.get("/api/catalog")
    def catalog():
        default = json.loads((ROOT / "public/catalog.json").read_text())
        return jsonify(default)

    @app.post("/api/auth/register")
    def register():
        if not cfg["local_accounts"]:
            abort(503, description="Use a connected sign-in provider.")
        throttle("signup:" + request.remote_addr, 5, 3600)
        body = request.get_json() or {}
        name = str(body.get("name", "")).strip()
        email = str(body.get("email", "")).strip().lower()
        password = body.get("password", "")
        if (
            not 1 <= len(name) <= 60
            or "@" not in email
            or len(email) > 254
            or not isinstance(password, str)
            or not 12 <= len(password) <= 200
        ):
            abort(
                400,
                description="Enter a name, email and a password of at least 12 characters.",
            )
        if body.get("adult") is not True or body.get("terms") is not True:
            abort(
                400,
                description="Confirm age 18+ and the terms before creating an account.",
            )
        with database(cfg) as db:
            if db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
                abort(409, description="Account exists. Please sign in.")
            id = uid()
            db.execute(
                "INSERT INTO users(id,name,email,password,created,consented) VALUES(?,?,?,?,?,1)",
                (id, name, email, generate_password_hash(password), time.time()),
            )
            audit(db, id, "account_created", {"terms": "2026-10-10", "adult": True})
        return login_user(id)

    @app.post("/api/auth/login")
    def login():
        if not cfg["local_accounts"]:
            abort(503)
        throttle("login:" + request.remote_addr, 15, 900)
        body = request.get_json() or {}
        with database(cfg) as db:
            row = db.execute(
                "SELECT * FROM users WHERE email=?",
                (str(body.get("email", "")).lower().strip(),),
            ).fetchone()
        if (
            not row
            or not row["password"]
            or not check_password_hash(row["password"], str(body.get("password", "")))
        ):
            abort(401, description="Email or password is incorrect.")
        return login_user(row["id"])

    @app.post("/api/auth/logout")
    def logout():
        with database(cfg) as db:
            db.execute(
                "DELETE FROM sessions WHERE token=?",
                (
                    hashlib.sha256(
                        request.cookies.get("westicker_session", "").encode()
                    ).hexdigest(),
                ),
            )
        result = jsonify(ok=True)
        result.delete_cookie("westicker_session")
        return result

    @app.post("/api/account/delete")
    def delete_account():
        user = current()
        body = request.get_json() or {}
        if body.get("confirmation") != "DELETE":
            abort(400, description="Type DELETE to confirm.")
        if user["customer"]:
            app.extensions["westicker"]["cancel_for_deletion"](user)
        if list((state / "wechat" / user["id"]).glob("*/runtime.json")):
            abort(
                409,
                description="Close your active private browser before deletion. Its profile and exports will be removed too.",
            )
        with database(cfg) as db:
            if db.execute(
                "SELECT id FROM jobs WHERE user_id=? AND state IN ('running','uncertain')",
                (user["id"],),
            ).fetchone():
                abort(
                    409,
                    description="Resolve the active generation before deleting its references.",
                )
            paths = [
                r[0]
                for r in db.execute(
                    "SELECT path FROM assets WHERE user_id=?", (user["id"],)
                )
            ]
            pack_ids = [
                row[0]
                for row in db.execute(
                    "SELECT id FROM packs WHERE user_id=?", (user["id"],)
                )
            ]
            job_ids = [
                row[0]
                for row in db.execute(
                    "SELECT id FROM jobs WHERE user_id=?", (user["id"],)
                )
            ]
            db.execute("DELETE FROM users WHERE id=?", (user["id"],))
        for path in paths:
            candidate = state / path
            if candidate.is_relative_to(state / "assets"):
                candidate.unlink(missing_ok=True)
        for id in pack_ids:
            shutil.rmtree(state / "listings" / id, ignore_errors=True)
        for id in job_ids:
            shutil.rmtree(state / "renders" / id, ignore_errors=True)
        shutil.rmtree(state / "wechat" / user["id"], ignore_errors=True)
        result = jsonify(ok=True)
        result.delete_cookie("westicker_session")
        return result

    @app.post("/api/account/consent")
    def consent():
        user = current()
        body = request.get_json() or {}
        if body.get("adult") is not True or body.get("terms") is not True:
            abort(400)
        with database(cfg) as db:
            db.execute("UPDATE users SET consented=1 WHERE id=?", (user["id"],))
            audit(
                db,
                user["id"],
                "creator_terms_accepted",
                {"adult": True, "version": "2026-10-10"},
            )
        return jsonify(ok=True)

    @app.post("/api/assets")
    def upload():
        user = current()
        throttle("upload:" + user["id"], 40, 3600)
        if request.form.get("rights") != "yes":
            abort(
                400, description="Confirm you own or have permission to use this image."
            )
        file = request.files.get("file")
        if not file:
            abort(400, description="Choose an image.")
        try:
            image = Image.open(file.stream)
            if image.width * image.height > 25_000_000 or image.format not in {
                "PNG",
                "JPEG",
                "WEBP",
            }:
                abort(400, description="Use a PNG, JPEG or WebP up to 25 megapixels.")
            image = ImageOps.exif_transpose(image).convert("RGBA")
            image.thumbnail((2048, 2048))
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            abort(400, description="This image could not be decoded.")
        id = uid()
        path = Path("assets") / (id + ".png")
        image.save(state / path, format="PNG")
        digest = hashlib.sha256((state / path).read_bytes()).hexdigest()
        with database(cfg) as db:
            db.execute(
                "INSERT INTO assets VALUES(?,?,?,?,?,?,?)",
                (
                    id,
                    user["id"],
                    str(path),
                    digest,
                    "reference",
                    time.time(),
                    time.time() + 30 * 86400,
                ),
            )
            audit(
                db,
                user["id"],
                "reference_uploaded",
                {"asset": id, "rights": True, "retention_days": 30},
            )
        return jsonify(id=id, url="/api/assets/" + id, sha256=digest), 201

    @app.get("/api/assets/<id>")
    def asset(id):
        row = owned("assets", id)
        return send_file(
            state / row["path"],
            mimetype="image/gif" if row["kind"] == "animation" else "image/png",
            download_name="sticker.gif"
            if row["kind"] == "animation"
            else "sticker.png",
        )

    @app.get("/api/workspace")
    def workspace():
        user = current()
        with database(cfg) as db:
            chars = [
                dict(x)
                for x in db.execute(
                    "SELECT * FROM characters WHERE user_id=? ORDER BY created DESC",
                    (user["id"],),
                )
            ]
            packs = [
                dict(x)
                for x in db.execute(
                    "SELECT * FROM packs WHERE user_id=? ORDER BY updated DESC",
                    (user["id"],),
                )
            ]
            jobs = [
                dict(x)
                for x in db.execute(
                    "SELECT id,pack_id,kind,state,progress,error,created FROM jobs WHERE user_id=? ORDER BY created DESC LIMIT 50",
                    (user["id"],),
                )
            ]
        for c in chars:
            c["refs"] = json.loads(c["refs"])
        for p in packs:
            p["items"] = json.loads(p["items"])
        return jsonify(characters=chars, packs=packs, jobs=jobs)

    @app.post("/api/characters")
    def character():
        user = current()
        body = request.get_json() or {}
        refs = body.get("refs", [])
        if not isinstance(refs, list) or not 1 <= len(refs) <= 5:
            abort(400, description="Choose one to five reference images.")
        for ref in refs:
            owned("assets", ref)
        name = str(body.get("name", "")).strip()
        style = str(body.get("style", "figurine"))
        if (
            not name
            or len(name) > 60
            or style not in {"figurine", "soft", "ink", "photo"}
        ):
            abort(400)
        with database(cfg) as db:
            count = db.execute(
                "SELECT count(*) FROM characters WHERE user_id=?", (user["id"],)
            ).fetchone()[0]
            limit = next(
                (
                    p["packs"]
                    for p in PLANS
                    if p["id"] == user["plan"] and user["expires"] > time.time()
                ),
                2,
            )
            if count >= limit:
                abort(403, description="Your character library is full for this plan.")
            id = uid()
            db.execute(
                "INSERT INTO characters VALUES(?,?,?,?,?,?,?)",
                (id, user["id"], name, style, json.dumps(refs), 0, time.time()),
            )
        return jsonify(id=id), 201

    @app.post("/api/characters/<id>/lock")
    def lock_character(id):
        c = owned("characters", id)
        if (request.get_json() or {}).get("approved") is not True:
            abort(400)
        with database(cfg) as db:
            db.execute("UPDATE characters SET locked=1 WHERE id=?", (id,))
            audit(db, c["user_id"], "character_approved", {"id": id})
        return jsonify(ok=True)

    @app.post("/api/packs")
    def pack():
        user = current()
        body = request.get_json() or {}
        c = owned("characters", body.get("character", ""))
        if not c["locked"]:
            abort(409, description="Approve the character reference first.")
        title = str(body.get("title", "")).strip()
        theme = body.get("theme", "daily")
        language = body.get("language", "zh")
        if (
            not title
            or len(title) > 60
            or theme not in THEMES
            or language not in {"zh", "en", "ja"}
        ):
            abort(400)
        items = [
            {"id": uid(), "label": label, "asset": None, "approved": False}
            for label in THEMES[theme][language]
        ]
        id = uid()
        now = time.time()
        with database(cfg) as db:
            db.execute(
                "INSERT INTO packs VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    id,
                    user["id"],
                    c["id"],
                    title,
                    theme,
                    language,
                    json.dumps(items, ensure_ascii=False),
                    "draft",
                    99,
                    now,
                    now,
                ),
            )
        return jsonify(id=id), 201

    @app.patch("/api/packs/<id>")
    def update_pack(id):
        p = owned("packs", id)
        body = request.get_json() or {}
        items = body.get("items")
        if p["status"] != "draft":
            abort(409, description="Only drafts can be edited.")
        if not isinstance(items, list) or not 1 <= len(items) <= 24:
            abort(400)
        if any(not isinstance(item, dict) for item in items) or len(
            {str(item.get("id")) for item in items}
        ) != len(items):
            abort(400)
        old = {x["id"]: x for x in json.loads(p["items"])}
        clean = []
        for item in items:
            if (
                item.get("id") not in old
                or not isinstance(item.get("label"), str)
                or not 1 <= len(item["label"]) <= 32
            ):
                abort(400)
            asset = item.get("asset")
            if asset:
                owned("assets", asset)
            clean.append(
                {
                    "id": item["id"],
                    "label": item["label"],
                    "asset": asset,
                    "approved": item.get("approved") is True,
                }
            )
        with database(cfg) as db:
            if db.execute(
                "SELECT id FROM jobs WHERE pack_id=? AND state IN ('queued','running','uncertain')",
                (id,),
            ).fetchone():
                abort(
                    409,
                    description="Wait for the current job before editing this pack.",
                )
            db.execute(
                "UPDATE packs SET items=?,updated=? WHERE id=?",
                (json.dumps(clean, ensure_ascii=False), time.time(), id),
            )
        return jsonify(ok=True)

    @app.post("/api/packs/<id>/generate")
    def generate(id):
        p = owned("packs", id)
        user = current()
        body = request.get_json() or {}
        kind = body.get("kind", "photo")
        attempt = body.get("attempt")
        consent = body.get("consent") is True
        if not isinstance(attempt, str) or not 16 <= len(attempt) <= 64 or not consent:
            abort(400, description="Confirm generation and permissions.")
        if kind not in {"photo", "ai", "animate"}:
            abort(400)
        if kind == "ai" and not cfg.get("image_api_key"):
            abort(
                503,
                description="AI generation is not connected yet. Photo stickers work now.",
            )
        if kind == "animate":
            if not cfg.get("local_video_url") or not cfg.get("image_api_key"):
                abort(
                    503,
                    description="Animation and its safety provider are not connected.",
                )
            if user["plan"] not in {"creator", "studio"}:
                abort(403, description="Animation is available with Creator or Studio.")
        c = owned("characters", p["character_id"])
        for ref in json.loads(c["refs"]):
            image = owned("assets", ref)
            if not (state / image["path"]).is_file():
                abort(
                    409,
                    description="A reference has expired. Create a new character with fresh references.",
                )
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT * FROM jobs WHERE user_id=? AND attempt=?",
                (user["id"], attempt),
            ).fetchone()
            if prior:
                if prior["pack_id"] != id or prior["kind"] != kind:
                    abort(409)
                return jsonify(id=prior["id"], state=prior["state"])
            p = dict(
                db.execute(
                    "SELECT * FROM packs WHERE id=? AND user_id=?", (id, user["id"])
                ).fetchone()
            )
            if p["status"] != "draft":
                abort(409)
            if db.execute(
                "SELECT id FROM jobs WHERE pack_id=? AND state IN ('queued','running','uncertain')",
                (id,),
            ).fetchone():
                abort(409, description="This pack already has an active job.")
            all_items = json.loads(p["items"])
            selected = body.get("items", [item["id"] for item in all_items])
            if (
                not isinstance(selected, list)
                or not selected
                or any(not isinstance(x, str) for x in selected)
                or len(set(selected)) != len(selected)
                or not set(selected) <= {item["id"] for item in all_items}
            ):
                abort(400)
            if kind == "animate" and any(
                not x.get("approved") or not x.get("asset")
                for x in all_items
                if x["id"] in selected
            ):
                abort(409, description="Approve each still image before animating it.")
            cost = (
                len(selected) * (3 if kind == "animate" else 1)
                if kind in {"ai", "animate"}
                else 0
            )
            if cost and (
                user["expires"] <= time.time()
                or db.execute(
                    "SELECT credits FROM users WHERE id=?", (user["id"],)
                ).fetchone()[0]
                < cost
            ):
                abort(
                    402,
                    description=f"This set needs {cost} AI credits. Nothing has been submitted.",
                )
            db.execute(
                "UPDATE users SET credits=credits-? WHERE id=?", (cost, user["id"])
            )
            job = uid()
            now = time.time()
            data = {
                "cost": cost,
                "completed": 0,
                "character": p["character_id"],
                "items": all_items,
                "selected": selected,
            }
            db.execute(
                "INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    job,
                    user["id"],
                    id,
                    kind,
                    attempt,
                    "queued",
                    json.dumps(data),
                    0,
                    None,
                    now,
                    now,
                ),
            )
            audit(
                db,
                user["id"],
                "generation_requested",
                {"job": job, "credits_reserved": cost, "kind": kind},
            )
        return jsonify(id=job, state="queued"), 202

    @app.get("/api/packs/<id>/export")
    def export_pack(id):
        p = owned("packs", id)
        from .market import export_materials, zip_materials

        try:
            out = io.BytesIO(zip_materials(export_materials(cfg, p)))
        except ValueError as e:
            abort(409, description=str(e))
        return send_file(
            out,
            mimetype="application/zip",
            as_attachment=True,
            download_name="WeSticker-" + id[:8] + ".zip",
        )

    @app.post("/api/reports")
    def report():
        user = current(False)
        throttle("report:" + request.remote_addr, 10, 3600)
        body = request.get_json() or {}
        reason = str(body.get("reason", "")).strip()
        target = str(body.get("target", "")).strip()
        if not 5 <= len(reason) <= 2000 or not 1 <= len(target) <= 150:
            abort(400, description="Please describe the problem.")
        with database(cfg) as db:
            db.execute(
                "INSERT INTO reports(id,user_id,target,reason,created) VALUES(?,?,?,?,?)",
                (uid(), user["id"] if user else None, target, reason, time.time()),
            )
        return jsonify(ok=True), 201

    @app.post("/api/blocks")
    def block():
        user = current()
        creator = str((request.get_json() or {}).get("creator", ""))
        if not creator or len(creator) > 100:
            abort(400)
        with database(cfg) as db:
            db.execute(
                "INSERT OR IGNORE INTO blocks VALUES(?,?)", (user["id"], creator)
            )
        return jsonify(ok=True)

    @app.get("/api/default/<pid>/download/<language>")
    def default_download(pid, language):
        user = current()
        if user["plan"] == "free" or user["expires"] <= time.time():
            abort(
                402,
                description="A WeSticker subscription includes all default language ZIPs.",
            )
        root = cfg.get("default_artifacts")
        if not root:
            abort(503, description="Downloads are being connected.")
        root = Path(root)
        artifacts = json.loads((root / "artifacts.json").read_text())
        item = artifacts.get(pid, {}).get("languages", {}).get(language)
        if not item:
            abort(404)
        return send_file(
            root / "downloads" / item["file"],
            as_attachment=True,
            download_name=f"WeSticker-{pid}-{language}.zip",
        )

    @app.get("/api/default/<pid>/sticker/<language>/<sid>")
    def public_sticker(pid, language, sid):
        import requests

        catalog = json.loads((ROOT / "public/catalog.json").read_text())
        pack = next((p for p in catalog["packs"] if p["id"] == pid), {})
        item = next(
            (s for s in pack.get("stickers", {}).get(language, []) if s["id"] == sid),
            None,
        )
        if not item:
            abort(404)
        url = item["gif"]
        if not url.startswith("https://aya.lazying.art/media/"):
            abort(404)
        with requests.get(
            url, timeout=30, stream=True, allow_redirects=False
        ) as upstream:
            if upstream.status_code != 200:
                abort(502)
            data = bytearray()
            for chunk in upstream.iter_content(65536):
                data.extend(chunk)
                if len(data) > 2_000_000:
                    abort(502)
        return send_file(
            io.BytesIO(data),
            mimetype="image/gif",
            as_attachment=True,
            download_name=sid + ".gif",
        )

    from .auth import register_auth
    from .billing import register_billing
    from .market import register_market
    from .wechat import register_wechat
    from .native_billing import register_native_billing

    register_auth(app, cfg)
    register_billing(app, cfg)
    register_market(app, cfg)
    register_wechat(app, cfg)
    register_native_billing(app, cfg)

    @app.get("/")
    @app.get("/<path:path>")
    def frontend(path=""):
        dist = ROOT / "dist"
        if path.startswith(("api/", "auth/")):
            abort(404)
        if path and (dist / path).is_file():
            return send_from_directory(dist, path)
        return send_from_directory(dist, "index.html")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=18641)
