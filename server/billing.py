"""Independent, server-verified WeSticker Stripe subscriptions. No client grants."""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import time
import uuid

from flask import abort, jsonify, request
import stripe

from .store import PLANS, database
from .market_billing import apply_market_receipt, register_market_billing


def initialize_stripe(cfg):
    """Own the additive Stripe schema; do not change native receipt tables."""
    with database(cfg) as db:
        db.executescript("""
CREATE TABLE IF NOT EXISTS stripe_context(id INTEGER PRIMARY KEY CHECK(id=1), merchant TEXT NOT NULL, mode TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stripe_customers(owner TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE, customer TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS stripe_orders(attempt TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, price TEXT NOT NULL, params TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stripe_inbox(id TEXT PRIMARY KEY, merchant TEXT NOT NULL, mode TEXT NOT NULL, kind TEXT NOT NULL, object_id TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, lease TEXT, lease_until REAL NOT NULL DEFAULT 0, error TEXT, created REAL NOT NULL, updated REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stripe_subscriptions(id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, customer TEXT NOT NULL, status TEXT NOT NULL, observed REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stripe_invoices(id TEXT PRIMARY KEY, subscription TEXT NOT NULL, owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, tier TEXT NOT NULL, starts REAL NOT NULL, ends REAL NOT NULL, amount INTEGER NOT NULL, state TEXT NOT NULL, observed REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stripe_grants(subscription TEXT NOT NULL, starts REAL NOT NULL, ends REAL NOT NULL, invoice TEXT NOT NULL, created REAL NOT NULL, PRIMARY KEY(subscription,starts,ends));
CREATE TABLE IF NOT EXISTS stripe_reconcile_cursors(scope TEXT PRIMARY KEY, cursor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS stripe_scan_cursors(owner TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE, scope TEXT NOT NULL, lane TEXT NOT NULL, cursor TEXT NOT NULL, PRIMARY KEY(owner,scope,lane));
""")


def stripe_mode(cfg):
    mode = cfg.get("stripe_mode")
    if mode not in {"test", "live"} or not cfg.get("stripe_account"):
        raise ValueError("Stripe merchant and mode must be explicitly configured")
    if not cfg.get("stripe_key", "").startswith(("sk_" + mode + "_", "rk_" + mode + "_")):
        raise ValueError("Stripe key mode mismatch")
    return mode


def check_mode(cfg, value):
    if value.get("livemode") is not (stripe_mode(cfg) == "live"):
        raise ValueError("Stripe object mode mismatch")


def object_id(value):
    return value.get("id") if isinstance(value, dict) else value


def stripe_client(cfg, *, deadline=None):
    mode = stripe_mode(cfg)
    timeout = 25 if deadline is None else min(25, max(0.1, deadline - time.monotonic()))
    api = stripe.StripeClient(cfg["stripe_key"], max_network_retries=1 if deadline is None else 0,
                              http_client=stripe.RequestsClient(timeout=timeout))
    if deadline is not None:
        api = _BudgetedStripe(api, deadline)
    if api.v1.accounts.retrieve_current().id != cfg["stripe_account"]:
        raise ValueError("Stripe merchant mismatch")
    with database(cfg) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM stripe_context WHERE id=1").fetchone()
        if row and (row["merchant"] != cfg["stripe_account"] or row["mode"] != mode):
            raise ValueError("Stripe database is bound to another merchant or mode")
        db.execute("INSERT OR IGNORE INTO stripe_context VALUES(1,?,?)", (cfg["stripe_account"], mode))
    return api


@contextmanager
def stripe_lock(cfg, name="stripe.lock"):
    """Serialize fresh provider reads and writes across processes, not just threads."""
    path = Path(cfg["state"]) / name
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class _BudgetExpired(Exception):
    pass


class _ScanPending(Exception):
    pass


class _BudgetedStripe:
    """Check the batch deadline before every SDK call, including nested services."""

    def __init__(self, service, deadline):
        self.service, self.deadline = service, deadline

    def __getattr__(self, name):
        value = getattr(self.service, name)
        if not callable(value):
            return _BudgetedStripe(value, self.deadline)

        def call(*args, **kwargs):
            if time.monotonic() >= self.deadline:
                raise _BudgetExpired()
            return value(*args, **kwargs)

        return call


def verified_price(cfg, api, price_id, for_sale=False):
    plan = next((p for p in PLANS if cfg.get("stripe_prices", {}).get(p["id"]) == price_id), None)
    if not plan:
        raise ValueError("Price is not in the WeSticker catalog")
    price = api.v1.prices.retrieve(price_id).to_dict()
    check_mode(cfg, price)
    product = api.v1.products.retrieve(object_id(price.get("product"))).to_dict()
    check_mode(cfg, product)
    if (price.get("metadata", {}).get("app") != "westicker"
            or price.get("metadata", {}).get("tier") != plan["id"]
            or product.get("metadata", {}).get("app") != "westicker"
            or price.get("currency") != "usd" or price.get("unit_amount") != plan["cents"]
            or price.get("recurring", {}).get("interval") != "month"
            or price.get("recurring", {}).get("interval_count") != 1):
        raise ValueError("WeSticker price contract mismatch")
    if for_sale and (not price.get("active") or not product.get("active")):
        raise ValueError("This price is not on sale")
    return plan


def bind_customer(cfg, api, owner, customer):
    value = api.v1.customers.retrieve(customer).to_dict()
    check_mode(cfg, value)
    if (value.get("deleted") or value.get("metadata", {}).get("app") != "westicker"
            or value.get("metadata", {}).get("owner") != owner):
        raise ValueError("Customer ownership mismatch")
    with database(cfg) as db:
        db.execute("BEGIN IMMEDIATE")
        user = db.execute("SELECT customer FROM users WHERE id=?", (owner,)).fetchone()
        prior = db.execute("SELECT customer FROM stripe_customers WHERE owner=?", (owner,)).fetchone()
        claimed = db.execute("SELECT owner FROM stripe_customers WHERE customer=?", (customer,)).fetchone()
        if (not user or user["customer"] != customer or (prior and prior["customer"] != customer)
                or (claimed and claimed["owner"] != owner)):
            raise ValueError("Immutable customer binding mismatch")
        db.execute("INSERT OR IGNORE INTO stripe_customers VALUES(?,?)", (owner, customer))


def invoice_subscription(invoice):
    return object_id(invoice.get("subscription") or (invoice.get("parent") or {}).get("subscription_details", {}).get("subscription"))


def invoice_payment_state(cfg, api, invoice):
    """Inspect actual payments, including modern InvoicePayment -> PI -> Charge."""
    charges = []
    if invoice.get("charge"):
        charges.append(api.v1.charges.retrieve(object_id(invoice["charge"])).to_dict())
    else:
        payments = api.v1.invoice_payments.list({"invoice": invoice["id"], "status": "paid", "limit": 100})
        if isinstance(api, _BudgetedStripe) and getattr(payments, "has_more", False):
            raise ValueError("Invoice payment count needs qualification")
        for item in payments.data if isinstance(api, _BudgetedStripe) else payments.auto_paging_iter():
            payment = item.to_dict()
            check_mode(cfg, payment)
            if object_id(payment.get("invoice")) != invoice["id"]:
                raise ValueError("Invoice payment mismatch")
            source = payment.get("payment", {})
            if source.get("type") == "payment_intent":
                intent = api.v1.payment_intents.retrieve(object_id(source["payment_intent"])).to_dict()
                check_mode(cfg, intent)
                if intent.get("status") != "succeeded" or object_id(intent.get("customer")) != object_id(invoice["customer"]):
                    raise ValueError("Invoice payment is not settled")
                charge_id = object_id(intent.get("latest_charge"))
            elif source.get("type") == "charge":
                charge_id = object_id(source.get("charge"))
            else:
                raise ValueError("Invoice payment source needs qualification")
            if charge_id:
                charges.append(api.v1.charges.retrieve(charge_id).to_dict())
    charges = {c["id"]: c for c in charges}.values()
    total = refunded = 0
    for charge in charges:
        check_mode(cfg, charge)
        if (object_id(charge.get("customer")) != object_id(invoice["customer"])
                or charge.get("currency") != invoice["currency"] or not charge.get("paid")):
            raise ValueError("Invoice charge mismatch")
        if charge.get("disputed"):
            return "disputed"
        total += charge.get("amount", 0)
        refunded += charge.get("amount_refunded", 0)
    if total < invoice["amount_paid"]:
        raise ValueError("Invoice has no qualified cash payment")
    return "refunded" if refunded >= invoice["amount_paid"] else "paid"


def reconcile_subscription(cfg, api, sub_id, now=None):
    """Caller holds stripe_lock; access derives from paid invoice time, never event order."""
    now = time.time() if now is None else now
    sub = api.v1.subscriptions.retrieve(sub_id).to_dict()
    check_mode(cfg, sub)
    meta = sub.get("metadata", {})
    if meta.get("app") != "westicker":
        return False
    owner, customer = meta.get("owner"), object_id(sub.get("customer"))
    bind_customer(cfg, api, owner, customer)
    items = sub.get("items", {})
    if items.get("has_more") or len(items.get("data", [])) != 1 or items["data"][0].get("quantity") != 1:
        raise ValueError("Subscription item contract mismatch")
    verified_price(cfg, api, object_id(items["data"][0]["price"]))
    # Read the latest invoice plus the last delivered period. An unpaid renewal
    # does not erase already-paid time, and an old refund cannot revoke a successor.
    with database(cfg) as db:
        prior = db.execute("SELECT * FROM stripe_subscriptions WHERE id=?", (sub_id,)).fetchone()
        if prior and (prior["owner"] != owner or prior["customer"] != customer):
            raise ValueError("Immutable subscription owner mismatch")
        invoice_ids = {r["id"] for r in db.execute("SELECT id FROM stripe_invoices WHERE subscription=? AND ends>?", (sub_id, now))}
    latest = object_id(sub.get("latest_invoice"))
    if latest:
        invoice_ids.add(latest)
    # Recover a missed paid notification even when the newest invoice failed.
    paid = api.v1.invoices.list({"subscription": sub_id, "status": "paid", "limit": 1})
    invoice_ids.update(i.id for i in paid.data)
    receipts = []
    for invoice_id in invoice_ids:
        invoice = api.v1.invoices.retrieve(invoice_id).to_dict()
        check_mode(cfg, invoice)
        if invoice_subscription(invoice) != sub_id or object_id(invoice.get("customer")) != customer:
            raise ValueError("Invoice subscription/customer mismatch")
        if invoice.get("status") != "paid" or invoice.get("amount_paid", 0) <= 0:
            continue
        if invoice.get("billing_reason") not in {"subscription_create", "subscription_cycle"}:
            continue  # Plan-change/proration credit requires a separately qualified contract.
        lines = invoice.get("lines", {})
        if lines.get("has_more") or len(lines.get("data", [])) != 1:
            raise ValueError("Invoice lines need qualification")
        line = lines["data"][0]
        details = (line.get("parent") or {}).get("subscription_item_details", {})
        price_id = object_id(line.get("price") or (line.get("pricing") or {}).get("price_details", {}).get("price"))
        plan = verified_price(cfg, api, price_id)
        if (line.get("quantity") != 1 or line.get("proration") or details.get("proration")
                or invoice.get("currency") != "usd" or line.get("currency") != "usd"
                or line.get("amount") != plan["cents"]):
            raise ValueError("Paid invoice contract mismatch")
        starts, ends = line.get("period", {}).get("start", 0), line.get("period", {}).get("end", 0)
        if not 0 < starts < ends:
            raise ValueError("Invalid paid period")
        state = invoice_payment_state(cfg, api, invoice)
        receipts.append((invoice_id, sub_id, owner, plan["id"], starts, ends, invoice["amount_paid"], state, now))
    with database(cfg) as db:
        db.execute("BEGIN IMMEDIATE")
        user = db.execute("SELECT * FROM users WHERE id=? AND customer=?", (owner, customer)).fetchone()
        if not user:
            raise ValueError("Subscription owner disappeared")
        db.execute("INSERT INTO stripe_subscriptions VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET status=excluded.status,observed=excluded.observed",
                   (sub_id, owner, customer, sub["status"], now))
        for receipt in receipts:
            old = db.execute("SELECT * FROM stripe_invoices WHERE id=?", (receipt[0],)).fetchone()
            if old and tuple(old[k] for k in ("subscription", "owner", "tier", "starts", "ends", "amount")) != receipt[1:7]:
                raise ValueError("Immutable invoice contract mismatch")
            db.execute("INSERT INTO stripe_invoices VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,observed=excluded.observed", receipt)
        paid = db.execute("SELECT * FROM stripe_invoices WHERE subscription=? AND starts<=? AND ends>? ORDER BY ends DESC LIMIT 1", (sub_id, now, now)).fetchone()
        other_active = user["subscription_id"] not in {None, sub_id} and user["expires"] > now
        if paid and paid["state"] == "paid" and sub["status"] in {"active", "past_due", "unpaid", "canceled"} and not other_active:
            inserted = db.execute("INSERT OR IGNORE INTO stripe_grants VALUES(?,?,?,?,?)", (sub_id, paid["starts"], paid["ends"], paid["id"], now)).rowcount
            # Preserve the legacy once-per-invoice marker during migration.
            legacy = db.execute("SELECT 1 FROM billing_events WHERE id=?", ("invoice:" + paid["id"],)).fetchone()
            credits = next(p["credits"] for p in PLANS if p["id"] == paid["tier"])
            db.execute("UPDATE users SET plan=?,expires=?,subscription_id=?,credits=CASE WHEN ? THEN ? ELSE credits END WHERE id=?",
                       (paid["tier"], paid["ends"], sub_id, bool(inserted and not legacy), credits, owner))
            db.execute("INSERT OR IGNORE INTO billing_events VALUES(?,?)", ("invoice:" + paid["id"], now))
        elif user["subscription_id"] == sub_id:
            db.execute("UPDATE users SET plan='free',expires=0,credits=0,subscription_id=NULL WHERE id=? AND subscription_id=?", (owner, sub_id))
    return True


def reconcile_customer(cfg, api, owner, customer, now=None, *, scan=None):
    if scan is not None:
        return _reconcile_customer_page(cfg, api, owner, customer, scan, now)
    bind_customer(cfg, api, owner, customer)
    for item in api.v1.checkout.sessions.list({"customer": customer, "limit": 100}).auto_paging_iter():
        value = item.to_dict()
        meta = value.get("metadata", {})
        if meta.get("app") == "westicker" and meta.get("owner") == owner and value.get("mode") == "subscription":
            with database(cfg) as db:
                known = db.execute("SELECT 1 FROM checkouts WHERE id=? AND user_id=?", (meta.get("attempt"), owner)).fetchone()
            if known:
                process_stripe_event(cfg, api, "checkout.session.completed", value["id"])
    for item in api.v1.subscriptions.list({"customer": customer, "status": "all", "limit": 100}).auto_paging_iter():
        value = item.to_dict()
        if value.get("metadata", {}).get("app") == "westicker":
            if value["metadata"].get("owner") != owner:
                raise ValueError("Customer subscription owner mismatch")
            reconcile_subscription(cfg, api, value["id"], now=now)


def _reconcile_customer_page(cfg, api, owner, customer, scope, now):
    """At most five Checkouts and five subscriptions; resume after each object."""
    bind_customer(cfg, api, owner, customer)
    complete, errors = True, []
    for lane in ("checkout", "subscription"):
        with database(cfg) as db:
            row = db.execute("SELECT cursor FROM stripe_scan_cursors WHERE owner=? AND scope=? AND lane=?",
                             (owner, scope, lane)).fetchone()
        cursor = row["cursor"] if row else ""
        if cursor == "done":
            continue
        params = {"customer": customer, "limit": 5}
        if cursor:
            params["starting_after"] = cursor
        if lane == "subscription":
            params["status"] = "all"
        service = api.v1.checkout.sessions if lane == "checkout" else api.v1.subscriptions
        try:
            page = service.list(params)
        except stripe.InvalidRequestError as error:
            # A deleted provider cursor must not wedge this customer forever.
            if cursor and error.param == "starting_after":
                with database(cfg) as db:
                    db.execute("DELETE FROM stripe_scan_cursors WHERE owner=? AND scope=? AND lane=?", (owner, scope, lane))
            raise
        for item in page.data:
            value = item.to_dict()
            try:
                meta = value.get("metadata", {})
                if meta.get("app") != "westicker":
                    continue
                if meta.get("owner") != owner:
                    raise ValueError("Customer object owner mismatch")
                if lane == "subscription":
                    reconcile_subscription(cfg, api, value["id"], now=now)
                elif value.get("mode") == "subscription":
                    with database(cfg) as db:
                        known = db.execute("SELECT 1 FROM checkouts WHERE id=? AND user_id=?", (meta.get("attempt"), owner)).fetchone()
                    if known:
                        process_stripe_event(cfg, api, "checkout.session.completed", value["id"])
            except (ValueError, stripe.StripeError) as error:
                errors.append(error)
                with database(cfg) as db:
                    db.execute("INSERT OR REPLACE INTO stripe_scan_cursors VALUES(?,?, 'retry','1')", (owner, scope))
            except _BudgetExpired:
                with database(cfg) as db:
                    db.execute("INSERT OR REPLACE INTO stripe_scan_cursors VALUES(?,?, 'retry','1')", (owner, scope))
                raise
            finally:
                # Rotate failures too. Retry on the next sweep, not every slot.
                with database(cfg) as db:
                    db.execute("INSERT OR REPLACE INTO stripe_scan_cursors VALUES(?,?,?,?)", (owner, scope, lane, value["id"]))
        more = getattr(page, "has_more", False)
        complete = complete and not more
        if not more:
            with database(cfg) as db:
                db.execute("INSERT OR REPLACE INTO stripe_scan_cursors VALUES(?,?,?,?)", (owner, scope, lane, "done"))
    if complete:
        with database(cfg) as db:
            retry = db.execute("SELECT 1 FROM stripe_scan_cursors WHERE owner=? AND scope=? AND lane='retry'", (owner, scope)).fetchone()
            db.execute("DELETE FROM stripe_scan_cursors WHERE owner=? AND scope=?", (owner, scope))
        if retry and scope.startswith("event:") and not errors:
            raise _ScanPending()
    if errors:
        raise errors[0]
    return complete


def process_stripe_event(cfg, api, kind, ident, *, scan=None):
    event = {"type": kind, "data": {"object": {"id": ident}}}
    if kind.startswith("checkout.session."):
        session = api.v1.checkout.sessions.retrieve(ident).to_dict()
        check_mode(cfg, session)
        if session.get("metadata", {}).get("app") != "westicker":
            return
        if session.get("mode") == "subscription":
            meta = session["metadata"]
            with database(cfg) as db:
                order = db.execute("SELECT * FROM checkouts WHERE id=? AND kind='subscription'", (meta.get("attempt"),)).fetchone()
                if not order or order["user_id"] != meta.get("owner") or session.get("client_reference_id") != order["user_id"]:
                    raise ValueError("Checkout order mismatch")
                if order["session"] not in {None, ident}:
                    raise ValueError("Checkout session mismatch")
                customer = db.execute("SELECT customer FROM users WHERE id=?", (order["user_id"],)).fetchone()
                if not customer or customer["customer"] != object_id(session.get("customer")):
                    raise ValueError("Checkout customer mismatch")
                db.execute("UPDATE checkouts SET session=?,url=? WHERE id=?", (ident, session.get("url"), order["id"]))
                # A legacy Checkout can be observed/closed without ever being
                # recreated. Preserve its attempt as a durable tombstone.
                db.execute("INSERT OR IGNORE INTO stripe_orders VALUES(?,?,?,?,?,?)",
                           (order["id"], order["user_id"], cfg.get("stripe_prices", {}).get(order["target"], ""),
                            json.dumps({"customer": customer["customer"], "metadata": meta}), session["status"], order["created"]))
                db.execute("UPDATE stripe_orders SET state=? WHERE attempt=?", (session["status"], order["id"]))
            if session.get("subscription"):
                reconcile_subscription(cfg, api, object_id(session["subscription"]))
            return
        apply_market_receipt(cfg, api, event)
    elif kind.startswith("customer.subscription."):
        reconcile_subscription(cfg, api, ident)
    elif kind.startswith("invoice."):
        invoice = api.v1.invoices.retrieve(ident).to_dict()
        check_mode(cfg, invoice)
        sub_id = invoice_subscription(invoice)
        if sub_id:
            reconcile_subscription(cfg, api, sub_id)
    elif kind.startswith(("charge.", "refund.")):
        if kind.startswith("charge.dispute."):
            obj = api.v1.disputes.retrieve(ident).to_dict()
            charge = api.v1.charges.retrieve(object_id(obj["charge"])).to_dict()
        elif kind.startswith("refund."):
            obj = api.v1.refunds.retrieve(ident).to_dict()
            charge = api.v1.charges.retrieve(object_id(obj["charge"])).to_dict()
        else:
            charge = api.v1.charges.retrieve(ident).to_dict()
        check_mode(cfg, charge)
        if charge.get("metadata", {}).get("kind") == "pack":
            apply_market_receipt(cfg, api, {"type": "charge.refunded", "data": {"object": {"id": charge["id"]}}})
        customer = object_id(charge.get("customer"))
        with database(cfg) as db:
            user = db.execute("SELECT id FROM users WHERE customer=?", (customer,)).fetchone() if customer else None
        if user:
            complete = reconcile_customer(cfg, api, user["id"], customer, scan=scan)
            if scan is not None and not complete:
                raise _ScanPending()


def process_inbox(cfg, event_id, *, deadline=None):
    token = uuid.uuid4().hex
    with stripe_lock(cfg):
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM stripe_inbox WHERE id=?", (event_id,)).fetchone()
            if not row or row["state"] == "done":
                return
            if row["lease_until"] > time.time():
                raise BlockingIOError("Stripe event is leased")
            if row["merchant"] != cfg.get("stripe_account") or row["mode"] != stripe_mode(cfg):
                raise ValueError("Inbox merchant/mode mismatch")
            db.execute("UPDATE stripe_inbox SET state='processing',lease=?,lease_until=?,attempts=attempts+1,updated=? WHERE id=?",
                       (token, time.time() + 300, time.time(), event_id))
        try:
            api = stripe_client(cfg, deadline=deadline)
            if deadline is None:
                process_stripe_event(cfg, api, row["kind"], row["object_id"])
            else:
                process_stripe_event(cfg, api, row["kind"], row["object_id"], scan="event:" + event_id)
            with database(cfg) as db:
                db.execute("UPDATE stripe_inbox SET state='done',lease=NULL,lease_until=0,error=NULL,updated=? WHERE id=? AND lease=?", (time.time(), event_id, token))
                db.execute("DELETE FROM stripe_scan_cursors WHERE scope=?", ("event:" + event_id,))
        except Exception as error:
            with database(cfg) as db:
                db.execute("UPDATE stripe_inbox SET state='pending',lease=NULL,lease_until=0,error=?,updated=? WHERE id=? AND lease=?", (type(error).__name__, time.time(), event_id, token))
            raise


def reconcile_stripe(cfg, *, limit=25, budget_seconds=45):
    """Bounded rotating batch. Deadline is checked between provider calls."""
    limit = max(1, min(int(limit), 100))
    deadline = time.monotonic() + max(1, min(float(budget_seconds), 300))
    initialize_stripe(cfg)
    result = {"events": 0, "customers": 0, "errors": 0, "checked": 0,
              "deferred": 0, "busy": 0, "budget_exhausted": False}
    try:
        with stripe_lock(cfg, "stripe-reconcile.lock"):
            with database(cfg) as db:
                cursors = {r["scope"]: r["cursor"] for r in db.execute("SELECT * FROM stripe_reconcile_cursors")}
                queues = {}
                for lane in ("events", "customers"):
                    table, condition, args = ("stripe_inbox", "state!='done' AND lease_until<=?", [time.time()]) if lane == "events" else ("users", "customer IS NOT NULL", [])
                    cursor = cursors.get(lane, "")
                    rows = db.execute(f"SELECT * FROM {table} WHERE {condition} AND id>? ORDER BY id LIMIT ?", (*args, cursor, limit)).fetchall()
                    if len(rows) < limit:
                        rows += db.execute(f"SELECT * FROM {table} WHERE {condition} AND id<=? ORDER BY id LIMIT ?", (*args, cursor, limit - len(rows))).fetchall()
                    queues[lane] = rows
            lane = cursors.get("next", "events")
            while result["checked"] < limit and any(queues.values()):
                if time.monotonic() >= deadline:
                    result["budget_exhausted"] = True
                    break
                if not queues[lane]:
                    lane = "customers" if lane == "events" else "events"
                row = queues[lane].pop(0)
                next_lane = "customers" if lane == "events" else "events"
                # Persist before network I/O so crashes and poison records rotate.
                with database(cfg) as db:
                    db.execute("INSERT OR REPLACE INTO stripe_reconcile_cursors VALUES(?,?)", (lane, row["id"]))
                    db.execute("INSERT OR REPLACE INTO stripe_reconcile_cursors VALUES('next',?)", (next_lane,))
                result["checked"] += 1
                try:
                    if lane == "events":
                        process_inbox(cfg, row["id"], deadline=deadline)
                    else:
                        with stripe_lock(cfg):
                            api = stripe_client(cfg, deadline=deadline)
                            if not reconcile_customer(cfg, api, row["id"], row["customer"], scan="periodic"):
                                result["deferred"] += 1
                    result[lane] += 1
                except _BudgetExpired:
                    result["budget_exhausted"] = True
                    break
                except _ScanPending:
                    result["deferred"] += 1
                except BlockingIOError:
                    result["busy"] += 1
                except (ValueError, stripe.StripeError):
                    result["errors"] += 1
                lane = next_lane
    except BlockingIOError:
        result["busy"] += 1
    return result


def register_billing(app, cfg):
    initialize_stripe(cfg)
    ext = app.extensions["westicker"]

    def client():
        if not cfg.get("stripe_key"):
            abort(
                503, description="Billing is not connected. You have not been charged."
            )
        try:
            return stripe_client(cfg)
        except (ValueError, stripe.StripeError):
            abort(503, description="Billing configuration could not be verified.")

    register_market_billing(app, cfg, client)

    def close_stripe_checkouts(user):
        """Parent native prepare hook: close open web sessions before another lane."""
        with stripe_lock(cfg):
            with database(cfg) as db:
                orders = db.execute("SELECT c.* FROM checkouts c LEFT JOIN stripe_orders o ON o.attempt=c.id WHERE c.user_id=? AND c.kind='subscription' AND (o.state IS NULL OR o.state NOT IN ('expired','complete'))", (user["id"],)).fetchall()
            if not orders and not user["customer"]:
                return True
            api = client()
            if user["customer"]:
                reconcile_customer(cfg, api, user["id"], user["customer"])
            with database(cfg) as db:
                orders = db.execute("SELECT c.* FROM checkouts c LEFT JOIN stripe_orders o ON o.attempt=c.id WHERE c.user_id=? AND c.kind='subscription' AND (o.state IS NULL OR o.state NOT IN ('expired','complete'))", (user["id"],)).fetchall()
            for order in orders:
                if not order["session"]:
                    abort(409, description="An uncertain web checkout must be reconciled first.")
                session = api.v1.checkout.sessions.retrieve(order["session"]).to_dict()
                check_mode(cfg, session)
                if (session.get("metadata", {}).get("app") != "westicker"
                        or session.get("metadata", {}).get("owner") != user["id"]
                        or session.get("metadata", {}).get("attempt") != order["id"]
                        or object_id(session.get("customer")) != user["customer"]):
                    raise ValueError("Native switch checkout binding mismatch")
                if session["status"] == "open":
                    api.v1.checkout.sessions.expire(session["id"], options={"idempotency_key": "westicker-expire-" + order["id"]})
                process_stripe_event(cfg, api, "checkout.session.expired", session["id"])
            with database(cfg) as db:
                active = db.execute("SELECT 1 FROM stripe_subscriptions WHERE owner=? AND status NOT IN ('canceled','incomplete_expired')", (user["id"],)).fetchone()
                paid = db.execute("SELECT 1 FROM users WHERE id=? AND expires>?", (user["id"], time.time())).fetchone()
                pending = db.execute("SELECT 1 FROM checkouts c LEFT JOIN stripe_orders o ON o.attempt=c.id WHERE c.user_id=? AND c.kind='subscription' AND (o.state IS NULL OR o.state NOT IN ('expired','complete'))", (user["id"],)).fetchone()
                if active or paid or pending:
                    abort(409, description="Manage or restore the existing web purchase before switching stores.")
            return True

    ext["close_stripe_checkouts"] = close_stripe_checkouts

    def cancel_for_deletion(user):
        with stripe_lock(cfg):
            cancel_owned_billing(user)

    def cancel_owned_billing(user):
        api = client()
        reconcile_customer(cfg, api, user["id"], user["customer"])
        for item in api.v1.checkout.sessions.list({"customer": user["customer"], "limit": 100}).auto_paging_iter():
            session = item.to_dict()
            meta = session.get("metadata", {})
            if meta.get("app") == "westicker" and meta.get("owner") == user["id"] and session.get("mode") == "subscription":
                check_mode(cfg, session)
                if session["status"] == "open":
                    api.v1.checkout.sessions.expire(session["id"], options={"idempotency_key": "westicker-delete-expire-" + session["id"]})
        with database(cfg) as db:
            unknown = db.execute("SELECT 1 FROM checkouts WHERE user_id=? AND kind='subscription' AND session IS NULL", (user["id"],)).fetchone()
            if unknown:
                abort(409, description="An uncertain checkout must be reconciled before deleting this account.")
        subscriptions = api.v1.subscriptions.list(
            {"customer": user["customer"], "status": "all", "limit": 100}
        )
        for subscription in subscriptions.auto_paging_iter():
            value = subscription.to_dict()
            meta = value.get("metadata", {})
            if (
                meta.get("app") == "westicker"
                and meta.get("owner") == user["id"]
                and value.get("status") not in {"canceled", "incomplete_expired"}
            ):
                check_mode(cfg, value)
                api.v1.subscriptions.cancel(value["id"])

    ext["cancel_for_deletion"] = cancel_for_deletion

    @app.get("/api/billing/status")
    def billing_status():
        user = ext["current"]()
        with database(cfg) as db:
            attempts = [dict(row) for row in db.execute(
                "SELECT c.id AS attempt,c.target AS plan,COALESCE(o.state,'unknown') AS state "
                "FROM checkouts c LEFT JOIN stripe_orders o ON o.attempt=c.id "
                "WHERE c.user_id=? AND c.kind='subscription' ORDER BY c.created DESC LIMIT 100",
                (user["id"],))]
        return jsonify(attempts=attempts, manage=bool(user["customer"] and cfg.get("stripe_portal_configuration")))

    @app.post("/api/billing/subscribe")
    def subscribe():
        user = ext["current"]()
        if not cfg.get("stripe_purchase_enabled", False):
            abort(503, description="New web subscriptions are not open yet.")
        if not cfg.get("stripe_webhook_secret"):
            abort(503, description="Billing notifications must be configured before purchase.")
        try:
            with stripe_lock(cfg):
                return start_subscription(user)
        except BlockingIOError:
            abort(409, description="Billing is being reconciled. Retry the same attempt.")
        except (ValueError, stripe.StripeError):
            abort(503, description="Checkout needs reconciliation. Retry only the same attempt.")

    def start_subscription(user):
        body = request.get_json() or {}
        plan = body.get("plan")
        attempt = body.get("attempt")
        if (
            not isinstance(attempt, str)
            or not 16 <= len(attempt) <= 64
            or plan not in {p["id"] for p in PLANS}
        ):
            abort(400)
        price = cfg.get("stripe_prices", {}).get(plan)
        if not price:
            abort(503, description="This plan is not on sale yet.")
        api = client()
        selected_plan = verified_price(cfg, api, price, for_sale=True)
        if user["customer"]:
            reconcile_customer(cfg, api, user["id"], user["customer"])
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute(
                "SELECT * FROM checkouts WHERE id=?", (attempt,)
            ).fetchone()
            if prior:
                if prior["user_id"] != user["id"] or prior["target"] != plan or prior["kind"] != "subscription":
                    abort(409)
            fresh = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
            if fresh["expires"] > time.time():
                abort(
                    409,
                    description="Manage your existing subscription instead of buying twice.",
                )
            native_pending = db.execute("SELECT 1 FROM native_intents WHERE user_id=? AND state IN ('prepared','pending')", (user["id"],)).fetchone()
            if native_pending:
                abort(409, description="Restore the pending native purchase before starting checkout.")
            if not prior:
                existing = db.execute("SELECT 1 FROM stripe_subscriptions WHERE owner=? AND status NOT IN ('canceled','incomplete_expired')", (user["id"],)).fetchone()
                if existing:
                    abort(409, description="Manage or restore the existing web subscription.")
                pending = db.execute(
                    "SELECT c.* FROM checkouts c LEFT JOIN stripe_orders o ON o.attempt=c.id WHERE c.user_id=? AND c.kind='subscription' AND (o.state IS NULL OR o.state NOT IN ('expired','complete')) ORDER BY c.created DESC LIMIT 1",
                    (user["id"],),
                ).fetchone()
                if pending:
                    abort(
                        409,
                        description="An earlier checkout is still reserved. Resume or reconcile it before starting another.",
                    )
                db.execute(
                    "INSERT INTO checkouts VALUES(?,?,?,?,?,?,?)",
                    (
                        attempt,
                        user["id"],
                        "subscription",
                        plan,
                        None,
                        None,
                        time.time(),
                    ),
                )
                db.execute("INSERT INTO stripe_orders VALUES(?,?,?,?,?,?)", (attempt, user["id"], price, "{}", "reserved", time.time()))
            binding = db.execute("SELECT * FROM stripe_orders WHERE attempt=?", (attempt,)).fetchone()
            if binding and binding["price"] != price:
                abort(409, description="Reserved price changed; reconcile the original checkout.")
            if binding and binding["state"] in {"expired", "complete"}:
                abort(409, description="This checkout is finished. Refresh your account.")
            if prior and not binding:
                abort(409, description="Legacy checkout requires reconciliation before retry.")
        if binding:
            params = json.loads(binding["params"])
            if prior and prior["session"]:
                session = api.v1.checkout.sessions.retrieve(prior["session"]).to_dict()
                check_mode(cfg, session)
                if session.get("customer") != params["customer"] or session.get("metadata") != params["metadata"]:
                    raise ValueError("Saved checkout binding mismatch")
                process_stripe_event(cfg, api, "checkout.session.completed", session["id"])
                if session["status"] == "open" and session.get("url"):
                    return jsonify(url=session["url"])
                abort(409, description="This checkout is finished. Refresh your account.")
            # Stripe can evict idempotency keys after 24h. Never recreate an old
            # uncertain operation, even if its local URL was never saved.
            if binding["created"] < time.time() - 23 * 3600:
                abort(409, description="Unknown checkout outcome requires operator reconciliation.")
            if params:
                result = api.v1.checkout.sessions.create(params, options={"idempotency_key": "westicker-checkout-" + attempt})
                return save_checkout(result, attempt)
        customer = fresh["customer"]
        if not customer:
            customer = api.v1.customers.create(
                {"metadata": {"app": "westicker", "owner": user["id"]}},
                options={"idempotency_key": "westicker-customer-" + user["id"]},
            ).id
            with database(cfg) as db:
                db.execute(
                    "UPDATE users SET customer=? WHERE id=?", (customer, user["id"])
                )
        bind_customer(cfg, api, user["id"], customer)
        params = {
                "mode": "subscription",
                "payment_method_types": ["card"],
                "customer": customer,
                "line_items": [{"price": price, "quantity": 1}],
                "client_reference_id": user["id"],
                "metadata": {
                    "app": "westicker",
                    "attempt": attempt,
                    "owner": user["id"],
                },
                "subscription_data": {
                    "metadata": {"app": "westicker", "owner": user["id"], "attempt": attempt}
                },
                "success_url": cfg["origin"] + "/?view=account&billing=return",
                "cancel_url": cfg["origin"] + "/?view=account&billing=cancelled",
                "adaptive_pricing": {"enabled": False},
                "custom_text": {"submit": {"message": (
                    f"WeSticker {selected_plan['name']}: "
                    f"{selected_plan['credits']} credits each month. "
                    "Renews monthly until cancelled. Saved creations remain after expiry."
                )}},
                "expires_at": int(time.time()) + 3600,
            }
        with database(cfg) as db:
            db.execute("UPDATE stripe_orders SET params=? WHERE attempt=?", (json.dumps(params, sort_keys=True), attempt))
        result = api.v1.checkout.sessions.create(params, options={"idempotency_key": "westicker-checkout-" + attempt})
        return save_checkout(result, attempt)

    def save_checkout(result, attempt):
        check_mode(cfg, result.to_dict())
        with database(cfg) as db:
            db.execute(
                "UPDATE checkouts SET session=?,url=? WHERE id=?",
                (result.id, result.url, attempt),
            )
        return jsonify(url=result.url)

    @app.post("/api/billing/manage")
    def portal():
        user = ext["current"]()
        if not user["customer"]:
            abort(404, description="No subscription to manage yet.")
        api = client()
        try:
            bind_customer(cfg, api, user["id"], user["customer"])
            configuration = cfg.get("stripe_portal_configuration")
            if not configuration:
                abort(503, description="The app-owned billing portal is not configured.")
            portal_cfg = api.v1.billing_portal.configurations.retrieve(configuration).to_dict()
            check_mode(cfg, portal_cfg)
            if (portal_cfg.get("metadata", {}).get("app") != "westicker"
                    or not portal_cfg.get("active")
                    or portal_cfg.get("features", {}).get("subscription_update", {}).get("enabled")):
                raise ValueError("Unqualified portal configuration")
            result = api.v1.billing_portal.sessions.create(
                {"customer": user["customer"], "configuration": configuration, "return_url": cfg["origin"] + "/?view=account"}
            )
        except (ValueError, stripe.StripeError):
            abort(503, description="Billing management needs configuration review.")
        return jsonify(url=result.url)

    @app.post("/api/billing/webhook")
    def webhook():
        if not cfg.get("stripe_webhook_secret"):
            abort(503, description="Webhook signing is not configured.")
        try:
            event = stripe.Webhook.construct_event(
                request.get_data(),
                request.headers.get("Stripe-Signature", ""),
                cfg["stripe_webhook_secret"],
            ).to_dict()
            check_mode(cfg, event)
            if event.get("account") not in {None, cfg["stripe_account"]} or event.get("context") not in {None, cfg["stripe_account"]}:
                raise ValueError("Webhook account mismatch")
            ident, kind, obj = event["id"], event["type"], event["data"]["object"]["id"]
            if not all(isinstance(v, str) and 0 < len(v) <= 255 for v in (ident, kind, obj)):
                raise ValueError("Invalid event envelope")
        except (ValueError, KeyError, TypeError, stripe.SignatureVerificationError):
            abort(400)
        with database(cfg) as db:
            db.execute("BEGIN IMMEDIATE")
            prior = db.execute("SELECT * FROM stripe_inbox WHERE id=?", (ident,)).fetchone()
            if prior and (prior["merchant"], prior["mode"], prior["kind"], prior["object_id"]) != (cfg["stripe_account"], cfg["stripe_mode"], kind, obj):
                abort(400)
            db.execute("INSERT OR IGNORE INTO stripe_inbox(id,merchant,mode,kind,object_id,created,updated) VALUES(?,?,?,?,?,?,?)",
                       (ident, cfg["stripe_account"], cfg["stripe_mode"], kind, obj, time.time(), time.time()))
        try:
            process_inbox(cfg, ident)
        except (ValueError, stripe.StripeError, BlockingIOError):
            abort(503, description="Notification saved; reconciliation is pending.")
        return jsonify(received=True)

    @app.post("/api/billing/restore")
    def restore():
        user = ext["current"]()
        if not user["customer"]:
            return jsonify(reconciled=True)
        try:
            with stripe_lock(cfg):
                reconcile_customer(cfg, client(), user["id"], user["customer"])
        except (ValueError, stripe.StripeError, BlockingIOError):
            abort(503, description="Subscription verification is pending.")
        return jsonify(reconciled=True)

    @app.post("/api/creator/onboard")
    def onboard():
        user = ext["current"]()
        if not cfg.get("creator_sales_enabled"):
            abort(503, description="Creator payouts are not open yet.")
        api = client()
        account = user["connect_id"]
        if not account:
            result = api.v1.accounts.create(
                {
                    "type": "express",
                    "capabilities": {"transfers": {"requested": True}},
                    "metadata": {"app": "westicker", "owner": user["id"]},
                },
                options={"idempotency_key": "westicker-creator-" + user["id"]},
            )
            account = result.id
            with database(cfg) as db:
                db.execute(
                    "UPDATE users SET connect_id=? WHERE id=?", (account, user["id"])
                )
        link = api.v1.account_links.create(
            {
                "account": account,
                "refresh_url": cfg["origin"] + "/?payout=retry",
                "return_url": cfg["origin"] + "/?payout=return",
                "type": "account_onboarding",
            }
        )
        return jsonify(url=link.url)

    @app.post("/api/creator/status")
    def creator_status():
        user = ext["current"]()
        if not user["connect_id"]:
            return jsonify(ready=False)
        account = client().v1.accounts.retrieve(user["connect_id"]).to_dict()
        ready = (
            account.get("payouts_enabled") is True
            and account.get("details_submitted") is True
            and account.get("capabilities", {}).get("transfers") == "active"
        )
        with database(cfg) as db:
            db.execute(
                "UPDATE users SET payout_ready=? WHERE id=?", (int(ready), user["id"])
            )
        return jsonify(ready=ready)
