import { useEffect, useState } from "react";
import { LogOut } from "lucide-react";
import { api, setCSRF, type Boot } from "./api";
import { WebPlans } from "./WebPlans";

export function AccountScreen({
  onAccount,
}: {
  onAccount: (boot: Boot) => void;
}) {
  const [boot, setBoot] = useState<Boot | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  function update(next: Boot) {
    setBoot(next);
    setCSRF(next.csrf);
    onAccount(next);
  }
  async function refresh() {
    update(await api<Boot>("/api/bootstrap"));
  }
  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);
  async function signOut(deleting = false) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await api(
        deleting ? "/api/account/delete" : "/api/auth/logout",
        deleting ? { confirmation: "DELETE" } : {},
      );
      await refresh();
      setConfirmation("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!boot)
    return (
      <section className="creator-workspace">
        <p role={error ? "alert" : "status"}>
          {error || "Loading your account…"}
        </p>
        {error && (
          <button onClick={() => refresh().catch((e) => setError(e.message))}>
            Try again
          </button>
        )}
      </section>
    );
  if (!boot.user) return null;
  return (
    <section className="creator-workspace account-workspace">
      <header className="creator-heading">
        <h1>Account</h1>
      </header>
      <h2>{boot.user.name}</h2>
      <WebPlans key={boot.user.id} boot={boot} onUpdated={update} />
      {error && (
        <p role="alert" className="studio-error">
          {error}
        </p>
      )}
      <button disabled={busy} onClick={() => signOut()}>
        <LogOut size={18} /> Sign out of WeSticker
      </button>
      <details className="account-delete">
        <summary>Delete my WeSticker account</summary>
        <p>
          Your private WeSticker creations and uploads will be deleted. Your
          LazyingArt account and other apps stay unchanged.
        </p>
        <p>
          Manage any App Store or Google Play subscription separately before
          deleting your account.
        </p>
        <label>
          Type DELETE
          <input
            value={confirmation}
            autoComplete="off"
            onChange={(e) => setConfirmation(e.target.value)}
          />
        </label>
        <button
          disabled={confirmation !== "DELETE" || busy}
          onClick={() => signOut(true)}
        >
          Delete WeSticker account
        </button>
      </details>
    </section>
  );
}
