"""Store-verified, account-bound native subscriptions.

The client supplies lookup hints, never entitlement facts. Provider failures
leave existing receipts unchanged; restore and reconciliation remain available.
"""

from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import os
from pathlib import Path
import re
import time
import uuid

from flask import abort, jsonify, request

from .store import PLANS, database

BUNDLE = "art.lazying.westicker"


@contextmanager
def verification_lock(cfg, owner):
    """Keep fresh provider reads and delivery ordered across API workers."""
    folder = Path(cfg["state"]) / "native-locks"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    name = hashlib.sha256(owner.encode()).hexdigest() + ".lock"
    fd = os.open(folder / name, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


@dataclass(frozen=True)
class Purchase:
    provider: str
    environment: str
    reference: str
    transaction: str
    binding: str
    product: str
    tier: str
    state: str
    expires: float


def binding(user_id, provider):
    if provider == "apple":
        return str(uuid.UUID(hex=user_id))
    return hashlib.sha256((BUNDLE + ":" + user_id).encode()).hexdigest()


def product_plan(cfg, provider, product):
    tier = cfg.get("native_billing", {}).get(provider, {}).get("products", {}).get(product)
    plan = next((p for p in PLANS if p["id"] == tier), None)
    if not plan:
        raise ValueError("Unrecognized store product")
    return plan


def value(enum):
    return getattr(enum, "value", enum)


def apple_components(cfg, environment):
    from appstoreserverlibrary.api_client import AppStoreServerAPIClient
    from appstoreserverlibrary.models.Environment import Environment
    from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier

    options = cfg.get("native_billing", {}).get("apple", {})
    if options.get("bundle_id") != BUNDLE or not options.get("app_id"):
        raise ValueError("Apple billing not configured")
    if environment not in {"Production", "Sandbox"} or (
        environment == "Sandbox" and not options.get("accept_sandbox")
    ):
        raise ValueError("Store environment not enabled")
    env = Environment.PRODUCTION if environment == "Production" else Environment.SANDBOX
    client = AppStoreServerAPIClient(
        Path(options["key_file"]).read_bytes(), options["key_id"],
        options["issuer_id"], BUNDLE, env,
    )
    verifier = SignedDataVerifier(
        [Path(p).read_bytes() for p in options["root_files"]], True, env,
        BUNDLE, int(options["app_id"]),
    )
    return client, verifier


def verify_apple(cfg, reference, environment):
    if not isinstance(reference, str) or not re.fullmatch(r"[0-9]{1,64}", reference):
        raise ValueError("Invalid transaction reference")
    client, verifier = apple_components(cfg, environment)
    response = client.get_all_subscription_statuses(reference)
    expected_app = cfg["native_billing"]["apple"]["app_id"]
    if response.bundleId != BUNDLE or (
        environment == "Production" and response.appAppleId != int(expected_app)
    ):
        raise ValueError("Wrong app")
    matches = []
    for group in response.data or []:
        for item in group.lastTransactions or []:
            if item.originalTransactionId != reference:
                continue
            tx = verifier.verify_and_decode_signed_transaction(item.signedTransactionInfo)
            renewal = verifier.verify_and_decode_renewal_info(item.signedRenewalInfo)
            if (tx.bundleId != BUNDLE or value(tx.environment) != environment
                    or value(renewal.environment) != environment
                    or tx.originalTransactionId != reference
                    or renewal.originalTransactionId != reference
                    or value(tx.type) != "Auto-Renewable Subscription"
                    or value(tx.inAppOwnershipType) != "PURCHASED"
                    or tx.quantity != 1 or not tx.appAccountToken
                    or renewal.productId != tx.productId):
                raise ValueError("Mismatched verified transaction")
            plan = product_plan(cfg, "apple", tx.productId)
            state = {1: "active", 2: "expired", 3: "hold", 4: "grace", 5: "revoked"}.get(value(item.status))
            if state is None:
                raise ValueError("Unknown subscription status")
            end = renewal.gracePeriodExpiresDate if state == "grace" else tx.expiresDate
            expires = (end or 0) / 1000
            if tx.revocationDate is not None:
                state = "revoked"
            elif tx.isUpgraded or expires <= time.time():
                state = "expired"
            matches.append(Purchase("apple", environment, reference, tx.transactionId,
                                    str(tx.appAccountToken).lower(), tx.productId,
                                    plan["id"], state, expires))
    if len(matches) != 1:
        raise ValueError("Subscription not found")
    return matches[0]


def google_session(cfg):
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    options = cfg.get("native_billing", {}).get("google", {})
    if options.get("package") != BUNDLE:
        raise ValueError("Play billing not configured")
    credentials = service_account.Credentials.from_service_account_file(
        options["key_file"], scopes=["https://www.googleapis.com/auth/androidpublisher"]
    )
    return AuthorizedSession(credentials)


def verify_google(cfg, token):
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_.\-:]{10,4096}", token):
        raise ValueError("Invalid purchase token")
    session = google_session(cfg)
    base = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/" + BUNDLE
    response = session.get(base + "/purchases/subscriptionsv2/tokens/" + token, timeout=30)
    response.raise_for_status()
    data = response.json()
    environment = "Sandbox" if "testPurchase" in data else "Production"
    options = cfg["native_billing"]["google"]
    if environment == "Sandbox" and not options.get("accept_sandbox"):
        raise ValueError("Sandbox disabled")
    lines = data.get("lineItems", [])
    if len(lines) != 1:
        raise ValueError("Expected one subscription line")
    line = lines[0]
    product = line["productId"]
    plan = product_plan(cfg, "google", product)
    if (line.get("offerDetails", {}).get("basePlanId") != options.get("base_plan", "monthly")
            or "autoRenewingPlan" not in line or "deferredItemReplacement" in line
            or "installmentDetails" in line.get("autoRenewingPlan", {})):
        raise ValueError("Unsupported subscription plan")
    states = {"SUBSCRIPTION_STATE_ACTIVE": "active", "SUBSCRIPTION_STATE_IN_GRACE_PERIOD": "grace",
              "SUBSCRIPTION_STATE_CANCELED": "active", "SUBSCRIPTION_STATE_EXPIRED": "expired",
              "SUBSCRIPTION_STATE_ON_HOLD": "hold", "SUBSCRIPTION_STATE_PAUSED": "hold",
              "SUBSCRIPTION_STATE_PENDING": "pending", "SUBSCRIPTION_STATE_PENDING_PURCHASE_CANCELED": "expired"}
    state = states.get(data.get("subscriptionState"))
    if state is None:
        raise ValueError("Unknown Play state")
    expires = datetime.fromisoformat(line["expiryTime"].replace("Z", "+00:00")).timestamp()
    if expires <= time.time():
        state = "expired"
    owner = data.get("externalAccountIdentifiers", {}).get("obfuscatedExternalAccountId")
    if not owner:
        raise ValueError("Missing account binding")
    reference = hashlib.sha256(token.encode()).hexdigest()
    transaction = line.get("latestSuccessfulOrderId") or "unpaid-" + reference
    if transaction.startswith("unpaid-") and state in {"active", "grace"}:
        raise ValueError("Missing paid order")
    return Purchase("google", environment, reference, transaction, owner, product,
                    plan["id"], state, expires), data, session


def apply_purchase(cfg, owner, purchase):
    if purchase.binding != binding(owner, purchase.provider):
        raise ValueError("This store purchase belongs to a different WeSticker account")
    plan = product_plan(cfg, purchase.provider, purchase.product)
    active = purchase.state in {"active", "grace"} and purchase.expires > time.time()
    source = ":".join((purchase.provider, purchase.environment, purchase.reference))
    grant_id = ":".join((purchase.provider, purchase.environment, purchase.transaction))
    with database(cfg) as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT * FROM native_subscriptions WHERE source=?", (source,)).fetchone()
        if old and old["user_id"] != owner:
            raise ValueError("Purchase is already bound to another account")
        db.execute("INSERT INTO native_subscriptions VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source) DO UPDATE SET product=excluded.product,tier=excluded.tier,state=excluded.state,expires=excluded.expires,observed=excluded.observed",
                   (source, owner, purchase.provider, purchase.product, plan["id"],
                    purchase.state, purchase.expires, time.time()))
        if active:
            inserted = db.execute("INSERT OR IGNORE INTO native_grants VALUES(?,?,?)",
                                  (grant_id, owner, time.time())).rowcount
            db.execute("UPDATE users SET plan=?,expires=?,subscription_id=?,credits=CASE WHEN ? THEN ? ELSE credits END WHERE id=?",
                       (plan["id"], purchase.expires, source, bool(inserted), plan["credits"], owner))
            db.execute("UPDATE native_intents SET state='delivered' WHERE user_id=? AND provider=? AND state IN ('prepared','pending')",
                       (owner, purchase.provider))
        else:
            db.execute("UPDATE users SET plan='free',expires=0,subscription_id=NULL WHERE id=? AND subscription_id=?",
                       (owner, source))
    return {"verified": True, "active": active, "plan": plan["id"] if active else "free",
            "expires": purchase.expires, "environment": purchase.environment}


def register_native_billing(app, cfg):
    ext = app.extensions["westicker"]
    with database(cfg) as db:
        db.executescript("""
CREATE TABLE IF NOT EXISTS native_subscriptions(source TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,provider TEXT NOT NULL,product TEXT NOT NULL,tier TEXT NOT NULL,state TEXT NOT NULL,expires REAL NOT NULL,observed REAL NOT NULL);
CREATE TABLE IF NOT EXISTS native_grants(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS native_intents(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,provider TEXT NOT NULL,product TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL);
""")

    @app.get("/api/billing/native/catalog")
    def native_catalog():
        user = ext["current"]()
        providers = {}
        for provider in ("apple", "google"):
            options = cfg.get("native_billing", {}).get(provider, {})
            providers[provider] = {"binding": binding(user["id"], provider),
                                   "products": options.get("products", {}),
                                   "purchase_enabled": bool(options.get("purchase_enabled"))}
        return jsonify(providers=providers)

    @app.post("/api/billing/native/prepare")
    def native_prepare():
        user = ext["current"]()
        body = request.get_json() or {}
        provider, product, attempt = body.get("provider"), body.get("product"), body.get("attempt")
        if provider not in {"apple", "google"} or not isinstance(attempt, str) or not re.fullmatch(r"[a-f0-9-]{32,36}", attempt):
            abort(400)
        options = cfg.get("native_billing", {}).get(provider, {})
        if not options.get("purchase_enabled"):
            abort(503, description="New native purchases are not enabled yet. Restore remains available.")
        try:
            product_plan(cfg, provider, product)
        except ValueError:
            abort(400)
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT * FROM native_intents WHERE id=?", (attempt,)).fetchone()
            if prior:
                if prior["user_id"] != user["id"] or prior["product"] != product or prior["provider"] != provider or prior["state"] != "prepared":
                    abort(409)
            else:
                fresh = db.execute("SELECT expires FROM users WHERE id=?", (user["id"],)).fetchone()
                pending = db.execute("SELECT 1 FROM native_intents WHERE user_id=? AND state IN ('prepared','pending')", (user["id"],)).fetchone()
                web = db.execute("SELECT 1 FROM checkouts WHERE user_id=? AND kind='subscription' AND created>?", (user["id"], time.time()-86400)).fetchone()
                if fresh["expires"] > time.time() or pending or web:
                    abort(409, description="Restore or manage the existing purchase before paying again.")
                db.execute("INSERT INTO native_intents VALUES(?,?,?,?,?,?)",
                           (attempt, user["id"], provider, product, "prepared", time.time()))
        return jsonify(binding=binding(user["id"], provider), attempt=attempt)

    @app.post("/api/billing/native/outcome")
    def native_outcome():
        user = ext["current"]()
        body = request.get_json() or {}
        if body.get("state") not in {"cancelled", "pending"}:
            abort(400)
        with database(cfg) as db:
            db.execute("UPDATE native_intents SET state=? WHERE id=? AND user_id=? AND state='prepared'",
                       (body["state"], body.get("attempt"), user["id"]))
        return jsonify(ok=True)

    @app.post("/api/billing/native/verify")
    def native_verify():
        user = ext["current"]()
        ext["throttle"]("native-verify:" + user["id"], 20, 60)
        body = request.get_json() or {}
        if body.get("provider") not in {"apple", "google"}:
            abort(400)
        try:
            with verification_lock(cfg, user["id"]):
                if body.get("provider") == "apple":
                    purchase = verify_apple(cfg, body.get("reference"), body.get("environment"))
                    return jsonify(apply_purchase(cfg, user["id"], purchase))
                purchase, data, session = verify_google(cfg, body.get("token"))
                result = apply_purchase(cfg, user["id"], purchase)
                # Delivery is durable before acknowledgement; retries reconcile
                # the same verified order and cannot grant duplicate credits.
                if result["active"] and data.get("acknowledgementState") == "ACKNOWLEDGEMENT_STATE_PENDING":
                    url = "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/" + BUNDLE + "/purchases/subscriptions/" + purchase.product + "/tokens/" + body["token"] + ":acknowledge"
                    response = session.post(url, json={}, timeout=30)
                    response.raise_for_status()
                return jsonify(result)
        except BlockingIOError:
            abort(409, description="Another restore is in progress. Wait for it to finish; do not pay again.")
        except ValueError:
            abort(400, description="Purchase or account binding could not be verified. No new credits were granted.")
        except Exception:
            # SDK exceptions can contain private transaction payloads.
            abort(503, description="Store verification is unavailable. Keep this purchase and use Restore; do not pay again.")
