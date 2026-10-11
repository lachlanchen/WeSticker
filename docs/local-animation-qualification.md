# Local Animation Qualification

One approved public Aya reference was rendered on 2026-10-11 through the real
WeSticker adapter and LocalVideoGen. No paid Xiaoyunque request or rerender was
made. The source photo was not a private customer image.

- Profile: `quality_int8_offload`, GPU 0, 25 steps, 512-square, requested 5 seconds.
- Verified result: 124 frames at 24 fps, 5.167 seconds, full decode passed.
- Motion review: one Aya in the reference outfit raises the notebook-holding
  hand, waves, tilts her head and returns toward the opening pose. Identity and
  limbs remain consistent in the 21-frame contact sheet.
- Caveats: the white background and original pedestal remain; this is not a
  transparency or seamless-loop qualification. The first part holds its pose.

The current renderer's output list provides `media_type: video` and a numeric ID,
not necessarily a filename. The adapter now selects that exact output contract;
download was recovered with the existing receipt after finding this mismatch.
There was exactly one render, not another attempt under a new job ID.

`scripts/qualify_local_animation.py` creates an exclusive private folder.
`--resume-receipt` requires an existing provider receipt and uses the same source
fingerprint. Active shared jobs, runnable series, nonempty global instructions,
insufficient RAM or excess swap defer a new submission. No model startup or
global driver changes are performed by the adapter.

Public animation remains disabled until the operator provides a qualified,
available service lifecycle. A completed test and an idle stopped engine are not
the same as a continuously available creator service. Preserve all originals,
GIF derivatives, references, requests and receipts outside Git.

The LocalVideoGen runtime owner verified the completed provider receipt and
empty queues, then stopped only the two owned services. Both loopback ports were
free afterward. No idle GPU model or GUI stack is kept as qualification evidence.
