import { useEffect, useRef, useState } from "react";
import {
  Capacitor,
  registerPlugin,
  type PluginListenerHandle,
} from "@capacitor/core";
import { Check, RefreshCw, Settings } from "lucide-react";
import { api, type Boot } from "./api";

type Receipt = {
  provider: string;
  binding: string;
  reference?: string;
  transaction?: string;
  environment?: string;
  token?: string;
};
type Result = { state?: string; receipts: Receipt[] };
type Catalog = {
  binding: string;
  products: Record<string, string>;
  purchase_enabled: boolean;
};
type Product = { id: string; name: string; price: string };
interface BillingPlugin {
  products(options: { ids: string[] }): Promise<{ products: Product[] }>;
  purchase(options: { product: string; binding: string }): Promise<Result>;
  restore(options: { sync: boolean }): Promise<Result>;
  finish(receipt: Receipt): Promise<void>;
  manage(): Promise<void>;
  addListener(
    event: "purchaseUpdated",
    callback: (event: Result | Receipt) => void,
  ): Promise<PluginListenerHandle>;
}
const Billing = registerPlugin<BillingPlugin>("WeStickerBilling");

export function NativePlans({
  boot,
  onSignIn,
  onRefresh,
}: {
  boot: Boot;
  onSignIn: () => void;
  onRefresh: () => Promise<unknown>;
}) {
  const provider = Capacitor.getPlatform() === "android" ? "google" : "apple";
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [products, setProducts] = useState<Product[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const owner = useRef(boot.user?.id);
  owner.current = boot.user?.id;
  const operation = useRef(false);

  async function deliver(
    receipts: Receipt[],
    expectedOwner: string,
    expected: Catalog,
  ) {
    for (const receipt of receipts) {
      if (owner.current !== expectedOwner)
        throw Error(
          "Account changed. Sign in to the purchasing account and restore.",
        );
      if (receipt.provider !== provider || receipt.binding !== expected.binding)
        throw Error(
          "This purchase belongs to another WeSticker account. Sign in to that account to restore it.",
        );
      const result = await api<{ verified: boolean }>(
        "/api/billing/native/verify",
        receipt,
      );
      if (!result.verified || owner.current !== expectedOwner)
        throw Error(
          "Purchase reconciliation is still pending. Use Restore; do not pay again.",
        );
      await Billing.finish(receipt);
    }
    if (owner.current === expectedOwner) await onRefresh();
  }

  async function run(action: () => Promise<void>) {
    if (operation.current) return;
    operation.current = true;
    setBusy(true);
    setMessage("");
    try {
      await action();
    } catch (error) {
      setMessage((error as Error).message);
    } finally {
      operation.current = false;
      setBusy(false);
    }
  }

  useEffect(() => {
    let alive = true;
    let listener: PluginListenerHandle | undefined;
    const expectedOwner = boot.user?.id;
    owner.current = expectedOwner;
    setCatalog(null);
    setProducts([]);
    setMessage("");
    if (!expectedOwner) return;
    async function load() {
      const response = await api<{ providers: Record<string, Catalog> }>(
        "/api/billing/native/catalog",
      );
      const current = response.providers[provider];
      if (!alive || owner.current !== expectedOwner) return;
      setCatalog(current);
      const ids = Object.keys(current.products);
      if (!ids.length) return;
      const available = await Billing.products({ ids });
      if (!alive) return;
      setProducts(available.products);
      listener = await Billing.addListener("purchaseUpdated", (event) => {
        if (!alive || owner.current !== expectedOwner) return;
        const receipts = "receipts" in event ? event.receipts : [event];
        void run(() => deliver(receipts, expectedOwner!, current));
      });
      if (!alive) {
        await listener.remove();
        return;
      }
      // Read current entitlements without forcing store authentication.
      await run(async () => {
        const result = await Billing.restore({ sync: false });
        if (alive) await deliver(result.receipts, expectedOwner!, current);
      });
    }
    void load().catch((error) => {
      if (alive) setMessage(error.message);
    });
    return () => {
      alive = false;
      owner.current = undefined;
      void listener?.remove();
    };
  }, [boot.user?.id, provider]);

  async function purchase(product: Product) {
    const expectedOwner = owner.current;
    if (!expectedOwner || !catalog) {
      onSignIn();
      return;
    }
    await run(async () => {
      const attempt = crypto.randomUUID();
      const prepared = await api<{ binding: string }>(
        "/api/billing/native/prepare",
        { provider, product: product.id, attempt },
      );
      if (
        owner.current !== expectedOwner ||
        prepared.binding !== catalog.binding
      )
        throw Error(
          "Account changed before purchase. Restore before trying again.",
        );
      const result = await Billing.purchase({
        product: product.id,
        binding: prepared.binding,
      });
      if (owner.current !== expectedOwner)
        throw Error(
          "Account changed. Restore from the purchasing account; do not pay again.",
        );
      if (result.state === "cancelled" || result.state === "pending") {
        await api("/api/billing/native/outcome", {
          attempt,
          state: result.state,
        });
        setMessage(
          result.state === "pending"
            ? "Purchase pending approval. Do not purchase again."
            : "Purchase cancelled.",
        );
      } else {
        if (!result.receipts.length)
          throw Error("Store result uncertain. Use Restore; do not pay again.");
        await deliver(result.receipts, expectedOwner, catalog);
        setMessage("Purchase verified.");
      }
    });
  }

  return (
    <>
      <div className="plans-grid">
        {boot.plans.map((plan, index) => {
          const product = products.find(
            (p) => catalog?.products[p.id] === plan.id,
          );
          return (
            <section className={"plan plan-" + index} key={plan.id}>
              <h2>{plan.name}</h2>
              <div className="price">
                {product?.price || "—"}
                <small>/ month</small>
              </div>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>
                    <Check size={17} />
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                className={
                  "button full " + (index === 1 ? "primary" : "outline")
                }
                disabled={
                  busy ||
                  (!!boot.user && (!product || !catalog?.purchase_enabled))
                }
                onClick={() =>
                  !boot.user ? onSignIn() : product && void purchase(product)
                }
              >
                {!boot.user
                  ? "Sign in to continue"
                  : !product || !catalog?.purchase_enabled
                    ? "Purchase setup pending"
                    : "Choose " + plan.name}
              </button>
            </section>
          );
        })}
      </div>
      <p className="plan-note">
        Monthly subscriptions renew until cancelled. The store confirms your
        localized price before purchase.
      </p>
      <div className="row">
        <button
          className="button outline"
          disabled={busy || !boot.user || !catalog}
          onClick={() =>
            void run(async () => {
              const expectedOwner = owner.current!;
              const result = await Billing.restore({ sync: true });
              await deliver(result.receipts, expectedOwner, catalog!);
              setMessage(
                result.receipts.length
                  ? "Purchases reconciled."
                  : "No current purchases found for this store account.",
              );
            })
          }
        >
          <RefreshCw size={17} />
          Restore purchases
        </button>
        <button
          className="button outline"
          disabled={busy}
          onClick={() => void run(() => Billing.manage())}
        >
          <Settings size={17} />
          Manage subscription
        </button>
      </div>
      {message && (
        <p role="status" className="plan-note">
          {message}
        </p>
      )}
    </>
  );
}
