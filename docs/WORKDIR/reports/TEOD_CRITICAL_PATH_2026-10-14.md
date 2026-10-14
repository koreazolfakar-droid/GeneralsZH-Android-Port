# Engine 3477 follow-up: terrain versions and complete CPU timing

GeneralsX @performance Codex 14/10/2026

## Evidence and limits

Owner reports Samsung Galaxy A56 5G SM-A566B, Exynos 1580, Android 16,
engine 3477: battle 14-26 FPS, terrain about 15,884 KB/frame and 132 synchronized
updates/frame, render-worker busy about 9-11 ms/frame, GPU time unavailable.
`generalszh-logs.zip` is not present in this workspace. These are supplied
observations, not independently parsed raw device logs. No ADB target, retail
game installation, TEOD package or Project X package is available here.

The complete FPS-collapse cause is not yet identified. Worker busy time alone
cannot distinguish GPU latency, producer work, simulation, waits or pacing.
An intentional 30 Hz simulation tick is not evidence of rendering throughput.

## Verified redundant work and correction

`HeightMapRenderObjClass::updateVBForLightOptimized` uses a whole-tile plain
write lock during dynamic-light processing. This can dirty unchanged static
terrain vertices. `ensureVBUploaded` consequently queues a synchronized
`glBufferSubData` for each dirty range, without testing whether bytes changed.
Production tiles contain 32 x 32 x 4 vertices at 32 bytes: 131,072 bytes each.
The reported call count is consistent with this large transfer path, but the
fraction of truly identical tiles in the user's scene must still be measured.

The candidate tracks the last queued bytes of static terrain buffers. Exact
comparison removes unchanged leading/trailing bytes; an identical range clears
the dirty marker without another transfer. Changed ranges still use the original
synchronized GL wrapper. No unsynchronized replacement, GL fence removal,
draw merging, culling, shader, texture, resolution or effect changes occur.

Only buffers first fully submitted as terrain are admitted to this cache. Dynamic
VB/IB paths are unchanged. Allocation and DISCARD still take the full path and
refresh the snapshot; unknown/uninitialized GPU tails cannot be skipped. A later
draw category using an admitted buffer also updates its logical version.
Queued upload wrappers capture source bytes before the snapshot is committed.
FIFO order preserves A -> B -> A while pending draws see B and then A.
Snapshots are limited to 512 KiB per buffer and 32 MiB total. Allocation refusal
falls back to ordinary uploads. Buffer destruction releases snapshot memory.

The existing `gx_gles_noopt.txt` named token `terrainreuse` disables this one
optimization for a same-binary A/B run, leaving other optimization switches alone.
An empty marker disables all optimizations and must not be used for this comparison.

## Exported diagnostics

All new engine diagnostics use the existing `gx_perf.txt` / Performance summary
switch and stderr ZIP export. No APK changes are required.

| Record | Meaning |
| --- | --- |
| GX-PERF-LOAD-END | Successful load completion, monotonic microseconds and load wall duration; saved/shell flags |
| GX-PERF-CPU-FIRST | First battle CPU frame end timestamp, main and pacer duration; display latency unavailable |
| GX-PERF-CPU | Two-second exact P50/P95/P99 for main wall, explicit pacer wall and their sum; render limit, simulation Hz and costly trace flags |
| GX-PERF-BATTLE / BATTLE-END | Existing frame intervals and first 120-second aggregate, bounded sample/drop counts |
| GX-PERF | Existing subsystem timings plus separately attributed speed catch-up logic |
| GX-PERF-TERRAIN-CPU | Nested main-thread lighting, recenter and terrain submission totals/call counts |
| perf-terrain-reuse | Attempted/avoided KB, unchanged tiles, comparison cost and live snapshot bytes |
| GX-PERF-RESOURCE | Read-only resource lookup count/wall cost, eager BIG read count/returned bytes/wall cost |
| GX-PERF-SLOW-MODULE | Sleepy module updates taking at least 5 ms, template/object/module attribution, at most 64 lines/process |
| GX-PERF-AI-NONFINITE | First stored Inf/NaN observations at AI entry, state result and locomotor result, raw position/goal/velocity/speed/transform bits, at most 64 lines/process |

Reuse existing LOGIC-DETAIL, AI, PATH, DISPLAY, SCENE, perf-upload-source,
perf-thread, perf-state, texture uploads/lifetime and program-build cost records.
Main wall includes producer waits; worker/GPU timings overlap it. Do not add
nested subsystem times or percentile values to reconstruct a frame. Pacer wall
may include scheduler delays; it is not a CPU-busy measurement.

The first I/O snapshot may include loading work since counters are drained at
the first battle CPU window. Later snapshots contain work since the last drain.
Resource lookup includes nested eager BIG costs. Streaming archive reads are
excluded. Live snapshots/texture counts are memory diagnostics; full malloc
allocation stacks, total driver memory and actual GPU/display latency are not
available through these counters. Existing GPU timers remain opt-in and may
report unavailable/disjoint; no forced query or blocking GPU measurement.

Russia_VehicleDozer FE_INVALID reports do not prove stored NaN coordinates.
The new integer-bit probes distinguish these cases without arithmetic,
normalization, exception-flag clearing or simulation mutation. Capture the first
state transition before choosing a gameplay fix; no speculative clamp is added.

## Automated validation

Production GLES functions are executed with host GL adapters and ASan/UBSan.
On exactly the same synthetic scenario, 132 unchanged 128 KiB terrain tiles:

| Source | Upload calls | Transferred bytes |
| --- | ---: | ---: |
| Engine 3477 source 0c2abdb81c76261f2ced12d5f5b1094a8cef625b | 132 | 17,301,504 |
| Candidate | 0 | 0 |

These are submitted-byte/call results, not frame-time or device FPS benchmarks.
Changed/restored data, synchronized ordering, NOOVERWRITE, DISCARD and sorted
older ranges retain byte correctness in the fixtures. Unknown GPU tails,
memory cap/release, map refusal and source lifetime are also covered.

Synthetic-clock tests validate separate CPU/pacer percentiles, 120-second battle
lifecycle, match reset and resource counter draining. Raw finite-bit tests detect
Inf/qNaN/sNaN without changing FE_INVALID. Existing vehicle AI, blocked path,
Project X policies, production archive precedence/switching, save/map safety,
engine security and native-version fixtures pass locally. Named TEOD BIGs in
archive tests are synthetic; they do not prove original mod visual compatibility.
Native ARM64 30/60 compilation and full CI checks are tracked by the PR/run.

## Release gate

Prepare engine-only OTA artifacts against the installed-APK baseline and existing
channel. Publish only after CI/ABI validation and same-scene physical performance,
terrain/unit/effect correctness and gameplay acceptance. A successful compilation
does not prove improvement. Capture instructions:
[in-app performance recording](../../HOWTO/ANDROID_BATTLE_PERFORMANCE_CAPTURE.md).
