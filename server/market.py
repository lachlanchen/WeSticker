"""Reviewed creator listings contain exported artwork, never original references."""

import io
import json
from pathlib import Path
import time
import zipfile

from flask import abort, jsonify, request, send_file

from .media import packaging, sticker_png, sticker_gif
from .store import audit, database


def export_materials(cfg, pack):
    items = json.loads(pack["items"])
    if not items or any(not x.get("approved") or not x.get("asset") for x in items):
        raise ValueError("Review and approve every sticker before export.")
    pictures = []
    files = {}
    with database(cfg) as db:
        for index, item in enumerate(items, 1):
            asset = db.execute(
                "SELECT * FROM assets WHERE id=? AND user_id=?",
                (item["asset"], pack["user_id"]),
            ).fetchone()
            if not asset or not (Path(cfg["state"]) / asset["path"]).is_file():
                raise ValueError("An image has expired or is unavailable.")
            pictures.append(
                sticker_png(Path(cfg["state"]) / asset["path"], item["label"], cfg)
            )
            if asset["kind"] == "animation":
                files[f"stickers/{index:02}.gif"] = sticker_gif(
                    Path(cfg["state"]) / asset["path"], item["label"], cfg
                )
            else:
                files[f"stickers/{index:02}.png"] = pictures[-1]
    files.update(packaging(pictures, pack["title"], cfg))
    files["metadata.json"] = json.dumps(
        {
            "title": pack["title"],
            "language": pack["language"],
            "words": [x["label"] for x in items],
            "format": "animated"
            if all(
                name.endswith(".gif") for name in files if name.startswith("stickers/")
            )
            else "static_or_mixed",
            "copyright": "Creator retains input rights.",
            "wechat": "Materials only. Verify the current live platform specifications before upload.",
        },
        ensure_ascii=False,
        indent=2,
    ).encode()
    return files


def zip_materials(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return out.getvalue()


def listing_dir(cfg, pack_id):
    # Database identifiers are generated internally, not paths supplied by clients.
    if len(pack_id) != 32 or any(c not in "0123456789abcdef" for c in pack_id):
        raise ValueError("Invalid pack identifier.")
    return Path(cfg["state"]) / "listings" / pack_id


def register_market(app, cfg):
    ext = app.extensions["westicker"]

    @app.get("/api/market")
    def listings():
        user = ext["current"](False)
        with database(cfg) as db:
            blocked = (
                {
                    r[0]
                    for r in db.execute(
                        "SELECT creator FROM blocks WHERE user_id=?", (user["id"],)
                    )
                }
                if user
                else set()
            )
            rows = db.execute(
                "SELECT p.id,p.title,p.language,p.price,p.items,u.id AS creator,u.name FROM packs p JOIN users u ON p.user_id=u.id WHERE p.status='listed'"
            ).fetchall()
        return jsonify(
            packs=[
                {
                    "id": r["id"],
                    "title": r["title"],
                    "language": r["language"],
                    "price": r["price"],
                    "creator": r["creator"],
                    "name": r["name"],
                    "count": len(json.loads(r["items"])),
                    "preview": f"/api/market/{r['id']}/preview/1.png",
                }
                for r in rows
                if r["creator"] not in blocked
            ]
        )

    @app.get("/api/market/<id>/preview/<int:number>.png")
    def preview(id, number):
        with database(cfg) as db:
            row = db.execute(
                "SELECT * FROM packs WHERE id=? AND status='listed'", (id,)
            ).fetchone()
        if not row or not 1 <= number <= len(json.loads(row["items"])):
            abort(404)
        return send_file(
            listing_dir(cfg, id) / f"{number:02}.png", mimetype="image/png"
        )

    @app.get("/api/market/<id>/download")
    def download(id):
        user = ext["current"]()
        with database(cfg) as db:
            row = db.execute("SELECT * FROM packs WHERE id=?", (id,)).fetchone()
            access = db.execute(
                "SELECT * FROM entitlements WHERE user_id=? AND pack_id=?",
                (user["id"], id),
            ).fetchone()
        if not row or row["status"] != "listed":
            abort(404)
        if row["user_id"] != user["id"] and not access:
            abort(402)
        return send_file(
            listing_dir(cfg, id) / "pack.zip",
            as_attachment=True,
            download_name=f"WeSticker-{id[:8]}.zip",
        )

    @app.post("/api/packs/<id>/listing")
    @app.post("/api/market/<id>/request")
    def request_listing(id):
        user = ext["current"]()
        pack = ext["owned"]("packs", id)
        body = request.get_json() or {}
        if not cfg.get("creator_sales_enabled"):
            abort(503, description="Creator sales are not open yet.")
        if not user["payout_ready"]:
            abort(409, description="Complete verified creator payout onboarding first.")
        if pack["status"] != "draft":
            abort(409, description="This collection is already under review or listed.")
        if body.get("rights") is not True or body.get("public_consent") is not True:
            abort(
                400,
                description="Confirm public sharing and commercial rights separately.",
            )
        price = body.get("price", 99)
        if type(price) is not int or not 99 <= price <= 9999:
            abort(400)
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            pack = db.execute(
                "SELECT * FROM packs WHERE id=? AND user_id=?", (id, user["id"])
            ).fetchone()
            if not pack or pack["status"] != "draft":
                abort(409, description="This collection is no longer editable.")
            if db.execute(
                "SELECT id FROM jobs WHERE pack_id=? AND state IN ('queued','running','uncertain')",
                (id,),
            ).fetchone():
                abort(409)
            # Freeze one reviewed revision under the same lock used by generation.
            try:
                files = export_materials(cfg, pack)
            except ValueError as e:
                abort(409, description=str(e))
            folder = listing_dir(cfg, id)
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            for name, data in files.items():
                if name.startswith("stickers/"):
                    if name.endswith(".gif"):
                        from PIL import Image

                        out = io.BytesIO()
                        Image.open(io.BytesIO(data)).convert("RGBA").save(out, "PNG")
                        (folder / Path(name).with_suffix(".png").name).write_bytes(
                            out.getvalue()
                        )
                    else:
                        (folder / Path(name).name).write_bytes(data)
            (folder / "pack.zip").write_bytes(zip_materials(files))
            db.execute(
                "UPDATE packs SET status='moderation',price=?,updated=? WHERE id=?",
                (price, time.time(), id),
            )
            audit(
                db,
                user["id"],
                "listing_requested",
                {"pack": id, "price": price, "public_consent": True, "rights": True},
            )
        return jsonify(status="moderation")
