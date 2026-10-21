# preRTT CPU attribution and redundant refresh correction

GeneralsX @performance Codex 14/10/2026

The owner reports engine 3486 (native CI #73, run 38568950324) at 20-23 FPS,
with preRTT 40-44 ms and mainScene 3-4 ms. Treat preRTT as the reported dominant
window. No complete raw session or synchronized subphase distribution is available
here, so its dominant subroutine and real before/after frame P50/P95 remain
unmeasured. The changes below address reproduced work in that window, rather than
claiming a GPU draw-call bottleneck or a resolved FPS collapse.

## Exact reproduced defects

HeightMapRenderObjClass::updateCenter calls the base terrain refresh, then returns
when the draw window covers both map extents. It never acknowledges
m_needFullUpdate in that branch. W3DView::update consequently calls updateTerrain
again each stationary frame. Base refresh marks tree/prop/road work dirty and
forces bridge preparation. Apply the pending full geometry/lighting update once,
consume the old request before refreshing so a new request raised during that
refresh survives; retain requests on missing resources/reentrancy, and keep
camera-driven ancillary refreshes. The scrolling-map branch is unchanged.

W3DBridgeBuffer::loadBridgesInVertexAndIndexBuffers opens full-capacity vertex and
index DISCARD locks even when m_numBridges is zero. Reset zero geometry counts
and return before those locks. Nonempty bridge fill, lighting, buffer lifetime,
lock flags and draw order remain unchanged. On GLES, Unlock only marks a range;
upload is deferred until a draw, and empty bridge draws already return. The
guard therefore verifies avoided locks/dirtying, not avoided GPU transfer bytes.

Host differential fixtures execute the actual 3486 and current whole-map branch
and bridge fill function, with counting/map/buffer adapters:

- 1,000 stationary dirty checks: 1,000 base/bridge refreshes in 3486, one after correction.
- Later lighting/time-of-day requests each refresh once; missing buffers and reentrancy retain retry; requests raised during refresh survive.
- Explicit camera refresh still performs tree/road/bridge work.
- 1,000 empty bridge fills avoid 2,000 DISCARD locks.
- Nonempty bridge vertex/index bytes, empty/nonempty transitions and original DISCARD flags match.

This establishes condition-specific redundant work and correctness of the guard.
It does not prove that this condition explains all 40-44 ms on the owner's map.

## Low-overhead attribution

GX-PERF-PRERTT shares a monotonic time/window and logic frame with existing
reports. It records preRTT P50/P95/P99, wall time, Android main-thread CPU time,
and actual GLES producer waits. The wait counter is monotonic and is not consumed
by the existing perf-thread interval reset. Reading it never synchronizes with GL.

Views, particles and terrain get coarse CPU/wall readings. Region scan time is
separated from callbacks; counters include examined/matched drawables, actual
Drawable::draw entries and hidden/shrouded early returns. Drawable prep and
inclusive module time expose work before doDrawModule as well. View count/other
time exposes camera work. GX-PERF-DRAWMODULE reports the eight most expensive
active type keys from a bounded 64-slot table; names resolve only at reporting.

GX-PERF-PRERTT-WORK splits whole-system particle updates, emission, particle
step loops, smudges and bridge preparation. Hierarchy pose calls, bones and
children reveal repeated model preparation. No per-particle/per-event log is
written and no per-frame aggregation heap allocation is introduced. The device
CPU clock lives in W3DDisplay; generic statistics receive its reader.

Nested times overlap and must not be added to complete frame time. Wall minus
thread CPU includes descheduling and blocking, not exclusively driver waits.
Producer wait measures an actual queued-GL wait subset. Missing CPU readings
remain -1; GPU time remains the existing supported/opt-in GLES timer. No query
blocking or GPU timing fabrication is introduced.

## Benchmark and diagnostic isolation

Explicit GX_PERF/gx_perf.txt now suppresses stale full/net event traces while
retaining summaries. Turn Performance summary off to use the existing detailed
switches, or combine them explicitly with GX_PERF_DETAIL/gx_perf_detail.txt.
The mode log records requested and effective settings. Native -replay launches
retain the installed APK Replay Check's existing CRC diagnostics; changing
launch arguments clears that override. No APK or marker files are modified.

Region predicates/callback order, fade/animation/shroud/shadow/physics and DrawModule
work remain unchanged. Both particle tick variants, deletion order, RNG calls
and smudge resets match 3486 in the production manager fixture. No additional
spatial culling or simulation scheduling change is justified by the supplied
subphase evidence.

## Validation and measurement limits

Run: python3 scripts/qa/test-prertt-regressions.py --benchmark.

ASan/UBSan fixtures cover nested scopes, exact percentiles, CPU-unavailable
handling, module bounds/overflow, mode/rewind reset, stale module keys, eight
trace/env/marker/replay modes, actual producer wait paths, production region
boundary/null/NaN/current-deletion behavior, both particle rate variants,
whole-map dirty acknowledgement and bridge geometry/flags.

Recorded host data is in PRERTT_CPU_HOST_2026-10-14.json. The whole-map counting
adapter P50/P95 is 0.020/0.030 us before and after: that is at the clock floor
and supplies no timing-gain evidence. The verified improvement is operation count.
Aggregation-only overhead for 600 callbacks/modules was P50/P95
71.829/124.819 us enabled, 0.200/0.201 us disabled, on this x86_64 host. These
are not Android/game frame times.

Existing GLES FIFO/static/dynamic/DISCARD/snapshot, lighting, CPU lifecycle,
vehicle/Project X AI, save/map and real-pipeline synthetic BIG precedence/switching
regressions pass locally. The new suite is mandatory in native CI and OTA
preparation. ARM64 compilation, merge and signed publication require their actual
subsequent results.

No connected Android target or original vanilla/TEOD/Project X assets are
available. Full game benchmarks, all-unit/effect visual acceptance, actual GPU
duration, phone crash/installation acceptance and multiplayer/replay CRC are
NOT TESTED. Do not infer device P50/P95 from FPS averages or host adapters.

After native OTA installation, use Performance summary only, restart, play the
same map/settings/mod/save for at least 125 seconds from loading completion,
then immediately View Logs -> Share the full ZIP. Include GX-PERF-MODE,
PRERTT/PRERTT-WORK/DRAWMODULE, CPU/DISPLAY/LOGIC/AI/PATH and perf-thread/gpu
from the same run. Repeat matched stationary and combat scenes on vanilla,
independent TEOD and Project X. Benchmark replay through the normal in-game
menu, not the detailed Replay Check launcher. Report terrain extents/refresh
counts and missing units, flicker, shadows, shroud and effects.
