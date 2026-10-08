# Guarded engine build route — 2026-10-08

## Scope and audited state

Repository: `koreazolfakar-droid/GeneralsZH-Android-Port`.
Branch: `dev/mobile-v4`. Starting local and remote HEAD:
`7f65f31c7338ef6967fa7194cfb21af6bf9e5467`.
Existing particle/video source changes are preserved in the working tree and are
not part of this build-route checkpoint. No engine, APK, simulation, save format,
launcher/update trust identity, mod manager or game data is changed by this route.
No Android compilation, packaging or publication has run in this phase.

The recurring blocker has two parts: this workspace has no runnable Android
CMake/compiler environment; full retained Actions state is scoped to
`refs/heads/debug/android-audio-sfx-v1`, inaccessible directly from the mobile
branch. An APK is not CMake/Ninja/object state. The original mobile workflow
cached SDK/vcpkg/ccache/DXVK, but did not preserve complete dual-engine state.

## Retained source and caches verified through GitHub API

The cache-host branch is at `c97bbcff665564efcc85804d12ca48b1d98d4b75`.
Its successful retained source is
`4a9d42c1fa6b9c919995b91897a0c8faa0ead4dc` (engine sequence 3338), run
`37668518095`. The four caches are still listed on 2026-10-08:

| Component | Cache ID | Compressed bytes |
| --- | ---: | ---: |
| common runtime/CMake/Ninja/objects | 8640749035 | 542331499 |
| 30 Hz engine state | 8640752830 | 234303779 |
| 60 Hz engine state | 8640755917 | 234400625 |
| ccache | 8640757910 | 49744235 |

Exact cache keys, NDK, vcpkg and legacy toolchain identity are recorded in
`.github/engine-baseline/config.json`. Historical 3338 is a restore reference,
not an override of the next engine sequence. The production complete-history
resolver still determines each resulting build number.

## Implemented route

`build-android.yml` now has a guarded, read-only `engine-incremental` job. Manual
workflow dispatch defaults to `inspect`; the old APK job is excluded for engine
modes. PR behavior is retained. There is no new push or scheduled build trigger.

- `inspect`: restore and verify complete engine states and bootstrap dependency
  fingerprints; no native compilation, APK, signing or publication.
- `build`: after successful inspection and source checks, configure the existing
  30/60 Hz directories and build only `z_generals` from the same committed HEAD.
- `export-legacy`: one-time restoration/export on the cache-owning branch; no
  native compilation. A reviewable standalone workflow template is supplied.
- `off`: explicitly select the original APK workflow, outside this task.

The existing proven builder/compiler/provider are promoted with narrow guards:
missing state/runtime outputs stop; workspace, configuration, object hashes,
ancestor source history and actual ELF GitRevision/GitSHA1 must match. Unchanged
source/generated input timestamps can be restored only when bytes match. A dry
run refuses more than 200 planned compilations per variant, and the compiler
launcher refuses external `_deps`/vcpkg translation units. Native dependencies
are compared against the committed verified bootstrap fingerprint list. A
mismatch reports `NEW APK REQUIRED`, rather than bypassing `requires_libs`.

After successful verification/build, complete state is preserved in an atomic
cache and an independent `engine-incremental-state` artifact (90-day retention):
CMake cache/files, Ninja graph/deps/log, objects, generated files, both raw engine
outputs, common runtime/DXVK outputs, ccache, SDK/NDK, vcpkg outputs/binary cache,
and retained CMake/Ninja/ccache host tools. Restore verifies all archive hashes
and member paths before extraction and refuses populated destination directories.
This backup excludes repository credentials, private signing keys, app/game data
and arbitrary extra directories. GitHub artifact access requires repository
Actions permission; these backups are not engine release packages.

Cache keys identify configuration plus source SHA/run; receipts additionally
verify actual tool versions and workspace. A runner/toolchain/path change stops
instead of rebasing state or compiling everything silently. System ABI remains
`ubuntu-24.04`; host executable preservation is not a promise of portability to
an incompatible future runner OS.

## Validation

PASS: 16 host tests in `scripts/qa/test-engine-incremental-state.py`: full eight-
component round trip; relative symlink/hardlink preservation; checksum corruption;
path traversal; escaping links; populated directory preservation; workspace/tool
mismatch; missing Ninja/objects; wrong 30/60 configuration; object tampering;
actual ELF revision mismatch; invalid ancestor/shallow history and incorrect Git sequence; byte-checked
mtime recovery; unexpected components; external compiler guard; accurate retry/
ccache accounting; duplicate-key YAML and shell syntax checks. Tests use temporary
data-only ELF vectors, not reconstructed native build outputs.

PASS: production engine-build-number host fixtures and 18 engine packaging cases.
PASS: save-map alignment/cleanup, mod localization, GPU timer/STUN/TURN order,
BIG/save/WebSocket security, and production TLS fixture checks. Mod fixture retains
pre-existing initialization-order/unused-variable warnings. TLS negative tests
can emit a local server BrokenPipe traceback; assertions passed.

PASS: 22 own-update-channel host checks, including the actual Engine 3333 APK
provenance and negative signature/channel/publication fixtures. JVM UpdateTrust
checks are NOT TESTED because javac is absent; no actual signing secret was read.

BLOCKED: `test-engine-native-version.py` attempted and failed its prerequisite
assertion because no CMake executable exists here. Searched retained local paths;
none available. Its generated-native-version check is NOT TESTED in this phase.
No toolchain reinstall is attempted. This check remains mandatory in engine build
mode after retained host tools are restored.

NOT TESTED: Actions full archive export/import on a real runner; Android engine
compilation, dependency compatibility on restored outputs, APK packaging, device
battles/save/mod/update acceptance. Host tests do not establish those results.
No Engine 3340 or other new engine was published.

## Remaining activation dependency

The route is source-tested and ready for a one-time state migration. Under the
owner's instruction to modify only `dev/mobile-v4`, the cache-host branch has not
been changed or dispatched. The export workflow must be installed there once
(or installed/run by the owner), then the mobile `inspect` mode can import its
artifact and seed branch-visible caches. Exact steps are in
`docs/HOWTO/ENGINE_INCREMENTAL_UPDATES.md`.

Artifacts expire after 90 days and caches can be evicted; retain an external copy
of the full state artifact and renew it before expiry. This is a durable recovery
route, not a guarantee that GitHub will keep unused storage forever.
