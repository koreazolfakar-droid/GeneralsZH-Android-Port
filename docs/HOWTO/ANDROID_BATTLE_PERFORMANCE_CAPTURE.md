# Capture the first 120 seconds of an Android battle

GeneralsX @feature Codex 14/10/2026

Use the installed application; no ADB or APK rebuild is required. Signed engine
3486 adds producer terrain-dirty and aligned CPU/render/logic/AI/path windows.
Existing engine 3481 exports provide the terrain-snapshot baseline. Actual phone
FPS/visual acceptance remains unmeasured; keep the build number with each ZIP.

1. In launcher setup, open **Diagnostics / التشخيص**. Enable only
   **Performance summary / ملخص الأداء**. Disable **Verbose trace log / سجل
   تتبع مفصّل** and **Online network log / سجل شبكة اللعب عبر الإنترنت** for
   performance runs: full network/CRC tracing can add per-object work. Restart
   the game process so marker settings take effect.
2. Record the engine build shown in the launcher/startup log, renderer, resolution,
   FPS setting, graphics/shadow options, selected mod version, map, factions,
   AI difficulty/count and device temperature/charging/power mode. Keep these
   identical for each compared pair. Do not change graphics to demonstrate a fix.
3. Start one reproducible skirmish and play for at least 125 wall-clock seconds
   after the loading screen disappears. A fixed-camera idle opening tests the
   initial collapse; a second repeatable combat scene tests active lights/effects.
   Use the same save/replay where compatible, without editing mod archives.
   Record missing terrain/units/textures, flicker, effects and targeting failures.
4. Exit the game, then immediately open **View Logs / عرض السجلات** and press
   **Share / مشاركة**. Save/share `generalszh-logs.zip`; Share includes full log
   files, whereas Copy/viewer text is capped. Avoid repeated launches before export:
   only current and previous engine stderr sessions are retained.
5. Label each ZIP with engine, mod, map and cold/warm run. Repeat identical tests
   on vanilla, independently installed TEOD and Project X Remastered. Use at
   least three matched runs per scene and let the phone cool between pairs.
   Preserve saves, caches and original mod assets.

For a same-candidate engine A/B comparison, put exactly `terrainreuse` in
`gx_gles_noopt.txt` in the selected game folder and restart. This disables only
the new terrain snapshot optimization. Export that run, remove this marker,
restart and repeat. Do not use an empty marker: it disables unrelated optimizations.
This manual marker is optional; the existing launcher UI has no switch for it.
On engine 3486 this marker does not disable producer terrain-light reuse. Compare
matched 3481 baseline exports with 3486 to evaluate that producer correction;
the marker alone is not an A/B switch for every change in the new engine.

Expected candidate records include GX-PERF-LOAD-END, GX-PERF-CPU-FIRST,
GX-PERF-CPU, GX-PERF-BATTLE-END near 120 seconds, GX-PERF-RESOURCE,
GX-PERF-TERRAIN-CPU, perf-terrain-reuse, perf-upload-source and perf-thread.
The lighting-dirty follow-up adds GX-PERF-TERRAIN-DIRTY, perf-window,
GX-PERF-PATH-REQUEST and periodic glyphpool counters. Keep their monotonic
timestamps/window durations when comparing CPU, simulation and render reports.
These windows share a clock but overlap; GPU/worker work is not additional
serial frame time. Terrain draw counts remain unchanged by the producer fix.
Absence of GX-PERF-AI-NONFINITE means no nonfinite state was observed at these
probe points; it does not rule out FE_INVALID or invalid values elsewhere.

Compare CPU/frame P50/P95/P99, first CPU frame, avoided terrain bytes/calls,
logic/AI/path cost, producer waits and swap. Report GPU time unavailable when
queries are unavailable/disjoint; never substitute render-worker busy time.
The preRTT follow-up adds GX-PERF-MODE, PRERTT, PRERTT-WORK and DRAWMODULE:
keep their timestamps, frame counts and CPU/wall/producer-wait fields. Explicit
Performance summary suppresses stale full/net event traces. To request detailed
diagnostics, turn Performance summary off, or explicitly create gx_perf_detail.txt
alongside the existing trace markers (GX_PERF_DETAIL also works for developers).
Replay Check intentionally preserves its CRC diagnostics and is not a normal
benchmark; use the in-game replay menu for matched performance runs.
The load-end to CPU-first timestamp difference is CPU transition latency, not
first displayed-frame latency. Nested timings overlap and must not be summed.

For a separate focused dozer exception run, enable Online network log only as
requested by the engineer, reproduce briefly and export. Do not mix that run
with timing baselines. This channel may contain simulation/network diagnostics;
the performance-only raw-bit probes already identify stored NaN/Inf states.
