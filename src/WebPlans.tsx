import { useEffect, useRef, useState } from "react";
import { CreditCard, RefreshCw, ShoppingCart } from "lucide-react";
import { Capacitor } from "@capacitor/core";
import { api, setCSRF, type Boot } from "./api";

type Attempt = { attempt: string; plan: string; state?: string };
type Status = { attempts: Attempt[]; manage: boolean };

export function WebPlans({ boot, onUpdated }: { boot: Boot; onUpdated: (boot: Boot) => void }) {
  const owner = boot.user?.id;
  const key = `westicker-checkout:${owner || "guest"}`;
  const active = useRef(true);
  const running = useRef(false);
  const checkedReturn = useRef(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const native = Capacitor.isNativePlatform();

  async function readStatus() {
    const value = await api<Status>("/api/billing/status");
    if (!active.current) return;
    const saved = localStorage.getItem(key);
    const local = saved ? JSON.parse(saved) as Attempt : null;
    if (local && (typeof local.attempt !== "string" || typeof local.plan !== "string"))
      throw Error("Purchase recovery needs review. No payment was started.");
    const record = local && value.attempts.find(a => a.attempt === local.attempt);
    const finished = record && ["expired", "complete"].includes(record.state || "");
    if (finished) localStorage.removeItem(key);
    setAttempt(value.attempts.find(a => !["expired", "complete"].includes(a.state || "")) || (finished ? null : local));
    setStatus(value);
  }
  useEffect(() => {
    active.current = true;
    if (owner && !native) {
      if (new URLSearchParams(location.search).get("billing") === "return" && !checkedReturn.current) {
        checkedReturn.current = true;
        void run(async () => {
          // The URL is only a prompt to reconcile provider truth, never a grant.
          await api("/api/billing/restore", {});
          await readStatus();
          const next = await api<Boot>("/api/bootstrap");
          if (active.current && next.user?.id === owner) {
            onUpdated(next);
            const url = new URL(location.href);
            url.searchParams.delete("billing");
            url.searchParams.set("view", "account");
            history.replaceState(null, "", url);
          }
        });
      } else readStatus().catch(e => { if (active.current) setError(e.message); });
    }
    return () => { active.current = false; };
  }, []);

  async function run(fn: () => Promise<void>) {
    if (running.current || native || !owner) return;
    running.current = true;
    setBusy(true); setError(""); setCSRF(boot.csrf);
    try { await fn(); }
    catch (e) { if (active.current) setError((e as Error).message); }
    finally { running.current = false; if (active.current) setBusy(false); }
  }
  function openStripe(value: string, host: string) {
    if (!active.current) return;
    const url = new URL(value);
    if (url.protocol !== "https:" || url.hostname !== host || url.username || url.password)
      throw Error("The billing destination could not be verified.");
    location.assign(url.href);
  }
  async function subscribe(plan: string) {
    const pending = attempt || { attempt: crypto.randomUUID(), plan };
    if (pending.plan !== plan) throw Error("Resume or reconcile your existing checkout first.");
    // Save before network I/O so refresh or a lost response preserves one operation.
    localStorage.setItem(key, JSON.stringify(pending)); setAttempt(pending);
    const result = await api<{ url: string }>("/api/billing/subscribe", pending);
    openStripe(result.url, "checkout.stripe.com");
  }
  const paid = (boot.user?.expires || 0) > Date.now() / 1000;
  if (native) return null;
  return <section className="web-plans" aria-label="Plans and billing">
    <h3>Plans & credits</h3>
    <p>{boot.user?.plan || "Free"} · {boot.user?.credits || 0} credits</p>
    {error && <p role="alert">{error}</p>}
    {busy && <p role="status">Checking your billing status…</p>}
    {!boot.capabilities.web_checkout && <p>New subscriptions are not open yet.</p>}
    <div className="web-plan-list">
      {boot.plans.map(plan => <div className="web-plan-row" key={plan.id}>
        <div><strong>{plan.name}</strong><span>{plan.credits} credits / month</span></div>
        <div><strong>${(plan.cents / 100).toFixed(2)}</strong><span>USD / month</span></div>
        <button className="button outline" disabled={busy || !owner || !status || paid || !boot.capabilities.web_checkout || Boolean(attempt && attempt.plan !== plan.id)}
          onClick={() => run(() => subscribe(plan.id))}>
          <ShoppingCart size={16}/>{attempt?.plan === plan.id ? "Resume" : "Choose"}
        </button>
      </div>)}
    </div>
    {attempt && <p>A checkout is reserved. Resume it or check its status before paying again.</p>}
    {owner && <div className="row">
      <button className="button outline" disabled={busy} onClick={() => run(async () => {
        await api("/api/billing/restore", {});
        await readStatus();
        const next = await api<Boot>("/api/bootstrap");
        if (active.current && next.user?.id === owner) onUpdated(next);
      })}><RefreshCw size={16}/>Restore / check status</button>
      <button className="button outline" disabled={busy || !status?.manage} onClick={() => run(async () => {
        const result = await api<{ url: string }>("/api/billing/manage", {});
        openStripe(result.url, "billing.stripe.com");
      })}><CreditCard size={16}/>Manage</button>
    </div>}
    <p className="plan-note">Monthly subscriptions renew until cancelled. Saved creations remain after expiry. <a href="/terms.html">Terms</a> · <a href="/privacy.html">Privacy</a></p>
  </section>;
}
