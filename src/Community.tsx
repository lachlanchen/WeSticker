import { useEffect, useState } from "react";
import { ArrowDownToLine, Store, Flag, UserX } from "lucide-react";
import { Capacitor } from "@capacitor/core";
import { api, API } from "./api";
type Listing = {
  id: string;
  title: string;
  name: string;
  creator: string;
  price: number;
  count: number;
  language: string;
  preview: string;
};
export function Community({
  signedIn,
  onSignIn,
  onReport,
  onNotice,
}: {
  signedIn: boolean;
  onSignIn: () => void;
  onReport: (id: string) => void;
  onNotice: (message: string) => void;
}) {
  const [packs, setPacks] = useState<Listing[]>([]),
    [busy, setBusy] = useState(false);
  async function refresh() {
    setPacks((await api("/api/market")).packs);
  }
  useEffect(() => {
    refresh().catch((e) => onNotice(e.message));
  }, []);
  return (
    <>
      <div className="page-heading">
        <div>
          <span className="eyebrow teal">SMALL CREATORS, BIG PERSONALITY</span>
          <h1>The creator market.</h1>
          <p>
            Original little characters, reviewed before they meet the world.
          </p>
        </div>
      </div>
      {!packs.length ? (
        <section className="empty">
          <Store size={36} />
          <h2>A new neighborhood is growing.</h2>
          <p>
            Reviewed creator collections will appear here. The Aya & Lala
            originals are always in Discover.
          </p>
        </section>
      ) : (
        <div className="pack-grid">
          {packs.map((p) => (
            <article key={p.id} className="pack-card">
              <img
                className="community-preview"
                src={API + p.preview}
                alt={p.title}
              />
              <div className="pack-content">
                <div>
                  <h2>{p.title}</h2>
                  <p>
                    by {p.name} · {p.count} stickers · {p.language}
                  </p>
                </div>
              </div>
              <div className="pack-footer">
                <button
                  disabled={busy || Capacitor.isNativePlatform()}
                  onClick={async () => {
                    if (!signedIn) {
                      onSignIn();
                      return;
                    }
                    setBusy(true);
                    try {
                      const r = await api(`/api/market/${p.id}/buy`, {
                        attempt: crypto.randomUUID(),
                      });
                      location.href = r.url || API + r.download;
                    } catch (e) {
                      onNotice((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <ArrowDownToLine size={15} />
                  {Capacitor.isNativePlatform()
                    ? "Store purchase coming later"
                    : `$${(p.price / 100).toFixed(2)} · Get pack`}
                </button>
                <button
                  aria-label="Report collection"
                  title="Report collection"
                  onClick={() => onReport("market:" + p.id)}
                >
                  <Flag size={15} />
                </button>
                <button
                  aria-label="Block creator"
                  title="Block creator"
                  onClick={async () => {
                    if (!signedIn) {
                      onSignIn();
                      return;
                    }
                    try {
                      await api("/api/blocks", { creator: p.creator });
                      await refresh();
                    } catch (e) {
                      onNotice((e as Error).message);
                    }
                  }}
                >
                  <UserX size={15} />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </>
  );
}
