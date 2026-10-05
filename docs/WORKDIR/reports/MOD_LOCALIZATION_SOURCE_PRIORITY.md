# Active mod localization source priority

Baseline branch: `dev/mobile-v4`.
Baseline commit: `ea7da71cd39039a5ee44e61e9fe663108e99ba8f`.

## Confirmed cause

The original production `GameTextManager::init()` selected the requested-language
STR before examining the CSF. A valid loose Vanilla `data/english/generals.str`
therefore suppressed an active mod's `Data/English/Generals.csf` inside a BIG.
The legacy fallback CSF was only initialized when CSF was the primary format.
An existing faction label resolved to Vanilla text; a mod-only label was MISSING.

This was reproduced by compiling the unchanged production `GameText.cpp` with
small host filesystem/framework adapters and synthetic STR/CSF data. This proves
the loader defect; it is not a claim that Project X Re or a physical phone was tested.

## Complete loading path

1. `ModManager.getActiveModPath()` resolves the persisted validated managed entry.
2. `GeneralsZHActivity.getArguments()` supplies `-mod <path>` to the chosen native
   engine. The launcher does not translate faction names.
3. `SDL3Main.cpp` exports the marker's `GENERALSX_TEXT_LANGUAGE`. Its text paths
   are `data/%s/generals.str` and `data/%s/generals.csf`.
4. `GameEngine::init()` parses the command line, calls
   `TheArchiveFileSystem->loadMods()`, then creates/initializes `TheGameText`.
5. `ArchiveFileSystem::loadMods()` mounts either the single mod BIG or the BIGs
   under the active directory with overwrite priority. Archived entry names are
   normalized for case and Windows/Unix separators.
6. `GameTextManager::init()` selects, parses and sorts the string lookup table.
7. INI localized-string parsing uses `TheGameText->fetch()`; player-template
   display names ultimately reach the faction selection UI through those strings.

For the SAME virtual path, `FileSystem::openFile()` normally checks a loose file
first, then the archive tree; file instances permit reading the next source.
Mod archive mounting overrides Vanilla archive entries. Game-folder archive order
and the general filesystem resolution rules were not changed.

## Minimal engine fix

Only `Core/GameEngine/Source/GameClient/GameText.cpp` changes runtime behavior.
At initialization, inspect the already-mounted archive owner of each text path.
Ownership is the exact active BIG path or a child archive under the active mod
directory with a separator boundary. A sibling directory prefix does not qualify.
No mod names, faction names or chip/device names are hardcoded.

Selection is:

1. Active mod's requested-language STR, if STR is enabled.
2. Active mod's requested-language CSF.
3. If neither exists, active mod's English STR/CSF in the same order.
4. Otherwise keep the old Vanilla requested-language STR-before-CSF behavior.

The chosen archived text instance skips a loose Vanilla file of the same path.
CSF fallback uses the instance after the selected primary CSF, preserving the
existing lower-priority incomplete-CSF fallback. Both count and parse use the SAME
instance for STR as well as CSF. No class fields/layouts were added or removed.

This intentionally follows a mod's supplied language when it has only English,
rather than substituting faction names from a base translation. It changes text
selection only, not the game's SKU language, assets, INI order or simulation.
STR-only mods retain the pre-existing behavior of having no CSF fallback table.
Mods must actually supply valid localization labels; missing labels are not
invented, and missing/corrupt mod data is not repaired by hardcoded names.

`[GX-TEXT]` logs the selected format, virtual path, file instance, source archive
(or loose file), and whether the table belongs to the active mod. It logs once
per text initialization, not per-frame or per-label.

## Cache / restart findings

The table is in the `GameTextManager` instance, not a persisted launcher cache.
`GameMain()` creates/initializes the engine for a launch and destroys it on exit.
`GameEngine::~GameEngine()` shuts down/deletes its subsystems. The text manager's
`deinit()` releases primary/fallback lookup tables and clears missing-string state.
`SDL3Main.cpp` ends the process with its existing `_exit()` path. A subsequent launch
recreates the table after mounting the persisted active mod.

Changing preferences while an existing game session is still running is not a
hot mod reload. No hot-switch or Android lifecycle behavior was introduced.
The fixture tests additionally exercise deinit/init in one manager to catch stale
labels, and construction of a fresh manager with the mod active.

## Verification

- PASS: unchanged production loader reproduces Vanilla STR masking mod CSF.
- PASS: production loader fixture Vanilla -> Mod -> Vanilla and fresh manager
  with mod active; no stale labels.
- PASS: active archive beats loose Vanilla STR and CSF; correct fallback instance.
- PASS: direct BIG ownership, directory ownership, case/separators/trailing slash,
  and sibling-prefix rejection.
- PASS: active mod without localization retains Vanilla STR priority.
- PASS: requested-language mod table wins; English mod fallback works; UTF-16
  Arabic CSF labels remain correct.
- PASS: mod STR beats mod CSF and loose Vanilla STR; Vanilla CSF-only still loads.
- PASS: host regression suite with AddressSanitizer and UndefinedBehaviorSanitizer.
- PASS: actual Android GameText.cpp compile with existing NDK configuration/PCH.
  Two existing Char/EOF comparison warnings remain; no unrelated parser cleanup.
- NOT RUN: physical-device Vanilla -> Project X Re -> Vanilla, restart, gameplay,
  replay/CRC or audio/render compatibility. Local Windows USB ADB is inaccessible
  from this workspace; no cloud ADB test is substituted for a local-device result.
- Dual-Hz build and APK validation: pending at time of initial report.

Run fixtures: `python3 scripts/qa/test-mod-localization.py`.
The adapters mock mounts/framework types; CSF/STR parsing, init, lookup and
cleanup execute the production source. They do not test the actual Android BIG
mount implementation or real mod assets.

## Build/cache preservation

`GX_INCREMENTAL=1 ./scripts/build/android/build-dual-hz.sh` uses the required
existing dual-Hz script. The minimal optional build-mode guards retain the Gradle
build directory, SDL source intermediate directory and staged JNI libraries.
Normal packaging copies current libraries over retained staged files. No clean,
cache purge, source rewrite, optimization or Mod Manager changes are required.
The stable APK is preserved outside `apk/` before replacing the current test APK.
