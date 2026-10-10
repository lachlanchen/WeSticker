import { useState } from "react";
import {
  ArrowDownToLine,
  Heart,
  Pause,
  Play,
  Plus,
  Search,
  X,
} from "lucide-react";
import { API, type Pack, type Sticker } from "./api";
import { AnimatedSticker } from "./AnimatedSticker";

const themes: Record<string, string> = {
  daily: "Everyday",
  office: "At work",
  couple: "Love notes",
  sports: "Little victories",
  phonetic: "Playful words",
  cantonese: "Cantonese",
  research: "Lab life",
  outing: "On the way",
};
const languages = [
  ["zh", "中文"],
  ["en", "English"],
  ["ja", "日本語"],
];

type Props = {
  packs: Pack[];
  selected: Pack | null;
  onSelect: (pack: Pack) => void;
  lang: string;
  onLanguage: (lang: string) => void;
  saved: string[];
  onFavorite: (id: string) => void;
  onPreview: (sticker: Sticker, pack: Pack) => void;
  onDownload: (pack: Pack) => void;
  onCreate?: () => void;
  onNativeSave?: (pack: Pack, sticker: Sticker) => void;
};

export function StickerBrowser(props: Props) {
  const { packs, selected, onSelect, lang, onLanguage, saved, onFavorite } =
    props;
  const [query, setQuery] = useState("");
  const [theme, setTheme] = useState("all");
  const [playing, setPlaying] = useState(
    () => !matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const filtered = packs.filter(
    (p) =>
      (theme === "all" || p.tag === theme) &&
      `${p.name} ${p.english} ${p.description}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  const active = filtered.find((p) => p.id === selected?.id) || filtered[0];

  return (
    <section className="sticker-browser">
      <header className="browse-heading">
        <h1>
          Sticker collections <span>{packs.length}</span>
        </h1>
        {props.onCreate && (
          <button className="button primary small" onClick={props.onCreate}>
            <Plus size={17} />
            Create
          </button>
        )}
      </header>
      <div className="browse-filters">
        <label className="search">
          <Search size={18} />
          <input
            aria-label="Search collections"
            placeholder="Search collections"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button aria-label="Clear search" onClick={() => setQuery("")}>
              <X size={16} />
            </button>
          )}
        </label>
        <select
          aria-label="Collection theme"
          value={theme}
          onChange={(e) => setTheme(e.target.value)}
        >
          <option value="all">All collections</option>
          {[...new Set(packs.map((p) => p.tag))].map((t) => (
            <option value={t} key={t}>
              {themes[t] || t}
            </option>
          ))}
        </select>
      </div>
      <div className="catalog-browser">
        <nav className="collection-list" aria-label="Sticker collections">
          {filtered.map((p) => (
            <button
              key={p.id}
              className="collection-link"
              aria-current={active?.id === p.id ? "true" : undefined}
              onClick={() => onSelect(p)}
            >
              <img
                src={p.stickers[lang]?.[0]?.poster}
                alt=""
                width="48"
                height="48"
              />
              <span>
                <strong>{p.english}</strong>
                <small>{p.count} GIFs</small>
              </span>
            </button>
          ))}
        </nav>
        {active ? (
          <section className="collection-content" aria-label={active.english}>
            <header className="collection-summary">
              <img src={active.banner} alt="" width="150" height="80" />
              <div className="collection-title">
                <h2>{active.english}</h2>
                <p>
                  {active.name} · {active.count} GIFs
                </p>
              </div>
              <div className="collection-actions">
                <button
                  className="button primary small"
                  onClick={() => props.onDownload(active)}
                >
                  <ArrowDownToLine size={16} />
                  Get collection
                </button>
                <button
                  className={
                    "icon-button border " +
                    (saved.includes(active.id) ? "favorited" : "")
                  }
                  aria-label={"Save " + active.english}
                  aria-pressed={saved.includes(active.id)}
                  title="Save collection"
                  onClick={() => onFavorite(active.id)}
                >
                  <Heart
                    size={18}
                    fill={saved.includes(active.id) ? "currentColor" : "none"}
                  />
                </button>
              </div>
            </header>
            <div className="sticker-toolbar">
              <div className="segmented" aria-label="Sticker language">
                {languages.map(([id, name]) => (
                  <button
                    key={id}
                    className={lang === id ? "selected" : ""}
                    aria-pressed={lang === id}
                    onClick={() => onLanguage(id)}
                  >
                    {name}
                  </button>
                ))}
              </div>
              <button
                className="icon-button border"
                aria-label={playing ? "Pause animations" : "Play animations"}
                title={playing ? "Pause animations" : "Play animations"}
                onClick={() => setPlaying(!playing)}
              >
                {playing ? <Pause size={18} /> : <Play size={18} />}
              </button>
            </div>
            <div className="sticker-grid">
              {active.stickers[lang]?.map((s) => (
                <article className="sticker-card" key={active.id + lang + s.id}>
                  <button
                    className="sticker-preview"
                    aria-label={"Preview " + s.label}
                    onClick={() => props.onPreview(s, active)}
                  >
                    <AnimatedSticker sticker={s} playing={playing} />
                  </button>
                  <div>
                    <span>{s.label}</span>
                    <a
                      className="icon-button"
                      title="Save GIF"
                      aria-label={"Download " + s.label}
                      href={
                        API +
                        `/api/default/${active.id}/sticker/${lang}/${s.id}`
                      }
                      onClick={
                        props.onNativeSave
                          ? (e) => {
                              e.preventDefault();
                              props.onNativeSave!(active, s);
                            }
                          : undefined
                      }
                    >
                      <ArrowDownToLine size={16} />
                    </a>
                  </div>
                </article>
              ))}
            </div>
          </section>
        ) : (
          <div className="empty">
            <Search size={30} />
            <h2>No collections found</h2>
            <button
              className="button outline"
              onClick={() => {
                setQuery("");
                setTheme("all");
              }}
            >
              Show all collections
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
