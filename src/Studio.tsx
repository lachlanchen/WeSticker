import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  ArrowDownToLine,
  ArrowUp,
  Check,
  CloudUpload,
  History,
  ImagePlus,
  Plus,
  RefreshCw,
  Sparkles,
  Store,
  Trash2,
  X,
} from "lucide-react";
import {
  api,
  APIError,
  API,
  setCSRF,
  type Boot,
  type Character,
  type Draft,
  type Item,
  type Job,
} from "./api";
import "./studio.css";
import { LocalStudio } from "./LocalStudio";
import { CreatorActions } from "./CreatorActions";
const ChatText = lazy(() =>
  import("./ChatText").then((m) => ({ default: m.ChatText })),
);

type Limits = {
  plan: string;
  pack_size: number;
  packs: number;
  characters: number;
  credits: number;
  trial_images: number;
  batch: boolean;
  animation: boolean;
};
type Workspace = {
  characters: Character[];
  packs: Draft[];
  jobs: Job[];
  limits: Limits;
};
type Proposal = {
  reply: string;
  items: Item[] | null;
  revision: number;
  source: string;
};
type Message = {
  id: string;
  text: string;
  state: string;
  result: Proposal | null;
};
type Quote = {
  credits: number;
  revision: number;
  can_generate: boolean;
  reason: string | null;
  kind: string;
  items: string[];
};
const blank: Workspace = {
  characters: [],
  packs: [],
  jobs: [],
  limits: {
    plan: "free",
    pack_size: 1,
    packs: 2,
    characters: 2,
    credits: 0,
    trial_images: 0,
    batch: false,
    animation: false,
  },
};
const asset = (id: string) => API + "/api/assets/" + id;
const newID = () => crypto.randomUUID().replaceAll("-", "");

export function Studio({
  section = "create",
  onSection,
  onAccount,
}: {
  section?: "create" | "library" | "characters";
  onSection?: (s: "create" | "library" | "characters") => void;
  onAccount?: (boot: Boot) => void;
}) {
  const [boot, setBoot] = useState<Boot | null>(null);
  const [w, setW] = useState<Workspace>(blank);
  const [pack, setPack] = useState<Draft | null>(null);
  const [rows, setRows] = useState<Item[]>([]);
  const [dirty, setDirty] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [refs, setRefs] = useState<string[]>([]);
  const [rights, setRights] = useState(false);
  const [name, setName] = useState("My character");
  const [title, setTitle] = useState("Everyday moments");
  const [language, setLanguage] = useState("en");
  const [character, setCharacter] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [versions, setVersions] = useState<
    { id: string; state: string; items: Item[] }[] | null
  >(null);
  const [creating, setCreating] = useState(false);
  const [showReferences, setShowReferences] = useState(false);
  const [pane, setPane] = useState("chat");
  const [libraryTab, setLibraryTab] = useState("creations");
  const [localView, setLocalView] = useState<"create" | "agent" | null>(null);
  const [creatorAction, setCreatorAction] = useState<
    "listing" | "wechat" | null
  >(null);
  const [notice, setNotice] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const packRef = useRef(pack);
  packRef.current = pack;
  const dirtyRef = useRef(dirty);
  const busyRef = useRef(false);
  dirtyRef.current = dirty;
  const active = w.jobs.some((j) => ["queued", "running"].includes(j.state));
  const locked = w.jobs.some(
    (j) =>
      j.pack_id === pack?.id &&
      ["queued", "running", "uncertain"].includes(j.state),
  );
  async function run(fn: () => Promise<void>) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
      if (e instanceof APIError && e.status === 401) {
        const signedOut = boot ? { ...boot, user: null } : null;
        setBoot(signedOut);
        if (signedOut) onAccount?.(signedOut);
        setW(blank);
        setPack(null);
        setMessages([]);
        setRows([]);
      }
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  async function refresh() {
    const b = await api<Boot>("/api/bootstrap");
    setCSRF(b.csrf);
    setBoot(b);
    onAccount?.(b);
    if (b.user?.consented) {
      let next: Workspace;
      try {
        next = await api<Workspace>("/api/workspace");
      } catch (e) {
        if (!(e instanceof APIError) || e.status !== 401) throw e;
        const signedOut = { ...b, user: null };
        setBoot(signedOut);
        onAccount?.(signedOut);
        setW(blank);
        setPack(null);
        setRows([]);
        setMessages([]);
        return;
      }
      setW(next);
      const current = next.packs.find((p) => p.id === packRef.current?.id);
      if (current && !dirtyRef.current) {
        setPack(current);
        setRows(current.items);
      }
    } else {
      setW(blank);
      setPack(null);
      setRows([]);
      setMessages([]);
      setRefs([]);
      setCharacter("");
      setQuote(null);
      setSelected([]);
      setDirty(false);
    }
  }
  useEffect(() => {
    refresh().catch(() =>
      setError(
        "The creator service is unavailable. Your saved catalog is still available.",
      ),
    );
  }, []);
  useEffect(() => {
    if (!active) return;
    const timer = setInterval(
      () =>
        refresh().catch(() =>
          setError(
            "Connection interrupted. Existing jobs continue; reconnect to check their status.",
          ),
        ),
      4000,
    );
    return () => clearInterval(timer);
  }, [active]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);
  useEffect(() => {
    setQuote(null);
  }, [selected]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    addEventListener("beforeunload", warn);
    return () => removeEventListener("beforeunload", warn);
  }, [dirty]);
  async function open(p: Draft) {
    if (dirty)
      throw Error("Save the current table before opening another creation.");
    setPack(p);
    setRows(p.items);
    setSelected(p.items.slice(0, 1).map((r) => r.id));
    setDirty(false);
    setQuote(null);
    setCreating(false);
    const result = await api<{ messages: Message[] }>(
      `/api/packs/${p.id}/conversation`,
    );
    setMessages(result.messages);
    onSection?.("create");
  }
  function edit(index: number, patch: Partial<Item>) {
    setRows((old) =>
      old.map((r, i) =>
        i === index ? { ...r, ...patch, approved: patch.approved ?? false } : r,
      ),
    );
    setDirty(true);
    setQuote(null);
  }
  async function save(items = rows, revision = pack?.revision) {
    if (!pack) return;
    const result = await api<{ revision: number }>(
      `/api/packs/${pack.id}`,
      { items, revision },
      "PATCH",
    );
    const updated = { ...pack, items, revision: result.revision };
    setPack(updated);
    packRef.current = updated;
    setRows(items);
    setDirty(false);
    dirtyRef.current = false;
    setQuote(null);
    await refresh();
  }
  async function upload(files: FileList | null) {
    if (!files) return;
    if (!rights) throw Error("Confirm permission before uploading references.");
    for (const f of Array.from(files).slice(0, 5 - refs.length)) {
      const form = new FormData();
      form.append("file", f);
      form.append("rights", "yes");
      const result = await api<{ id: string }>("/api/assets", form);
      setRefs((old) => [...old, result.id]);
    }
  }
  async function create() {
    let id = character;
    if (!id) {
      if (!rights || !refs.length)
        throw Error("Upload and approve your character references first.");
      const c = await api<{ id: string }>("/api/characters", {
        name,
        style: "figurine",
        refs,
      });
      id = c.id;
      setCharacter(id);
    }
    await api(`/api/characters/${id}/lock`, { approved: true });
    if (pack && !creating && !pack.character_id) {
      await api(`/api/packs/${pack.id}/character`, {
        character: id,
        revision: pack.revision,
      });
      await refresh();
      setShowReferences(false);
      return;
    }
    const made = await api<{ id: string }>("/api/packs", {
      character: id,
      title,
      language,
      theme: "daily",
    });
    const next = await api<Workspace>("/api/workspace");
    setW(next);
    await open(next.packs.find((p) => p.id === made.id)!);
    setShowReferences(false);
  }
  async function send() {
    if (!text.trim()) return;
    if (dirty) throw Error("Save the table before asking for a revision.");
    const input = text.trim();
    let current = pack;
    if (!current || creating) {
      const made = await api<{ id: string }>("/api/packs", {
        title: input.slice(0, 60),
        language,
        theme: "daily",
      });
      const next = await api<Workspace>("/api/workspace");
      setW(next);
      current = next.packs.find((p) => p.id === made.id)!;
      await open(current);
    }
    const attempt = newID();
    setMessages((old) => [
      ...old,
      { id: attempt, text: input, state: "working", result: null },
    ]);
    setText("");
    try {
      await api(`/api/packs/${current.id}/chat`, { text: input, attempt });
    } finally {
      const result = await api<{ messages: Message[] }>(
        `/api/packs/${current.id}/conversation`,
      );
      setMessages(result.messages);
    }
  }
  async function generate() {
    if (!quote || !pack) return;
    const key = `westicker-generation:${boot?.user?.id}:${pack.id}:${quote.kind}:${quote.revision}:${quote.items.join(",")}`;
    const attempt = localStorage.getItem(key) || newID();
    localStorage.setItem(key, attempt);
    await api(`/api/packs/${pack.id}/generate`, {
      kind: quote.kind,
      items: quote.items,
      revision: quote.revision,
      attempt,
      consent: true,
    });
    setQuote(null);
    await refresh();
  }
  const composer = (
    <form
      className="studio-composer"
      onSubmit={(e) => {
        e.preventDefault();
        run(send);
      }}
    >
      <button
        type="button"
        title="Character references"
        aria-label="Character references"
        onClick={() => setShowReferences(!showReferences)}
      >
        <ImagePlus size={20} />
      </button>
      <textarea
        aria-label="Message your sticker assistant"
        placeholder="Tell Aya what you have in mind…"
        value={text}
        maxLength={2000}
        onChange={(e) => setText(e.target.value)}
        rows={2}
      />
      <button
        className="primary"
        aria-label="Send message"
        title="Send message"
        disabled={busy || !text.trim() || dirty || locked}
      >
        <ArrowUp size={20} />
      </button>
    </form>
  );
  if (localView)
    return (
      <section className="creator-workspace">
        <button onClick={() => setLocalView(null)}>Back to studio</button>
        <LocalStudio view={localView} onView={setLocalView} />
      </section>
    );
  if (!boot)
    return (
      <section className="creator-workspace">
        <p role={error ? "alert" : "status"}>
          {error || "Connecting to your studio…"}
        </p>
        {error && <button onClick={() => run(refresh)}>Try again</button>}
      </section>
    );
  if (!boot.user) return null;
  if (!boot.user.consented) return null;
  return (
    <section className="creator-workspace">
      <header className="creator-heading">
        <div>
          <h1>{section === "create" ? "Create" : "Library"}</h1>
        </div>
        <button
          title="Refresh workspace"
          aria-label="Refresh workspace"
          className="icon-button"
          disabled={busy}
          onClick={() => run(refresh)}
        >
          <RefreshCw size={18} />
        </button>
      </header>
      {error && (
        <p role="alert" className="studio-error">
          {error}
        </p>
      )}
      {section !== "create" && (
        <button
          className="local-draft-link"
          onClick={() => setLocalView("create")}
        >
          Saved local photo draft
        </button>
      )}
      {
        <>
          {section !== "create" && (
            <div className="library-tabs" role="tablist" aria-label="Library">
              {[
                ["creations", "Creations"],
                ["characters", "Characters"],
              ].map(([id, label]) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={
                    (section === "characters" ? "characters" : libraryTab) ===
                    id
                  }
                  onClick={() => {
                    setLibraryTab(id);
                    if (section === "characters") onSection?.("library");
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          {section === "characters" ||
          (section === "library" && libraryTab === "characters") ? (
            <div className="character-library">
              {w.characters.map((c) => (
                <article key={c.id}>
                  <div className="reference-strip">
                    {c.refs.map((r) => (
                      <img key={r} src={asset(r) + "?preview=1"} alt={c.name} />
                    ))}
                  </div>
                  <h2>{c.name}</h2>
                  <span>
                    {c.locked ? "Approved reference" : "Awaiting approval"}
                  </span>
                  <button
                    onClick={() => {
                      setCharacter(c.id);
                      setCreating(true);
                      setShowReferences(true);
                      onSection?.("create");
                    }}
                  >
                    Create with {c.name}
                  </button>
                </article>
              ))}
              <button
                className="new-character"
                onClick={() => {
                  setCharacter("");
                  setRefs([]);
                  setCreating(true);
                  setShowReferences(true);
                  onSection?.("create");
                }}
              >
                <Plus /> Add character
              </button>
            </div>
          ) : section === "library" ? (
            <div className="creation-library">
              {w.packs.map((p) => (
                <button
                  className="creation-entry"
                  key={p.id}
                  onClick={() => run(() => open(p))}
                >
                  <div className="reference-strip">
                    {p.items
                      .filter((r) => r.asset)
                      .slice(0, 4)
                      .map((r) => (
                        <img
                          key={r.id}
                          src={asset(r.asset!) + "?preview=1"}
                          alt={r.label}
                        />
                      ))}
                  </div>
                  <strong>{p.title}</strong>
                  <span>
                    {p.items.length} sticker{p.items.length === 1 ? "" : "s"} ·{" "}
                    {p.status}
                  </span>
                </button>
              ))}
              <button
                onClick={() => {
                  setCreating(true);
                  onSection?.("create");
                }}
              >
                <Plus /> New creation
              </button>
            </div>
          ) : (
            <>
              {w.packs.length > 0 && (
                <div className="studio-collection-bar">
                  <select
                    aria-label="Current creation"
                    value={creating ? "" : pack?.id || ""}
                    onChange={(e) => {
                      const p = w.packs.find((p) => p.id === e.target.value);
                      if (p) run(() => open(p));
                    }}
                  >
                    <option value="">Choose a creation</option>
                    {w.packs.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.title}
                      </option>
                    ))}
                  </select>
                  <button
                    aria-label="New creation"
                    title="New creation"
                    onClick={() => setCreating(true)}
                  >
                    <Plus size={18} />
                  </button>
                </div>
              )}
              {showReferences ? (
                <div className="studio-start">
                  <button onClick={() => setShowReferences(false)}>
                    <X size={16} /> Back to chat
                  </button>
                  <h2>Who are we creating?</h2>
                  <label>
                    Character
                    <select
                      value={character}
                      onChange={(e) => setCharacter(e.target.value)}
                    >
                      <option value="">New character</option>
                      {w.characters.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  {!character && (
                    <>
                      <label>
                        Name
                        <input
                          value={name}
                          maxLength={60}
                          onChange={(e) => setName(e.target.value)}
                        />
                      </label>
                      <label className="check-row">
                        <input
                          type="checkbox"
                          checked={rights}
                          onChange={(e) => setRights(e.target.checked)}
                        />
                        I have permission to use these images
                      </label>
                      <input
                        hidden
                        type="file"
                        multiple
                        accept="image/png,image/jpeg,image/webp"
                        ref={file}
                        onChange={(e) => run(() => upload(e.target.files))}
                      />
                      <button
                        disabled={!rights || busy || refs.length >= 5}
                        onClick={() => file.current?.click()}
                      >
                        <ImagePlus size={18} /> Upload references ({refs.length}
                        /5)
                      </button>
                      <div className="reference-strip">
                        {refs.map((r, i) => (
                          <figure key={r}>
                            <img
                              src={asset(r) + "?preview=1"}
                              alt={`Reference ${i + 1}`}
                            />
                            <button
                              aria-label={`Remove reference ${i + 1}`}
                              onClick={() =>
                                setRefs((old) => old.filter((x) => x !== r))
                              }
                            >
                              <X size={14} />
                            </button>
                          </figure>
                        ))}
                      </div>
                    </>
                  )}
                  {character && (
                    <div className="reference-strip">
                      {w.characters
                        .find((c) => c.id === character)
                        ?.refs.map((r) => (
                          <img
                            key={r}
                            src={asset(r) + "?preview=1"}
                            alt="Selected character reference"
                          />
                        ))}
                    </div>
                  )}
                  <label>
                    Collection name
                    <input
                      value={title}
                      maxLength={60}
                      onChange={(e) => setTitle(e.target.value)}
                    />
                  </label>
                  <label>
                    Lettering
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      <option value="en">English</option>
                      <option value="zh">中文</option>
                      <option value="ja">日本語</option>
                    </select>
                  </label>
                  <button
                    className="primary"
                    disabled={busy || (!character && !refs.length)}
                    onClick={() => run(create)}
                  >
                    <Check size={18} /> Approve references & start
                  </button>
                </div>
              ) : !pack || creating ? (
                <div className="chat-welcome">
                  <img
                    src={import.meta.env.BASE_URL + "icon-192.png"}
                    alt="Aya and Lala"
                    width="80"
                    height="80"
                  />
                  <h2>What shall we make?</h2>
                  <div className="chat-suggestions">
                    {[
                      "A cheerful hello sticker",
                      "Help me choose my character",
                      "Something funny for a busy day",
                    ].map((s) => (
                      <button key={s} onClick={() => setText(s)}>
                        {s}
                      </button>
                    ))}
                  </div>
                  {composer}
                </div>
              ) : (
                <div className={`chat-studio pane-${pane}`}>
                  <div
                    className="studio-pane-switch"
                    role="tablist"
                    aria-label="Creation view"
                  >
                    {[
                      ["chat", "Chat"],
                      ["plan", "Sticker plan"],
                    ].map(([id, label]) => (
                      <button
                        key={id}
                        role="tab"
                        aria-selected={pane === id}
                        onClick={() => setPane(id)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  <div className="studio-chat">
                    <div className="chat-transcript" aria-live="polite">
                      <div className="studio-greeting">
                        <img
                          src={import.meta.env.BASE_URL + "icon-192.png"}
                          alt="Aya and Lala"
                        />
                        <h2>{pack.title}</h2>
                        <p>
                          {boot.capabilities.chat
                            ? "What should your character say today?"
                            : "Offline planner · Direct editing is available"}
                        </p>
                      </div>
                      {messages.map((m) => (
                        <div className="chat-exchange" key={m.id}>
                          <p className="chat-user">{m.text}</p>
                          <div className="chat-assistant">
                            <Suspense
                              fallback={
                                <p>{m.result?.reply || "Aya is thinking…"}</p>
                              }
                            >
                              <ChatText>
                                {m.result?.reply ||
                                  (m.state === "failed"
                                    ? "The request failed. Your draft is unchanged."
                                    : "Aya is thinking…")}
                              </ChatText>
                            </Suspense>
                            {m.result?.items && (
                              <>
                                <div className="proposal-table">
                                  <table>
                                    <thead>
                                      <tr>
                                        <th>Word</th>
                                        <th>Action</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {m.result.items.map((r, i) => (
                                        <tr key={i}>
                                          <td>{r.label}</td>
                                          <td>
                                            {r.action || "Choose a gesture"}
                                          </td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                                <button
                                  disabled={
                                    busy ||
                                    dirty ||
                                    locked ||
                                    m.result.revision !== pack.revision
                                  }
                                  onClick={() =>
                                    run(() =>
                                      save(
                                        m.result!.items!,
                                        m.result!.revision,
                                      ),
                                    )
                                  }
                                >
                                  <Check size={16} /> Apply table
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                      <div ref={bottom} />
                    </div>
                    {composer}
                  </div>
                  <div className="studio-artifacts">
                    {!pack.character_id && (
                      <button
                        className="primary"
                        onClick={() => setShowReferences(true)}
                      >
                        <ImagePlus size={18} /> Choose character references
                      </button>
                    )}
                    <header>
                      <h2>Sticker plan</h2>
                      <span>
                        {rows.length}/{w.limits.pack_size}
                      </span>
                      <button
                        className="icon-button"
                        aria-label="Version history"
                        title="Version history"
                        onClick={() =>
                          run(async () =>
                            setVersions(
                              (await api(`/api/packs/${pack.id}/versions`))
                                .versions,
                            ),
                          )
                        }
                      >
                        <History size={18} />
                      </button>
                    </header>
                    <div className="reference-strip small">
                      {w.characters
                        .find(
                          (c) =>
                            c.id ===
                            (pack as Draft & { character_id?: string })
                              .character_id,
                        )
                        ?.refs.map((r) => (
                          <img
                            key={r}
                            src={asset(r) + "?preview=1"}
                            alt="Locked character reference"
                          />
                        ))}
                    </div>
                    <div className="artifact-table">
                      <table>
                        <thead>
                          <tr>
                            <th scope="col">Select</th>
                            <th scope="col">Word & action</th>
                            <th scope="col">Reference</th>
                            <th scope="col">Review</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((r, i) => (
                            <tr key={r.id}>
                              <td>
                                <input
                                  type="checkbox"
                                  aria-label={`Select sticker ${i + 1}`}
                                  checked={selected.includes(r.id)}
                                  onChange={(e) =>
                                    setSelected((old) =>
                                      e.target.checked
                                        ? [...old, r.id]
                                        : old.filter((id) => id !== r.id),
                                    )
                                  }
                                />
                                <small>{i + 1}</small>
                              </td>
                              <td>
                                <input
                                  aria-label={`Caption ${i + 1}`}
                                  disabled={locked || busy}
                                  value={r.label}
                                  maxLength={32}
                                  onChange={(e) =>
                                    edit(i, { label: e.target.value })
                                  }
                                />
                                <textarea
                                  aria-label={`Action ${i + 1}`}
                                  disabled={locked || busy}
                                  value={r.action || ""}
                                  placeholder="Gesture, expression, timing"
                                  rows={2}
                                  maxLength={500}
                                  onChange={(e) =>
                                    edit(i, { action: e.target.value })
                                  }
                                />
                              </td>
                              <td>
                                {r.asset ? (
                                  <a
                                    href={asset(r.asset)}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    <img
                                      src={asset(r.asset) + "?preview=1"}
                                      alt={`${r.label} reference`}
                                    />
                                  </a>
                                ) : (
                                  <span className="empty-art">
                                    <ImagePlus size={22} />
                                  </span>
                                )}
                              </td>
                              <td>
                                <label className="artifact-approval">
                                  <input
                                    type="checkbox"
                                    aria-label={`Approve sticker ${i + 1}`}
                                    disabled={!r.asset || locked || busy}
                                    checked={r.approved}
                                    onChange={(e) =>
                                      edit(i, { approved: e.target.checked })
                                    }
                                  />
                                  Approve
                                </label>
                                <button
                                  className="icon-button"
                                  aria-label={`Remove sticker ${i + 1}`}
                                  disabled={rows.length <= 1 || locked || busy}
                                  onClick={() => {
                                    setRows((old) =>
                                      old.filter((x) => x.id !== r.id),
                                    );
                                    setSelected((old) =>
                                      old.filter((id) => id !== r.id),
                                    );
                                    setDirty(true);
                                  }}
                                >
                                  <Trash2 size={15} />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="artifact-actions">
                      <button
                        disabled={
                          rows.length >= w.limits.pack_size || locked || busy
                        }
                        onClick={() => {
                          setRows((old) => [
                            ...old,
                            {
                              id: newID(),
                              label: "Hello",
                              action: "",
                              asset: null,
                              approved: false,
                            },
                          ]);
                          setDirty(true);
                        }}
                      >
                        <Plus size={16} />
                        Add word
                      </button>
                      <button
                        className={dirty ? "primary" : ""}
                        disabled={!dirty || busy || locked}
                        onClick={() => run(() => save())}
                      >
                        <Check size={16} />
                        Save table
                      </button>
                    </div>
                    {w.jobs
                      .filter((j) => j.pack_id === pack.id)
                      .slice(0, 3)
                      .map((j) => (
                        <div className="studio-job" key={j.id}>
                          <strong>
                            {j.kind || "Generation"} · {j.state}
                          </strong>
                          <progress value={j.progress} max={100} />
                          {j.error && <p>{j.error}</p>}
                        </div>
                      ))}
                    <div className="generation-actions">
                      {[
                        ["photo", "Use uploaded photo"],
                        ["ai", "Generate references"],
                        ["animate", "Animate approved"],
                      ].map(([kind, label]) => (
                        <button
                          key={kind}
                          disabled={busy || locked || dirty || !selected.length}
                          onClick={() =>
                            run(async () =>
                              setQuote(
                                await api(`/api/packs/${pack.id}/quote`, {
                                  kind,
                                  items: selected,
                                }),
                              ),
                            )
                          }
                        >
                          <Sparkles size={16} />
                          {label}
                        </button>
                      ))}
                      <a
                        aria-disabled={dirty || !rows.every((r) => r.approved)}
                        className="button"
                        href={API + `/api/packs/${pack.id}/export`}
                        onClick={(e) => {
                          if (dirty || !rows.every((r) => r.approved))
                            e.preventDefault();
                        }}
                      >
                        <ArrowDownToLine size={16} />
                        Export
                      </a>
                      {boot.capabilities.creator_sales && (
                        <button
                          disabled={
                            busy ||
                            dirty ||
                            locked ||
                            !rows.every((r) => r.approved)
                          }
                          onClick={() => setCreatorAction("listing")}
                        >
                          <Store size={16} />
                          Request marketplace review
                        </button>
                      )}
                      {boot.capabilities.wechat_worker &&
                        w.limits.plan === "studio" && (
                          <button
                            disabled={
                              busy ||
                              dirty ||
                              locked ||
                              !rows.every((r) => r.approved)
                            }
                            onClick={() => setCreatorAction("wechat")}
                          >
                            <CloudUpload size={16} />
                            Prepare WeChat draft
                          </button>
                        )}
                    </div>
                    {notice && <p role="status">{notice}</p>}
                    {quote && (
                      <div className="generation-quote" role="status">
                        <strong>
                          {quote.items.length} sticker
                          {quote.items.length === 1 ? "" : "s"} ·{" "}
                          {quote.credits} credits
                        </strong>
                        {quote.reason && <p>{quote.reason}</p>}
                        <button
                          className="primary"
                          disabled={busy || !quote.can_generate}
                          onClick={() => run(generate)}
                        >
                          Confirm{" "}
                          {quote.kind === "photo"
                            ? "photo preview"
                            : "generation"}
                        </button>
                        <button onClick={() => setQuote(null)}>Cancel</button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </>
      }
      {creatorAction && pack && (
        <CreatorActions
          mode={creatorAction}
          pack={pack}
          onClose={() => setCreatorAction(null)}
          onDone={(message) => {
            setNotice(message);
            refresh().catch((e) => setError(e.message));
          }}
        />
      )}
      {versions && (
        <div className="modal-backdrop" onClick={() => setVersions(null)}>
          <section
            role="dialog"
            aria-modal="true"
            aria-label="Version history"
            className="version-dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <header>
              <h2>Preserved versions</h2>
              <button
                className="icon-button"
                aria-label="Close version history"
                onClick={() => setVersions(null)}
              >
                <X />
              </button>
            </header>
            {!versions.length && <p>No generated versions yet.</p>}
            {versions.map((v) => (
              <article key={v.id}>
                <strong>{v.state}</strong>
                <div className="reference-strip">
                  {v.items
                    .filter((i) => i.asset)
                    .map((i) => (
                      <a
                        key={i.id}
                        href={asset(i.asset!)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <img
                          src={asset(i.asset!) + "?preview=1"}
                          alt={i.label}
                        />
                        <span>{i.label}</span>
                      </a>
                    ))}
                </div>
              </article>
            ))}
          </section>
        </div>
      )}
    </section>
  );
}
