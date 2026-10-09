"""Explicit export handoff to an isolated, user-owned WeChat browser."""

import hashlib
import json
from pathlib import Path
import time

from flask import abort, jsonify, request
from .market import export_materials
from .store import audit, database, uid


def register_wechat(app, cfg):
    ext = app.extensions["westicker"]

    @app.post("/api/packs/<id>/wechat")
    def queue_upload(id):
        pack = ext["owned"]("packs", id)
        user = ext["current"]()
        body = request.get_json() or {}
        if user["plan"] != "studio" or user["expires"] <= time.time():
            abort(
                403, description="Studio includes the optional draft-upload assistant."
            )
        if body.get("draft_only") is not True or body.get("consent") is not True:
            abort(400)
        if not cfg.get("wechat_worker_enabled"):
            abort(
                503,
                description="The isolated WeChat browser service is not connected. You can still export your materials.",
            )
        copyright = str(body.get("copyright", "")).strip()
        description = str(body.get("description", "")).strip()
        if not 1 <= len(copyright) <= 100 or not 5 <= len(description) <= 500:
            abort(
                400,
                description="Provide an accurate copyright holder and introduction.",
            )
        try:
            files = export_materials(cfg, pack)
        except ValueError as e:
            abort(409, description=str(e))
        digest = hashlib.sha256(
            json.dumps(
                {
                    "items": pack["items"],
                    "title": pack["title"],
                    "description": description,
                    "copyright": copyright,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        with database(cfg) as db:
            prior = db.execute(
                "SELECT * FROM upload_tickets WHERE user_id=? AND pack_id=? AND digest=?",
                (user["id"], id, digest),
            ).fetchone()
            if prior:
                return jsonify(id=prior["id"], state=prior["state"])
        ticket = uid()
        folder = Path(cfg["state"]) / "wechat" / user["id"] / ticket
        folder.mkdir(parents=True, mode=0o700)
        for name, data in files.items():
            target = folder / name
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(data)
        stickers = sorted(name for name in files if name.startswith("stickers/"))
        if len({Path(name).suffix for name in stickers}) != 1:
            abort(
                409,
                description="Choose all-static or all-animated stickers for one WeChat album.",
            )
        manifest = {
            "id": ticket,
            "owner": user["id"],
            "pack": id,
            "digest": digest,
            "mode": "draft_only",
            "format": "animated" if stickers[0].endswith(".gif") else "static",
            "title": pack["title"],
            "description": description,
            "copyright": copyright,
            "stickers": [
                {"file": filename, "meaning": item["label"]}
                for filename, item in zip(stickers, json.loads(pack["items"]))
            ],
            "approved": True,
            "created": time.time(),
        }
        (folder / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2)
        )
        with database(cfg) as db:
            db.execute(
                "INSERT INTO upload_tickets VALUES(?,?,?,?,?,?,?)",
                (
                    ticket,
                    user["id"],
                    id,
                    digest,
                    "awaiting_browser",
                    str(folder.relative_to(Path(cfg["state"]))),
                    time.time(),
                ),
            )
            audit(
                db,
                user["id"],
                "wechat_draft_requested",
                {"ticket": ticket, "pack": id, "consent": True},
            )
        return jsonify(id=ticket, state="awaiting_browser"), 202

    @app.get("/api/wechat/<ticket>")
    def status(ticket):
        user = ext["current"]()
        with database(cfg) as db:
            row = db.execute(
                "SELECT * FROM upload_tickets WHERE id=? AND user_id=?",
                (ticket, user["id"]),
            ).fetchone()
        if not row:
            abort(404)
        receipt = Path(cfg["state"]) / row["path"] / "receipt.json"
        result = json.loads(receipt.read_text()) if receipt.is_file() else {}
        return jsonify(
            id=ticket,
            state=result.get("status", row["state"]),
            message=result.get(
                "message", "Your isolated browser needs to be provisioned before login."
            ),
        )
