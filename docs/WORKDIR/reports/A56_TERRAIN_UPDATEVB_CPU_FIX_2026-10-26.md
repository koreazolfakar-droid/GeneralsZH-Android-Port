# A56 terrain-scroll CPU fix — 2026-10-26

## Scope

This change targets the CPU cost observed during continuous camera movement in `HeightMapRenderObjClass::updateVB`. It does not change simulation state, terrain resolution, blend equations, depth/stencil state, or the existing GLES/Vulkan fallback policy.

The Android port resolves to native GLES when `render_backend.cfg` is absent; Vulkan/DXVK is opt-in through the explicit `vulkan` value. The change is in the shared terrain CPU path, so it applies to both backends. The existing dynamic-buffer persistent/ring implementation remains the upload path, with its existing fallback when the driver does not expose the required extensions.

## Implemented changes

* Global terrain light rays are computed once per rectangular `updateVB` call instead of once per cell.
* `getXWithOrigin()` and `getYWithOrigin()` results used by the rectangle are cached once per update. The existing `mapX - 1` / `mapY - 1` neighbor arithmetic and clamping are unchanged.
* A conservative real-coordinate broad-phase checks the light iterator once per rectangle. If no point/spot light overlaps the rectangle and there is no directional light, `doTheLight` receives `nullptr`; this preserves the ambient/static result and skips per-vertex dynamic-light iterator work. Wrapped windows use enclosing bounds, so the test can retain extra work but cannot falsely exclude a touching light.
* Existing `m_doXNextTime` axis splitting and the existing persistent/ring upload fallback were retained. A new deferred block queue was not forced into this patch because deferring a strip can expose stale terrain for a frame; that visual behavior was not provable equivalent from the available host harness.

## CPU-only benchmark

Harness: `scripts/qa/bench-terrain-updatevb.py`. It mirrors the production height sampling, circular-origin indexing, normal calculation, global-light work, and continuous scroll pattern. It is explicitly not a real-device GPU/FPS benchmark.

Configuration: 720 simulated frames, map extent 768, updated region 96×96, `g++ -O2`, host sandbox.

| Mode | p50 ms/update | p95 ms/update | Mean ms/update | Checksum |
|---|---:|---:|---:|---:|
| Baseline | 3.016 | 3.412 | 3.072 | `5345044300678934630` |
| Optimized | 2.924 | 3.104 | 2.953 | `5345044300678934630` |

The checksum matched, so the modeled generated terrain values were unchanged. This is a modest CPU improvement in the synthetic workload, not proof of an FPS gain on an A56. The broad-phase benefit depends on the active dynamic-light list and was not represented as a separate device measurement.

## Validation completed

* `test-gles-upload-regressions.py`: PASS. It covers FIFO/lifetime/map fallback, unchanged terrain upload suppression, and static/dynamic synchronized, `NOOVERWRITE`, and `DISCARD` byte/range behavior.
* `test-gles-terrain-fused.py`: PASS. 100,000 random texels matched the legacy `SRCALPHA/INVSRCALPHA` blend exactly; the legacy noise pass and GLES fallback guards remained present.
* `test-terrain-light-dirty.py`: PASS.
* `test-terrain-snapshot-safety.py`: PASS.
* `test-teod-camera-scroll.py`: PASS on independent reruns. One earlier run timed out at its 15-second harness limit; the test passed on the retry and final rerun.
* `test-engine-budget-v2.sh`: PASS.
* `git diff --check` and Python bytecode compilation: PASS.

## Not tested / publication gate

No Samsung A56, GLES3 GPU, Vulkan GPU, Android NDK, or native `libmain.so` build was available in the sandbox. Therefore no real-device CPU/GPU frame-time, draw-call, upload-stall, visual-edge, mod, or backend result is claimed here. The next gate is the official Android dual-engine build on the pushed source commit. OTA publication must remain fail-closed until that build is PASS and the live manifest, signatures, and both engine payload checksums verify.
