# Producer-side unchanged terrain lighting

GeneralsX @performance Codex 14/10/2026

## Evidence boundaries

The owner provided excerpts reporting 27-48 FPS, 219-279 terrain draws, two
shader passes over 70 base tiles, and 70 unchanged snapshot comparisons/frame:
8,925.8 KiB attempted and avoided, 1.232 ms comparison/frame, 9,945.7 KiB snapshots.
These are quoted excerpts, not a raw log independently parsed here. The later
clarification identifies independent TEOD and historical 1,111 total / 549 terrain
draws, 18.2 MB uploads and 24.48 ms worker time as historical, unsynchronized
measurements. The complete battle critical path remains unidentified.

Snapshot comparison has a benefit: it prevented the quoted 8.7 MiB transfers.
Its measurable CPU cost is a separate optimization target. Terrain draw count
and pass count alone do not measure GPU cost. Worker CPU busy time is not GPU
frame duration; simulation tick duration is not complete main-thread wall time.
The listed examples themselves include 663 draws at 39.9 FPS and 538 at 27 FPS,
so draw count alone cannot establish the proposed ordering of bottlenecks.

Frequency samples alone do not establish thermal throttling, and not all CPU
cores are big cores. Idle frequency/governor/affinity can produce such a snapshot.
The existing thermal probe reports available temperatures off the game thread.
No temperature/thermal-status sequence establishing throttling was supplied.

## Verified correction

Both terrain lighting functions acquire a whole-tile WriteLock even if the final
diffuse colors stay identical. GLES then compares the whole XYZ/diffuse/UV buffer
against its submitted version. Instead, a bounded producer cache remembers
current and pending 32-bit diffuse values per terrain buffer. Original lighting
calculations, normals, light intersection, disabled-light cleanup, alpha and
legacy optimized-corner copy order remain unchanged.

Every geometry update remembers exactly the diffuse values copied to that VB.
New buffers start with empty colors and immediately run the original geometry
initialization. Lighting writes into pending colors; only the final differences
open one smallest enclosing AppendLock, which uses the original flags=0
synchronized contract. Identical final colors cause no dirty lock, so GLES has
no lighting upload or full-vertex snapshot comparison to perform. Geometry dirty
ranges from other writers are retained. A -> B -> A during one lighting call
is correctly clean; changes between calls remain real updates.

Color arrays use 32 KiB per 4,096-vertex tile and are capped at 8 MiB total,
plus small map metadata. Allocator/cap refusal keeps the original synchronized
WriteLock path and existing GLES snapshot protection. Buffer destruction erases
entries before reference release; repeated map switches/pointer reuse cannot
retain an old version. No per-frame allocations, GPU reads, unsynchronized
overwrites, skipped lighting ticks or camera-only update assumptions are added.

The Android diffuse path uses this cache on both render backends. Non-Android
and USE_NORMALS paths retain original locking and writes. The shader's two
passes, textures, effects, draw order, culling and geometry layout are unchanged.
Terrain batching is deferred until same-window CPU/GPU costs justify it and
equivalent shader/render-order semantics can be validated. Removing a pass is
not an equivalent optimization by itself.

## Existing text cache and diagnostic alignment

Render2DSentence already has a shared 32-entry glyph texture recycle pool with
size/format matching, Reset salvage and explicit flush. Texchurn lines and
created-minus-deleted lifetime totals cannot prove every label bypasses it.
Reuse its existing glyphpool hit/miss/salvage/size counters every terrain CPU
report, without enabling verbose tracing or adding another atlas system.

New GX-PERF-TERRAIN-DIRTY reports changed/no-op/fallback updates, color checks,
final color changes, locked vertices and cache bytes alongside terrain CPU costs.
GLES perf-window identifies the monotonic report end, wall duration and frame
count. CPU, logic and AI windows now expose shared monotonic anchors and window
durations. GX-PERF-PATH-REQUEST observes findPath calls, including early returns
and direct calls outside the queued AI phase. Its costs are nested; do not add
them again to logic/main totals. Other specialized path routines remain covered
by existing phase/module measurements rather than claiming every path API is timed.
GPU timing remains the existing supported/opt-in path; unavailable/disjoint
queries must still be reported unavailable. No blocking GPU query is introduced.

## Validation and device follow-up

The ASan/UBSan host fixture executes both current production lighting functions
and the actual 3481 versions, including their identical production dynamic-light
formula. Host adapters supply map/vector/float-conversion primitives; exact normals/call order/count, final vertex bytes and immutable
base mirrors are compared. It covers stationary/moving/disabled lights, alpha,
partial rectangles, terrain-origin wrapping, geometry edits, pointer reuse,
fallback and cap/release. All 140 repeated unchanged updates avoid dirty locks;
3481 still locks each call. These are operation counts, not device CPU/FPS results.
Existing GLES upload ordering and bounded snapshot tests also pass. Native ARM64
CI checks actual lighting math compilation and APK dependency compatibility.

After OTA installation, enable Performance summary only, keep graphics/map/mod
settings fixed, play the first 125 seconds, then View Logs -> Share the full ZIP.
Capture GX-PERF-CPU, DISPLAY, LOGIC-DETAIL, AI-DETAIL, PATH-REQUEST, TERRAIN-CPU,
TERRAIN-DIRTY, perf-window/cpu/thread/gpu/terrain-reuse, glyphpool and thermal
lines from the same session. Compare identical vanilla/TEOD/Project X scenes.
Expect unchanged producer lighting updates to stop generating consumer comparisons;
do not expect total terrain draws to fall from this correction. Actual phone FPS,
visual correctness and multiplayer/replay CRC remain unmeasured here.
