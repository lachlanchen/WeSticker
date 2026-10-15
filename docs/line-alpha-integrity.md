# LINE Alpha Integrity

2026-10-16: `scripts/export_line_pack.py` now preserves supplied transparency by
default. Previously it applied a white-background key after decoding every GIF;
this could remove white robot panels/fur even from a reviewed transparent source.
Its palette fallback also converted soft alpha to binary alpha.

Use a reviewed transparent source with `--alpha-mode preserve` (the default).
Opaque inputs fail rather than silently guessing which white pixels are body
parts. `--alpha-mode legacy-white-key` is an explicit comparison/recovery option,
not a recommended production matte. No existing pack was replaced or submitted.

RGB reduction now returns RGBA frames with the original alpha channel. If the
bounded encodings do not meet the byte limit, the exporter fails rather than
discarding alpha precision. Existing frame timing and LINE size limits remain.

For repair, start from native source video and create a separately reviewed
lossless RGBA master. A damaged GIF cannot reconstruct already removed pixels.
LALACHAN's `references/wechat-stickers/matting-research/` records the current
temporal/semantic prototype, failures, tests and research plan. It is not yet an
automatically qualified production matting service.

Verification:

```bash
python -m pytest tests/test_line_export.py -q
```

Tests include white foreground touching transparent borders, opaque-input refusal,
and exact preservation of all soft-alpha levels after APNG decode. Resizing still
resamples alpha; perform visual review on the final 270px/240px exports.
