# Engine 3643 recovery candidate — 2026-11-03

Baseline: dev/mobile-v4, 979ca62d3c169660bc68c834c252caf5f053ede0, OTA 3643 / serial 29. No APK built; OTA manifest unchanged. This is a host-tested source candidate, not an Android-validated release.

## Repairs

- HeightMap::setTerrainDrawSize compares effective stretch/full-map sizes before reinitialization. Reproduced 1000 repeated rebuilds before repair; 6000 unchanged requests now preserve buffers/shroud. Device recurrence in the reported performance window is not proven.
- HeightMap::doPartialUpdate splits both circular axes; 3000 affected-cell comparisons pass across clipping, wrapping, rectangular/full/empty regions. Existing normals, UV generation and material/shoreline paths remain in place.
- Terrain metrics attribute rebuild requests to initialization, lighting/height, time-of-day, resources, draw size and invalid cells; completed/partial builds, regenerated quads and submitted VB bytes report in existing two-second performance windows.
- GLES bindTextures/applySamplerState avoid redundant active-unit commands and initialize immutable sampler selectors once per linked program. Immediate/queued state equivalence tests pass. No terrain passes removed or reordered.
- Both FFmpegFile implementations report virtual-file size while preserving nonseekable streaming, clean packet references on error, and reject failed reads before stream lookup. Real host FFmpeg valid Xing MP3 and malformed concatenation tests pass with ASan/UBSan; genuine malformed diagnostics remain.
- ScriptList::ParseScriptsDataChunk clears stale publication count and releases partial parse allocations on failure; exact 16-list boundary accepted. Sanitized retry/ownership regression passes.
- ProductionUpdate stage profiling is optional and bounded to 64 reports above 5 ms, with no production scheduling/rules changed. It supplies attribution needed before attempting optimization; it does not prove the spike source.

## Validation executed after recovery

Passed: test-terrain-invalidation.py, test-terrain-partial-region.py, test-gles-texture-state.py, test-gles-upload-regressions.py, test-terrain-light-dirty.py, test-ai-script-loader-cleanup.py, test-production-stage-profile.py, test-ffmpeg-avio-size.py (both real production copies), test-teod-camera-scroll.py, test-engine-security.py, test-save-map-safety.py, test-engine-packaging.py, test-shader-cache-async.py; standalone terrain geometry ASan/UBSan and telemetry header compilation; git diff --check.

The 9000 earlier terrain cases were rerun because the recovered telemetry edits required integration regression verification. Host save-map safety checks do not demonstrate real save/load compatibility.

Initial audio test was blocked by missing development headers. Debian 7.1.5 development headers extracted outside the repository resolved that dependency; the rerun passed against installed host FFmpeg 7.1.5 (Android ships another version).

Unfinished test-ai-script-coverage.py fails because its proposed diagnostic function was never implemented. It and test-frame-pacing-lifecycle.py are preserved uncommitted as drafts, not included in the validated subset.

## Release blockers and outstanding work

Android configure-only check fails: ANDROID_NDK_HOME/VCPKG_ROOT unavailable; cmake, ninja, meson, glslangValidator and DXVK fork submodule missing. No Android compilation/link or binary packaging has passed. Repository instructions prohibit dispatching CI for builds; no CI was triggered. No local signing key configured in the recovered environment.

No attached Galaxy A56 or TEOD MODDB_Ver11 data: all ten requested physical scenarios remain pending (Vanilla/TEOD idle/moving, high units, terrain/lighting, jumps/bounds, map/mod switch, lifecycle, saves). No device FPS, low percentiles, GPU timing, CPU synchronization or before/after benefit measured.

480 Hz request/uncapped pacing and lifecycle reset are still unimplemented. Scheduling currently permits at most one normal logic tick per engine update, so a 30 Hz render-loop cap can slow 60 Hz simulation; safe decoupling needs separate implementation and tests. No video acceleration change: current cached software/NEON conversion remains. Missing textures trstrtholecvr.tga, ru-navalyard.tga and music CHI_01.mp3 cannot be classified without actual mod/archive inventory. Seven missing AI sides remain unclassified; no faction fallback fabricated. Production spikes require new stage measurements before optimization. No additional AI scalability or multipass change was attempted without evidence.

## Modified production files

- `Core/GameEngineDevice/Source/VideoDevice/FFmpeg/FFmpegFile.cpp`
- `Core/GameEngineDevice/Source/W3DDevice/GameClient/BaseHeightMap.cpp`
- `Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp`
- `Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp`
- `Core/Libraries/Source/d3d8gles/src/gles_pipeline.h`
- `GeneralsMD/Code/GameEngine/Source/GameLogic/Object/Update/ProductionUpdate.cpp`
- `GeneralsMD/Code/GameEngine/Source/GameLogic/ScriptEngine/Scripts.cpp`
- `GeneralsMD/Code/GameEngineDevice/Source/VideoDevice/FFmpeg/FFmpegFile.cpp`
- `Core/Libraries/Include/GXTerrainUpdateStats.h`
- `Core/Libraries/Include/GXProductionProfile.h`

No OTA version allocated or artifact published. Existing OTA 3643 / serial 29 remains the release baseline.
