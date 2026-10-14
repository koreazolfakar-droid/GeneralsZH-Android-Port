# Signed Engine 3486 terrain lighting correction

GeneralsX @build Codex 14/10/2026

Engine **3486**, manifest **serial 16**, is published on the existing
`koreazolfakar-droid/mobile-v4/v1` signed engine OTA channel. The owner authorized continued
fixes and publication after available validation, with physical-device limits
disclosed. This verifies release availability and a specific redundant work
correction; it does not establish that the full FPS collapse is resolved.

## Verified cause and correction

Both production terrain lighting paths take a whole-tile WriteLock even when
final diffuse colors do not change. Engine 3481 consequently compares all
XYZ/diffuse/UV bytes against its last submitted snapshot to avoid the upload.
Remember current/pending 32-bit colors at the producer, keep every original
lighting calculation and geometry copy, and omit a dirty lock when final colors
are unchanged. Changed colors take one smallest enclosing AppendLock with the
original synchronized flags=0. No unsynchronized overwrite is introduced.

Only complete tiles initialized by a full geometry write are eligible. Partial
borders, early lighting calls, allocation failure and the 8 MiB color-payload cap
retain original locks. Entries are released before buffer destruction; pointer
reuse/map switching cannot inherit stale colors. Non-Android/USE_NORMALS paths
retain original writes. Terrain passes, textures, effects, order and culling are
unchanged. No simulation/AI scheduling change or arbitrary NaN clamp is made.

The differential ASan/UBSan host fixture executes current and actual 3481
production lighting functions with the same original dynamic-light formula.
Across both paths **140 repeated unchanged calls produce zero dirty locks**;
final vertex bytes, base mirrors and calculation counts match. Moving/disabled
lights, alpha, rectangles, origin wrapping, geometry edits, unknown GPU tails,
fallback, cap/release and pointer reuse pass. These are reproducible host
operation counts, not phone FPS or CPU-time measurements.

The quoted 70 unchanged tile comparisons / 8,925.8 KiB avoided / 1.232 ms/frame
identify an optimization target; the original ZIP and synchronized current-device
windows are unavailable here. Draw counts, worker busy time, pass counts and CPU
frequency alone cannot identify the complete critical path or prove throttling.
GPU, simulation, pacing and render waits must be compared using new exports.

Shared monotonic timestamps/window durations now relate CPU, rendering, logic
and AI reports; direct findPath requests have nested wall timings. Producer dirty
statistics and existing shared glyph-pool counters expose useful work/no-ops.
Existing supported/opt-in GPU timing and raw-bit Russia_VehicleDozer NaN/Inf probes
are retained. No captured first invalid dozer state establishes its cause yet.

## Source, integration and tests

- Source: `00dc954e02d1e346caa90e69739012f70ce69a80`; build number uses the established complete-history mechanism.
- [PR #21](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/pull/21) merged to dev/mobile-v4 at `d1c16016aab65fc5248d5b36b7b6fc8fac61ebd7`; its tree equals the tested source.
- [Native CI](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/38568950324): SUCCESS, **20 source suites**, ARM64 30/60 engines, dependency compatibility PASS, new_apk_required=false.
- Tests cover actual upload FIFO/lifetime/DISCARD/static/dynamic behavior, initialized-prefix snapshot safety, lighting correctness, CPU percentiles/120-second accounting, AI/path regressions, save/map safety and production synthetic BIG switching/precedence. Synthetic named TEOD archives are not original mod assets.
- Local TLS fixtures pass trusted/untrusted roots, hostname checks, downgrade rejection and production call sites. CI skips that suite because host libcurl development files are absent. Two optional historical tests are not committed and remain NOT TESTED; JSON lists exact reasons.
- Incremental CI reuses successful retained state from run 38548771965. Intermediate 3485 remains unpublished. SDK/NDK/Gradle/CMake/ccache states and existing fixes are preserved; no clean build or APK job is performed.

Files changed from the preceding development HEAD (publisher control and these
release records are subsequent changes):

- `.github/engine-baseline/build.py`
- `Core/GameEngine/Source/GameLogic/AI/AIPathfind.cpp`
- `Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp`
- `Core/Libraries/Include/GXTerrainLightColors.h`
- `Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp`
- `GeneralsMD/Code/GameEngine/Source/Common/GameEngine.cpp`
- `GeneralsMD/Code/GameEngine/Source/GameLogic/AI/AI.cpp`
- `GeneralsMD/Code/GameEngine/Source/GameLogic/System/GameLogic.cpp`
- `docs/DEV_BLOG/2026-10-DIARY.md`
- `docs/HOWTO/ANDROID_BATTLE_PERFORMANCE_CAPTURE.md`
- `docs/WORKDIR/reports/TEOD_LIGHT_DIRTY_2026-10-14.md`
- `scripts/README.md`
- `scripts/qa/test-terrain-light-dirty.py`
- `scripts/update/prepare-engine-run.py`

## Signed publication and independent verification

The registered signing-only publisher reuses successful native artifacts,
pinning exact source/run/merge parent/previous version. Controller
`2f5a8e10e799c7a2b7aceac5d9128b6cd826038a` triggers
[publisher run 38571071267](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/38571071267), which succeeds through sign,
verify, push and live payload verification. Updates branch commit:
`967d795076d4139bcebe58303c5c48836c976b54`. Signing helpers, updater protocol and APK remain
unchanged; the existing secret stays in Actions. Previous immutable engine
payloads remain available. No separate GitHub Release/tag is used by this protocol.

[Exact app manifest](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/manifest.json) and
[detached signature](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/manifest.json.sig) were independently fetched without
query parameters. Exact bytes verify with the ECDSA P-256 key embedded in the
original bootstrap APK. Both downloads equal the successful CI binaries, with
correct ARM64 source/build stamps. All 15 runtime fingerprints match that APK,
JNI/SDL entry points and DT_NEEDED match 3481, and configuration is unchanged.

| File | Native bytes | Native SHA256 |
| --- | ---: | --- |
| [libmain.so (30Hz)](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/engine/3486/libmain.so.gz) | 42,292,432 | `4a1f4262146afd68901134687ff5d8612a51a5fce09e021b4fb7498ec71f708d` |
| [libmain60.so (60Hz)](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/engine/3486/libmain60.so.gz) | 42,296,624 | `a8060ecb1da4889c747ad22e4c069d9cc0e5e41ae950e31db0408db1254b38c0` |

Manifest SHA256: `cd93afe84106d4f9bae1c2bc3fc8f317f34bdf7ba9b0678073dd68ffafe8d374`.
Compressed checksums/sizes and detailed evidence:
[verification JSON](TEOD_LIGHT_OTA_3486.json).

## Application availability and remaining physical evidence

The installed-app discovery contract passes: exact public URLs, valid signed
channel, increasing serial/sequence and unchanged APK identity. In launcher
Updates choose **Check for updates / البحث عن تحديثات**, complete download and
verification, then restart to load 3486. No new APK is needed.

Actual phone installation, first displayed-frame latency, GPU duration, FPS,
mod visuals and multiplayer/replay CRC remain **NOT TESTED**. No ADB target or
original TEOD/Project X assets are attached. Matched vanilla, independent TEOD
and Project X performance comparisons have not been performed; there is no
invented before/after FPS number. The complete critical path remains unresolved.

Enable **Performance summary** only, restart, keep graphics/map/mod settings
fixed, play at least 125 seconds from loading completion, then immediately
**View Logs -> Share** the full ZIP. Capture CPU/DISPLAY/LOGIC-DETAIL/AI-DETAIL,
PATH-REQUEST, TERRAIN-CPU/DIRTY, perf-window/cpu/thread/gpu/terrain-reuse, glyph
and thermal lines from the same session. Compare three matched runs per scene
using existing 3481 baseline exports; GPU unavailable must remain unavailable.
See [capture guide](../../HOWTO/ANDROID_BATTLE_PERFORMANCE_CAPTURE.md) and
[producer reasoning](TEOD_LIGHT_DIRTY_2026-10-14.md). Terrain draw counts are
expected to remain unchanged by this correction.
