# Large battles performance — Phase 1, 2 November 2026

## Baseline and objective

Source branch starts from signed Engine **3631** (OTA serial 27) at
`8c5e0a312d5b6ccea3c52da90f24995bba92defd`. The user's Galaxy A56
(Exynos 1580) runs heavily modded Zero Hour; TEOD previously reported 15–20 FPS
when panning the camera, while vanilla and other mods performed better.
These are **historical user observations**, not measurements on Engine 3631.

**Goal:** scale real battles with 1,000 / 2,000 / 4,000 active units, preserve
simulation determinism and complete original visual/gameplay behavior. There
is no honest guarantee of 60/120 FPS with four thousand units on any device.
A display-refresh request and high in-game FPS counter do not prove that the
GPU presents that many actual frames. Rendering/AI/pathfinding/particles may
have different bottlenecks depending on the mod and scene.

## Actual Phase 1 changes

- In Zero Hour `GameClient::update()`, cache the unchanged per-frame shroud
  and GhostObjectManager tracking flags. This removes one repeated manager
  query per Drawable during shroud-enabled games without dropping a single
  local/nonlocal ghost refresh or Drawable update.
- Under existing opt-in `gx_perf.txt` / Performance summary diagnostics,
  emit `[GX-PERF-SCALE]` every ~2 sec with live/max Drawable counts,
  shroud-status query rate and whole-loop CPU wall time.
- To distinguish shroud refresh vs client modules with bounded instrumentation,
  sample one out of 32 Drawables each frame, rotate across frames, and record
  the two sampled costs independently. Off mode has no per-Drawable clocks.
- No LOD changes, input delays, false culling, reduced AI ticks, effects
  removal, save format, network protocol, mod priority or APK/OTA changes.

## Automated safeguards

The source-equivalence regression runs 1,000, 2,000, and 4,000 synthetic
Drawables, with 1, 4 or 8 players, with/without ghost tracking and shroud.
It verifies identical status refresh and Drawable update visitation ordering,
the single manager query, and fair 32-frame sample coverage. **This is not a
native compile or real-device FPS benchmark**.

## Physical benchmark protocol (before any OTA)

Enable only Performance summary; turn off verbose and network tracing. For
Vanilla, TEOD and Project X, repeat controlled saves/scenes with unit counts
100/500/1,000/2,000/4,000 where mod/game limits allow, fixed view and panning,
30 and 60Hz engines, camera/lighting/resolution/settings held equal. Collect
at least three 120-second recordings per scene, note thermal throttling, and
export the existing `generalszh-logs.zip` through View Logs > Share.

Compare:
- `[GX-PERF-CPU]` P50/P95/P99 main+pacer; **do not sum overlapping times**;
- `[GX-PERF-LOGIC-DETAIL]` AI, modules, command, partition breakdown;
- `[GX-PERF-PATH-REQUEST]` request count/timing under movement/fights;
- `[GX-PERF-SCALE]` avg/max drawables, ghost refresh volume, loop cost and
  sampled shroud/client update costs;
- `[GX-PERF-TERRAIN-CPU]`, perf-thread, perf-upload-source and GPU query if
  available (otherwise state GPU timing unavailable);
- visual correctness: intact animations, hit effects, unit detection, pathing
  and mod features.

### Next code candidates (only after evidence)

If per-unit client cost dominates: optimize pure client update/render state,
explore safe off-screen LOD for **visual-only** work without delaying gameplay.
If AI/pathfinding dominates: reduce redundant path queries with deterministic
cache invalidation and test lockstep CRC/replays. If GPU dominates: reduce
draw-state submissions and overdraw using equivalent GLES behavior. If many
particles dominate: budget only nonessential offscreen visuals with explicit
A/B screenshots and no gameplay hit detection changes.

Release gate: PR CI, host stress equivalence, dual ARM64 engine build,
native ABI checks, signed engine-only OTA (30+60) after baseline comparison.
No APK unless unavoidable and separately explained.
