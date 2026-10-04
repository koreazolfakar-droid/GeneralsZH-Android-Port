# Mod safety fixes — 2026-10-04

## Result

Implemented the launcher-side fixes requested after inspecting the existing engine and Mod Manager. The work stays on `dev/mobile-v4` and does not change gameplay, AI, rendering, networking, simulation, native launch arguments, storage permissions, or the native engine.

Installed mod cards now expose a 48 dp delete action. Deletion requires a confirmation containing the real mod name. `ModManager.deleteManagedMod()` accepts only a canonical, non-hidden direct child of the managed `Mods` directory, rejects symbolic-link entries and non-mod files, and walks directories without following links. The active selection is cleared before removing an active mod, returning the launcher to Vanilla even if storage fails partway through. The base installation and Vanilla archives cannot pass the direct-child check.

Imports now have an explicit Cancel import action. Copy, folder traversal, ZIP extraction, and BIG validation check a cooperative cancellation signal. Cancellation occurs before the atomic rename that makes a mod visible and removes the staging entry, so already-installed mods remain unchanged. Once the atomic rename commits, the operation is reported as successful rather than pretending a committed install was cancelled.

The Interface Size screen now shows a warning above 100% that some mods replace `ControlBar.wnd` and should first be tested at 100% when elements overlap. This does not alter `GXUiScale` or game layouts. Tools/Diagnostics checks the real selected game directory for `Audio.big`, `Speech.big`, and `Music.big`; when present it directs a silent-game report to the existing Audio log switch, and when absent it lists the missing filenames. It does not claim that archive presence proves OpenAL output works.

## Verification

- Incremental command: `:app:testDebugUnitTest :app:assembleDebug`
- Final build: success in 26 seconds; 7 tasks executed and 34 up-to-date.
- Tests: 30 passed, 0 failed, 0 errors.
- Coverage added: active/inactive managed deletion, base-file and hidden-staging refusal, symbolic-link refusal where supported, nested directories, confirmation cancellation, cooperative mid-copy import cancellation, staging cleanup, 48 dp delete target, long names, audio archive readiness, and the interface-scale warning.
- APK signature verification, ZIP CRC, and `zipalign -c -p 4` pass.
- Signing certificate SHA-256 remains `644a3b0f8234c6ea8960ece9b55a161c00966b8dd522d2558d84883f4f77c48e`, allowing `adb install -r`.
- All 17 packaged native libraries are byte-identical to the working baseline, including `libmain.so` (30 Hz) and `libmain60.so` (60 Hz).
- All 22 recorded native output/cache hashes and nanosecond modification times are unchanged. All ten runtime assets are unchanged. No native build, clean, CMake/NDK run, dependency rebuild, or cache deletion occurred.

Global lint returns the same 69 baseline errors: 29 SDL permission findings, 38 pre-existing missing translations, one SDL API-level finding, and one SDL receiver-flag finding. The new string-format findings found during implementation were corrected; the final lint report contains no new error category. It also reports 181 warnings, including existing compileSdk/tooling and Java warnings.

## APK

- File: `apk/GeneralsZH-TacticalLauncher-dedup-debug.apk`
- Absolute path: `/workspace/GeneralsZH-Android-Port/apk/GeneralsZH-TacticalLauncher-dedup-debug.apk`
- Size: 73,127,303 bytes
- SHA-256: `bb3e5248c1cfba95e3bfbe2bca893b1bc17256f3347b85733d9fb578bd8da739`

The physical Samsung phone was not reachable from this workspace, so installation, an actual game session, OpenAL output, control-bar rendering, logcat, and FPS remain device-test items. The interface warning and archive check prevent common configuration mistakes and improve evidence collection; they are not presented as a native fix for the photographed overlap or silence without the device logs.
