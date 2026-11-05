# PR #45 performance continuation validation

Base: `dev/mobile-v4` at 7141f1b. Continued existing branch
`perf/android-engine-tick-gpu-20261105` from 0c97b711 without rebasing or
repeating its normal-speed debt recovery and upload attribution changes.

## Root causes reproduced and repaired

1. An unchanged static-terrain DISCARD forced full upload even with a matching
   queued snapshot. Compare the entire initialized prefix a full upload would
   send. Skip only an exact match. Changed bytes outside the lock, unknown
   initialization, first allocation, dynamic buffers and the opt-out retain the
   original path. No GL entry points, fences, persistent/index buffers, ownership,
   FIFO commands, shaders or terrain draw order changed.
2. Catch-up eligibility was sampled only once per rendered frame. End-game,
   network/replay and shell/freeze transitions inside callbacks could admit
   additional ticks. Eligibility now runs at each boundary and after messages.
   Fresh script freezes and speed/time-scale/limiter changes stop recovery even
   before cached FramePacer state is refreshed.
   Catch-up also requires a completed primary logic update. Recheck the deadline
   after messages so expensive message handling cannot admit a late logic tick.
   Step count remains at most three extra ticks, elapsed input at most 100ms,
   normal recovery admission budget at most 6ms. An individual admitted tick is
   not preemptible and can exceed that budget.
3. The new budget fixture was absent from native reports and OTA prerequisites.
   Require both budget and actual-orchestration regressions, including rejection
   of missing, failed or unrun evidence. Engine-only commit markers now suppress
   APK build jobs on performance branches as well as the development branch.

## Host validation

44 relevant scripts returned zero, including terrain batching/lighting/snapshot,
shroud, GLES upload/FIFO/lifetime, context/surface restoration, program bindings,
frame limiter, module factory, native-version/security/packaging, save-map,
localization/mod loading, AI, TLS and update-channel tests. ASan/UBSan exercise
production code via host adapters; no sanitizer findings were observed. The
initial lighting fixture needed its pinned historical source fetched. It then
passed unchanged. The timing and upload regressions were observed failing before
the corresponding fixes and passing afterward.

The EGL pixel check initially skipped for missing headers; rerun with Khronos
headers and `--require-egl` passed with Mesa llvmpipe EGL 1.5. It verifies 12
surface recreations, preserved textures, complete clears and contiguous UI
pixels. This is a host software renderer, not an Android/Mali device test.

Local logs are in `/workspace/validation-final/`. Production UpdateTrust JVM
validation passed eight crypto checks with a user-local JDK. The own-channel
suite passed 22 host checks using the unchanged downloaded Bootstrap 3333 APK.
The final exact-source native build must still be inspected before release.
The superseded 3677 native run was canceled during runner cleanup before
compilation after additional mode-transition cases required a source correction.
No APK is built by these changes.

## Measurements and provenance

- Post-3667 summary from the original PR: ~46.7 rendered FPS / ~46.3 ticks/s
  for a configured 60Hz engine; ~12 MB/frame full VBO and ~10 MB/frame terrain
  append traffic. No newer raw device log was present in the checkout or recent
  repository discussions. These summaries do not attribute the full-upload
  volume to the new static-terrain case.
- Deterministic production-orchestration host fixture: 30/60Hz cadence within one
  tick over ten seconds at half and two-thirds rendering cadence, bounded stalls,
  time admission, game transitions and network/replay/freeze/pause exclusions.
- Host fixture, 120 unchanged 128KiB terrain DISCARDs: 120 full transfers /
  15,728,640 bytes before; zero afterward. This is mechanism coverage, not a
  measured improvement in device FPS or camera-pan latency.
- Existing native run 41971063496 built engine 3676 from 0c97b711 at both rates.
  Downloaded actual artifact hashes match `result.json`:
  - 30Hz: 44b9eb50507cd25dc3b7eda9df84f97fb9b53b049a051687a7a24a213b9821e2
  - 60Hz: 373745540950bdc369d7dc11bdb07787bd8900a6f22e8c6bf97eb87ead7923f7
  AArch64 ELF headers and unchanged dependency comparison were inspected. These
  earlier artifacts do not validate the continuation commit.

## Release acceptance still required

No Android device/ADB or retail/TEOD assets/replay fixtures are attached. Real
unit/vehicle travel distance, battle frame-time percentiles, camera movement,
Vanilla/TEOD graphics, input, saved-game load, replay CRC, multiplayer lockstep
and actual OTA activation/rollback have not been tested. Latest full-upload
source/reuse-miss counters are needed to identify the remaining device transfer
and synchronization costs; no general DISCARD/NOOVERWRITE rewrite is justified.

Do not mark these gates passed, merge PR #45 or publish a signed OTA without the
required evidence. The live baseline inspected this session is engine 3667,
serial 32, source a892c63a0cee78ae84c751b05a06913294cfcf3e. Preserve its signed
manifest and payloads. No signing identity, updater, APK or production update
branch changes are part of this continuation.
