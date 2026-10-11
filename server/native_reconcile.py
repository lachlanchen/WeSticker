"""Private native lookup storage and bounded, fresh-provider recovery.

Notifications only enqueue work. Never log provider exceptions, HTTP bodies,
JWTs or lookup material. The scheduler is explicit, not a Flask import thread.
"""

import argparse
import base64
from dataclasses import replace
import hashlib
import json
import os
import re
import stat
import time
import uuid

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from flask import abort, jsonify, request

from . import native_billing as billing
from .store import database

NOTIFICATION_PATHS = frozenset({
    "/api/billing/native/notifications/apple",
    "/api/billing/native/notifications/google",
})
MAX_EVENT_BYTES = 65536


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def purchase_source(purchase):
    reference = ("sha256-" + digest(purchase.reference)
                 if purchase.provider == "apple" else purchase.reference)
    return ":".join((purchase.provider, purchase.environment, reference))


def grant_key(purchase):
    return ":".join((purchase.provider, purchase.environment,
                     "sha256-" + digest(purchase.transaction)))


def validate_lookup(provider, lookup):
    pattern = r"[0-9]{1,64}" if provider == "apple" else r"[A-Za-z0-9_.\-:]{10,4096}"
    if provider not in {"apple", "google"} or not isinstance(lookup, str) or not re.fullmatch(pattern, lookup):
        raise ValueError("Invalid store lookup")


def lookup_cipher(cfg):
    """Read an operator-provisioned private key; never generate one implicitly."""
    try:
        path = cfg["native_billing"]["key_file"]
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
                raise ValueError()
            key = base64.b64decode(stream.read(129).strip(), altchars=b"-_", validate=True)
        if len(key) != 32:
            raise ValueError()
        scoped = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
                      info=(billing.BUNDLE + ":native-lookup:v1").encode()).derive(key)
        return Fernet(base64.urlsafe_b64encode(scoped))
    except Exception:
        raise RuntimeError("Native recovery key unavailable") from None


def initialize_recovery(cfg):
    with database(cfg) as db:
        db.executescript("""
CREATE TABLE IF NOT EXISTS native_lookups(
 source TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 provider TEXT NOT NULL,environment TEXT NOT NULL,ciphertext BLOB NOT NULL,
 next_attempt REAL NOT NULL DEFAULT 0,failures INTEGER NOT NULL DEFAULT 0,
 last_error TEXT,wake_version INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS native_lookups_due ON native_lookups(next_attempt);
CREATE TABLE IF NOT EXISTS native_lineage(
 predecessor TEXT PRIMARY KEY,successor TEXT NOT NULL,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS native_lineage_successor ON native_lineage(successor);
CREATE TABLE IF NOT EXISTS native_notifications(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 source TEXT NOT NULL REFERENCES native_lookups(source) ON DELETE CASCADE,
 received REAL NOT NULL);
CREATE TABLE IF NOT EXISTS native_owner_bindings(
 provider TEXT NOT NULL,binding TEXT NOT NULL,
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 PRIMARY KEY(provider,binding),UNIQUE(provider,user_id));
""")
        # Preserve recoverable legacy Apple references before hashing them.
        # Without a key leave existing rows untouched; do not discard recovery
        # material. Legacy Google tokens were never retained and need Restore.
        db.execute("BEGIN IMMEDIATE")
        for row in db.execute("SELECT * FROM native_subscriptions WHERE provider='apple'").fetchall():
            parts = row["source"].split(":", 2)
            if len(parts) == 3 and not parts[2].startswith("sha256-"):
                purchase = billing.Purchase("apple", parts[1], parts[2], "migration",
                                            billing.binding(row["user_id"], "apple"), row["product"],
                                            row["tier"], row["state"], row["expires"])
                try:
                    save_lookup(db, cfg, row["user_id"], purchase, parts[2])
                except RuntimeError:
                    continue
                hashed = ":".join(parts[:2] + ["sha256-" + digest(parts[2])])
                db.execute("UPDATE native_subscriptions SET source=? WHERE source=?", (hashed, row["source"]))
                db.execute("UPDATE users SET subscription_id=? WHERE subscription_id=?", (hashed, row["source"]))
        for row in db.execute("SELECT id FROM native_grants").fetchall():
            parts = row["id"].split(":", 2)
            if len(parts) == 3 and not parts[2].startswith("sha256-"):
                hashed = ":".join(parts[:2] + ["sha256-" + digest(parts[2])])
                db.execute("UPDATE native_grants SET id=? WHERE id=?", (hashed, row["id"]))
        for row in db.execute("SELECT id FROM users").fetchall():
            _remember_binding(db, row["id"])


def _remember_binding(db, owner):
    for provider in ("apple", "google"):
        db.execute("INSERT OR IGNORE INTO native_owner_bindings VALUES(?,?,?)",
                   (provider, billing.binding(owner, provider), owner))


def remember_binding(cfg, owner):
    with database(cfg) as db:
        _remember_binding(db, owner)


def save_lookup(db, cfg, owner, purchase, lookup):
    validate_lookup(purchase.provider, lookup)
    expected = lookup if purchase.provider == "apple" else digest(lookup)
    if expected != purchase.reference or purchase.binding != billing.binding(owner, purchase.provider):
        raise ValueError("Lookup identity mismatch")
    source = purchase_source(purchase)
    existing = db.execute("SELECT user_id FROM native_lookups WHERE source=?", (source,)).fetchone()
    if existing and existing["user_id"] != owner:
        raise ValueError("Lookup already owned")
    payload = {"app": billing.BUNDLE, "owner": owner, "source": source,
               "provider": purchase.provider, "environment": purchase.environment, "lookup": lookup}
    ciphertext = lookup_cipher(cfg).encrypt(json.dumps(payload, separators=(",", ":")).encode())
    db.execute("""INSERT INTO native_lookups(source,user_id,provider,environment,ciphertext)
        VALUES(?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET ciphertext=excluded.ciphertext""",
               (source, owner, purchase.provider, purchase.environment, ciphertext))
    _remember_binding(db, owner)


def read_lookup(cfg, row):
    try:
        payload = json.loads(lookup_cipher(cfg).decrypt(row["ciphertext"]))
        expected = {"app": billing.BUNDLE, "owner": row["user_id"], "source": row["source"],
                    "provider": row["provider"], "environment": row["environment"]}
        if any(payload.get(key) != val for key, val in expected.items()):
            raise ValueError()
        validate_lookup(row["provider"], payload["lookup"])
        ref = ("sha256-" + digest(payload["lookup"]) if row["provider"] == "apple"
               else digest(payload["lookup"]))
        if row["source"] != ":".join((row["provider"], row["environment"], ref)):
            raise ValueError()
        return payload["lookup"]
    except Exception:
        raise RuntimeError("Native recovery lookup unavailable") from None


def save_lineage(db, owner, purchase, active):
    source = purchase_source(purchase)
    superseded = db.execute("SELECT user_id FROM native_lineage WHERE predecessor=?", (source,)).fetchone()
    if superseded and superseded["user_id"] != owner:
        raise ValueError("Replacement belongs to another account")
    if purchase.replaces and active and not superseded:
        if purchase.provider != "google":
            raise ValueError("Unsupported replacement")
        predecessor = purchase_source(replace(purchase, reference=purchase.replaces))
        if predecessor == source:
            raise ValueError("Cyclic replacement")
        # A predecessor may have been superseded before its first local restore.
        # Keep an ownership tombstone even when its original lookup is unknown.
        for table, column in (("native_subscriptions", "source"), ("native_lookups", "source"),
                              ("native_lineage", "predecessor"), ("native_lineage", "successor")):
            rows = db.execute(f"SELECT user_id FROM {table} WHERE {column}=?", (predecessor,)).fetchall()
            if any(row["user_id"] != owner for row in rows):
                raise ValueError("Replacement belongs to another account")
        old = db.execute("SELECT successor FROM native_lineage WHERE predecessor=?", (predecessor,)).fetchone()
        if old and old["successor"] != source:
            raise ValueError("Conflicting replacement")
        db.execute("INSERT OR IGNORE INTO native_lineage VALUES(?,?,?)", (predecessor, source, owner))
        db.execute("UPDATE native_subscriptions SET state='superseded' WHERE source=?", (predecessor,))
    return bool(superseded)


def delete_native_account(db, owner):
    """Call inside the parent's account-deletion transaction, before users DELETE."""
    for table in ("native_notifications", "native_lookups", "native_lineage", "native_owner_bindings",
                  "native_intents", "native_grants", "native_subscriptions"):
        db.execute(f"DELETE FROM {table} WHERE user_id=?", (owner,))


def reconcile_due(cfg, *, limit=25, budget_seconds=60):
    """One single-host batch. Deadline is checked between bounded provider calls."""
    limit = max(1, min(int(limit), 100))
    deadline = time.monotonic() + max(1, min(float(budget_seconds), 300))
    result = dict(checked=0, verified=0, failed=0, busy=0, expired=0, missing_lookups=0)
    with database(cfg) as db:
        result["missing_lookups"] = db.execute("""SELECT count(*) FROM native_subscriptions s
            WHERE NOT EXISTS (SELECT 1 FROM native_lookups l WHERE l.source=s.source)""").fetchone()[0]
        result["expired"] = db.execute("""UPDATE users SET plan='free',expires=0,subscription_id=NULL
            WHERE expires<=? AND subscription_id IN (SELECT source FROM native_subscriptions)""",
            (time.time(),)).rowcount
    try:
        with billing.verification_lock(cfg, "native-reconcile-batch"):
            with database(cfg) as db:
                rows = db.execute("SELECT * FROM native_lookups WHERE next_attempt<=? ORDER BY next_attempt,source LIMIT ?",
                                  (time.time(), limit)).fetchall()
            for row in rows:
                if time.monotonic() >= deadline:
                    break
                try:
                    with billing.verification_lock(cfg, row["user_id"]):
                        # Re-read after the owner lock: a restore/deletion may
                        # have changed the row while this batch was queued.
                        with database(cfg) as db:
                            current = db.execute("SELECT * FROM native_lookups WHERE source=?", (row["source"],)).fetchone()
                        if not current or current["next_attempt"] > time.time():
                            continue
                        row = current
                        lookup = read_lookup(cfg, row)
                        result["checked"] += 1
                        billing.verify_and_deliver(cfg, row["user_id"], row["provider"], lookup, row["environment"])
                        result["verified"] += 1
                        delay = max(60, min(int(cfg.get("native_billing", {}).get("reconcile_interval", 900)), 3600))
                        _schedule(cfg, row, delay, None)
                except BlockingIOError:
                    result["busy"] += 1
                except Exception:
                    # SDK errors can embed tokens in URLs or full signed data.
                    result["failed"] += 1
                    delay = min(21600, 60 * 2 ** min(row["failures"], 9))
                    _schedule(cfg, row, delay, "verification_unavailable")
    except BlockingIOError:
        result["busy"] += 1
    return result


def _schedule(cfg, row, delay, error):
    with database(cfg) as db:
        # A notification during verification must survive this scheduling write.
        db.execute("""UPDATE native_lookups SET
            next_attempt=CASE WHEN wake_version=? THEN ? ELSE next_attempt END,
            failures=?,last_error=? WHERE source=? AND user_id=?""",
            (row["wake_version"], time.time() + delay, row["failures"] + 1 if error else 0,
             error, row["source"], row["user_id"]))


class NotificationError(Exception):
    def __init__(self, status):
        self.status = status


def apple_event(cfg, body):
    from appstoreserverlibrary.signed_data_verifier import VerificationException, VerificationStatus

    if set(body) != {"signedPayload"} or not isinstance(body.get("signedPayload"), str):
        raise NotificationError(400)
    options = cfg.get("native_billing", {}).get("apple", {})
    environments = ["Production"] + (["Sandbox"] if options.get("accept_sandbox") else [])
    notification = None
    for environment in environments:
        try:
            _, verifier = billing.apple_components(cfg, environment)
            notification = verifier.verify_and_decode_notification(body["signedPayload"])
            break
        except VerificationException as error:
            if error.status == VerificationStatus.RETRYABLE_VERIFICATION_FAILURE:
                raise NotificationError(503) from None
            if error.status not in {VerificationStatus.INVALID_ENVIRONMENT, VerificationStatus.INVALID_APP_IDENTIFIER}:
                raise NotificationError(400) from None
        except ValueError:
            raise NotificationError(503) from None
    if notification is None:
        raise NotificationError(400)
    try:
        identifier = str(uuid.UUID(notification.notificationUUID))
        kind = billing.value(notification.notificationType)
        if notification.version != "2.0" or not re.fullmatch(r"[A-Z_]{1,80}", kind):
            raise ValueError()
        data = notification.data
        if (data is None or data.bundleId != billing.BUNDLE
                or billing.value(data.environment) != environment
                or (environment == "Production" and data.appAppleId != int(options["app_id"]))):
            raise ValueError()
        if kind == "TEST":
            return None
        tx = verifier.verify_and_decode_signed_transaction(data.signedTransactionInfo)
        if tx.bundleId != billing.BUNDLE or billing.value(tx.environment) != environment:
            raise ValueError()
        billing.product_plan(cfg, "apple", tx.productId)
        validate_lookup("apple", tx.originalTransactionId)
        return identifier, tx.originalTransactionId, environment
    except VerificationException as error:
        raise NotificationError(503 if error.status == VerificationStatus.RETRYABLE_VERIFICATION_FAILURE else 400) from None
    except (ValueError, TypeError, AttributeError, KeyError):
        raise NotificationError(400) from None


def google_claims(token, audience):
    from google.auth.exceptions import GoogleAuthError, TransportError
    from google.auth.transport.requests import Request
    from google.oauth2.id_token import verify_oauth2_token

    class BoundedRequest(Request):
        def __call__(self, *args, **kwargs):
            kwargs["timeout"] = 10
            return super().__call__(*args, **kwargs)

    try:
        return verify_oauth2_token(token, BoundedRequest(), audience=audience)
    except TransportError:
        raise NotificationError(503) from None
    except (ValueError, TypeError, KeyError, GoogleAuthError):
        raise NotificationError(401) from None


def google_event(cfg, body, authorization):
    options = cfg.get("native_billing", {}).get("google", {})
    auth = options.get("notifications", {})
    if options.get("package") != billing.BUNDLE or any(
            not isinstance(auth.get(key), str) or not auth[key]
            for key in ("audience", "service_account_email", "service_account_subject", "subscription")):
        raise NotificationError(503)
    if not isinstance(authorization, str) or len(authorization) > 16384 or not authorization.startswith("Bearer "):
        raise NotificationError(401)
    claims = google_claims(authorization[7:], auth["audience"])
    if (claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
            or claims.get("aud") != auth["audience"] or claims.get("email_verified") is not True
            or claims.get("email") != auth["service_account_email"]
            or claims.get("sub") != auth["service_account_subject"]):
        raise NotificationError(401)
    try:
        if body.get("subscription") != auth["subscription"]:
            raise ValueError()
        message = body["message"]
        identifier = message["messageId"]
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9]{1,100}", identifier):
            raise ValueError()
        payload = json.loads(base64.b64decode(message["data"], validate=True))
        if payload.get("version") != "1.0" or payload.get("packageName") != billing.BUNDLE:
            raise ValueError()
        kinds = [key for key in ("subscriptionNotification", "voidedPurchaseNotification", "testNotification",
                                 "oneTimeProductNotification", "pendingRefundReviewNotification") if key in payload]
        if len(kinds) != 1 or not isinstance(payload[kinds[0]], dict):
            raise ValueError()
        kind, details = kinds[0], payload[kinds[0]]
        if kind == "testNotification":
            if details.get("version") != "1.0":
                raise ValueError()
            return None
        if kind in {"oneTimeProductNotification", "pendingRefundReviewNotification"}:
            return None
        if kind == "voidedPurchaseNotification":
            if details.get("productType") != 1:
                return None
        elif (details.get("version") != "1.0" or type(details.get("notificationType")) is not int
              or details["notificationType"] <= 0):
            raise ValueError()
        validate_lookup("google", details["purchaseToken"])
        return identifier, details["purchaseToken"], None
    except (ValueError, KeyError, TypeError, AttributeError):
        raise NotificationError(400) from None


def enqueue_notification(cfg, provider, event):
    if event is None:
        return "ignored"
    identifier, lookup, environment = event
    event_id = digest(billing.BUNDLE + ":" + provider + ":" + identifier)
    reference = "sha256-" + digest(lookup) if provider == "apple" else digest(lookup)
    with database(cfg) as db:
        if db.execute("SELECT 1 FROM native_notifications WHERE id=?", (event_id,)).fetchone():
            return "duplicate"
        if environment:
            row = db.execute("SELECT * FROM native_lookups WHERE source=?",
                             (":".join((provider, environment, reference)),)).fetchone()
        else:
            rows = db.execute("SELECT * FROM native_lookups WHERE source IN (?,?)",
                              tuple(":".join((provider, env, reference)) for env in ("Sandbox", "Production"))).fetchall()
            if len(rows) > 1:
                raise ValueError("Ambiguous store environment")
            row = rows[0] if rows else None
    purchase = None
    if row:
        owner, source = row["user_id"], row["source"]
    else:
        # A notification may arrive before client delivery. Resolve the owner
        # from fresh provider truth, never an event's claimed account or tier.
        lookup_cipher(cfg)
        if provider == "apple":
            purchase = billing.verify_apple(cfg, lookup, environment)
        else:
            purchase, _, session = billing.verify_google(cfg, lookup)
            if hasattr(session, "close"):
                session.close()
        with database(cfg) as db:
            account = db.execute("SELECT user_id FROM native_owner_bindings WHERE provider=? AND binding=?",
                                 (provider, purchase.binding)).fetchone()
            if not account and provider == "apple":
                account = db.execute("SELECT id AS user_id FROM users WHERE id=?",
                                     (uuid.UUID(purchase.binding).hex,)).fetchone()
        if not account:
            return "unowned"  # Deleted/foreign accounts must never be recreated.
        owner, source = account["user_id"], purchase_source(purchase)
    with database(cfg) as db:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM users WHERE id=?", (owner,)).fetchone():
            return "unowned"
        if purchase:
            save_lookup(db, cfg, owner, purchase, lookup)
        inserted = db.execute("INSERT OR IGNORE INTO native_notifications VALUES(?,?,?,?)",
                              (event_id, owner, source, time.time())).rowcount
        if inserted:
            db.execute("UPDATE native_lookups SET next_attempt=0,wake_version=wake_version+1 WHERE source=?", (source,))
    return "queued" if inserted else "duplicate"


def register_notifications(app, cfg):
    app.extensions["westicker"]["reconcile_native"] = lambda **kwargs: reconcile_due(cfg, **kwargs)
    app.extensions["westicker"]["delete_native_account"] = delete_native_account

    def receive(provider):
        options = cfg.get("native_billing", {}).get(provider, {})
        if not options.get("notifications_enabled"):
            abort(503, description="Native notifications are not configured.")
        if (request.content_length or 0) > MAX_EVENT_BYTES:
            abort(413)
        request.max_content_length = MAX_EVENT_BYTES
        raw = request.get_data(cache=False)
        if len(raw) > MAX_EVENT_BYTES:
            abort(413)
        try:
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise NotificationError(400)
            event = (apple_event(cfg, body) if provider == "apple"
                     else google_event(cfg, body, request.headers.get("Authorization")))
            enqueue_notification(cfg, provider, event)
            return jsonify(ok=True)
        except NotificationError as error:
            abort(error.status, description="Native notification was not accepted.")
        except (ValueError, TypeError):
            abort(400, description="Native notification was not accepted.")
        except Exception:
            abort(503, description="Native notification verification is unavailable.")

    app.add_url_rule("/api/billing/native/notifications/apple", "native_apple_notification",
                     lambda: receive("apple"), methods=["POST"])
    app.add_url_rule("/api/billing/native/notifications/google", "native_google_notification",
                     lambda: receive("google"), methods=["POST"])


def main():
    parser = argparse.ArgumentParser(description="Run one bounded native billing recovery batch")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--budget-seconds", type=float, default=60)
    args = parser.parse_args()
    from .app import create_app
    try:
        app = create_app()
        result = app.extensions["westicker"]["reconcile_native"](
            limit=args.limit, budget_seconds=args.budget_seconds)
        print(json.dumps(result, sort_keys=True))
        return 1 if result["failed"] or result["missing_lookups"] else 0
    except Exception:
        print('{"error":"native_recovery_unavailable"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
