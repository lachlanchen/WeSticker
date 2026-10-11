import { useEffect, useState } from "react";
import {
  Heart,
  Sticker as StickerIcon,
  X,
  ImagePlus,
  Library,
  Users,
  LogOut,
} from "lucide-react";
import { Studio } from "./Studio";
import { StickerBrowser } from "./StickerBrowser";
import {api, setCSRF, type Boot, type Pack, type Sticker} from "./api";

const base = import.meta.env.BASE_URL;
const asset = (path: string) =>
  path.startsWith("/") ? base + path.slice(1) : path;

export function PublicCatalog() {
  const [packs, setPacks] = useState<Pack[]>([]);
  const [selected, setSelected] = useState<Pack | null>(null);
  const [lang, setLang] = useState("zh");
  const [saved, setSaved] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("westicker-saved") || "[]");
    } catch {
      return [];
    }
  });
  const [view, setView] = useState<
    "stickers" | "create" | "library" | "characters" | "saved"
  >(
    ["native_link", "welcome", "login"].some(k => new URLSearchParams(location.search).has(k))
      ? "create"
      : "stickers",
  );
  const favorites = view === "saved";
  const tabs = [
    { id: "stickers", label: "Stickers", Icon: StickerIcon },
    { id: "create", label: "Create", Icon: ImagePlus },
    { id: "library", label: "Library", Icon: Library },
    { id: "characters", label: "Characters", Icon: Users },
  ] as const;
  const [preview, setPreview] = useState<Sticker | null>(null);
  const [error, setError] = useState("");
  const [account, setAccount] = useState<Boot | null>(null);
  const [accountOpen, setAccountOpen] = useState(false);
  const [accountBusy, setAccountBusy] = useState(false);
  const [accountError, setAccountError] = useState("");
  const [accountEpoch, setAccountEpoch] = useState(0);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  useEffect(() => {
    fetch(base + "catalog.json")
      .then((r) => {
        if (!r.ok) throw Error("Please reload the catalog.");
        return r.json();
      })
      .then((c) =>
        setPacks(
          c.packs.map((p: Pack) => ({
            ...p,
            banner: asset(p.banner),
            stickers: Object.fromEntries(
              Object.entries(p.stickers).map(([l, items]) => [
                l,
                items.map((s) => ({
                  ...s,
                  poster: asset(s.poster),
                  motion: s.motion ? asset(s.motion) : undefined,
                })),
              ]),
            ),
          })),
        ),
      )
      .catch((e) => setError(e.message));
    if (import.meta.env.PROD && "serviceWorker" in navigator)
      navigator.serviceWorker
        .register(base + "sw.js", { scope: base })
        .catch(() => {});
  }, []);
  useEffect(() => {
    localStorage.setItem("westicker-saved", JSON.stringify(saved));
  }, [saved]);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPreview(null);
    };
    addEventListener("keydown", close);
    return () => removeEventListener("keydown", close);
  }, []);
  function download(_: Pack, sticker: Sticker) {
    const url = new URL(sticker.gif);
    if (
      url.origin !== "https://aya.lazying.art" ||
      !url.pathname.startsWith("/media/")
    )
      return;
    const link = document.createElement("a");
    link.href = url.href;
    link.download = url.pathname.split("/").pop() || "sticker.gif";
    link.click();
  }
  return (
    <div className="app public-catalog">
      <aside className="sidebar">
        <a className="brand" href={base}>
          <img src={base + "icon-192.png"} alt="Aya and Lala" />
          <span>
            WeSticker<small>BY LAZYINGART</small>
          </span>
        </a>
        <nav>
          <button
            className={view === "stickers" ? "active" : ""}
            onClick={() => setView("stickers")}
          >
            <StickerIcon size={20} />
            Discover
          </button>
          <button
            className={favorites ? "active" : ""}
            onClick={() => setView("saved")}
          >
            <Heart size={20} />
            Saved<small>{saved.length}</small>
          </button>
        </nav>
        <div className="side-bottom">
          <strong>Aya, Lala, Sasa & Zhuangzi</strong>
          <a href="https://aya.lazying.art">Aya & Lala shop</a>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <strong>WeSticker</strong>
          <span>Creator beta</span>
          {account?.user && <button className="icon-button" aria-label="Your account" onClick={() => setAccountOpen(true)}><Users size={20}/></button>}
          <button
            className="icon-button"
            aria-label="Saved collections"
            onClick={() => setView(favorites ? "stickers" : "saved")}
          >
            <Heart fill={favorites ? "currentColor" : "none"} />
          </button>
        </header>
        <main>
          {view === "create" || view === "library" || view === "characters" ? (
            <Studio key={accountEpoch} section={view} onSection={setView} onAccount={setAccount} />
          ) : error ? (
            <p role="alert">{error}</p>
          ) : (
            <StickerBrowser
              packs={
                favorites ? packs.filter((p) => saved.includes(p.id)) : packs
              }
              selected={selected}
              onSelect={setSelected}
              lang={lang}
              onLanguage={setLang}
              saved={saved}
              onFavorite={(id) =>
                setSaved((old) =>
                  old.includes(id) ? old.filter((x) => x !== id) : [...old, id],
                )
              }
              onPreview={(sticker) => setPreview(sticker)}
              onNativeSave={download}
              onDownload={(pack) => {
                location.href =
                  "https://aya.lazying.art/pack/" + encodeURIComponent(pack.id);
              }}
            />
          )}
        </main>
      </div>
      <nav className="studio-bottom-nav" aria-label="App navigation">
        {tabs.map(({ id, label, Icon }) => (
          <button
            key={id}
            className={view === id ? "active" : ""}
            aria-current={view === id ? "page" : undefined}
            onClick={() => setView(id)}
          >
            <Icon size={22} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      {accountOpen && account?.user && <div className="modal-backdrop" onClick={() => setAccountOpen(false)}>
        <section className="auth-modal" role="dialog" aria-modal="true" aria-label="Your account" onClick={e => e.stopPropagation()}>
          <button className="icon-button close" aria-label="Close account" onClick={() => setAccountOpen(false)}><X/></button>
          <h2>{account.user.name}</h2>
          <p>LazyingArt account</p>
          {accountError && <p role="alert">{accountError}</p>}
          <button className="button outline full" disabled={accountBusy} onClick={async()=>{
            setAccountBusy(true);setAccountError("");
            try {setCSRF(account.csrf);await api('/api/auth/logout',{});setAccount(null);setAccountOpen(false);setAccountEpoch(n=>n+1);}
            catch(e){setAccountError((e as Error).message);}finally{setAccountBusy(false);}
          }}><LogOut size={18}/> Sign out of WeSticker</button>
          <details><summary>Delete my WeSticker account</summary>
            <p>Your private WeSticker creations and uploads will be deleted. Your LazyingArt account and other apps stay unchanged.</p>
            <label>Type DELETE<input value={deleteConfirmation} onChange={e=>setDeleteConfirmation(e.target.value)}/></label>
            <button className="button outline full" disabled={deleteConfirmation!=="DELETE"||accountBusy} onClick={async()=>{
              setAccountBusy(true);setAccountError("");
              try{setCSRF(account.csrf);await api('/api/account/delete',{confirmation:'DELETE'});setAccount(null);setAccountOpen(false);setAccountEpoch(n=>n+1);}
              catch(e){setAccountError((e as Error).message);}finally{setAccountBusy(false);}
            }}>Delete WeSticker account</button>
          </details>
        </section>
      </div>}
      {preview && (
        <div className="modal-backdrop" onClick={() => setPreview(null)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label={preview.label}
            className="preview-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button"
              aria-label="Close preview"
              onClick={() => setPreview(null)}
            >
              <X />
            </button>
            <img
              src={preview.gif}
              alt={preview.label}
              width="240"
              height="240"
            />
            <h2>{preview.label}</h2>
            <a className="button primary" href={preview.gif} download>
              Save GIF
            </a>
          </section>
        </div>
      )}
    </div>
  );
}
