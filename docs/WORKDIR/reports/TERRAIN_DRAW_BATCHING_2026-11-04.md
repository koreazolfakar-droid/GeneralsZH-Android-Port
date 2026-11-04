# Fixed-grid terrain submission batching — 2026-11-04

Source baseline: `11219eb4`, `dev/mobile-v4`. Implementation and host validation;
no device measurement or standalone engine build by this subtask.

The actual `HeightMapRenderObjClass::Render` and supplemental `renderTerrainPass`
paths now submit consecutive groups of four original 32x32 terrain VB tiles.
An immutable index list repeats the original `(0,2,3,0,1,2)` quad triangles with
per-tile vertex offsets. Geometry generation, duplicate seam vertices, UVs,
texture/shader selection, fog, water, light calculations, pass ordering and
all supplemental overlay call sites remain in their existing order. Each pass
still finishes before the next begins. Hidden terrain submits nothing.

Each group owns one static VB, referenced once per tile alias. Updates lock the
original tile rectangle at its group offset with synchronized flags=0. Compact
lighting state remains independent for each `(VB, tile offset)`; missing state,
partial edges and budget exhaustion use a synchronized tile-range fallback.
The final group allocates only its actual number of tiles. Existing reset/free
paths release all aliases and tile cache entries. Android builds with normals
or software pretransform, plus desktop builds, keep legacy allocation and draws.
No GLES buffer synchronization contract changed.

Four 4096-vertex tiles use 16384 vertices and 24576 indices, within existing
16-bit draw arguments. A full group is 512 KiB in the current diffuse/UV vertex
format, preserving the existing terrain snapshot maximum and 32 MiB aggregate
budget. No additional full-geometry staging copy was introduced.

Expected fixed-grid submissions per pass are `ceil(tileCount / 4)` instead of
`tileCount`; actual main-pass telemetry counts that number. The reported ~644
fixed-grid draws/frame alone does not determine the exact new total because
rounding applies separately to every pass. Worker/GPU time, battle FPS and
visual equivalence remain device validation gates.

## Host validation

The new batching regression was first run before the helper existed and failed
its required-helper assertion. Final commands:

```sh
python3 scripts/qa/test-terrain-draw-batching.py
python3 scripts/qa/test-terrain-light-dirty.py
python3 scripts/qa/test-terrain-snapshot-safety.py
python3 scripts/qa/test-terrain-partial-region.py
python3 scripts/qa/test-terrain-invalidation.py
c++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined -I Core/Libraries/Include scripts/qa/test-terrain-geometry-diff.cpp -o /tmp/gx-terrain-geometry-diff
/tmp/gx-terrain-geometry-diff
```

Batch tests compare every triangle index in original order for 1..128 tiles,
including shorter final groups and 16-bit bounds. Extracted production allocation,
vertex-offset, draw and cleanup functions execute under ASan/UBSan for Android
batching, desktop, Android normals and Android software-pretransform adapters.
They check one owned reference per alias, hidden terrain, final-group sizes and
idempotent release. Geometry lock expressions and both actual render entry points
are checked for batch wiring. These are host adapters, not a full engine link.

The extended lighting regression executes both actual production lighting loops
against the legacy implementation at every shared offset. Exact tile bytes match,
neighboring tile bytes remain unchanged, and both cached and missing-cache paths
are covered. Existing 140 unchanged-light updates still produce zero dirty locks;
geometry resets, alpha, moving/disabled lights, pointer reuse and the 8 MiB cache
budget/release checks still pass. Existing snapshot, circular partial-region,
invalidation and geometry-diff regressions pass.

No APK was created or modified. No commit, push, CI dispatch or OTA publication
was performed by this subtask.
