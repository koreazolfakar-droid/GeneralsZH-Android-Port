# Standalone mod archive release

## Confirmed source defects

- Published engine 3344 (`775111c69ec93c0665d7eb610dcbfc4d50d1aa17`)
  mounts directory BIGs in alphabetical order with overwrite enabled. Each new
  archive goes to the front: the last BIG wins. Retail mounting appends, so the
  first BIG wins. Replaying the published production function fails the same
  conflicting-path fixture that passes for the root layout.
- The already merged mobile overlay at `317d55b8b` corrects this order, masks
  physically replaced same-name primary ZH archives, preserves sibling Generals
  fallback, and excludes inactive Mods/ archives. It was not in engine 3344.
- Recursive `StdLocalFileSystem::getFileListInDirectory` discarded its parent
  path. The production scanner finds zero BIGs for a mod with only nested
  archives before this fix. The retail `Data/INI/INIZH.big` duplicate exception
  also applied to explicit mods; it now applies only to retail scans.

## Initialization and state

Android passes the persisted active mod as an absolute `-mod` argument.
`GameEngine::init` mounts its complete archive set before GameText, object,
particle, model and texture consumers. The earlier base GameData initialization
and command-line contract are preserved. Virtual archive paths are lowercased
and split on either slash by the existing parser/index. BIG filename scans are
case insensitive. Loose-file precedence remains the retail VFS contract.

Mod selection applies at the next game start. The native exit path terminates
the process (`_exit(exitcode)`), so a subsequent launch recreates archive,
existence, model, texture and animation caches. No live mount replacement or
save/settings deletion is introduced. Host tests use this fresh-process model;
they do not claim to exercise Android lifecycle or SharedPreferences.

## Executed local validation

- New production archive pipeline: 11 fresh-process fixture runs under
  ASan/UBSan, including Vanilla -> Mod -> Vanilla -> Mod and selected-mod restart.
- Root vs standalone payload equality for vehicle/infantry/animation W3D,
  DDS/TGA shield textures, object INI, FXList and ParticleSystem INI.
- Multiple conflicting BIGs, same-name ZH replacement, surviving sibling
  Generals archive, inactive-mod exclusion, nested mixed-case BIGs and direct BIG.
- Provenance trace disabled by default, filtered by case/slash-insensitive path,
  enabled by marker, and all-file mode including loose hits and unresolved reads.
- Existing overlay, both localization suites, save-map safety, BIG/save/message
  security, incremental state, build number, packaging and update-channel checks.
- Negative controls: published loadMods fails duplicate payload selection;
  pre-fix directory traversal fails to find nested mod BIGs.

Synthetic payloads verify selection and byte delivery, not rendering. No Android
device or real game/mod data is connected. Real Project X vehicle/infantry/shield
visibility, gameplay, save/load, app restart preferences and both-rate runtime
checks are NOT TESTED and remain the owner's phone acceptance checks.

## Build and publication

Use the existing `build-android.yml` engine-incremental mode and retained run
37797101176 state if a matching branch cache is unavailable. Missing state,
unexpected dependency changes or excessive recompilation must stop the build.
No clean task, cache/artifact deletion, dependency rebuild or APK repack is
requested. Preserve engine 3344 and its signed metadata for rollback.

The normal `sign-update.yml` is absent from GitHub's registered workflow list
(HTTP 404). The existing registered signer path is reused on dev/mobile-v4 with
explicit dispatch inputs, exact successful build/source validation, and the same
production preparation/signature/publication scripts and pinned public key.
Final run IDs, source SHA, sequence and published URLs are recorded after the
actual workflows complete; this source checkpoint does not claim a release.
