# Save/resume and online assessment — 05 October 2026

Branch: `dev/mobile-v4`. Baseline APK and build outputs preserved.

## Existing save architecture

Android SDL3Main sets GENERALSX_USERDATA_DIR to shared storage under
`/storage/emulated/<userId>/Generals/Command and Conquer Generals Zero Hour Data/`.
GameState::getSaveDirectory appends `Save/`. The existing GameState,
XferSave/XferLoad and snapshot block registry are retained. Blocks include map,
terrain logic, teams, players, game logic, radar, scripts, sides, client/UI,
partition, particles, terrain visuals and ghosts. Individual object snapshots
need further compatibility review before any field changes. GameState header
version is 2; version 1 handling exists. No serialized fields, ordering or version changes made.
Mission saves start a mission; normal saves serialize battle snapshots.
XferSave opens the destination with w+b and does not check fclose failure.
Atomic replacement and late-write error handling need a separate verified step.
The header does not identify the active mod; remaining blocks must be reviewed
before adding optional sidecar metadata. Legacy saves must not be silently
classified as compatible using absent metadata.

## First verified fix

GameStateMap::clearScratchPadMaps previously ignored directory lookup/change
failure and returned from failed enumeration without restoring the directory.
It could enumerate/delete .map files in the original working directory when
Save was inaccessible. Guard lookup and directory change; restore cwd on failed
enumeration. Existing normal cleanup behavior remains. Snapshot format unchanged.

Further review found GameStateMap::xfer loading tested currentVersion >= 2
instead of the file version. A version-1 stream has no gameMode field; the old
condition consumed the next map-data word as that field. The load-only condition
now tests version >= 2. Saving remains version 2 with identical field ordering.
The test executes the extracted production conditional for versions 1/2 and
checks cursor alignment and mode assignment. Full historical saves remain
NOT TESTED; this is not a claim of complete old-save compatibility.

Host test compiled the actual extracted production function against filesystem
API doubles: normal cleanup, failed cwd query, inaccessible Save, failed
FindFirstFile. All four PASS; no deletion on failure, cwd preserved. This is not
an Android filesystem or battle save/load test.

## Online architecture and investigation boundaries

GeneralsOnlineActivity / GeneralsOnlineSession store account credentials and
refresh a session at launch. Native AndroidGlue reads the marker, supplies the
external session, and renews expired tokens before WebSocket connect. Native NGMP
services handle lobby/host/join, with NetworkMesh and NextGenTransport handling
peer connectivity and UDP. Lobby join already logs local and host executable/INI
CRCs. Native renewal and rotated-token persistence already exist.

Possible investigation points, not diagnosed causes: launcher/native refresh
coordination, WebSocket authorization, lobby CRC mismatch, mesh/relay and UDP,
background/disconnect handling. No online failure log for the current task was
provided. No network fix or deterministic simulation edit is justified yet.
UpdateManager prunes its private engineRoot, not the shared user-data directory.
Full cleanup/path audit remains pending; do not interpret this as universal proof.

## Build blocker

Attempt: GX_INCREMENTAL=1 with the existing dual-Hz build wrapper.
Stopped before compilation: sudo missing. Cached CMake references /opt/android-sdk
and /opt/vcpkg; these paths are unavailable. cmake and ninja are also unavailable.
Existing toolchain files under workspace/scratch are preserved. No dependencies
reinstalled, caches deleted, app uninstalled or data cleared. No new APK produced.
Build log: /workspace/scratch/save-resume-incremental.log.
The user subsequently instructed no local builds and designated the existing
GitHub Actions workflow as the build environment. No more local Android builds
will be attempted. Workflow retains SDK/vcpkg/DXVK/ccache/Gradle cache mechanisms,
enables incremental staging, and builds both 60/30 Hz engines from the same
checkout. Existing workflow previously built only one engine. Symbols for both
are collected before stripping, and APK validation requires both libraries.
No clean task or cache/output deletion was introduced. Warm ccache provides
compile reuse; engine CMake objects are not persisted between GitHub runners by
the existing workflow, so this is compiler-cache reuse, not proof that every
object survives across jobs. Cache misses may require compilation. Workflow
YAML and shell syntax PASS; Actions execution NOT TESTED. No dispatch or push.

## Next verified steps

1. Run the existing build-android.yml on this branch using its retained caches.
2. Compile this one change for both engines, package incrementally.
3. Verify manual save/load and old save visibility on device before further work.
4. Review serialization widths/versions and mod metadata; implement only proven gaps.
5. After manual compatibility passes, consider rotating single-player autosaves
   dispatched at an existing safe engine point; never Android UI or multiplayer.
6. Obtain current online failure logs and trace the failing stage before edits.

## Regression status

NOT TESTED: Android compilation; Vanilla campaign/skirmish; real battle save/load;
old saves; restart persistence; in-place APK update persistence; mod installation,
active persistence and switching; authentication/token renewal/lobby/host/join;
Android-PC match and desync; graphics/touch/audio/settings/language/game folder.
Host filesystem control-flow and map-version field-alignment tests PASS:
`python3 scripts/qa/test-save-map-safety.py`. Existing production GameText
localization fixtures with ASan/UBSan PASS. Workflow YAML/run-block bash syntax
PASS. git diff --check PASS. Android Java/Gradle tests NOT TESTED (no local Android
build environment); these results do not replace device regressions.

## Online follow-up from the user

Failure occurs at match start or during gameplay. Focus next on match transition,
peer connectivity/relay/UDP, disconnect reasons and deterministic checksum
comparison. Existing transport packet CRC logs are different from simulation
CRC/desync. A zipped complete log of one failed match is needed to distinguish
these; no speculative online fixes or per-frame diagnostics added.

## Installation gate

After the Actions APK is produced and verified, install only with
`adb install -r <apk>`. Never uninstall or clear app data. Save/load the same
battle before/after update and check mod and settings persistence. Autosave and
sidecar metadata are pending, not implemented in this step.
No success claim for save/resume or online play.
