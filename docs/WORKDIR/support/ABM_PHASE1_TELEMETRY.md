# ABM Phase 1 — read-only bottleneck diagnosis

This is the **measurement and correlation** stage of the Autonomous Bottleneck Manager, not a runtime self-healing controller. It makes no changes to renderer, simulation, AI, visuals, GPU synchronization, or OTA packaging.

## Run

From repository root, Python 3 standard library only:

    python3 scripts/qa/abm/diagnose.py generals-stderr.log --output abm-report.json
    python3 scripts/qa/abm/diagnose.py generals-stderr.log --battle-only --top 15
    python3 -m unittest discover -s scripts/qa/abm -p 'test_*.py'

Default includes all windows; --battle-only selects only intervals bracketed by [GX-PERF-BATTLE-BEGIN] and [GX-PERF-BATTLE-END]. Some play and menu activity is otherwise lost.

## Five monitored categories

| Source | Direct observation | Important limitation |
|---|---|---|
| [d3d8gles] perf-gpu | Worker swap and GPU execution time per frame | Swap is CPU waiting, not GPU time. GPU timer may be delayed or unavailable. |
| [d3d8gles] perf-draws/frame by source | Draws grouped by subsystem | Draw count alone cannot establish a bottleneck. |
| [GX-PERF-LOGIC-DETAIL] | Average modules time per logic tick | Nearby correlation does not prove a module stalled a render frame. |
| [GX-PERF-PATH-REQUEST] | Request count, total, worst nested request | Nested within logic, not additive to frame time. |
| [GX-PERF-TERRAIN-REBUILD] and perf-upload-source | Terrain submitted bytes and driver terrain KB/frame | Different measurement stages; never add together. |

Engine telemetry often supplies microsecond timestamps (t=...us). Different subsystems are aligned to their nearest timestamps within five seconds and labelled 'Nearby' in output. This is **window-level proximity, not frame-exact causality**. Never add overlapping CPU, worker and GPU time.

## Supplied November 7 Project X log: initial findings

- 753 renderer windows; 753 reported GPU timing values.
- Peak window-averaged worker swap: 71.46 ms/frame, with GPU timer 83.69 ms/frame in the same renderer interval.
- Maximum window-averaged draw count: 1,786.7 calls/frame, but swap was only 0.73 ms/frame in that window. Draw count alone does not explain worst stalls.
- Nearby peak logic modules time: 11.69 ms/tick.
- Peak individual path request in its own window: 352.499 ms.
- Terrain rebuild telemetry summed 3,583,414,144 bytes *submitted* across intervals; not proven bus traffic per individual frame.

These values are from distinct measurement windows. Comparing different mods and scenes is not a controlled A/B test.

## Next on-device instrumentation gaps

1. Assign a shared frame/interval identifier to CPU, render, GPU, path and terrain samples for exact pairing.
2. Log GPU timer query validity, coverage and disjoint status; missing values must not be presented as zero.
3. Record presentation mode, swap interval, queue depth and fence wait categories to separate GPU saturation from VSync and synchronization.
4. Add bounded pre/post hitch snapshots with build, mod, map, resolution and optional thermal status.
5. Verify profiling overhead and timing on both 30 Hz / 60 Hz builds with matched scenes, ensuring deterministic gameplay.

This stage is diagnostics only, not self-healing. OTA publication requires actual native build and device validation.
