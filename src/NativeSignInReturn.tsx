import { useState } from "react";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { api, type Boot } from "./api";

export function nativeSignInIntent() {
  const query = new URLSearchParams(location.search);
  const id = query.get("native_link");
  return id && /^[a-f0-9]{32}$/.test(id)
    ? { id, returnToApp: query.get("native_return") === "1" }
    : null;
}

export function NativeSignInReturn({
  boot,
  intent,
}: {
  boot: Boot;
  intent: NonNullable<ReturnType<typeof nativeSignInIntent>>;
}) {
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");
  const returnURL = `art.lazying.westicker://auth/complete?link=${intent.id}`;
  async function connect() {
    if (busy || connected) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ return_url: string }>(
        `/api/native/link/${intent.id}/approve`,
        { approved: true },
      );
      if (result.return_url !== returnURL)
        throw Error(
          "The app return could not be verified. Start sign-in again from WeSticker.",
        );
      setConnected(true);
      if (intent.returnToApp) location.assign(returnURL);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="authentication-page">
      <section
        className="creator-workspace sign-in-screen"
        aria-label="Connect WeSticker"
      >
        <a className="signin-back button" href={import.meta.env.BASE_URL}>
          <ArrowLeft size={18} /> Back to stickers
        </a>
        <div className="studio-login">
          <img
            src={import.meta.env.BASE_URL + "icon-192.png"}
            alt="Aya and Lala"
            width="76"
            height="76"
          />
          <h1>{connected ? "You're connected" : "Return to WeSticker"}</h1>
          <p>
            {connected
              ? "Your account is ready in the app."
              : `Continue as ${boot.user?.name || "Creator"}.`}
          </p>
          {error && (
            <p role="alert" className="studio-error">
              {error}
            </p>
          )}
          {!connected ? (
            <button className="primary" disabled={busy} onClick={connect}>
              {busy ? "Connecting…" : "Connect device"}
              <ArrowRight size={18} />
            </button>
          ) : (
            <>
              <p role="status">
                <Check size={18} /> Connected. Return to the app.
              </p>
              {intent.returnToApp && (
                <a className="button primary" href={returnURL}>
                  Return to WeSticker
                  <ArrowRight size={18} />
                </a>
              )}
            </>
          )}
        </div>
      </section>
    </main>
  );
}
