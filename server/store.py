import contextlib
import json
import os
from pathlib import Path
import sqlite3
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def settings():
    from .generation import load_keys
    path = os.environ.get("WESTICKER_CONFIG")
    value = json.loads(Path(path).read_text()) if path else {}
    return load_keys(
        dict(
            origin="http://127.0.0.1:18642",
            state=str(ROOT / "data"),
            local_accounts=False,
            providers={},
            image_model="gpt-image-1.5",
            moderation_model="omni-moderation-latest",
        )
        | value
    )


@contextlib.contextmanager
def database(config):
    path = Path(config["state"])
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    con = sqlite3.connect(path / "westicker.sqlite", timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def initialize(config):
    with database(config) as db:
        db.executescript("""
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE, password TEXT,
 created REAL NOT NULL, plan TEXT NOT NULL DEFAULT 'free', credits INTEGER NOT NULL DEFAULT 0,
 expires REAL NOT NULL DEFAULT 0, customer TEXT, connect_id TEXT, payout_ready INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS identities(issuer TEXT NOT NULL, subject TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, UNIQUE(issuer,subject));
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,path TEXT NOT NULL,sha256 TEXT NOT NULL,kind TEXT NOT NULL,created REAL NOT NULL,expires REAL);
CREATE TABLE IF NOT EXISTS characters(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,name TEXT NOT NULL,style TEXT NOT NULL,refs TEXT NOT NULL,locked INTEGER NOT NULL DEFAULT 0,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS packs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,character_id TEXT REFERENCES characters(id),title TEXT NOT NULL,theme TEXT NOT NULL,language TEXT NOT NULL,items TEXT NOT NULL DEFAULT '[]',status TEXT NOT NULL DEFAULT 'draft',price INTEGER NOT NULL DEFAULT 99,created REAL NOT NULL,updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,pack_id TEXT NOT NULL REFERENCES packs(id) ON DELETE CASCADE,kind TEXT NOT NULL,attempt TEXT NOT NULL,state TEXT NOT NULL,data TEXT NOT NULL,progress INTEGER NOT NULL DEFAULT 0,error TEXT,created REAL NOT NULL,updated REAL NOT NULL,UNIQUE(user_id,attempt));
CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id) ON DELETE SET NULL,target TEXT NOT NULL,reason TEXT NOT NULL,created REAL NOT NULL,status TEXT NOT NULL DEFAULT 'open');
CREATE TABLE IF NOT EXISTS blocks(user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,creator TEXT NOT NULL,UNIQUE(user_id,creator));
CREATE TABLE IF NOT EXISTS checkouts(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,kind TEXT NOT NULL,target TEXT NOT NULL,session TEXT,url TEXT,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS entitlements(user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,pack_id TEXT NOT NULL,source TEXT NOT NULL,UNIQUE(user_id,pack_id));
CREATE TABLE IF NOT EXISTS billing_events(id TEXT PRIMARY KEY,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS upload_tickets(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,pack_id TEXT NOT NULL REFERENCES packs(id) ON DELETE CASCADE,digest TEXT NOT NULL,state TEXT NOT NULL,path TEXT NOT NULL,created REAL NOT NULL,UNIQUE(user_id,pack_id,digest));
CREATE TABLE IF NOT EXISTS rate_limits(key TEXT PRIMARY KEY,starts REAL NOT NULL,count INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id TEXT PRIMARY KEY,user_id TEXT,action TEXT NOT NULL,details TEXT NOT NULL,created REAL NOT NULL);
""")
        columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
        if "consented" not in columns:
            db.execute(
                "ALTER TABLE users ADD COLUMN consented INTEGER NOT NULL DEFAULT 0"
            )
        if "subscription_id" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN subscription_id TEXT")
        if "trial_images" not in columns:
            db.execute(
                "ALTER TABLE users ADD COLUMN trial_images INTEGER NOT NULL DEFAULT 1"
            )
        pack_columns = {row["name"] for row in db.execute("PRAGMA table_info(packs)")}
        if "revision" not in pack_columns:
            db.execute(
                "ALTER TABLE packs ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"
            )
        db.executescript("""
CREATE TABLE IF NOT EXISTS studio_messages(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 pack_id TEXT NOT NULL REFERENCES packs(id) ON DELETE CASCADE,attempt TEXT NOT NULL,
 text TEXT NOT NULL,result TEXT,state TEXT NOT NULL,created REAL NOT NULL,
 UNIQUE(user_id,attempt));
CREATE TABLE IF NOT EXISTS native_links(
 id TEXT PRIMARY KEY,challenge TEXT NOT NULL,user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
 expires REAL NOT NULL,used INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS shared_grants(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 issuer TEXT NOT NULL,subject TEXT NOT NULL,link_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shared_account_attempts(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 session_hash TEXT NOT NULL,purpose TEXT NOT NULL,subject TEXT,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS shared_points_connections(
 user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
 issuer TEXT NOT NULL,subject TEXT NOT NULL,link_id TEXT NOT NULL,
 state TEXT NOT NULL,revision TEXT NOT NULL DEFAULT '0',
 UNIQUE(issuer,subject));
CREATE TABLE IF NOT EXISTS shared_account_returns(
 id TEXT PRIMARY KEY,purpose TEXT NOT NULL,subject TEXT NOT NULL,
 completion_id TEXT NOT NULL,created REAL NOT NULL);
""")
        for table in ("sessions", "native_links"):
            if "auth_kind" not in {r["name"] for r in db.execute(f"PRAGMA table_info({table})")}:
                db.execute(f"ALTER TABLE {table} ADD COLUMN auth_kind TEXT NOT NULL DEFAULT 'legacy'")


def uid():
    return uuid.uuid4().hex


def audit(db, user, action, details):
    db.execute(
        "INSERT INTO audit VALUES(?,?,?,?,?)",
        (uid(), user, action, json.dumps(details, ensure_ascii=False), time.time()),
    )


PLANS = [
    dict(
        id="pocket",
        name="Pocket",
        cents=99,
        credits=3,
        packs=2,
        characters=2,
        pack_size=8,
        upload=False,
        features=[
            "All Aya & Lala language ZIPs",
            "3 AI images each month",
            "2 private character collections",
            "Photo stickers & caption editor",
        ],
    ),
    dict(
        id="creator",
        name="Creator",
        cents=999,
        credits=40,
        packs=25,
        characters=25,
        pack_size=16,
        upload=False,
        features=[
            "40 AI image credits each month",
            "25 character collections",
            "Animated sticker workflow",
            "Creator storefront application",
        ],
    ),
    dict(
        id="studio",
        name="Studio",
        cents=2499,
        credits=120,
        packs=100,
        characters=100,
        pack_size=24,
        upload=True,
        features=[
            "120 AI image credits each month",
            "100 character collections",
            "Optional WeChat draft-upload assistant",
            "Version history & export packages",
        ],
    ),
]


def limits(user):
    """Expired plans retain their files, not permission to start larger jobs."""
    plan = next(
        (p for p in PLANS if p["id"] == user["plan"] and user["expires"] > time.time()),
        None,
    )
    return {
        "plan": plan["id"] if plan else "free",
        "pack_size": plan["pack_size"] if plan else 1,
        "packs": plan["packs"] if plan else 2,
        "characters": plan["characters"] if plan else 2,
        "batch": bool(plan),
        "credits": user["credits"],
        "trial_images": user.get("trial_images", 0),
        "animation": bool(plan and plan["id"] in {"creator", "studio"}),
    }


THEMES = {
    "daily": {
        "zh": ["早呀", "谢谢", "抱抱", "好耶", "收到", "晚安", "加油", "想你"],
        "en": [
            "Morning",
            "Thank you",
            "Hug?",
            "Yay!",
            "Got it",
            "Night night",
            "You got this",
            "Miss you",
        ],
        "ja": [
            "おはよう",
            "ありがとう",
            "ぎゅっ",
            "やった",
            "了解",
            "おやすみ",
            "がんばれ",
            "会いたい",
        ],
    },
    "office": {
        "zh": [
            "收到",
            "辛苦啦",
            "我来吧",
            "没问题",
            "下班啦",
            "听不懂",
            "好想玩",
            "明天见",
        ],
        "en": [
            "On it",
            "Great work",
            "I got this",
            "No problem",
            "Clocking out",
            "Huh?",
            "Play time?",
            "See you",
        ],
        "ja": [
            "了解",
            "おつかれ",
            "任せて",
            "大丈夫",
            "退勤",
            "わからない",
            "遊ぼう",
            "また明日",
        ],
    },
    "couple": {
        "zh": ["想你", "抱抱", "亲亲", "哼", "和好吧", "给你", "陪着你", "晚安"],
        "en": [
            "Miss you",
            "Hugs",
            "Kiss kiss",
            "Hmph",
            "Friends again?",
            "For you",
            "Here for you",
            "Sweet dreams",
        ],
        "ja": [
            "会いたい",
            "ぎゅっ",
            "ちゅっ",
            "ふん",
            "仲直り",
            "どうぞ",
            "そばにいる",
            "おやすみ",
        ],
    },
    "sports": {
        "zh": ["出发", "加油", "有点重", "歇一下", "再来", "好棒", "饿了", "躺平"],
        "en": [
            "Let’s go",
            "You got this",
            "So heavy",
            "Tiny break",
            "Again!",
            "Well done",
            "Hungry",
            "Rest day",
        ],
        "ja": [
            "行こう",
            "がんばれ",
            "重い",
            "ひと休み",
            "もう一回",
            "すごい",
            "おなかすいた",
            "休もう",
        ],
    },
}
