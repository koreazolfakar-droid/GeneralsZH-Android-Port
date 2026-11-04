# Android GLES surface restoration validation — 2026-11-04

Base: `3f9d3f3b85bbfdeaea6cbc1ff97a3256efbfec45`, `dev/mobile-v4`.
Live OTA inspected during this work: engine **3659**, serial **31**, source
`474b7c0fb484b9b0c2ce22f6c2f991fb7c167554`.

## Confirmed production defects

- The Android engine deliberately executed one extra update/render after polling
  pause. SDL's Android backend sends background events, then backs up/detaches
  EGL before event polling returns. That frame therefore submitted direct GL
  without a current context after the worker handed ownership back.
- `handleWindowEvent` was empty. Pixel-size, restored and exposed events never
  reached the GLES pipeline. The independent per-frame resize path invoked a
  full D3D device Reset for a physical surface-size change.
- Several context handoff results were ignored; SDL's replacement context was
  accepted while every cached GPU object still belonged to the lost context.
- The swap cache was invalidated at handoff, but the unchanged-policy `-1`
  presentation request never reapplied the desired interval.

These are code-level findings reproduced by regression fixtures. Attribution of
this particular Samsung screenshot to a specific defect still requires device
reproduction; no claim of physical-device screen restoration is made.

## Implementation

Android gates rendering immediately on pause and until a valid drawable is
available. Watchers only request surface repair. The engine coalesces foreground,
resize, pixel-size, restored and exposed events after SDL polling. It queries
`SDL_GetWindowSizeInPixels`, ignores invalid/transient portrait sizes and retries
without rendering until valid. The renderer preserves logical D3D/backbuffer and
UI/touch coordinates while scaling raster rectangles to current physical pixels.

The physical resize path avoids device Reset, terrain rebuilds, texture uploads
and virtual-target reallocations. The existing virtual scene-resolution and
upscaler choices remain intact. Restore checks context ownership, drains queued
commands, rebinds the current FBO, invalidates draw-state caches, reapplies the
retained swap policy, and forces the next backbuffer clear to cover every region.
Explicit game-resolution Reset remains separate from drawable-size updates.

The context handoff checks every detach/bind; worker-bind failure falls back only
when the original context can actually be made current on the main thread. An
unrecoverable handoff or genuinely replaced context emits a fatal diagnostic and
stops before further GL work. **Complete GPU-resource reconstruction following
real context loss is not implemented. This candidate does not satisfy seamless
context-loss recovery and is not approved for OTA publication.**

## Automated verification

All tests exercise actual production methods/state transitions. Driver boundaries
are injected for the host fixtures; these are not Android instrumentation tests.

- `python3 scripts/qa/test-sdl3-render-lifecycle.py`: actual watcher, Android update
  gate, restoration service, window handler and wrapper resize path; first paused
  frame, invalid-drawable retry, window-ID filtering, coalescing, unchanged/changed
  sizes, 100 switches, unchanged Vulkan Reset path. Original source fails the
  first-paused-frame assertion.
- `python3 scripts/qa/test-gles-context-lifecycle.py`: compiles the complete actual
  thread implementation with real `std::thread` and command ring. Validates drain,
  ownership transfer, duplicate resume, 100 rapid switches, verified fallback,
  direct context rebind, retained swap policy, and injected detach/bind/replacement
  failures. The pre-fix thread implementation allowed unsafe replacement.
- `python3 scripts/qa/test-gles-surface-restoration.py`: production resize,
  explicit backbuffer Reset, virtual target allocation/resize/disable, refresh,
  FBO restore, viewport mapping, stretching and clear in immediate/queued modes
  under ASan/UBSan. Includes invalid dimensions, unchanged resources, UI rectangle
  consistency, offscreen target isolation, full first clear and 100 switches.
  Original resize overwrote valid dimensions with zero.
- `python3 scripts/qa/test-gles-egl-surface.py --headers <Khronos-header-dir>
  --require-egl`: actual host EGL 1.5 / GLES3 Mesa llvmpipe. Twelve pbuffer
  recreations retain the original context and exact texture RGBA bytes; production
  restore rebinds the window framebuffer. Every pixel is checked after resumed
  full clears and adjacent HUD/scene region clears. `GL_NO_ERROR` is asserted.
  This is real software-EGL validation, not Android/device validation.
- Existing GLES suites: `test-gles-upload-regressions.py`,
  `test-gles-texture-state.py` (412 snapshots), `test-gles-terrain-fused.py`
  (100,000 texels): pass.
- Existing resolution policy C++ test: compiled with C++17,
  `-Wall -Wextra -Werror -pedantic`, then executed: pass.
- Existing `test-engine-security.py`: big parser, save-block streaming,
  websocket fragments: pass.
- `git diff --check`: pass.

Full replay/game/UI/mod compatibility runs require a runnable engine and licensed
Vanilla/TEOD assets; neither was executed in this environment.

## Native build and release gates

The production `d3d8gles/CMakeLists.txt` target compiles and archives successfully
using NDK r27c / Clang 18, Android API 28, AArch64. This includes complete
`d3d8gles.cpp` (which includes `gles_pipeline.cpp`), `gles_dispatch.cpp`, and
`gles_thread.cpp`; it uses the pinned DXVK headers and SDL 3.4.2 headers. Only the
pre-existing `INVALID_HANDLE_VALUE` macro redefinition warning is emitted.
The final archive SHA256 is
`ccabfe29c07ded6f5d6b2d5784a74ebf8b233a2eb301c7e5eb08d4a32deda189`.
`llvm-readelf` confirms all three archive objects are AArch64. The harness used the
production CMake target, with interface targets supplying the existing CompatLib,
pinned DXVK and SDL include paths; it did not replace production sources.

This is a renderer static-library build, **not** a linked engine build. The local
native engine build script fails preflight because vcpkg, glslang and the complete
DXVK build prerequisites are absent. The existing incremental engine-state
artifact is 5,398,376,241 bytes compressed and cannot be downloaded and unpacked
within the remaining workspace storage. `libmain.so` and `libmain60.so` were not
produced or claimed validated. No APK was built.

All changed native components are within the engine payload: d3d8gles is statically
linked, and the SDL engine/wrapper changes are engine code. No Activity Java,
packaged SDL3 library, signing identity, or runtime dependency changes were made.
There is no structural APK packaging blocker for these changes.

OTA publication remains blocked on complete context-loss handling, linked dual
engines from one exact source, baseline native-dependency hash compatibility,
engine build/provenance manifest verification, and signing. No local private
signing key is available; the existing signing mechanism was not altered. No OTA
branch was force-pushed or update manifest/version changed.

## Physical validation still required

No Android device, USB target or emulator was exposed. Validate Samsung Galaxy A56
Home, Recents, application switches, rapid/repeated resumes and real surface
recreation with Vanilla and TEOD, both 30/60 Hz engines. Inspect the battlefield,
command bar, minimap, selection/construction panels, HUD text, cursor/touch
coordinates, menus/dialogs, orientation and audio. Verify context survival and
record context-loss behavior separately. Host fixtures cannot establish these
visual or device-specific results.
