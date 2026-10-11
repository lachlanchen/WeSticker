import { useEffect, useState } from "react";
import {
  Heart,
  Sticker as StickerIcon,
  X,
  ImagePlus,
  Library,
  UserRound,
} from "lucide-react";
import { Studio } from "./Studio";
import { StickerBrowser } from "./StickerBrowser";
import { AccountScreen } from "./AccountScreen";
import { SignInScreen, CreatorConsentScreen } from "./SignInScreen";
import { NativeSignInReturn, nativeSignInIntent } from "./NativeSignInReturn";
import { API, api, setCSRF, type Boot, type Pack, type Sticker } from "./api";

const base = import.meta.env.BASE_URL;
const asset = (path: string) =>
  path.startsWith("/") ? base + path.slice(1) : path;

export function PublicCatalog() {
  const nativeIntent = nativeSignInIntent();
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
    "stickers" | "create" | "library" | "characters" | "saved" | "account"
  >(
    new URLSearchParams(location.search).get("view") === "account"
      ? "account"
      : new URLSearchParams(location.search).get("view") === "library"
        ? "library"
        : new URLSearchParams(location.search).get("view") === "create" ||
            ["native_link", "welcome", "login"].some((k) =>
              new URLSearchParams(location.search).has(k),
            )
          ? "create"
          : "stickers",
  );
  const favorites = view === "saved";
  const tabs = [
    { id: "stickers", label: "Stickers", Icon: StickerIcon },
    { id: "create", label: "Create", Icon: ImagePlus },
    { id: "library", label: "Library", Icon: Library },
    { id: "account", label: "Account", Icon: UserRound },
  ] as const;
  const [preview, setPreview] = useState<{
    sticker: Sticker;
    pack: Pack;
  } | null>(null);
  const [error, setError] = useState("");
  const [accountEpoch, setAccountEpoch] = useState(0);
  const [session, setSession] = useState<Boot | null>(null);
  const [loginError, setLoginError] = useState("");
  const protectedView = ["create", "library", "characters", "account"].includes(
    view,
  );
  function updateSession(next: Boot) {
    setSession(next);
    setCSRF(next.csrf);
  }
  async function refreshSession() {
    setLoginError("");
    try {
      updateSession(await api<Boot>("/api/bootstrap"));
    } catch (e) {
      setLoginError((e as Error).message);
      throw e;
    }
  }
  useEffect(() => {
    if (protectedView && !session && !loginError)
      void refreshSession().catch(() => {});
  }, [protectedView, session, loginError]);
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
  function stickerDownload(pack: Pack, sticker: Sticker) {
    return (
      API +
      `/api/default/${encodeURIComponent(pack.id)}/sticker/${encodeURIComponent(lang)}/${encodeURIComponent(sticker.id)}`
    );
  }
  function download(pack: Pack, sticker: Sticker) {
    const url = new URL(sticker.gif);
    if (
      url.origin !== "https://aya.lazying.art" ||
      !url.pathname.startsWith("/media/")
    )
      return;
    const link = document.createElement("a");
    link.href = stickerDownload(pack, sticker);
    link.download = url.pathname.split("/").pop() || "sticker.gif";
    link.click();
  }
  if (protectedView && !session?.user)
    return (
      <SignInScreen
        boot={session}
        destination={
          view === "account"
            ? "account"
            : view === "create"
              ? "create"
              : "library"
        }
        onLogin={refreshSession}
        onBack={() =>
          nativeIntent ? location.assign(base) : setView("stickers")
        }
        loadError={loginError}
        onRetry={() => {
          void refreshSession().catch(() => {});
        }}
      />
    );
  if (protectedView && session?.user && !session.user.consented)
    return (
      <CreatorConsentScreen
        onDone={refreshSession}
        onBack={() =>
          nativeIntent ? location.assign(base) : setView("stickers")
        }
      />
    );
  if (nativeIntent && session?.user)
    return <NativeSignInReturn boot={session} intent={nativeIntent} />;
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
            <Studio
              key={accountEpoch}
              section={view}
              onSection={setView}
              onAccount={updateSession}
            />
          ) : view === "account" ? (
            <AccountScreen
              onAccount={(next) => {
                updateSession(next);
                setAccountEpoch((n) => n + 1);
              }}
            />
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
              onPreview={(sticker, pack) => setPreview({ sticker, pack })}
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
            className={
              view === id || (id === "library" && view === "characters")
                ? "active"
                : ""
            }
            aria-current={
              view === id || (id === "library" && view === "characters")
                ? "page"
                : undefined
            }
            onClick={() => setView(id)}
          >
            <Icon size={22} />
            <span>{label}</span>
          </button>
        ))}
      </nav>
      {preview && (
        <div className="modal-backdrop" onClick={() => setPreview(null)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label={preview.sticker.label}
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
              src={preview.sticker.gif}
              alt={preview.sticker.label}
              width="240"
              height="240"
            />
            <h2>{preview.sticker.label}</h2>
            <a
              className="button primary"
              href={stickerDownload(preview.pack, preview.sticker)}
              download
            >
              Save GIF
            </a>
          </section>
        </div>
      )}
    </div>
  );
}
