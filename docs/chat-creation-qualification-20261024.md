# Chat Creation Qualification

Verified on 2026-10-24 against the live DeepSeek API and WeSticker's restricted
AgInTi integration. The web release is available at
[westicker.lazying.art](https://westicker.lazying.art).

## Models

| Role | API identifier | Live API display name |
| --- | --- | --- |
| Default chat | `deepseek-flash` | DeepSeek-V4.1-Flash |
| Operator-selectable alternative | `deepseek-v4-pro` | DeepSeek-V4-Pro |

The official documentation and authenticated model list did not expose a 5.1
model. Use the available identifiers, not a guessed version string. See
[DeepSeek models](https://api-docs.deepseek.com/api/list-models/),
[model documentation](https://api-docs.deepseek.com/quick_start/pricing/) and
[release updates](https://api-docs.deepseek.com/updates/).

Each model returned a valid one-sticker caption/action proposal through the
pinned AgInTi SDK. Replaying the same attempt returned the saved response. This
check used two real text requests total and no media requests. Production remains
on Flash; Pro was tested separately and is not a new user-facing model selector.
The direct API fallback also defaults to Flash with thinking disabled.

## Verified Creation Path

1. Authenticate an isolated synthetic account and lock an approved public Aya
   character reference.
2. Ask the production restricted chat service for one greeting sticker. Receive
   a structured `Hello!` caption and natural waving action.
3. Replay the attempt, verify the same proposal, and verify chat created no jobs.
4. Explicitly apply the table and request a quote for one image credit.
5. Submit once through the normal idempotent generation endpoint. Replay the
   submission and verify the same job ID.
6. Run the real AgInTi image worker, inspect the result, approve it, and export
   through the normal ZIP endpoint.

Exactly one real image render completed. DeepSeek planned the sticker;
AgInTi's GRS AI image route (`nano-banana-2`) generated it. Approval and ZIP export
made no additional provider requests. The export contains the sticker, cover,
icon, banner, thank-you artwork and metadata; ZIP integrity passed.

The inspected image retained Aya's face, outfit and proportions. Background
removal remained conservative with a pale background: this is not qualification
of a perfect transparent cutout. No new animated GIF render was performed in
this check. Existing animation capability was preserved, not requalified here.
Production users, drafts and purchases were not used as test fixtures.

## Workflow Fix

Applying a fresh proposal can replace every caption-row ID. Web, Apple and
Android clients now reconcile the selection against the saved table, retaining
valid selections or selecting only the first new row. This prevents generation
requests from carrying obsolete IDs without selecting an entire paid pack.

The browser regression applies a new table with different IDs before continuing
the reference, photo-generation, review and export workflow. It also checks
390, 768 and 1360 pixel layouts. Public-site QA reads animation URLs from the
catalog instead of assuming a `/motion/` directory, and waits for the actual
sign-in screen rather than capturing its loading state.

## Validation And Deployment

- Backend suite: 518 passed, 18 skipped, including the new direct-provider
  assertion. The focused studio/chat/contract run also passed all 42 tests.
- Restricted SDK security tests: 9 passed.
- TypeScript and production web build passed.
- Isolated chat browser regression passed.
- Android `:app:compileDebugKotlin` passed with one Gradle worker.
- Live public mobile/desktop checks passed, including catalog media, layout,
  authentication boundaries, CSRF and private-header rejection.
- The synthetic image and ZIP copies in the configured Nutstore share match
  their source SHA-256 hashes. Remote cloud acknowledgment was not checked.

Deployed backend snapshot: `b44507a392b27a2e`.
Deployed edge web release: `a28600ed2eb386b8`.
The restricted agent was rebuilt and replaced only after app admission stopped
and its idle state was confirmed. Its replay-state volume was preserved. Public
health and capability checks passed after activation.

The Apple and Android selection fixes are source changes, not newly distributed
native builds. Apple compilation was not performed in this Linux qualification;
no TestFlight or Google Play upload is claimed.

## Reproduction

Fast checks, without live provider calls:

```bash
.venv/bin/pytest -q
npm run build
.venv/bin/python scripts/test_studio_isolated.py chat
WESTICKER_QA_OUT=.runtime/creator-edge-qa node scripts/creator_edge_test.mjs
```

The explicit `scripts/verify_agent_models.mjs --live --config ... --sdk ...
--output ...` check makes one text request per supported model. Run it in the
qualified agent image with its dependencies; the SDK source hash must match the
pin. It requires a new output directory and never overwrites previous evidence.

`scripts/qualify_aginti.py --submit-one` makes a real image request. Its optional
`--chat-token-file` and `--chat-url` include the chat-to-apply steps. Use a new
synthetic state directory and a public reference. Inspect existing receipts
before another run, especially if a request timed out or its outcome is unclear.

After visual inspection, `scripts/review_image_canary.py --state ...
--approve-inspected-image` approves and exports only the isolated fixture. It
rejects production receipts, mixed-user state and an existing export. This step
does not call a provider.

Private receipts remain under `.runtime/deepseek-models-20261024`,
`.runtime/chat-image-20261024` and `.runtime/creator-live-20261024`. Credentials,
generated media, databases and raw responses remain outside git.
