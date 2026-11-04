# Targeted performance changes — 2026-11-04

Source baseline: `392b2f7b12da16786661ab1c8aa75ee0d736d933`, branch `dev/mobile-v4`.
This is a source/test delivery, **not a verified full-game performance improvement or OTA release**.

## Evidence and implemented paths

The supplied Performance_Log_Report.md identifies terrain submission, VB full/append
uploads, worker synchronization, high shroud-query counts and creation hitches.
The raw `generalszh-logs.zip` was not exposed in this session's attachment directory;
its window statistics could not be independently recalculated. No broad discovery
or camera-full-rebuild hypothesis was substituted for that report.

- `HeightMapRenderObjClass::Render` submits fixed-grid terrain for each shader pass,
  plus overlays. Fusion and unchanged-terrain suppression already exist. Static
  buffer writes reach `WebGLPipeline::ensureVBUploaded`; its min/max dirty interval
  formerly sent unchanged interior data between separated edits. The added snapshot
  selector skips verified unchanged interior blocks, caps output at eight ranges,
  requires 4 KiB savings for multiple writes, and falls back early for dense changes.
  It applies only to static terrain with an existing snapshot and synchronized locks.
  Initial uploads, DISCARD, dynamic buffers and NOOVERWRITE retain their contracts.
  Snapshot versions advance after the GL wrappers capture bytes in FIFO order.
  Upload telemetry counts actual bytes/calls; comparison time includes range selection.
- Full and synchronized GL buffer wrappers used `Blob<256>`: every ordinary write
  above 256 bytes allocated on the producer and freed on the worker. They now use
  the existing `postBytes` owned command payload, retaining null allocation, immediate
  execution and the oversized heap fallback. This removes allocations, **not the
  copied bytes themselves**. No GL fence or synchronization requirement was removed.
- `GameClient::update` visibility queries reach `PartitionData::getShroudedStatus`.
  Its invalid-state scan read the same pure cell accessor twice and scanned all
  intersections even after both clear and non-clear cells proved PARTIAL_CLEAR.
  It now reads each visited cell once and stops when the result is determined.
  Ghost snapshots, previously visible state, neutrality, mines, immobility and
  invalidation retain their original paths. No cross-tick visibility cache was added.

No movement constants, simulation tick contents, save layouts, assets, shaders,
texture quality, mods, networking, launcher or updater code changed.

## Tick pacing and creation: investigated, unresolved

`GameEngine::canUpdateRegularGameLogic` returns one step per rendered frame when
logic time scale is uncapped, as documented by `FramePacer::getActualLogicTimeScaleFps`.
`gxCatchUpSpedUpLogic` explicitly requires an offline live campaign/skirmish,
excludes replay/network/shell/paused/frozen states, and requires a speed limit
**above** normal. Android additionally restricts catch-up to remaining CPU budget.
Thus normal-speed render pressure can slow wall-clock gameplay; zero reported
catch-up is consistent with the existing policy. This session did **not** establish
an unintended timer defect or change that policy without runnable replay/game
validation. Restoring 60 ticks per wall second under load remains unresolved.

`ProductionUpdate`'s `GXPS_CREATE` scope calls `ThingFactory::newObject`, which
selects build variations, creates the object/modules, invokes `onCreate`, registers
partition data and initializes the object. Asset creation uses cached prototypes
with load-on-demand fallback. The supplied aggregate creation timings do not
isolate which of these operations caused each hitch. No speculative preload,
async creation, callback rescheduling or mod-asset cache was introduced. Creation
hitches remain unresolved. The 379 ms event remains a full-frame hitch, not a
379 ms script call.

Terrain draw count (~644), total draw count (~2440), worker/GPU time, and actual
battle FPS have **not** been shown to improve. No draw batching was shipped.

## Verification and reproducible host measurements

[Host check inventory](performance-2026-11-04/host-checks.json) records the Python,
shell and standalone C++ checks: 50 checks passed, one update-channel check is
partial, and one OTA preparation check is unavailable. The broad Python sweep initially had three
prerequisite failures: native-version passed after installing CMake and retrieving
resources; FFmpeg AVIO passed against local FFmpeg 7.1 headers and installed runtime
libraries. The EGL surface check initially skipped for missing headers; rerunning
with NDK Khronos headers and `--require-egl` passed real host software GLES pixel
checks. `test-own-update-channel.py` passed its publisher/signer guards but skipped
JVM UpdateTrust checks (`javac` absent) and the real baseline APK check; it is marked
partial. `test-prepare-engine-run.py` remains unavailable because its verified
3339 native pair and Bootstrap 3333 APK fixtures are absent. It is not counted as a pass.

New/extended regression commands:

```sh
python3 scripts/qa/test-gles-upload-regressions.py
python3 scripts/qa/test-gles-upload-regressions.py --legacy-ref 392b2f7b12da16786661ab1c8aa75ee0d736d933
python3 scripts/qa/test-terrain-snapshot-safety.py
python3 scripts/qa/test-gles-context-lifecycle.py
python3 scripts/qa/test-shroud-classification.py
python3 scripts/qa/bench-terrain-sparse-uploads.py
```

- Upload test first failed the ordinary-allocation assertion on the baseline;
  sparse integration first failed its two-range assertion before implementation.
  Both current and baseline comparison modes now pass with their respective costs.
  Ordinary full/synchronized pair: **2 heap allocations -> 0** in queued and
  immediate modes. Source mutation after submission, A/B/A versions, null/oversized
  writes, synchronized writes, NOOVERWRITE and DISCARD bytes are checked.
- Actual production thread/ring: 400 owned 128 KiB uploads (50 MiB) preserve FIFO
  and lifetime across the 16 MiB ring wrap. This validates correctness under host
  concurrency; it does not establish device ring-wait performance.
- Snapshot checks include uninitialized tails, restoration, budget/release,
  fragmentation fallback, dense movement and 2048 differential mutation rounds.
- Shroud: **2,519,040** exhaustive state/ghost-transition comparisons per build,
  run with and without `DISABLE_INVALID_PREVENTION`. Baseline mixed-visibility
  fixtures of 100/500/1376 **cells** query 200/1000/2752 times; candidate queries 2.
  These are cells of an object's footprint, **not measured unit-count battles**.

[Measured CSV](performance-2026-11-04/terrain-benchmark.csv): host C++ `-O2`,
132 synthetic 128 KiB tiles, 120 iterations, median of five runs. Same inputs for
baseline leading/trailing trim and candidate selection; output GPU-shadow bytes
are checked for equality. Timings include host copying and snapshot updates.

| Host fixture | Baseline bytes / iteration | Candidate bytes / iteration | Uploads before / after | CPU ms before / after |
|---|---:|---:|---:|---:|
| Unchanged tiles | 0 | 0 | 0 / 0 | 1.750 / 1.752 |
| All bytes moving | 17,301,504 | 17,301,504 | 132 / 132 | 3.198 / 3.082 |
| Two separated edits / tile | 15,838,020 | 264 | 132 / 264 | 2.737 / 2.353 |

The dense fixture initially regressed when every chunk was scanned; the final
selector detects dense prefixes and retains the original span. These host results
are synthetic mechanism measurements, **not camera/device FPS benchmarks**.
Sparse uploads trade fewer bytes for more synchronized GL calls; inline payloads
increase command-ring occupancy relative to heap-backed commands. Device measurements
of driver upload time and ring/sync waits are required to settle the runtime tradeoff.
The existing `terrainreuse` opt-out disables the snapshot/sparse path.

## Android build and OTA gates

Installed user-local CMake/Ninja and NDK r27c. Built the unmodified production
`Core/Libraries/Source/d3d8gles/CMakeLists.txt` target for **Android API 28,
arm64-v8a**, including complete `d3d8gles.cpp`/pipeline, dispatch and render thread.
The isolated harness supplies interface include targets for SDL 3.4.2,
pinned DXVK `46a3bc018bcae408d49d3c500e4e536a11f6789a` and existing CompatLib.
No production source was replaced by a stub. All three archive objects are AArch64.
Only the existing `INVALID_HANDLE_VALUE` redefinition warning was emitted.

Archive SHA256: `d65488006f5d3807a6dd2bd93acf5d29dae2e0da59e6d111874e2889f30dadf8`.
[Compiler log](performance-2026-11-04/android-renderer-build.txt).

The dual-Hz build script stopped at missing `sudo`. With user-local NDK and CMake,
[direct engine preflight](performance-2026-11-04/android-engine-preflight.txt)
still fails: no vcpkg dependency tree, Meson, glslangValidator or configured DXVK
submodule. No complete `libmain.so`/`libmain60.so`, APK or compatible OTA artifact
was built. The renderer archive alone is not publishable through the updater.
No Actions build was dispatched; source push uses `[skip ci]` to respect the
repository's local-build instruction despite existing push-triggered workflows.

**OTA version/URL: none published.** Existing signed update manifest, signing keys,
sequence/version and download payloads were left unchanged.

No Android device/ADB is available (confirmed by the user). Static-camera,
camera-pan, 100/500/1000+ unit device captures, actual travel distance per wall
second, replay CRC, save/load, graphical equivalence, mods and in-app OTA
update/version/load verification were not performed. These gates remain open.
