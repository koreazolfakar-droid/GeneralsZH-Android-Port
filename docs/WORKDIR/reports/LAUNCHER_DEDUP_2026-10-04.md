# Launcher navigation deduplication — 2026-10-04

On `dev/mobile-v4`, removed duplicate Home quick-access buttons for Mods, Graphics, and Tools; each remains in the bottom navigation. Removed the extra active-mod management row (the hero/status still show the actual selection), redundant Mods/Game Data entries from Play Options, and the Settings shortcut to logs (Tools retains its original log action). The single Game Folder row retains all original folder selection/clear actions. Interface and Help stay in Settings; simulation-rate settings remain in Graphics and Play Options. Import/activation/Vanilla and the Mod Manager screen are unchanged. Read-only status summaries are not additional actions.

Only `SetupActivity.java`, `LauncherUi.java`, and `LauncherHomeUiTest.java` changed in source. No backend, manifest, permissions, native source, gameplay, arguments, or stored preferences changed. Removed only duplicate entry points, not any underlying feature. The fallback APK is preserved outside `apk/` at `/workspace/scratch/launcher-dedup-fallback/GeneralsZH-TacticalLauncher-debug.apk`.

Incremental Debug build: **SUCCESS**, 38 seconds, 8 tasks executed / 33 up-to-date. All **26 tests pass**, including single visible navigation entries and original feature routes, active-state rendering, orientation/launch intent, import failures/cancellation, narrow Arabic layouts, long names, and Mod Manager persistence/switching. No clean/native/dependency rebuild or cache deletion. All 17 APK native libraries (including 30/60 Hz engines), ten runtime assets, and 22 recorded native output/cache hashes + timestamps remain unchanged. APK signature, ZIP integrity, and alignment pass. Signing certificate is unchanged for in-place installation. [Actual Home render](LAUNCHER_DEDUP_HOME_2026-10-04.png).

- File: `apk/GeneralsZH-TacticalLauncher-dedup-debug.apk`
- Exact path: `/workspace/GeneralsZH-Android-Port/apk/GeneralsZH-TacticalLauncher-dedup-debug.apk`
- Size: 72803811 bytes
- SHA-256: `9f774974c62dae4e2dd4fb2ec068d6afec67a48427fc9937be8fafcfcaa0e2b8`

Physical USB phone testing/game/FPS/logcat remain unavailable in this workspace. The previous global lint run recorded 69 baseline errors; lint was not rerun for this removal of UI shortcuts. Gradle's compileSdk support/deprecation warnings remain. Build and verification logs are in ignored `logs/launcher-dedup-*`. Dropbox upload was explicitly authorized at `/GeneralsZH-TacticalLauncher-dedup-debug.apk`; previous uploads are preserved.
