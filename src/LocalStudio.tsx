import { useEffect, useRef, useState } from "react";
import { Download, ImagePlus, MessageCircle, Sparkles } from "lucide-react";
import "./local-studio.css";

type Draft = {
  name: string;
  title: string;
  language: string;
  theme: string;
  labels: string[];
  photo: string;
  rights: boolean;
  locked: boolean;
};
type Plans = {
  themes: Record<string, Record<string, string[]>>;
  keywords: Record<string, string[]>;
};
const key = "westicker-local-studio-v1";
const initial: Draft = {
  name: "My character",
  title: "My first pack",
  language: "en",
  theme: "daily",
  labels: [],
  photo: "",
  rights: false,
  locked: false,
};
const themes = {
  daily: "Daily",
  office: "Work",
  couple: "Couple",
  sports: "Sports",
};

function readDraft(): Draft {
  const raw = localStorage.getItem(key);
  if (!raw) return initial;
  const data = JSON.parse(raw);
  if (
    ![data.name, data.title, data.photo].every((v) => typeof v === "string") ||
    !Object.keys(themes).includes(data.theme) ||
    !["en", "ja", "zh"].includes(data.language) ||
    !Array.isArray(data.labels) ||
    data.labels.length > 24 ||
    !data.labels.every((v: unknown) => typeof v === "string") ||
    (data.photo && !data.photo.startsWith("data:image/png;base64,"))
  )
    throw Error("Saved draft could not be opened. Its data was preserved.");
  return {
    ...initial,
    ...data,
    rights: data.rights === true,
    locked: data.rights === true && !!data.photo && data.locked === true,
  };
}

export function LocalStudio({
  view,
  onView,
}: {
  view: "create" | "agent";
  onView: (view: "create" | "agent") => void;
}) {
  const [loaded] = useState(() => {
    try {
      return { draft: readDraft(), error: "" };
    } catch (e) {
      return { draft: initial, error: String(e) };
    }
  });
  const [draft, setDraft] = useState<Draft>(loaded.draft);
  const [plans, setPlans] = useState<Plans | null>(null);
  const [error, setError] = useState(loaded.error);
  const [selected, setSelected] = useState(0);
  const [brief, setBrief] = useState("");
  const [plan, setPlan] = useState<{ theme: string; labels: string[] } | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    fetch(import.meta.env.BASE_URL + "creator-plans.json")
      .then((r) => {
        if (!r.ok) throw Error("Caption plans unavailable. Please try again.");
        return r.json();
      })
      .then((data: Plans) => {
        setPlans(data);
        setDraft((old) =>
          old.labels.length ? old : { ...old, labels: data.themes.daily.en },
        );
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    if (loaded.error) return;
    try {
      localStorage.setItem(key, JSON.stringify(draft));
    } catch {
      setError(
        "Draft storage is full or unavailable. Export before closing this page.",
      );
    }
  }, [draft, loaded.error]);
  useEffect(() => {
    let cancelled = false;
    const c = canvas.current,
      ctx = c?.getContext("2d");
    if (!c || !ctx) return;
    ctx.clearRect(0, 0, 320, 320);
    if (!draft.photo) return;
    const image = new Image();
    image.onload = () => {
      if (cancelled) return;
      const scale = Math.min(304 / image.width, 280 / image.height);
      ctx.drawImage(
        image,
        (320 - image.width * scale) / 2,
        (292 - image.height * scale) / 2,
        image.width * scale,
        image.height * scale,
      );
      const label = draft.labels[selected] || "";
      let size = 25;
      ctx.font = `800 ${size}px system-ui`;
      while (ctx.measureText(label).width > 300 && size > 9)
        ctx.font = `800 ${--size}px system-ui`;
      ctx.textAlign = "center";
      ctx.lineJoin = "round";
      ctx.lineWidth = 3;
      ctx.strokeStyle = "#162d3b";
      ctx.fillStyle = "white";
      ctx.strokeText(label, 160, 307);
      ctx.fillText(label, 160, 307);
    };
    image.src = draft.photo;
    return () => {
      cancelled = true;
    };
  }, [draft.photo, draft.labels, selected, view]);
  const update = (value: Partial<Draft>) =>
    setDraft((old) => ({ ...old, ...value }));
  async function importPhoto(file?: File) {
    if (!file) return;
    setBusy(true);
    setError("");
    let url = "";
    try {
      if (file.size > 20_000_000 || !file.type.startsWith("image/"))
        throw Error("Choose a supported photo smaller than 20 MB.");
      url = URL.createObjectURL(file);
      const image = new Image();
      image.src = url;
      await image.decode();
      const scaled = document.createElement("canvas");
      const ratio = Math.min(1, 640 / Math.max(image.width, image.height));
      scaled.width = Math.max(1, Math.round(image.width * ratio));
      scaled.height = Math.max(1, Math.round(image.height * ratio));
      scaled
        .getContext("2d")!
        .drawImage(image, 0, 0, scaled.width, scaled.height);
      update({
        photo: scaled.toDataURL("image/png"),
        rights: false,
        locked: false,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Photo could not be opened.");
    } finally {
      if (url) URL.revokeObjectURL(url);
      setBusy(false);
    }
  }
  function prepare() {
    if (!plans) return;
    const hits = Object.entries(plans.keywords)
      .map(([theme, words]) => ({
        theme,
        count: words.filter((w) =>
          brief.toLowerCase().includes(w.toLowerCase()),
        ).length,
      }))
      .filter((row) => row.count > 0)
      .sort((a, b) => b.count - a.count || a.theme.localeCompare(b.theme));
    const theme = hits[0]?.theme || draft.theme;
    setPlan({ theme, labels: [...plans.themes[theme][draft.language]] });
  }
  function exportPhoto() {
    if (!draft.photo || !draft.rights || !draft.locked || !canvas.current)
      return;
    canvas.current.toBlob((blob) => {
      if (!blob) return;
      const url = URL.createObjectURL(blob),
        link = document.createElement("a");
      link.href = url;
      link.download = "westicker-photo.png";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 30_000);
    }, "image/png");
  }
  return (
    <section className="local-studio">
      <header className="studio-heading">
        <div>
          <h1>{view === "create" ? "Create" : "Agent"}</h1>
          <span>
            {view === "create"
              ? "Private draft · On this device"
              : "On-device caption planner"}
          </span>
        </div>
        <button
          className="icon-button"
          title={view === "create" ? "Ask Agent" : "Edit draft"}
          aria-label={view === "create" ? "Ask Agent" : "Edit draft"}
          onClick={() => onView(view === "create" ? "agent" : "create")}
        >
          <MessageCircle />
        </button>
      </header>
      {error && <p role="alert">{error}</p>}
      {view === "create" ? (
        <div className="studio-columns">
          <div className="studio-fields">
            <div className="character-photo">
              <img
                src={draft.photo || import.meta.env.BASE_URL + "icon-192.png"}
                alt="Character reference"
              />
              <label className="button secondary">
                <ImagePlus size={18} />
                {busy ? "Opening…" : "Choose photo"}
                <input
                  type="file"
                  accept="image/*"
                  disabled={busy || !!loaded.error}
                  onChange={(e) => {
                    void importPhoto(e.target.files?.[0]);
                    e.target.value = "";
                  }}
                />
              </label>
            </div>
            <label>
              Character name
              <input
                value={draft.name}
                maxLength={60}
                onChange={(e) => update({ name: e.target.value })}
              />
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={draft.rights}
                onChange={(e) =>
                  update({
                    rights: e.target.checked,
                    locked: e.target.checked && draft.locked,
                  })
                }
              />
              I have permission to use this photo
            </label>
            <label className="check-row">
              <input
                type="checkbox"
                checked={draft.locked}
                disabled={!draft.photo || !draft.rights}
                onChange={(e) => update({ locked: e.target.checked })}
              />
              Keep this character reference
            </label>
            <label>
              Pack title
              <input
                value={draft.title}
                maxLength={80}
                onChange={(e) => update({ title: e.target.value })}
              />
            </label>
            <label>
              Lettering
              <select
                value={draft.language}
                onChange={(e) => update({ language: e.target.value })}
              >
                <option value="en">English</option>
                <option value="ja">日本語</option>
                <option value="zh">中文</option>
              </select>
            </label>
            <fieldset>
              <legend>Captions</legend>
              {draft.labels.map((label, index) => (
                <div className="caption-row" key={index}>
                  <input
                    type="radio"
                    name="caption"
                    aria-label={`Preview caption ${index + 1}`}
                    checked={selected === index}
                    onChange={() => setSelected(index)}
                  />
                  <input
                    aria-label={`Caption ${index + 1}`}
                    value={label}
                    maxLength={48}
                    onChange={(e) =>
                      update({
                        labels: draft.labels.map((old, i) =>
                          i === index ? e.target.value : old,
                        ),
                      })
                    }
                  />
                </div>
              ))}
            </fieldset>
          </div>
          <div className="studio-preview">
            <canvas
              ref={canvas}
              width={320}
              height={320}
              aria-label="Photo sticker preview"
            />
            <button
              className="button primary"
              disabled={!draft.photo || !draft.rights || !draft.locked || busy}
              onClick={exportPhoto}
            >
              <Download size={18} />
              Export photo sticker
            </button>
            <small>Cloud AI: not connected</small>
          </div>
        </div>
      ) : (
        <div className="agent-workspace">
          <h2>{draft.title}</h2>
          <label>
            Pack brief
            <textarea
              value={brief}
              maxLength={2000}
              rows={4}
              onChange={(e) => setBrief(e.target.value)}
            />
          </label>
          <div className="studio-themes">
            {Object.entries(themes).map(([id, label]) => (
              <label key={id}>
                <input
                  type="radio"
                  name="theme"
                  value={id}
                  checked={draft.theme === id}
                  onChange={() => update({ theme: id })}
                />
                {label}
              </label>
            ))}
          </div>
          <button
            className="button primary"
            disabled={!plans}
            onClick={prepare}
          >
            <Sparkles size={18} />
            Prepare captions
          </button>
          {plan && (
            <section className="caption-plan">
              <h3>
                {plan.labels.length} captions ·{" "}
                {themes[plan.theme as keyof typeof themes]}
              </h3>
              <ol>
                {plan.labels.map((label, i) => (
                  <li key={i}>{label}</li>
                ))}
              </ol>
              <button
                className="button secondary"
                onClick={() => {
                  if (confirm("Replace this draft's captions?")) {
                    update({ labels: plan.labels, theme: plan.theme });
                    setSelected(0);
                    onView("create");
                  }
                }}
              >
                Apply to draft
              </button>
            </section>
          )}
          <footer>
            <span>Cloud AI: not connected</span>
            <span>WeChat upload: not connected</span>
          </footer>
        </div>
      )}
    </section>
  );
}
