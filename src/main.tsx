import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowRight,
  Check,
  CheckCheck,
  ChevronRight,
  Clapperboard,
  CloudUpload,
  FolderHeart,
  Heart,
  ImagePlus,
  Languages,
  LockKeyhole,
  LogOut,
  Menu,
  MessageCircle,
  Package,
  Palette,
  Plus,
  Settings,
  ShieldCheck,
  Sparkles,
  Star,
  Sticker as StickerIcon,
  Trash2,
  WandSparkles,
  X,
} from "lucide-react";
import { Capacitor } from "@capacitor/core";
import {
  api,
  API,
  setCSRF,
  type Pack,
  type Sticker,
  type Draft,
  type Item,
  type Boot,
  type Character,
  type Job,
} from "./api";
import "./style.css";
import { CreatorActions } from "./CreatorActions";
import { Community } from "./Community";
import { AnimatedSticker } from "./AnimatedSticker";
import { StickerBrowser } from "./StickerBrowser";
import { NativePlans } from "./NativePlans";
import { saveSticker } from "./native";
import { PublicCatalog } from "./PublicCatalog";

const native = Capacitor.isNativePlatform();
type View = "discover" | "studio" | "library" | "plans" | "account" | "market";
const themeNames: Record<string, string> = {
  daily: "Little everyday moments",
  office: "Work besties",
  couple: "Just the two of us",
  sports: "One more little step",
};
const languages = [
  ["zh", "中文"],
  ["en", "English"],
  ["ja", "日本語"],
];

function App() {
  const [creatorAction, setCreatorAction] = useState<
    "listing" | "wechat" | null
  >(null);
  const [boot, setBoot] = useState<Boot | null>(null),
    [packs, setPacks] = useState<Pack[]>([]),
    [view, setView] = useState<View>("discover"),
    [selected, setSelected] = useState<Pack | null>(null),
    [lang, setLang] = useState("zh"),
    [preview, setPreview] = useState<{ sticker: Sticker; pack: Pack } | null>(
      null,
    ),
    [auth, setAuth] = useState(false),
    [authMode, setAuthMode] = useState("login"),
    [toast, setToast] = useState(""),
    [busy, setBusy] = useState(false),
    [mobile, setMobile] = useState(false),
    [legal, setLegal] = useState(""),
    [report, setReport] = useState("");
  const [saved, setSaved] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("westicker-saved") || "[]");
    } catch {
      return [];
    }
  });
  const [drafts, setDrafts] = useState<Draft[]>([]),
    [characters, setCharacters] = useState<Character[]>([]),
    [jobs, setJobs] = useState<Job[]>([]),
    [editor, setEditor] = useState<Draft | null>(null);
  const [refs, setRefs] = useState<string[]>([]),
    [characterName, setCharacterName] = useState(""),
    [style, setStyle] = useState("figurine"),
    [theme, setTheme] = useState("daily"),
    [title, setTitle] = useState("My little everyday"),
    [rights, setRights] = useState(false),
    [approved, setApproved] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const [reuseCharacter, setReuseCharacter] = useState("");
  async function refresh() {
    const b = await api<Boot>("/api/bootstrap");
    setBoot(b);
    setCSRF(b.csrf);
    return b;
  }
  async function workspace() {
    const w = await api("/api/workspace");
    setDrafts(w.packs);
    setCharacters(w.characters);
    setJobs(w.jobs);
    setEditor((old) =>
      old ? w.packs.find((p: Draft) => p.id === old.id) || old : null,
    );
  }
  useEffect(() => {
    Promise.all([
      refresh().catch(() =>
        setBoot({
          user: null,
          csrf: "",
          providers: [],
          local_accounts: false,
          capabilities: {},
          plans: [],
          themes: {},
        }),
      ),
      api("/api/catalog")
        .catch(() => fetch("/catalog.json").then((r) => r.json()))
        .then((c) => setPacks(c.packs)),
    ]).catch((e) => setToast(e.message));
  }, []);
  useEffect(() => {
    if (boot?.user?.consented) workspace().catch((e) => setToast(e.message));
    else {
      setDrafts([]);
      setCharacters([]);
      setJobs([]);
    }
  }, [boot?.user?.id, boot?.user?.consented]);
  useEffect(() => {
    if (!jobs.some((j) => ["queued", "running"].includes(j.state))) return;
    const id = setInterval(() => workspace().catch(() => {}), 3000);
    return () => clearInterval(id);
  }, [jobs]);
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(""), 7000);
    return () => clearTimeout(id);
  }, [toast]);
  useEffect(() => {
    localStorage.setItem("westicker-saved", JSON.stringify(saved));
  }, [saved]);
  useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPreview(null);
        setAuth(false);
        setLegal("");
        setReport("");
      }
    };
    addEventListener("keydown", listener);
    return () => removeEventListener("keydown", listener);
  }, []);
  useEffect(() => {
    if (import.meta.env.PROD && !native && "serviceWorker" in navigator)
      navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);
  async function action(fn: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setToast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function navigate(v: View) {
    setView(v);
    setSelected(null);
    setMobile(false);
    window.scrollTo(0, 0);
  }
  function needAccount(fn: () => void) {
    if (!boot?.user) setAuth(true);
    else fn();
  }
  function favorite(id: string) {
    setSaved((old) =>
      old.includes(id) ? old.filter((x) => x !== id) : [...old, id],
    );
  }
  const icon = (I: typeof Heart) => <I size={19} strokeWidth={1.8} />;
  const user = boot?.user;

  async function upload(files: FileList | null) {
    if (!files) return;
    if (!rights) throw Error("Please confirm image permissions first.");
    for (const f of Array.from(files).slice(0, 5 - refs.length)) {
      const form = new FormData();
      form.append("file", f);
      form.append("rights", "yes");
      const result = await api("/api/assets", form);
      setRefs((old) => [...old, result.id]);
    }
  }
  async function makeDraft() {
    if (!approved)
      throw Error(
        "Confirm that these references show your character correctly.",
      );
    const c = reuseCharacter
      ? { id: reuseCharacter }
      : await api("/api/characters", {
          name: characterName,
          style,
          refs,
        });
    await api(`/api/characters/${c.id}/lock`, { approved: true });
    const p = await api("/api/packs", {
      character: c.id,
      title,
      theme,
      language: lang,
    });
    await workspace();
    const w = await api("/api/workspace");
    setEditor(w.packs.find((x: Draft) => x.id === p.id));
    setToast("Character locked. Your new collection is ready.");
  }
  async function saveEditor() {
    if (editor && editor.status === "draft")
      await api("/api/packs/" + editor.id, { items: editor.items }, "PATCH");
  }
  async function generate(kind: string, items?: string[]) {
    if (!editor) return;
    await saveEditor();
    await api(`/api/packs/${editor.id}/generate`, {
      kind,
      attempt: crypto.randomUUID(),
      consent: true,
      ...(items ? { items } : {}),
    });
    await workspace();
    setToast(
      kind === "photo"
        ? "Preparing your photo stickers."
        : "Your AI job is queued. Keep this tab or come back later.",
    );
  }
  function updateItem(index: number, patch: Partial<Item>) {
    setEditor((old) =>
      old
        ? {
            ...old,
            items: old.items.map((x, i) =>
              i === index ? { ...x, ...patch } : x,
            ),
          }
        : null,
    );
  }
  const navItems: [View, typeof Heart, string][] = [
    ["discover", StickerIcon, "Discover"],
    ["studio", WandSparkles, "Create"],
    ["library", FolderHeart, "My library"],
    ["market", Package, "Creator market"],
  ];

  return (
    <div className="app">
      <aside className={"sidebar " + (mobile ? "open" : "")}>
        <a
          className="brand"
          href="/"
          onClick={(e) => {
            e.preventDefault();
            navigate("discover");
          }}
        >
          <img src="/icon-192.png" alt="Aya" />
          <span>
            WeSticker<small>BY LAZYINGART</small>
          </span>
        </a>
        <nav>
          {navItems.map(([id, I, label]) => (
            <button
              key={id}
              className={view === id ? "active" : ""}
              onClick={() => navigate(id)}
            >
              {icon(I)}
              {label}
              {id === "library" && saved.length > 0 && (
                <small>{saved.length}</small>
              )}
            </button>
          ))}
        </nav>
        <div className="side-divider" />
        <span className="eyebrow">YOUR LITTLE STUDIO</span>
        <button className="side-link" onClick={() => navigate("plans")}>
          {icon(Sparkles)} Plans & credits
        </button>
        <button
          className="side-link"
          onClick={() => needAccount(() => navigate("account"))}
        >
          {icon(Settings)} Account
        </button>
        <div className="side-bottom">
          <div className="tiny-buddies">
            {packs[0]?.stickers.zh.slice(0, 3).map((s) => (
              <img key={s.id} src={s.poster} alt="" />
            ))}
          </div>
          <strong>A little more you.</strong>
          <p>Made for everyday conversations.</p>
          <a href="https://aya.lazying.art" target="_blank" rel="noreferrer">
            Visit Aya & Lala <ArrowRight size={14} />
          </a>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Menu"
            onClick={() => setMobile(!mobile)}
          >
            <Menu />
          </button>
          <div className="crumb">
            WeSticker <ChevronRight size={14} />{" "}
            {selected
              ? selected.english
              : view === "studio"
                ? "Your creative space"
                : view === "library"
                  ? "Made for you"
                  : view === "plans"
                    ? "Find your rhythm"
                    : view === "account"
                      ? "Your account"
                      : "Sticker collections"}
          </div>
          <div className="top-actions">
            <span className="guest-note">
              {user
                ? `${user.credits} AI credits`
                : "A little joy, no login needed"}
            </span>
            <button
              className={user ? "avatar-button" : "button outline small"}
              onClick={() => (user ? navigate("account") : setAuth(true))}
            >
              {user ? user.name.slice(0, 1).toUpperCase() : "Sign in"}
            </button>
          </div>
        </header>
        <main>
          {view === "discover" && (
            <StickerBrowser
              packs={packs}
              selected={selected}
              onSelect={setSelected}
              lang={lang}
              onLanguage={setLang}
              saved={saved}
              onFavorite={favorite}
              onPreview={(sticker, pack) => setPreview({ sticker, pack })}
              onCreate={() => navigate("studio")}
              onDownload={(pack) =>
                needAccount(() => {
                  if (user?.plan === "free") navigate("plans");
                  else
                    window.location.href =
                      API + `/api/default/${pack.id}/download/${lang}`;
                })
              }
              onNativeSave={
                native
                  ? (pack, sticker) =>
                      action(() => saveSticker(pack, sticker, lang))
                  : undefined
              }
            />
          )}
          {view === "studio" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow coral">
                    MADE BY YOU, WITH A LITTLE HELP
                  </span>
                  <h1>{editor ? editor.title : "Meet your sticker self."}</h1>
                  <p>
                    {editor
                      ? "Small words. A familiar face. Review every little expression."
                      : "Your face, your pet, or a character that is completely yours."}
                  </p>
                </div>
                {editor && (
                  <button
                    className="button outline"
                    onClick={() => setEditor(null)}
                  >
                    <Plus size={17} />
                    New collection
                  </button>
                )}
              </div>
              {!user ? (
                <section className="welcome-studio">
                  <div className="studio-samples">
                    {packs[0]?.stickers.zh.slice(0, 4).map((s) => (
                      <img key={s.id} src={s.poster} alt={s.label} />
                    ))}
                  </div>
                  <h2>Your next favorite sticker could be you.</h2>
                  <p>
                    A private character library, your own words, and a
                    collection ready to share.
                  </p>
                  <button
                    className="button primary"
                    onClick={() => setAuth(true)}
                  >
                    <Sparkles size={18} />
                    Start my collection
                  </button>
                </section>
              ) : !editor ? (
                <div className="studio-layout">
                  <section className="form-section">
                    <div className="step-title">
                      <span>1</span>
                      <h2>Your character</h2>
                    </div>
                    {characters.length > 0 && (
                      <label>
                        Character library
                        <select
                          value={reuseCharacter}
                          onChange={(e) => {
                            setReuseCharacter(e.target.value);
                            const c = characters.find(
                              (x) => x.id === e.target.value,
                            );
                            setRefs(c?.refs || []);
                            setCharacterName(c?.name || "");
                            setStyle(c?.style || "figurine");
                            setApproved(!!c?.locked);
                          }}
                        >
                          <option value="">New character</option>
                          {characters.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    <label>
                      Name
                      <input
                        disabled={!!reuseCharacter}
                        value={characterName}
                        onChange={(e) => setCharacterName(e.target.value)}
                        placeholder="A name that feels like you"
                        maxLength={60}
                      />
                    </label>
                    <label className="checkline">
                      <input
                        type="checkbox"
                        checked={rights}
                        onChange={(e) => setRights(e.target.checked)}
                      />
                      <span>
                        I own these images or have permission. Everyone depicted
                        is 18+ and has agreed.
                      </span>
                    </label>
                    <input
                      ref={fileInput}
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      multiple
                      hidden
                      onChange={(e) => action(() => upload(e.target.files))}
                    />
                    <div className="ref-grid">
                      {refs.map((r) => (
                        <div key={r}>
                          <img
                            src={API + "/api/assets/" + r}
                            alt="Character reference"
                          />
                          <button
                            aria-label="Remove reference"
                            disabled={!!reuseCharacter}
                            onClick={() =>
                              setRefs((old) => old.filter((x) => x !== r))
                            }
                          >
                            <X size={13} />
                          </button>
                        </div>
                      ))}
                      {!reuseCharacter && refs.length < 5 && (
                        <button
                          className="upload-tile"
                          disabled={!rights || busy}
                          onClick={() => fileInput.current?.click()}
                        >
                          <ImagePlus size={24} />
                          <span>Add photos</span>
                          <small>{refs.length}/5</small>
                        </button>
                      )}
                    </div>
                    <label>
                      Style
                      <select
                        disabled={!!reuseCharacter}
                        value={style}
                        onChange={(e) => setStyle(e.target.value)}
                      >
                        <option value="figurine">
                          Realistic little figurine
                        </option>
                        <option value="soft">Soft & cuddly</option>
                        <option value="ink">Playful illustration</option>
                        <option value="photo">Original photo</option>
                      </select>
                    </label>
                    <label className="checkline">
                      <input
                        type="checkbox"
                        checked={approved}
                        onChange={(e) => setApproved(e.target.checked)}
                      />
                      <span>
                        These photos show the character I want. Keep this
                        identity consistent.
                      </span>
                    </label>
                    <p className="fine">
                      <ShieldCheck size={14} /> Private references. Metadata
                      removed. Originals expire after 30 days.
                    </p>
                  </section>
                  <section className="form-section">
                    <div className="step-title">
                      <span>2</span>
                      <h2>Your everyday story</h2>
                    </div>
                    <label>
                      Collection name
                      <input
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        maxLength={60}
                      />
                    </label>
                    <label>
                      Little moments
                      <select
                        value={theme}
                        onChange={(e) => setTheme(e.target.value)}
                      >
                        {Object.entries(themeNames).map(([id, name]) => (
                          <option key={id} value={id}>
                            {name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Sticker language
                      <select
                        value={lang}
                        onChange={(e) => setLang(e.target.value)}
                      >
                        {languages.map(([id, name]) => (
                          <option key={id} value={id}>
                            {name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <div className="caption-list">
                      {boot?.themes[theme]?.[lang]?.map((label, i) => (
                        <div key={label}>
                          <span>{String(i + 1).padStart(2, "0")}</span>
                          {label}
                          <Check size={15} />
                        </div>
                      ))}
                    </div>
                    <button
                      className="button primary full"
                      disabled={
                        busy ||
                        !refs.length ||
                        !approved ||
                        !characterName.trim() ||
                        !title.trim()
                      }
                      onClick={() => action(makeDraft)}
                    >
                      <LockKeyhole size={18} />
                      Lock character & create draft
                    </button>
                  </section>
                </div>
              ) : (
                <>
                  <div className="editor-toolbar">
                    <span className="status">
                      <span className="dot" />
                      {(
                        {
                          draft: "Private draft",
                          moderation: "In review",
                          listed: "Published",
                          rejected: "Needs revision",
                          hidden: "Hidden",
                        } as Record<string, string>
                      )[editor.status] || editor.status}
                    </span>
                    <span>
                      {editor.items.filter((i) => i.approved).length}/
                      {editor.items.length} reviewed
                    </span>
                    <div className="spacer" />
                    <button
                      className="button outline small"
                      disabled={busy || editor.status !== "draft"}
                      onClick={() =>
                        action(async () => {
                          await saveEditor();
                          setToast("Draft saved.");
                        })
                      }
                    >
                      Save changes
                    </button>
                    <button
                      className="button primary small"
                      disabled={
                        busy ||
                        editor.items.some((i) => !i.asset || !i.approved)
                      }
                      onClick={() =>
                        action(async () => {
                          await saveEditor();
                          window.location.href =
                            API + `/api/packs/${editor.id}/export`;
                        })
                      }
                    >
                      <ArrowDownToLine size={16} />
                      Export ZIP
                    </button>
                  </div>
                  {jobs
                    .filter((j) => j.pack_id === editor.id)
                    .slice(0, 1)
                    .map((j) => (
                      <div key={j.id} className={"job-status " + j.state}>
                        <div>
                          <Clapperboard size={18} />
                          <strong>
                            {j.state === "review"
                              ? "Ready for your review"
                              : j.state === "uncertain"
                                ? "Needs an operator check"
                                : j.state === "failed"
                                  ? "Could not finish"
                                  : `Preparing your stickers · ${j.progress}%`}
                          </strong>
                        </div>
                        {j.error && <p>{j.error}</p>}
                        <progress max="100" value={j.progress} />
                      </div>
                    ))}
                  <div className="editor-grid">
                    {editor.items.map((item, i) => (
                      <article
                        key={item.id}
                        className={
                          "edit-sticker " + (item.approved ? "approved" : "")
                        }
                      >
                        <div className="edit-preview">
                          {item.asset ? (
                            <img
                              src={API + "/api/assets/" + item.asset}
                              alt={item.label}
                            />
                          ) : (
                            <div>
                              <StickerIcon size={35} />
                              <small>Expression {i + 1}</small>
                            </div>
                          )}
                        </div>
                        <input
                          aria-label={"Caption " + (i + 1)}
                          disabled={editor.status !== "draft"}
                          maxLength={32}
                          value={item.label}
                          onChange={(e) =>
                            updateItem(i, {
                              label: e.target.value,
                              approved: false,
                            })
                          }
                        />
                        <label className="checkline">
                          <input
                            type="checkbox"
                            disabled={!item.asset || editor.status !== "draft"}
                            checked={item.approved}
                            onChange={(e) =>
                              updateItem(i, { approved: e.target.checked })
                            }
                          />
                          Looks like me
                        </label>
                        <div className="expression-tools">
                          <button
                            className="icon-button"
                            title="Generate this expression · 1 credit"
                            aria-label={
                              "Generate expression " + (i + 1) + " for 1 credit"
                            }
                            disabled={
                              busy ||
                              editor.status !== "draft" ||
                              !boot?.capabilities.ai_images ||
                              jobs.some(
                                (j) =>
                                  j.pack_id === editor.id &&
                                  ["queued", "running", "uncertain"].includes(
                                    j.state,
                                  ),
                              )
                            }
                            onClick={() =>
                              action(() => generate("ai", [item.id]))
                            }
                          >
                            <WandSparkles size={16} />
                            <span>1</span>
                          </button>
                          <button
                            className="icon-button"
                            title="Animate approved expression · 3 credits"
                            aria-label={
                              "Animate expression " + (i + 1) + " for 3 credits"
                            }
                            disabled={
                              busy ||
                              editor.status !== "draft" ||
                              !item.approved ||
                              !boot?.capabilities.animation ||
                              jobs.some(
                                (j) =>
                                  j.pack_id === editor.id &&
                                  ["queued", "running", "uncertain"].includes(
                                    j.state,
                                  ),
                              )
                            }
                            onClick={() =>
                              action(() => generate("animate", [item.id]))
                            }
                          >
                            <Clapperboard size={16} />
                            <span>3</span>
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                  <div className="generation-bar">
                    <div>
                      <strong>Choose how to make this set</strong>
                      <p>
                        Photo keeps your uploaded image. AI creates a new
                        expression for each caption.
                      </p>
                    </div>
                    <div className="row">
                      <button
                        className="button outline"
                        disabled={
                          busy ||
                          editor.status !== "draft" ||
                          jobs.some(
                            (j) =>
                              j.pack_id === editor.id &&
                              ["queued", "running", "uncertain"].includes(
                                j.state,
                              ),
                          )
                        }
                        onClick={() => action(() => generate("photo"))}
                      >
                        <ImagePlus size={18} />
                        Photo stickers · free
                      </button>
                      <button
                        className="button primary"
                        disabled={
                          busy ||
                          editor.status !== "draft" ||
                          !boot?.capabilities.ai_images
                        }
                        title={
                          !boot?.capabilities.ai_images
                            ? "AI provider not connected yet"
                            : ""
                        }
                        onClick={() => action(() => generate("ai"))}
                      >
                        <WandSparkles size={18} />
                        AI expressions · {editor.items.length} credits
                      </button>
                    </div>
                  </div>
                  <div className="publish-tools">
                    <button
                      onClick={() =>
                        action(async () => {
                          await saveEditor();
                          setCreatorAction("listing");
                        })
                      }
                    >
                      <Package size={18} />
                      Sell this collection <ChevronRight size={16} />
                    </button>
                    <button
                      onClick={() =>
                        action(async () => {
                          await saveEditor();
                          setCreatorAction("wechat");
                        })
                      }
                    >
                      <CloudUpload size={18} />
                      WeChat draft assistant <ChevronRight size={16} />
                    </button>
                    <button onClick={() => setReport("pack:" + editor.id)}>
                      Report a generation problem
                    </button>
                  </div>
                </>
              )}
            </>
          )}
          {view === "market" && (
            <Community
              signedIn={!!user}
              onSignIn={() => setAuth(true)}
              onReport={setReport}
              onNotice={setToast}
            />
          )}
          {view === "library" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow teal">
                    YOUR FAVORITES & LITTLE CREATIONS
                  </span>
                  <h1>A happy little collection.</h1>
                  <p>
                    Saved favorites stay on this device. Your private creations
                    stay in your account.
                  </p>
                </div>
                <button
                  className="button primary"
                  onClick={() => navigate("studio")}
                >
                  <Plus size={18} />
                  Create
                </button>
              </div>
              {drafts.length > 0 && (
                <>
                  <h2 className="section-title">Your creations</h2>
                  <div className="draft-list">
                    {drafts.map((d) => (
                      <button
                        key={d.id}
                        onClick={() => {
                          setEditor(d);
                          navigate("studio");
                        }}
                      >
                        <div className="draft-thumb">
                          {d.items.find((i) => i.asset) ? (
                            <img
                              src={
                                API +
                                "/api/assets/" +
                                d.items.find((i) => i.asset)!.asset
                              }
                              alt=""
                            />
                          ) : (
                            <Palette />
                          )}
                        </div>
                        <span>
                          <strong>{d.title}</strong>
                          <small>
                            {d.items.length} stickers · {d.status}
                          </small>
                        </span>
                        <ArrowRight size={18} />
                      </button>
                    ))}
                  </div>
                </>
              )}
              <h2 className="section-title">Saved collections</h2>
              <div className="saved-grid">
                {packs
                  .filter((p) => saved.includes(p.id))
                  .map((p) => (
                    <button
                      key={p.id}
                      onClick={() => {
                        navigate("discover");
                        setSelected(p);
                      }}
                    >
                      <img src={p.banner} alt="" />
                      <strong>{p.english}</strong>
                      <span>{p.count} stickers</span>
                    </button>
                  ))}
              </div>
              {!saved.length && (
                <div className="empty">
                  <FolderHeart size={34} />
                  <h2>Your favorites belong here.</h2>
                  <button
                    className="button outline"
                    onClick={() => navigate("discover")}
                  >
                    Find a little joy
                  </button>
                </div>
              )}
            </>
          )}
          {view === "plans" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow coral">
                    ROOM FOR A LITTLE MORE YOU
                  </span>
                  <h1>Pick your creative rhythm.</h1>
                  <p>
                    One account, your own creations. Your photos are never sold.
                  </p>
                </div>
              </div>
              {native && boot ? (
                <NativePlans
                  boot={boot}
                  onSignIn={() => setAuth(true)}
                  onRefresh={refresh}
                />
              ) : (
                <>
                  <div className="plans-grid">
                    {boot?.plans.map((p, i) => (
                      <section key={p.id} className={"plan plan-" + i}>
                        <span className="plan-label">
                          {i === 0
                            ? "A LITTLE JOY"
                            : i === 1
                              ? "MAKE IT YOURS"
                              : "YOUR OWN LITTLE STUDIO"}
                        </span>
                        <h2>{p.name}</h2>
                        <div className="price">
                          ${(p.cents / 100).toFixed(2)}
                          <small>/ month</small>
                        </div>
                        <ul>
                          {p.features.map((f) => (
                            <li key={f}>
                              <Check size={17} />
                              {f}
                            </li>
                          ))}
                        </ul>
                        <button
                          className={
                            "button full " + (i === 1 ? "primary" : "outline")
                          }
                          disabled={
                            busy || native || !boot.capabilities.web_checkout
                          }
                          onClick={() =>
                            needAccount(() =>
                              action(async () => {
                                const r = await api("/api/billing/subscribe", {
                                  plan: p.id,
                                  attempt: crypto.randomUUID(),
                                });
                                location.href = r.url;
                              }),
                            )
                          }
                        >
                          {!boot.capabilities.web_checkout || native
                            ? "Purchase setup pending"
                            : `Choose ${p.name}`}
                        </button>
                      </section>
                    ))}
                  </div>
                  <p className="plan-note">
                    Prices in USD. Monthly subscriptions renew until canceled.
                    AI images consume one credit each; failed requests are
                    reconciled before retry. Native purchases will use the
                    platform store. No earnings or WeChat approval is
                    guaranteed.
                  </p>
                  <div className="row">
                    <button
                      className="text-button"
                      onClick={() =>
                        needAccount(() =>
                          action(async () => {
                            const r = await api("/api/billing/manage", {});
                            location.href = r.url;
                          }),
                        )
                      }
                    >
                      Manage subscription
                    </button>
                  </div>
                </>
              )}
              <div className="row">
                <button
                  className="text-button"
                  onClick={() => setLegal("terms")}
                >
                  Terms
                </button>
                <button
                  className="text-button"
                  onClick={() => setLegal("privacy")}
                >
                  Privacy
                </button>
              </div>
            </>
          )}
          {view === "account" && (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow teal">YOUR SPACE</span>
                  <h1>Hello, {user?.name || "friend"}.</h1>
                </div>
              </div>
              <section className="account-section">
                <h2>Account & privacy</h2>
                <dl>
                  <dt>Plan</dt>
                  <dd>{user?.plan || "Guest"}</dd>
                  <dt>AI credits</dt>
                  <dd>{user?.credits || 0}</dd>
                  <dt>Character cards</dt>
                  <dd>{characters.length}</dd>
                </dl>
                <button
                  className="button outline"
                  onClick={() =>
                    action(async () => {
                      const r = await api("/api/creator/onboard", {});
                      location.href = r.url;
                    })
                  }
                >
                  Creator payout setup <ArrowRight size={16} />
                </button>
                <p>
                  WeSticker purchases and AYA store purchases are separate.
                  Sharing an identity does not merge subscriptions.
                </p>
                <div className="account-actions">
                  <button
                    onClick={() =>
                      action(async () => {
                        await api("/api/auth/logout", {});
                        await refresh();
                        navigate("discover");
                      })
                    }
                  >
                    <LogOut size={17} />
                    Sign out
                  </button>
                  <button className="danger" onClick={() => setLegal("delete")}>
                    <Trash2 size={17} />
                    Delete my account
                  </button>
                </div>
              </section>
            </>
          )}
          <footer>
            <span>
              WeSticker <span className="footer-dot">·</span> Made with a little
              love.
            </span>
            <div>
              <button onClick={() => setLegal("privacy")}>Privacy</button>
              <button onClick={() => setLegal("terms")}>Terms</button>
              <button onClick={() => setReport("app")}>Report</button>
              <a href="mailto:hello@lazying.art">Help</a>
            </div>
          </footer>
        </main>
      </div>
      {user && !user.consented && (
        <div className="modal-backdrop">
          <section
            className="auth-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Creator agreement"
          >
            <h2>Welcome, {user.name}.</h2>
            <p>
              Your original photos and characters stay private until you choose
              to share.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                action(async () => {
                  await api("/api/account/consent", {
                    adult: true,
                    terms: true,
                  });
                  await refresh();
                });
              }}
            >
              <label className="checkline">
                <input type="checkbox" required />I am 18 or older.
              </label>
              <label className="checkline">
                <input type="checkbox" required />I agree to the creator terms
                and privacy policy.
              </label>
              <div className="row">
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setLegal("terms")}
                >
                  Read terms
                </button>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => setLegal("privacy")}
                >
                  Read privacy
                </button>
              </div>
              <button className="button primary full" disabled={busy}>
                Continue
              </button>
              <button
                type="button"
                className="text-button full"
                onClick={() =>
                  action(async () => {
                    await api("/api/auth/logout", {});
                    await refresh();
                  })
                }
              >
                Sign out
              </button>
            </form>
          </section>
        </div>
      )}
      {creatorAction && editor && (
        <CreatorActions
          mode={creatorAction}
          pack={editor}
          onClose={() => setCreatorAction(null)}
          onDone={(message) => {
            setToast(message);
            workspace().catch((e) => setToast(e.message));
          }}
        />
      )}
      {preview && (
        <div className="modal-backdrop" onClick={() => setPreview(null)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Sticker preview"
            className="preview-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              className="icon-button close"
              aria-label="Close preview"
              onClick={() => setPreview(null)}
            >
              <X />
            </button>
            <AnimatedSticker sticker={preview.sticker} />
            <h2>{preview.sticker.label}</h2>
            <p>{preview.pack.english}</p>
            <a
              className="button primary"
              onClick={
                native
                  ? (e) => {
                      e.preventDefault();
                      action(() =>
                        saveSticker(preview.pack, preview.sticker, lang),
                      );
                    }
                  : undefined
              }
              href={
                API +
                `/api/default/${preview.pack.id}/sticker/${lang}/${preview.sticker.id}`
              }
            >
              <ArrowDownToLine size={18} />
              Save GIF
            </a>
            <button
              className="text-button"
              onClick={() => {
                setReport(preview.pack.id + ":" + preview.sticker.id);
                setPreview(null);
              }}
            >
              Report this sticker
            </button>
          </section>
        </div>
      )}
      {auth && (
        <div className="modal-backdrop">
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Sign in"
            className="auth-modal"
          >
            <button
              className="icon-button close"
              aria-label="Close sign in"
              onClick={() => setAuth(false)}
            >
              <X />
            </button>
            <img className="auth-mascot" src="/icon-192.png" alt="Aya" />
            <h2>Your little creative world.</h2>
            <p>Keep your characters, drafts and downloads together.</p>
            {boot?.providers.map((p) => (
              <a
                className="button outline full provider"
                key={p}
                href={API + `/auth/${p}/start`}
              >
                Continue with{" "}
                {p === "lazyingart"
                  ? "LazyingArt"
                  : p.charAt(0).toUpperCase() + p.slice(1)}
              </a>
            ))}
            {boot?.local_accounts ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const form = new FormData(e.currentTarget);
                  action(async () => {
                    await api(
                      "/api/auth/" +
                        (authMode === "login" ? "login" : "register"),
                      {
                        email: form.get("email"),
                        password: form.get("password"),
                        name: form.get("name"),
                        adult: form.get("adult") === "on",
                        terms: form.get("terms") === "on",
                      },
                    );
                    await refresh();
                    setAuth(false);
                  });
                }}
              >
                {authMode === "register" && (
                  <label>
                    Name
                    <input
                      name="name"
                      required
                      maxLength={60}
                      autoComplete="name"
                    />
                  </label>
                )}
                <label>
                  Email
                  <input
                    name="email"
                    type="email"
                    required
                    autoComplete="email"
                  />
                </label>
                <label>
                  Password
                  <input
                    name="password"
                    type="password"
                    minLength={12}
                    required
                    autoComplete={
                      authMode === "register"
                        ? "new-password"
                        : "current-password"
                    }
                  />
                </label>
                {authMode === "register" && (
                  <>
                    <label className="checkline">
                      <input name="adult" type="checkbox" required />I am 18 or
                      older.
                    </label>
                    <label className="checkline">
                      <input name="terms" type="checkbox" required />I agree to
                      the terms and privacy policy.
                    </label>
                  </>
                )}
                <button className="button primary full" disabled={busy}>
                  {authMode === "login" ? "Sign in" : "Create account"}
                </button>
                <button
                  type="button"
                  className="text-button full"
                  onClick={() =>
                    setAuthMode(authMode === "login" ? "register" : "login")
                  }
                >
                  {authMode === "login"
                    ? "New here? Create an account"
                    : "Already here? Sign in"}
                </button>
              </form>
            ) : (
              !boot?.providers.length && (
                <p className="notice">
                  Account connections are being prepared. You can browse and
                  save all default previews without signing in.
                </p>
              )
            )}
            <small>Your private photos stay yours.</small>
          </section>
        </div>
      )}
      {report && (
        <div className="modal-backdrop">
          <section
            className="auth-modal"
            role="dialog"
            aria-modal="true"
            aria-label="Report content"
          >
            <button
              className="icon-button close"
              aria-label="Close report"
              onClick={() => setReport("")}
            >
              <X />
            </button>
            <h2>Help keep this place kind.</h2>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const data = new FormData(e.currentTarget);
                action(async () => {
                  await api("/api/reports", {
                    target: report,
                    reason: data.get("reason"),
                  });
                  setReport("");
                  setToast("Report received. Thank you for telling us.");
                });
              }}
            >
              <label>
                What happened?
                <textarea
                  name="reason"
                  required
                  minLength={5}
                  maxLength={2000}
                />
              </label>
              <button className="button primary full" disabled={busy}>
                Send report
              </button>
            </form>
          </section>
        </div>
      )}
      {legal && (
        <div className="modal-backdrop">
          <section
            className="auth-modal legal"
            role="dialog"
            aria-modal="true"
            aria-label={legal}
          >
            <button
              className="icon-button close"
              aria-label="Close"
              onClick={() => setLegal("")}
            >
              <X />
            </button>
            {legal === "delete" ? (
              <>
                <h2>Delete your account?</h2>
                <p>
                  Your private references, characters and packs will be removed.
                  Cancel any active subscription separately in the store where
                  you purchased it. Legally required payment records may be
                  retained.
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const data = new FormData(e.currentTarget);
                    action(async () => {
                      await api("/api/account/delete", {
                        confirmation: data.get("confirm"),
                      });
                      setLegal("");
                      await refresh();
                      navigate("discover");
                    });
                  }}
                >
                  <label>
                    Type DELETE
                    <input name="confirm" required pattern="DELETE" />
                  </label>
                  <button className="button danger-button full" disabled={busy}>
                    Delete account and creations
                  </button>
                </form>
              </>
            ) : (
              <>
                <h2>
                  {legal === "privacy"
                    ? "Your privacy matters."
                    : "Make something kind."}
                </h2>
                {legal === "privacy" ? (
                  <>
                    <p>
                      We store your account identity, private images, creations
                      and purchase entitlements to operate WeSticker. Original
                      photo metadata is removed. Uploaded references are
                      scheduled for deletion after 30 days; generated art stays
                      until you delete it.
                    </p>
                    <p>
                      AI generation sends the references you choose to the
                      configured image provider only after you request it. We do
                      not use your private uploads as marketplace examples.
                      Public sharing and WeChat uploading require separate
                      consent.
                    </p>
                    <p>
                      Stripe or native stores handle payment details. An
                      isolated WeChat browser is optional and never submits
                      review. You can report content, export your creations and
                      request account deletion inside the app.
                    </p>
                  </>
                ) : (
                  <>
                    <p>
                      Use images you own or have permission to use. Creators
                      must be 18+. Do not impersonate others, exploit minors or
                      upload infringing or abusive material.
                    </p>
                    <p>
                      Default Aya & Lala downloads are for personal use. You
                      retain rights to your own original inputs. AI output
                      rights and originality depend on applicable law and
                      provider terms.
                    </p>
                    <p>
                      Subscriptions renew monthly until canceled. Quotas and
                      price appear before purchase. Marketplace listings need
                      moderation and verified payout onboarding; no earnings or
                      platform approval is promised.
                    </p>
                  </>
                )}
                <p>
                  Questions or deletion requests:{" "}
                  <a href="mailto:hello@lazying.art">hello@lazying.art</a>
                </p>
              </>
            )}
          </section>
        </div>
      )}
      {toast && (
        <div role="status" className="toast">
          <MessageCircle size={18} />
          <span>{toast}</span>
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {import.meta.env.VITE_PUBLIC_CATALOG_ONLY === "true" ? <PublicCatalog /> : <App />}
  </React.StrictMode>,
);
