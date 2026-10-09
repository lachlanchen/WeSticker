import { useState } from "react";
import { X, CloudUpload, Store } from "lucide-react";
import { api, type Draft } from "./api";

export function CreatorActions({
  mode,
  pack,
  onClose,
  onDone,
}: {
  mode: "listing" | "wechat";
  pack: Draft;
  onClose: () => void;
  onDone: (message: string) => void;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <div className="modal-backdrop">
      <section
        role="dialog"
        aria-modal="true"
        aria-label={
          mode === "wechat" ? "WeChat draft upload" : "List a collection"
        }
        className="auth-modal"
      >
        <button
          className="icon-button close"
          aria-label="Close"
          onClick={onClose}
        >
          <X />
        </button>
        <h2>
          {mode === "wechat"
            ? "Your work. Your account."
            : "A little shop of your own."}
        </h2>
        <p>
          {mode === "wechat"
            ? "Upload reviewed artwork to your own isolated WeChat browser. You log in and decide whether to submit for review."
            : "Only the reviewed, captioned stickers become public. Original reference photos stay private."}
        </p>
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (busy) return;
            setBusy(true);
            setError("");
            const form = new FormData(e.currentTarget);
            try {
              if (mode === "wechat") {
                const result = await api(`/api/packs/${pack.id}/wechat`, {
                  draft_only: true,
                  consent: true,
                  copyright: form.get("copyright"),
                  description: form.get("description"),
                });
                onDone(
                  "Draft-upload request saved. Browser connection ticket: " +
                    result.id.slice(0, 8),
                );
              } else {
                await api(`/api/packs/${pack.id}/listing`, {
                  rights: true,
                  public_consent: true,
                  price: Math.round(Number(form.get("price")) * 100),
                });
                onDone(
                  "Collection sent for marketplace review. It is not public yet.",
                );
              }
              onClose();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {mode === "wechat" ? (
            <>
              <label>
                Copyright holder
                <input name="copyright" required maxLength={100} />
              </label>
              <label>
                Introduction
                <textarea
                  name="description"
                  required
                  minLength={5}
                  maxLength={500}
                  defaultValue={pack.title}
                />
              </label>
            </>
          ) : (
            <>
              <label>
                Pack price · USD
                <input
                  name="price"
                  type="number"
                  min="0.99"
                  max="99.99"
                  step="0.01"
                  defaultValue="0.99"
                  required
                />
              </label>
              <p className="fine">
                Platform fee: 15%, plus payment processing and applicable taxes.
                Payouts require verified onboarding.
              </p>
            </>
          )}
          <label className="checkline">
            <input type="checkbox" required />
            <span>
              {mode === "wechat"
                ? "I authorize draft uploading only. I will confirm rights and submit for review myself."
                : "I have commercial rights and permission from everyone depicted. I want these exported stickers to be public after review."}
            </span>
          </label>
          {error && (
            <p role="alert" className="notice">
              {error}
            </p>
          )}
          <button className="button primary full" disabled={busy}>
            {mode === "wechat" ? (
              <CloudUpload size={18} />
            ) : (
              <Store size={18} />
            )}{" "}
            {mode === "wechat"
              ? "Prepare draft upload"
              : "Request marketplace review"}
          </button>
        </form>
      </section>
    </div>
  );
}
