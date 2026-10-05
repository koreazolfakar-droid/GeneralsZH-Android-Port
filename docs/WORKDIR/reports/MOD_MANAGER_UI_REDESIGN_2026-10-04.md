# Mod Manager UI redesign — 2026-10-04

## Result and scope

The working baseline is commit `c0fbb2b48cb8fb1648b69c969b952760ae8c4252`
on `dev/mobile-v4`. Its APK is preserved at
`/workspace/scratch/mod-manager-ui-fallback/GeneralsZH-ModManager-working.apk`;
the previously uploaded Dropbox APK also remains unchanged.

The app continues to use programmatic Java Views and Material Components.
The reference image guided the dark tactical palette, stacked Generals branding,
compact mod cards, subdued gold active state, and prominent Import Mod / Use
Vanilla controls. The original vector header uses local geometric artwork;
no external images, logos, fonts, or copyrighted battlefield images were added.

The library reads actual entries through the existing `ModManager.listMods()`.
Filesystem discovery, legacy-mod checks, free-space queries, and directory size
accounting run on one activity-owned background executor. Sizes use metadata
rather than reading archive payloads, do not follow symlinks, stop on interruption,
and mark incomplete/inaccessible scans as unavailable. Activation re-renders
cached entry sizes; it does not re-scan each folder. Names wrap to two lines
with ellipsis, content scrolls vertically, and primary actions stay available
at the bottom. No fake mod names, versions, descriptions, history, percentages,
or storage values are supplied by production code.

Activation and Vanilla selection use the existing preference backend. Launch
buttons delegate to SetupActivity's original landscape-rotation gate before
starting GeneralsZHActivity. `-mod` arguments are still constructed exclusively
by the unchanged native-launcher integration. Import pickers, grants, staged
copy, validation, installation, and completion choices use the existing pipeline.
The import surface adds an indeterminate indicator and retains the explicit
message that installed mods are unchanged until validation succeeds.

Delete, search, settings shortcuts, and recent-activity history are omitted from
this iteration. Delete has no safe existing backend, and adding it would expand
this UI-only task into destructive filesystem behavior.

## APK

- File: `apk/GeneralsZH-ModLibrary-debug.apk`
- Absolute path: `/workspace/GeneralsZH-Android-Port/apk/GeneralsZH-ModLibrary-debug.apk`
- Size: 72,765,624 bytes (69.39 MiB)
- SHA-256: `81b2ef71202fa2821409727739fba7de5ec7b37e58306199b3f477834c709a7b`
- Debug, package `com.generalsx.zerohour`, version 1.4.0 / 10400,
  ARM64, minimum Android 9 / API 28.
- APK Signature Scheme v2 verification and `zipalign -c 4` pass.
- Certificate SHA-256:
  `644a3b0f8234c6ea8960ece9b55a161c00966b8dd522d2558d84883f4f77c48e`;
  identical to the working APK, allowing an in-place update that preserves app data.
- ZIP CRC checks pass. No test classes or concept-image example mod names are
  packaged. Test dependencies are JVM-only and do not enter the application.

## Incremental build and preserved native baseline

The existing Docker build environment, Gradle caches, SDK, vcpkg artifacts,
CMake cache, Ninja intermediates, and native outputs were reused. No clean task,
native build script, CMake configuration, dependency rebuild, or cache deletion
was performed. The Gradle command ran only Android module tasks:

```sh
/opt/gradle-8.7/bin/gradle --console=plain --max-workers=3 \
  :app:testDebugUnitTest :app:assembleDebug
```

The final run succeeded in 19 seconds: 5 executed tasks, 36 up-to-date tasks.
`mergeDebugJniLibFolders`, `mergeDebugNativeLibs`, and
`stripDebugDebugSymbols` were all up-to-date. All 17 packaged native libraries,
including both engines, are byte-identical to the device-tested baseline.
All 22 recorded native outputs/cache files retained their original hashes AND
modification timestamps. Runtime assets and `engine_build.txt` are unchanged;
the native source build ID remains 3293 because the engines were reused.
`ModManager.java`, `ModImportService.java`, `GeneralsZHActivity.java`, and
`AndroidManifest.xml` match the baseline byte for byte. No permission or native
launcher arguments changed. One URI-grant expression now passes the explicit
read-only constant after checking the same masked flag; its behavior is identical.

## Validation

All **15** JUnit/Robolectric Android-framework and filesystem tests pass:

- Installed entry detection, empty and missing-root states, no concept-image
  fake entries, active badge/button state, activation, and Activity recreation.
- Switching between installed entries without import; launching a selected mod,
  selecting and launching Vanilla, and selecting a mod again.
- Setup's original orientation guard routes to GeneralsZHActivity only after
  landscape configuration is delivered.
- Import-choice and system-picker cancellation preserve installed files and
  active selection.
- Indeterminate import progress while a controlled input stream is copying;
  failed validation then preserves the existing installed selection and bytes.
- Valid BIG and nested ZIP imports through the unchanged importer, duplicate
  names creating distinct installations, and unchanged live-game files.
- Corrupt BIG and absolute/traversal ZIP paths rejected without damaging an
  installed mod or leaving staged files.
- Nested size accounting, symlink escapes/cycles, unavailable paths,
  interruption, and metadata-only measurement of a sparse 1.8 GB fixture.
- Long names on a 360dp screen, Arabic/RTL controls on a 320dp screen, and
  minimum usable action dimensions.

The [screenshot](MOD_MANAGER_UI_2026-10-04.png) is drawn from the real Android
Views using Robolectric native graphics. It deliberately uses a long-name test
fixture to demonstrate clipping; it is not production mod data or a mock webpage.

| Requested regression | Evidence / remaining device check |
|---|---|
| App launches | Mod Manager and Setup Android Activity tests pass; physical launch still needs testing. |
| Installed mod detected | Real filesystem fixture detection passes. |
| Active mod shown | Card activation state/badge checks and rendered screenshot pass. |
| Restart keeps active mod | Activity destruction/recreation passes; original preference backend unchanged. Full process restart remains a device check. |
| Existing mod launches | Selection plus the existing Setup → GeneralsZHActivity intent/rotation route verified; actual game execution remains a device check. |
| Vanilla launches | Selection cleared and launch route verified; actual game execution remains a device check. |
| Vanilla → installed mod without import | Passes with the same installed files and entry count. |
| Import still works | BIG/ZIP integration tests pass; folder SAF pipeline unchanged. Real large-file/folder import remains a device check. |
| Validation failure preserves mods | Corrupt BIG, unsafe ZIP and UI failure tests pass. |
| Cancellation preserves mods | Choice/picker cancellation passes. In-flight import remains non-cancellable, as before. |
| No native/base files changed | Native and asset byte comparison passes; importer live-root preservation tests pass. |
| Storage permissions | Manifest unchanged; picker/grant flow retained. Physical permission prompts remain a device check. |
| Empty Mods directory | Passes. |
| Long names | 220-character name layout passes with two-line ellipsis. |
| No fake mod data | Production DEX checks and empty-library test pass. |

The owner offered phone testing over ADB. Explicit `adb devices -l` checks on
both the workspace host and build container returned an empty device list;
no USB device bus is exposed here. A wireless debugging endpoint was requested.
No emulator is connected, and `/dev/kvm` is unavailable.
The actual native game, device process restart, and real SAF folder/large-import
flows were not claimed as rerun here. The owner's previously confirmed device
baseline is preserved by unchanged native, import, state, and permission code.

## Diagnostics

The first UI compile found a duplicate local variable name in the progress
surface; it was corrected and the incremental build rerun. A test fixture used
the wrong static/instance Robolectric API; that test setup was corrected and all
tests rerun successfully. These were development-time errors, not retained bugs.

Full `:app:lintDebug` was run. It still exits unsuccessfully with **69 existing
errors**: {'MissingPermission': 29, 'NewApi': 1, 'UnspecifiedRegisterReceiverFlag': 1, 'MissingTranslation': 38}. All are in unchanged staged SDL Java or
pre-existing Mod Manager translation keys. None is in the new UI/helper/header
or launch bridge. New UI strings were supplied for all 13 resource locales.
No baseline was generated, no errors suppressed, and no new permissions added
just to make global lint green. AGP 8.5.2 also retains its existing compileSdk-35
compatibility warning; Java reports deprecated APIs.

Logs and verification JSON are retained under ignored `logs/`.

## Changed files

- `android/app/src/main/java/com/generalsx/zerohour/ModManagerActivity.java`
- `android/app/src/main/java/com/generalsx/zerohour/ModLibraryInfo.java` (new read-only helper)
- `android/app/src/main/java/com/generalsx/zerohour/SetupActivity.java` (six-line launch bridge)
- `android/app/src/main/res/drawable/mods_tactical_header.xml` (new vector)
- `android/app/src/main/res/values/strings.xml` and all 12 `values-*/strings.xml` locales
- `android/app/build.gradle` (unit-test-only configuration/dependencies)
- Three new tests under `android/app/src/test/java/com/generalsx/zerohour/`
- Monthly diary, this report, rendered screenshot, and current APK replacement
