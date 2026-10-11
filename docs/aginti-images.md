# AgInTi Image Generation

WeSticker invokes the installed AgInTi image tool in an isolated worker process.
It does not start an agent conversation or expose the auxiliary server publicly.
The operator supplies `aginti_root` and optionally `aginti_node` in private
configuration. AgInTi reads its existing private credentials. No key is copied
into app source, native clients, browser storage or a generation prompt.

```json
{
  "image_provider": "aginti",
  "aginti_root": "/operator/configured/AgInTiFlow",
  "aginti_image_model": "nano-banana-2",
  "aginti_qualified": false,
  "image_generation_enabled": false
}
```

## Contract

The normal workflow stays unchanged: user consent, uploaded references, approved
character, editable caption/action table, quote, explicit submission, job status,
review and export. Free accounts generate one selected sticker at a time.

- GRS AI is selected explicitly through AgInTi; there is no provider fallback.
- References are private workspace files, at most five and 4 MB each after the
  existing upload normalization. The requested image is square, 1K.
- OpenAI's free moderation endpoint screens input text/references and generated
  output. A missing, malformed or flagged result stops delivery. This is not
  OpenAI image generation. Provider transfers are disclosed in the privacy page.
- A process lock and source/prompt/model fingerprint bind each item attempt.
- A durable transport intent precedes the one permitted generation POST.
  AgInTi's internal transient retries reuse its saved response, never a second
  provider submission. A lost reply without a provider ID stays uncertain.
- With a known provider ID, polling may resume. A completed, hash-checked local
  receipt returns the original image without another provider call.
- Raw images, prompts and provider receipts remain in private render history.
  White-background outputs receive the existing AYA perimeter-connected matte
  removal as a derivative. Enclosed white fur/clothing remains opaque. This is
  a simple matte treatment, not a general-purpose segmentation model.

The browser receives only the resulting account-owned asset. A failed output or
uncertain provider request is preserved and never silently regenerated.

## Qualification

Run only with an approved public reference and one explicitly authorized render:

```bash
.venv/bin/python scripts/qualify_aginti.py \
  --state .runtime/aginti-canary-unique \
  --aginti-root "$AGINTI_ROOT" \
  --public-reference "$APPROVED_PUBLIC_REFERENCE" --submit-one
node --test tests/aginti-transport.test.mjs
.venv/bin/pytest -q tests/test_aginti.py tests/test_generation_contract.py
```

The private canary records the real worker job, resulting asset and review state.
Inspect identity, pose, framing and matte on a contrasting background before
setting both qualification/enable flags. A doctor response only confirms key
presence; it is not generation evidence.

11 October 2026: one real GRS AI / nano-banana-2 job completed using the approved
public Aya reference. Both safety checks passed. The raw result and matte
derivative were visually inspected; face, outfit and whole-body framing remained
consistent. An earlier local preflight used an unsupported style enum and stopped
before any provider submission. No paid rerender was performed.

Live image qualification does not qualify animation, social login or purchases.
The local animation backend has its own readiness and resource requirements.
