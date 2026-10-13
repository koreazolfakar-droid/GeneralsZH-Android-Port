# Android native GLES performance diagnostics (diagnostic-only)

Target: `dev/mobile-v4`. All additions are guarded by the existing `gx_perf.txt`
logging mode or its existing renderer reporting path. No simulation, render order,
archive priority, mod behavior, or timing limits are changed.

## Added metrics
- `[GX-PERF-LOGIC-DETAIL]`: elapsed GameLogic tick, maximum tick in the sample,
  script/terrain/commands/sleepy update modules/AI/partition buckets, and residual
  time. These are milliseconds per **logic tick**, not milliseconds per render frame.
- `[GX-PERF-AI-DETAIL]`: pathfinding queue versus player/strategy updates,
  milliseconds per AI tick. No extra pathfinding steps are executed.
- `[d3d8gles] perf-upload-source`: VB-append KiB, append count and
  synchronized VB/IB uploads by currently tagged render category. **OTHER is an
  attribution fallback** when a buffer is prepared before a render category is tagged.
- `[d3d8gles] perf-terrain-passes`: legacy heightmap fixed-tile grid shader
  pass calls and expected base tile draws. Does not cover shoreline/extra-blend
  overlays or FlatHeightMap. Counts do not imply those draws are offscreen.

## How to gather evidence
1. Select **native GLES** (not DXVK/Vulkan). Put an empty `gx_perf.txt` marker in
   the game's working folder, as already supported by the project. Restart the game.
2. Replay the same map, camera angle, player count, units and battle duration
   both for vanilla and the affected mod. Capture exported logs.
3. Compare `[GX-PERF]`, `[GX-PERF-LOGIC-DETAIL]`, `[GX-PERF-AI-DETAIL]`,
   `perf-upload-source`, `perf-terrain-passes`, `perf-thread` and `perf-gpu`.
4. Check exact backend, frame cap and quality settings. A low Render Worker busy
   number **does not** prove CPU-only bottleneck without GPU timing.
5. Do **not** enable `gx_gles_gputimer.txt` on Mali-G57 r32p1: existing
   engine notes report a native crash on this driver. Keep GPU timer off unless
   the specific device driver has been verified safe.

## Safety and limitations
No automatic shader merging, buffer policy changes, draw skips, AI scheduling
changes or terrain culling changes. This commit collects evidence first.
The per-category VB attribution happens at upload time and may classify some
uploads as OTHER. Base terrain tile counters record only the non-flat heightmap
regular tile pass, without any visibility assumptions. Timing scopes use
steady_clock and are never active unless the existing GX perf flag is set.
