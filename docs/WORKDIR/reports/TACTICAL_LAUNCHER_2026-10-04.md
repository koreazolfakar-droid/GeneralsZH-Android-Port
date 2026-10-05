# Tactical Android launcher — 2026-10-04

Implemented the approved Home + Mods concept using the existing Java Views and Material Components on `dev/mobile-v4`. The fallback source is `9fea9e619a6b71e1ee5f73900313dc4d91de726d`; its signed APK is preserved at `/workspace/scratch/launcher-design-fallback/GeneralsZH-ModLibrary-debug.apk`. Previous Dropbox uploads remain untouched.

## Result

Home has a tactical hero, actual readiness/active-mod/engine/account values, Play Now with existing launch options, quick access, expandable original game-folder, account, and signed-update controls. Settings retains Interface, Help, and logs. The shared four-tab navigation also reaches Graphics and Tools. Mods has search of cached real installed entries, active-first cards, actual sizes/free space, and the existing Launch, Activate, Import, and Vanilla actions. Long names wrap/ellipsis; small screens use full-width action rows. No fabricated mod metadata, progress percentages, history, or destructive delete operation was introduced.

ModManager, ModImportService, ModLibraryInfo, GeneralsZHActivity, UpdateManager, GeneralsOnlineActivity, UiKit, and the manifest are byte-identical to the fallback source. Native gameplay, AI, graphics, networking, simulation, archive formats, arguments, and permissions were not changed. Home rearranges presentation while retaining the original handlers and integrity checks. Eighteen new launcher strings are present in every supported locale.

Artwork is generated locally for this design, encoded as two 1024×597 WebP drawables; no external battlefield assets were downloaded. Mod cards share decorative artwork rather than pretending to have mod-specific covers. Decoded size is approximately 2.33 MiB per image. Filesystem scans/sizes remain on the existing background executor and search/activation reuse cached entries.

## APK

- Filename: `GeneralsZH-TacticalLauncher-debug.apk`
- Path: `/workspace/GeneralsZH-Android-Port/apk/GeneralsZH-TacticalLauncher-debug.apk`
- Size: 73,100,343 bytes (69.71 MiB)
- SHA-256: `2166b0dccc706dc8734105fabb4787ff37cd42f7154f81ef4b7619afe7d86d4f`
- Package `com.generalsx.zerohour`, version 1.4.0 / 10400, Debug, ARM64, minimum API 28.
- APK signature, ZIP CRC, and `zipalign -c -p 4` pass.
- Signing certificate SHA-256: `644a3b0f8234c6ea8960ece9b55a161c00966b8dd522d2558d84883f4f77c48e`, identical to the fallback for `adb install -r`.

## Build and native preservation

Only the Android app module was built incrementally, using existing Gradle/toolchain caches:

```sh
docker exec generalszh-android-build bash /run/run-mod-library-gradle.sh \
  :app:testDebugUnitTest :app:assembleDebug \
  -DmodUiScreenshot=/opt/launcher-design.png
```

Final build: **SUCCESS**, 36 seconds, 15 tasks executed / 26 up-to-date. No clean task, native build script, CMake configure, dependency rebuild, cache deletion, or CI was invoked. The owner's newer instruction to preserve native outputs supersedes the repository's general dual-Hz rebuild instruction for this cosmetic change.

All **17 packaged native libraries** are byte-identical to the working fallback, including 30 Hz `libmain.so` and 60 Hz `libmain60.so`. All **22 captured native output/cache files** retain their hashes and nanosecond modification times. All **10 runtime assets** are identical. The engine was **not rebuilt**.

## Verification and limits

All **25 JVM/Robolectric Android tests pass**: Home readiness/missing files, access to original settings/folder/account/update controls, navigation, launch rotation intent and persisted selection, Arabic/narrow touch targets, installed library/search/recreation, active switching/Vanilla/reusing mods, picker cancellation, import progress/validation failure, BIG/ZIP malformed archives/traversal, metadata size accounting, empty folders, and long names. Skia native View rendering produced the attached captures; no game engine was executed by these tests.

Compilation and Debug packaging succeed. Global Android lint remains **69 errors / 175 warnings**: 29 SDL permission errors, one SDL API-level error, one SDL receiver-flag error, and 38 pre-existing missing translations. The error groups match the fallback's recorded 69 errors; all 38 translation entries predate this change. New strings are translated in all locales. AGP 8.5.2 warns about compileSdk 35 support; existing deprecated Java APIs also warn. Unrelated SDL/permission changes were intentionally excluded.

Physical phone testing, real game sessions, logcat crash/ANR collection, and FPS measurement were **not performed**: this workspace has no connection to the user's local USB ADB. Source/intent tests cannot establish physical-device stability or performance. Preserve app data and test the updated APK with local `adb install -r`, including the user's large mod, before treating the redesign as device-validated.

Build/lint/verification logs are under ignored `logs/tactical-launcher-*`. Visual review: [QA report](TACTICAL_LAUNCHER_DESIGN_QA_2026-10-04.md).

## Changed files

- `android/app/src/main/java/com/generalsx/zerohour/{SetupActivity,ModManagerActivity,LauncherUi}.java`: presentation and navigation only.
- `android/app/src/main/res/drawable-nodpi/launcher_{battlefield,mods_battlefield}.webp`: local artwork.
- `android/app/src/main/res/values*/strings.xml`: 18 launcher labels in 13 locales.
- `android/app/src/test/java/com/generalsx/zerohour/{LauncherHomeUiTest,ModManagerUiTest}.java`: UI regressions.
- `apk/GeneralsZH-TacticalLauncher-debug.apk`: updated signed Debug artifact, replacing the previous repository APK.
- This report, visual QA/captures/reference, and the October diary.
