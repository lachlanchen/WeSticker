import { useEffect, useState } from "react";
import { Link2, RefreshCw, Unlink } from "lucide-react";
import { api } from "./api";

type Connection = {
  linked: boolean;
  can_link: boolean;
  points: { available: boolean; state: string; can_disconnect: boolean };
};
type Balance = {
  state: string;
  awarded_points?: string;
  pending_points?: string;
  as_of?: number;
};

export function SharedAccountPanel({ owner }: { owner: string }) {
  const [connection, setConnection] = useState<Connection | null>(null);
  const [balance, setBalance] = useState<Balance | null>(null);
  const [password, setPassword] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function refresh() {
    setBusy(true);
    setBalance(null);
    setError("");
    try {
      const next = await api<Connection>("/api/account/shared");
      setConnection(next);
      if (
        next.points.available &&
        next.linked &&
        next.points.state === "consented"
      )
        setBalance(await api<Balance>("/api/account/shared/points"));
    } catch {
      setConnection(null);
      setError(
        "Account connection is unavailable. Your WeSticker creations are unchanged.",
      );
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    setConnection(null);
    setBalance(null);
    setConfirmed(false);
    setPassword("");
    api<Connection>("/api/account/shared")
      .then(async (next) => {
        if (!active) return;
        setConnection(next);
        if (
          next.points.available &&
          next.linked &&
          next.points.state === "consented"
        ) {
          const value = await api<Balance>("/api/account/shared/points");
          if (active) setBalance(value);
        }
      })
      .catch(() => {
        if (active)
          setError("Shared account information is currently unavailable.");
      });
    return () => {
      active = false;
    };
  }, [owner]);

  // A valid zero is distinct from no response. Expired snapshots disappear.
  useEffect(() => {
    if (balance?.state !== "ready" || !balance.as_of) return;
    const timer = window.setTimeout(
      () => setBalance({ state: "stale" }),
      Math.max(0, balance.as_of * 1000 + 60000 - Date.now()),
    );
    return () => window.clearTimeout(timer);
  }, [balance]);

  async function connect() {
    if (!confirmed || busy || !connection) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{ url: string }>(
        connection.linked
          ? "/api/account/shared/points/consent"
          : "/api/account/shared/link",
        { confirmed: true, ...(connection.linked ? {} : { password }) },
      );
      window.location.assign(result.url);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    } finally {
      setPassword("");
    }
  }

  async function disconnect() {
    setBusy(true);
    setBalance(null);
    try {
      await api("/api/account/shared/points/disconnect", {});
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const canConnect =
    connection &&
    (connection.can_link ||
      (connection.linked &&
        connection.points.available &&
        (connection.points.state !== "consented" ||
          balance?.state === "reconnect")));
  return (
    <section className="shared-account" aria-labelledby="shared-account-title">
      <div className="shared-account-heading">
        <h2 id="shared-account-title">LazyingArt account</h2>
        <button
          type="button"
          onClick={refresh}
          disabled={busy}
          aria-label="Refresh shared account"
          title="Refresh shared account"
        >
          <RefreshCw size={18} />
        </button>
      </div>
      <p>
        {connection
          ? connection.linked
            ? "Connected to this WeSticker creator."
            : "Not connected."
          : error
            ? "Connection unavailable."
            : "Checking account connection…"}
      </p>
      <h3>Shared LAC points</h3>
      <p>
        Nonmonetary recognition. Separate from WeSticker generation credits and
        subscriptions.
      </p>
      {balance?.state === "ready" ? (
        <div aria-live="polite" className="shared-points-balance">
          <strong>{balance.awarded_points} LAC points</strong>
          <span>{balance.pending_points} pending</span>
          <time dateTime={new Date(balance.as_of! * 1000).toISOString()}>
            Updated {new Date(balance.as_of! * 1000).toLocaleTimeString()}
          </time>
        </div>
      ) : (
        <p role="status">
          {!connection?.points.available
            ? "Not available yet."
            : !connection.linked
              ? "Connect your LazyingArt identity first."
              : balance?.state === "stale"
                ? "Balance expired. Refresh for a current reading."
                : balance?.state === "unavailable"
                  ? "Balance unavailable. No balance is assumed."
                  : balance?.state === "reconnect"
                    ? "Reconnect to read your balance."
                    : connection.points.state === "consented"
                      ? "Loading balance…"
                      : "Balance access needs your consent."}
        </p>
      )}
      {canConnect && (
        <div className="shared-account-consent">
          {!connection.linked && (
            <label>
              Current WeSticker password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
          )}
          <label>
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            {connection.linked
              ? "Allow WeSticker to read my shared LAC points."
              : "Link my LazyingArt identity to this creator. My private packs and purchases stay in WeSticker."}
          </label>
          <button
            disabled={busy || !confirmed || (!connection.linked && !password)}
            onClick={connect}
          >
            <Link2 size={18} />
            {connection.linked ? "Connect points" : "Connect LazyingArt"}
          </button>
        </div>
      )}
      {connection?.points.can_disconnect && (
        <button disabled={busy} onClick={disconnect}>
          <Unlink size={18} />
          Disconnect points
        </button>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
