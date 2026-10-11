import {lazy, Suspense, useEffect, useRef, useState} from "react";
import {ArrowUp, Plus} from "lucide-react";
import {api} from "./api";
const ChatText = lazy(() => import("./ChatText").then(m => ({default: m.ChatText})));

type Turn = {role: "user" | "assistant"; content: string};
const key = "westicker-guest-chat-v1";
function read(): Turn[] {
  try {
    const value = JSON.parse(sessionStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value.filter(t => t && ["user", "assistant"].includes(t.role) && typeof t.content === "string").slice(-40) : [];
  } catch { return []; }
}

export function GuestChat() {
  const [turns, setTurns] = useState<Turn[]>(read);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = useRef(false), bottom = useRef<HTMLDivElement>(null);
  useEffect(() => {
    try {sessionStorage.setItem(key, JSON.stringify(turns));} catch { /* Private mode may disallow storage. */ }
    bottom.current?.scrollIntoView({block: "nearest"});
  }, [turns, busy]);
  async function send() {
    const message = text.trim();
    if (!message || pending.current) return;
    pending.current = true; setBusy(true); setError("");
    const history = turns.slice(-8);
    while (history.reduce((n, t) => n + t.content.length, 0) > 16000) history.shift();
    setTurns(old => [...old, {role: "user", content: message}]);
    setText("");
    try {
      const result = await api<{reply: string}>("/api/guest/chat", {message, history, locale: navigator.language});
      setTurns(old => [...old, {role: "assistant", content: result.reply}]);
    } catch(e) {
      setTurns(old => old.slice(0, -1)); setText(message);
      setError((e as Error).message);
    } finally {pending.current = false; setBusy(false);}
  }
  return <div className="guest-chat">
    {turns.length > 0 && <header className="conversation-tools"><span>Chat with Aya</span><button title="New chat" aria-label="New chat" className="icon-button" disabled={busy} onClick={() => {setTurns([]); setError("");}}><Plus size={18}/></button></header>}
    <div className="chat-transcript" aria-live="polite">
      {!turns.length && <div className="chat-welcome">
        <img src={import.meta.env.BASE_URL + "icon-192.png"} alt="Aya and Lala" width="64" height="64"/>
        <h2>What shall we make?</h2>
      </div>}
      {turns.map((turn, i) => <div key={i} className={"chat-message chat-" + turn.role}>{turn.role === "assistant" ? <Suspense fallback={<p>{turn.content}</p>}><ChatText>{turn.content}</ChatText></Suspense> : <p>{turn.content}</p>}</div>)}
      {busy && <p className="chat-pending" role="status">Aya is thinking…</p>}
      <div ref={bottom}/>
    </div>
    {error && <p role="alert" className="studio-error">{error}</p>}
    <form className="studio-composer" onSubmit={e => {e.preventDefault(); void send();}}>
      <textarea aria-label="Message Aya" placeholder="Message Aya…" value={text} maxLength={2000} rows={2} onChange={e => setText(e.target.value)} onKeyDown={e => {if(e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {e.preventDefault(); void send();}}}/>
      <button className="primary" title="Send message" aria-label="Send message" disabled={busy || !text.trim()}><ArrowUp size={20}/></button>
    </form>
  </div>;
}
