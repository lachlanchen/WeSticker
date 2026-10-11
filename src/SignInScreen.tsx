import { useState } from "react";
import { ArrowLeft, ArrowRight, Eye, EyeOff } from "lucide-react";
import { api, API, type Boot } from "./api";

export type AccountDestination = "create" | "library" | "account";

export function CreatorConsentScreen({
  onDone,
  onBack,
}: {
  onDone: () => Promise<unknown>;
  onBack: () => void;
}) {
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return (
    <main className="authentication-page">
      <section
        className="creator-workspace sign-in-screen"
        aria-label="Creator agreement"
      >
        <button className="signin-back" onClick={onBack}>
          <ArrowLeft size={18} /> Back to stickers
        </button>
        <div className="studio-login">
          <img
            src={import.meta.env.BASE_URL + "icon-192.png"}
            alt="Aya and Lala"
            width="76"
            height="76"
          />
          <h1>Your private studio</h1>
          <label className="check-row">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            I am 18+, accept the creator terms, and will use references I own or
            have permission to use.
          </label>
          {error && <p role="alert">{error}</p>}
          <button
            className="primary"
            disabled={!checked || busy}
            onClick={async () => {
              if (busy) return;
              setBusy(true);
              setError("");
              try {
                await api("/api/account/consent", { adult: true, terms: true });
                await onDone();
              } catch (e) {
                setError((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            {busy ? "Saving…" : "Continue"}
          </button>
          <div className="login-legal">
            <a href={API + "/terms.html"}>Terms</a>
            <a href={API + "/privacy.html"}>Privacy</a>
          </div>
        </div>
      </section>
    </main>
  );
}

export function SignInScreen({
  boot,
  destination = "create",
  onLogin,
  onBack,
  loadError = "",
  onRetry,
}: {
  boot: Boot | null;
  destination?: AccountDestination;
  onLogin: () => Promise<unknown>;
  onBack?: () => void;
  loadError?: string;
  onRetry?: () => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [register, setRegister] = useState(false);
  const [consent, setConsent] = useState(false);
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const providerNames: Record<string, string> = {
    google: "Google",
    apple: "Apple",
    github: "GitHub",
    lazyingart: "LazyingArt",
  };
  function providerURL(provider: string) {
    const params = new URLSearchParams(location.search);
    const query = new URLSearchParams({ view: destination });
    for (const key of ["native_link", "native_return"]) {
      if (params.has(key)) query.set(key, params.get(key)!);
    }
    return API + "/auth/" + provider + "/start?" + query;
  }
  return (
    <main className="authentication-page">
      <section
        className="creator-workspace sign-in-screen"
        aria-label="Sign in to WeSticker"
      >
        {onBack && (
          <button className="signin-back" onClick={onBack}>
            <ArrowLeft size={18} /> Back to stickers
          </button>
        )}
        {!boot ? (
          <div className="studio-login">
            <p role={loadError ? "alert" : "status"}>
              {loadError || "Connecting…"}
            </p>
            {loadError && <button onClick={onRetry}>Try again</button>}
          </div>
        ) : (
          <div className="studio-login">
            <img
              src={import.meta.env.BASE_URL + "icon-192.png"}
              alt="Aya and Lala"
              width="76"
              height="76"
            />
            <h1>{register ? "Create your account" : "Welcome to WeSticker"}</h1>
            <p>
              {destination === "create"
                ? "Sign in to create with Aya."
                : destination === "library"
                  ? "Sign in to your library."
                  : "Sign in to your account."}
            </p>
            {new URLSearchParams(location.search).get("login") ===
              "cancelled" && (
              <p role="status">Sign-in cancelled. Your drafts are safe.</p>
            )}
            <div className="signin-providers">
              {boot.providers.map((provider) => (
                <a
                  className="button outline"
                  key={provider}
                  href={providerURL(provider)}
                >
                  Continue with {providerNames[provider] || provider}
                  <ArrowRight size={17} />
                </a>
              ))}
            </div>
            {boot.local_accounts && (
              <>
                {boot.providers.length > 0 && (
                  <div className="signin-divider">
                    <span>or use email</span>
                  </div>
                )}
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    if (busy) return;
                    setBusy(true);
                    setError("");
                    try {
                      await api(
                        "/api/auth/" + (register ? "register" : "login"),
                        {
                          email,
                          password,
                          name: "Creator",
                          adult: consent,
                          terms: consent,
                        },
                      );
                      setPassword("");
                      await onLogin();
                    } catch (e) {
                      setError((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <label>
                    Email
                    <input
                      type="email"
                      value={email}
                      autoComplete="username"
                      autoCapitalize="none"
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Password
                    <div className="signin-password">
                      <input
                        type={visible ? "text" : "password"}
                        value={password}
                        autoComplete={
                          register ? "new-password" : "current-password"
                        }
                        onChange={(e) => setPassword(e.target.value)}
                        minLength={12}
                        required
                      />
                      <button
                        type="button"
                        className="icon-button"
                        title={visible ? "Hide password" : "Show password"}
                        aria-label={visible ? "Hide password" : "Show password"}
                        onClick={() => setVisible(!visible)}
                      >
                        {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </label>
                  {register && (
                    <label className="check-row">
                      <input
                        type="checkbox"
                        checked={consent}
                        onChange={(e) => setConsent(e.target.checked)}
                        required
                      />
                      I am 18+ and accept the creator terms and image-rights
                      requirements.
                    </label>
                  )}
                  {error && (
                    <p role="alert" className="studio-error">
                      {error}
                    </p>
                  )}
                  <button className="primary" disabled={busy}>
                    {busy
                      ? "Connecting…"
                      : register
                        ? "Create account"
                        : "Sign in"}
                  </button>
                  <button
                    type="button"
                    className="signin-switch"
                    onClick={() => {
                      setRegister(!register);
                      setError("");
                    }}
                  >
                    {register
                      ? "Already have an account? Sign in"
                      : "Create an account"}
                  </button>
                </form>
              </>
            )}
            {!boot.local_accounts && !boot.providers.length && (
              <>
                <p role="status">
                  Sign-in is temporarily unavailable. You can still browse
                  stickers.
                </p>
                {onRetry && <button onClick={onRetry}>Try again</button>}
              </>
            )}
            <div className="login-legal">
              <a href={API + "/terms.html"}>Terms</a>
              <a href={API + "/privacy.html"}>Privacy</a>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
