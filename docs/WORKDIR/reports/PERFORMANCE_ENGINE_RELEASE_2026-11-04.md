# Remaining performance implementation and engine-only release gates

Continues `21878c25` and `11219eb4` on `dev/mobile-v4` without merging other branches.

## Implemented

- Four consecutive terrain tiles share a static VB and rebased immutable index
  list. Each existing terrain/shroud pass submits `ceil(tileCount/4)` draws;
  triangle order, geometry, materials and pass boundaries remain unchanged.
  Tile writers use synchronized offsets and independent cached lighting versions.
  Four tiles remain within the existing 512 KiB snapshot limit. Normals and
  software T&L paths retain legacy allocation/drawing.
- The limiter retains scheduled deadlines across small oversleeps, rebases after
  missed periods/long lifecycle gaps or rate changes, resumes interrupted POSIX
  sleep and reduces its spin margin from 2 ms to 0.2 ms. The exact uncapped
  sentinel returns immediately. Actual elapsed intervals, simulation scheduling,
  game-speed settings and replay/network semantics are unchanged.
- Module creation reuses factory-owned registrations resolved for live INI data,
  validating name/type and falling back for manual/null/foreign/mismatched data.
  Callbacks, creation timing, RNG and ModuleData layout remain unchanged.
- Linked GLES program initialization queries 13 uniform locations and one uniform
  block in one render-thread round trip instead of 14. Raw GL queries run behind
  link commands on the GL owner; results and caller lifetimes remain synchronous.
- Engine-only CI removes only fixed unused hosted-image SDK directories before
  restoring verified state. It preserves pinned SDK/vcpkg/compiler inputs. Both
  native CI and OTA preparation require the new regressions in addition to their
  existing checks; native dependency mismatch still prevents publication.

## Validation

Independent review found no correctness blocker. New production-code fixtures:

```sh
python3 scripts/qa/test-terrain-draw-batching.py
python3 scripts/qa/test-terrain-light-dirty.py
python3 scripts/qa/test-frame-rate-limit.py
python3 scripts/qa/test-module-factory-resolution.py
python3 scripts/qa/test-gles-program-bindings.py
python3 scripts/qa/test-engine-runner-space.py
```

Terrain tests cover exact ordered indices, partial final groups, four platform
configurations, all geometry/light writer offsets, fallback paths and shared
buffer lifetime under ASan/UBSan. Limiter tests exercise production POSIX/Windows
branches with a deterministic clock, 30/60 Hz, uncapped/rate changes, interruptions
and long stalls. Module tests compare legacy and cached production functions,
including registration growth/update, name/type mismatch and creator ordering.
GLES tests verify identical missing/active bindings and one synchronous boundary.

These establish draw submission and lookup-count reductions, not device FPS.
Creation's repeated factory resolution is removed; no claim that this eliminates
all of the reported 31–47 ms device hitches. The GLES static target also compiles
for Android AArch64/API 28 locally. Full linked dual-engine/dependency verification
and signed OTA integrity are required from the existing CI/publisher before release.

The previous failed CI run's annotation reports `No space left on device` during
state restore. The reusable workflow cleanup is narrowly tested and does not
remove build objects or bypass receipt, source, compiler, checksum or dependency
guards. Restore must use an ancestor source, not state from separate branches.

No APK is built or modified. Physical-device FPS, camera captures, unit travel,
Vanilla/TEOD visual validation and in-app update installation remain unverified
because no Android device is connected. The existing signed OTA stays intact until
a replacement passes the build and release verification.
