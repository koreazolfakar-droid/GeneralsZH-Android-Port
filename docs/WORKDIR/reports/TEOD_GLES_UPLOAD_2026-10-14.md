# GLES upload regression fixes and battle diagnostics, 2026-10-14

Base: `dev/mobile-v4` at `88d5758621658736e652b5fcaa24a3b8531746e0`.
The currently published Engine 3472 is from `c9ca6a0c2928e1ae2d2e133a778b669f1aeda29c`.
PR #18 remains unmerged; its production diagnostics from `65b45ff1` and
`a02fb070e82c` are reused here. The latter only fixes a diagnostic newline.

## Verified unnecessary work

1. `gxrt::bufferWrite` always constructed a `Blob<256>`, which allocated on the
   engine thread and freed on Render Worker for each upload larger than 256 bytes,
   even without a worker. The new `postBytes` copies bytes into the existing FIFO
   ring before returning. Headers plus bytes are bounded to 1 MiB; oversized or
   null payloads retain the old path. Mapping flags, buffer bindings, GL operation
   count, fallback behavior and ordering are preserved. No GPU waiting is removed
   by assuming an unsafe memory lifetime.
2. `HeightMapRenderObjClass::updateVB` copied only cells inside its rectangle but
   locked the entire tile. The GLES translator correctly treated that lock as a
   full dirty range. Lock the smallest contiguous range enclosing the cells,
   retaining the same ordinary synchronized lock. Rebase only the destination
   pointer; all geometry, UVs, normals, lighting and row gaps retain their bytes.
   Lighting-only updates and other terrain passes are unchanged.

Host ASan/UBSan comparison executes production code:

| Scenario | Previous | Updated |
| --- | ---: | ---: |
| 491 queued 1-KiB buffer writes | 491 heap allocations | 0 |
| One 400-KiB write with worker disabled | 1 heap allocation | 0 |
| One cell in a 16x16 terrain tile, 44-byte vertices | 45,056 bytes marked for upload | 176 bytes |
| Terrain vertex output | Exact reference bytes | Exact reference bytes |

These scenarios isolate the defects; they do not reproduce a TEOD game or measure
Android CPU/GPU duration. Existing static GPU buffers already reuse storage when
not dirty, and the host test confirms no further uploads across 120 calls. The
existing shader/program, texture/bind and persistent-buffer caches remain active.
No batching, shader/material merging, new terrain culling, effect removal, texture
quality change or AI scheduling change is justified by available measurements.

## Lifecycle and instrumentation

With the existing `gx_perf.txt` marker, `GX-PERF-BATTLE-BEGIN` reports the first
CPU main-frame duration observed with an active non-shell battle. Subsequent
`GX-PERF-BATTLE` lines report exact nearest-rank frame-interval P50/P95/P99 every
two seconds, main duration and worst interval. Frame intervals include pacing;
main duration excludes the FramePacer. `GX-PERF-BATTLE-END` summarizes approximately
120 seconds (through the first frame crossing 120 s). The boundary is the first
observed battle update, not an independently measured loading-screen/GPU boundary.
Counts are bounded (4096/window, 32768/total); `dropped` discloses overflow, in
which case percentiles cover retained samples only. Leaving the match or a logic
frame reset starts a new capture. Synthetic clock tests verify this accounting.

Reuse `[GX-PERF]`, `[GX-PERF-LOGIC-DETAIL]`, `[GX-PERF-AI-DETAIL]`,
`perf-thread`, `perf-gpu`, `perf-upload`, `perf-upload-source`, `perf-draws`,
`perf-terrain-passes`, existing program-build/cache timings and `GX_ASSET_TRACE`
resource provenance. Category upload attribution is best-effort, not a proof of
culled terrain work. GPU duration remains unavailable when timer queries are
unsupported/disabled. Do not enable the known unsafe Mali-G57 r32p1 timer path.

Full engine allocation profiling, BIG access/read durations and exact
loading-complete-to-first-present latency still require device traces. Buffer
allocation counts above cover this upload path only. No device or original mod
assets are attached, so the dominant battle-start/sustained critical path, AI
request frequency, GPU synchronization cost and FPS improvement are NOT MEASURED.

## Reproduction and regression checks

Run `python3 scripts/qa/test-gles-upload-regressions.py`; add
`--legacy-ref 88d5758621658736e652b5fcaa24a3b8531746e0` to reproduce the previous
operation counts. Tests cover FIFO order, caller memory reuse, map refusal,
large upload fallback, static/dynamic VB and IB behavior, DISCARD retaining older
ranges, range accumulation and all 166,464 rectangles over nine tile origins.
`test-battle-perf-window.py` tests statistics and match/menu/reset lifecycle.

`test-mod-archive-loading.py` executes production BIG parsing/mount/index/open
against synthetic `!TEOD_INI.big`, `!TEOD_W3D.big`, `!TEOD_Textures.big`,
`!TEOD_Terrain.big`, `!TEOD_Maps.big`, and `!TEOD_Audio.big`, duplicate archives,
vanilla and another standalone selection. It verifies precedence, inactive mod
isolation, restart/switching and original fixture hashes. A Windows `d3d8.dll`
is never treated as an archive or Android payload. This does not validate actual
factions, rendered units, textures, effects or Mod Manager preference persistence.

Existing localization, save, update security, provenance, Project X script lookup,
AI scheduling guards and blocked-repath policy checks are run as regressions.
Both new performance tests and the existing AI guards are required by incremental
build and OTA preparation; absence/failure stops publication.

For device A/B, use the same native GLES backend, engine Hz, resolution, quality,
FPS limit, map, factions, AI difficulty/player count, camera and replay/orders.
Capture from before loading completion through 120 seconds; repeat cold and warm
shader-cache runs and record device/GPU/driver, temperatures and APK version.
Run vanilla, standalone TEOD and Project X; check visuals, save/load and replay
CRC/multiplayer separately. Use Perfetto/Simpleperf for allocation/archive/CPU
samples if the existing timers do not identify the critical path. Never infer
per-frame P99 or a sole bottleneck from aggregate average logs.

## Native and OTA evidence

Pending at the implementation commit: use the existing explicit
`build-android.yml` dispatch with `engine_incremental_mode=build`, complete Git
history and retained state. Build only ARM64 `libmain.so`/`libmain60.so`; verify
native source stamps, all bootstrap dependency fingerprints and required tests.
The engine identifier is the existing complete-history commit count.
After successful checks/integration, use `sign-update.yml` with the immutable
successful source/run, then independently verify the live ECDSA signature,
manifest serial/source, both compressed URLs, decompressed sizes/SHA-256 and
native stamps. Publication evidence is recorded separately after those actions.
No APK rebuild, signing identity change or OTA protocol change is required.
