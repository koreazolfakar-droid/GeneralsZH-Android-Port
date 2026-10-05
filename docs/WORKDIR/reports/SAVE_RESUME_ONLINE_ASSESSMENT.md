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

## Completed cached Actions build and artifact verification

Native build run [37316733729](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/37316733729)
PASS, source commit 7ab71998932150132c9a5890f312ca858240769d from dev/mobile-v4.
GitHub cache scope required running the existing workflow on its warm
`debug/android-audio-sfx-v1` branch with an explicit mobile source_ref. Only the
workflow was updated on that cache-host branch; engine sources remained on
mobile. All four required caches restored. SDK installation was skipped;
25 vcpkg packages restored from binary archives. Ccache reported 481 hits/482
cacheable calls, but 2133 calls were uncacheable; this is not a claim that every
object was reused. No clean build/cache deletion was performed. Checkout uses
depth 1 to avoid historical APK blobs. Initial run 37316019216 was canceled before
native compilation. Source-level save/localization tests passed on the runner.
The remote TURN deferred-signalling fix is included; device efficacy is unproven.

Original build passed native dependency checks, but artifact comparison found
its optional validation library missing. Logs proved download succeeded into
the fetcher's HOME default while packaging checked the configured staging root.
Pass GX_VULKAN_VALIDATION explicitly; production-shell fixture tests PASS for
selected paths, cached layers and unavailable-layer warnings.

Final [verification/repackaging run 37319710595](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/37319710595)
PASS, without rebuilding either engine. Added the exact baseline validation
library (SHA256 1b8e4bc4701c6f7448bf6028aed4a787fb04e2e2aa8c2ad47265101ccffacc68),
then aligned and signed with the unchanged committed debug key. Every original
non-signature payload, including both engines, is verified byte-identical.
All 17 baseline library names are present. Signature, package identity,
versionCode 10401, ZIP CRC/duplicate entries/16 KiB alignment and AArch64 checks
PASS. Detailed results: SAVE_ONLINE_DEBUG_APK_VERIFICATION.json.

Final artifact: [GeneralsZH-SaveOnline-debug.apk](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/37319710595/artifacts/11349493751)
(download ZIP containing APK). Existing APK/artifacts, local baseline history,
mods, saves, caches and compiled objects were preserved. Cross-branch artifact
cleanup is disabled. Source was published as non-force Git data API commits;
normal Git push authentication and large historical blob upload had failed.
No local Android build or toolchain installation was attempted in this continuation.

NOT TESTED: APK installation on the real device, full battle save/load, old
full saves, in-place update persistence, Vanilla/mod switching, account renewal,
match start/in-game cross-play/desync, touch/graphics/audio/language/settings.
No app uninstall or data clear performed. Install only with:
`adb install -r GeneralsZH-SaveOnline-debug.apk`.
Sidecar mod-save metadata and autosave remain pending; no full save/resume or
online success claim. Further online diagnosis requires a failed-match log.
