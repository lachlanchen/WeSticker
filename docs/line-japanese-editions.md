# Japanese LINE Editions

Use the approved Japanese artwork from the AYA catalog, not private customer
photos or the Chinese phonetic lettering edition. Originals remain read-only.

## Export

```sh
python scripts/export_line_pack.py "$APPROVED_ARTWORK_ROOT" vol-01 "$NEW_OUTPUT_DIR"
```

The output includes numbered APNGs, `main.png`, `tab.png`, `line-upload.zip`,
an HTML review gallery and a source/output hash manifest. The directory must
be new. Partial or unsuccessful conversions remain separate from selected ones.

Validated against LINE's [animated sticker guidelines](https://creator.line.me/en/guideline/animationsticker/)
and [detailed animation rules](https://creator.line.me/en/guideline/animationsticker/detail/)
on 2026-10-10:

- Animated packs contain 8, 16 or 24 stickers.
- Sticker canvas is at most 320 x 270; one dimension is at least 270.
- This exporter uses 270-square, 20 frames, one four-second loop, transparent
  APNG and a conservative 1,000,000-byte cap per image.
- Main image: 240-square animated PNG. Tab: 96 x 74 static transparent PNG.
- ZIP remains below 60 MB.

The GIF motion is time-sampled to 20 frames, not regenerated. When needed, a
shared 192/128-color palette keeps the APNG within the cap. Transparency removes
only perimeter-connected near-white pixels. Check pale fur, robot panels, white
lettering, dark/light backgrounds and motion extrema before accepting an export.
This is a separately encoded LINE edition, not a lossless GIF copy.

## Initial Upload Scope

| Pack | Count | Japanese title |
| --- | ---: | --- |
| vol-01 | 24 | アヤとララの毎日 |
| vol-02 | 16 | アヤとララ いつも一緒 |
| vol-03 | 16 | アヤとララ いっしょに行こう |
| vol-04 | 24 | ロボット荘子と仕事仲間 |
| phonetic | 16 | アヤとララ たのしいあいさつ |

The five 12-sticker packs need their own LINE grouping decision. Do not pad with
duplicates or silently discard four animations to satisfy a count.

On 2026-10-10 the five editions above (96 stickers) were verified as **Waiting
for Review**, not yet on sale. All use the lowest offered animated-sticker tier,
**US$1.99+**, and **Start sales automatically** after approval. The live price
menu offered US$1.99+, 2.39+, 2.59+, 2.99+, 3.99+ and 4.99+. These are the
account's displayed tiers, not a guaranteed Japanese checkout price: LINE says
prices vary by sale region and by in-app shop versus LINE STORE.

The catalog has ten selected packs and 156 distinct source animations. Archive
editions, language exports and alternative candidates are not additional selected
packs. The other five packs each have 12 stickers; their LINE grouping/expansion
remains pending. Existing WeChat works and AYA shop editions remain unchanged.

Suggested Japanese description, adjusted to each theme:

> アヤ、ララ、ササ、ロボットの荘子。仲良しの4人が、毎日の気持ちをかわいく伝えます。

## Upload And Verification

1. Reuse the owner-authorized browser, open LINE Creators Market and let the
   owner authenticate. Registration, legal/account declarations and payout
   information must be genuine; do not infer them from another platform.
2. Inspect existing items before creating one draft per selected pack. Record
   the durable item ID privately before subsequent edits or uploads.
3. Select animated stickers, the actual count, Japanese lettering and distinct
   pack metadata. Upload that pack's ZIP; inspect every remote preview/order.
4. Reload the same draft and verify images and text persisted. A selected local
   file, upload spinner or item ID alone is not proof of a saved upload.
5. Report `prepared`, `uploaded draft`, `submitted`, `approved` and `on sale`
   separately. On 2026-10-10 the owner explicitly authorized completing the
   Japanese review submissions, superseding the earlier upload-only scope.
   Inspect the final confirmation and verify each saved item's resulting status.

Creator-registration country is the verified legal entity's country, not the
artwork language or target audience. Use the actual company record for account
setup. Registration email confirmation, payout eligibility, item review and
sale availability are separate milestones. Do not infer one from another.

## Reusable Browser Commands

```sh
node scripts/stage_line_japanese.mjs --cdp "$CDP_URL" --pack vol-02 \
  --assets "$APNG_EDITION" --receipt "$PRIVATE_RECEIPT"
node scripts/submit_line_review.mjs --cdp "$CDP_URL" \
  --receipt "$PRIVATE_RECEIPT" --confirm-review
```

Staging saves a draft and checks remote image persistence. Review is a separate,
owner-authorized action. The review helper checks the saved title, image count,
lowest price, automatic release and final confirmation. It saves submission
intent before clicking OK and verifies status again after navigation. An
ambiguous review intent blocks automatic retries; already-submitted items are
read back without another request. Unexpected pricing requires inspection.

The observed review dialog includes a rights agreement; read it and verify the
owner's authority before using the review command. Registration/payout setup is
not performed by these helpers. On the legacy form, text inputs needed typed
events and blur; `fill()` alone did not update validation. Wait for the product
status or specific fields after navigation rather than treating page load as
complete. Animated previews are canvas elements, not ordinary images.

Owners can view pending works in [Creators Market](https://creator.line.me/my/)
under **Manage Items**, and open **Sticker Images** or **Preview**. The item
page says its public store link appears after approval. Save the exact observed
link then; do not claim an inferred URL is already a live listing.

Login receipts, account pages and upload IDs stay private. The portable artwork
gallery and ZIP may be copied to the owner's sticker share folder after hashes
match. A sync-folder copy does not prove cloud synchronization.
