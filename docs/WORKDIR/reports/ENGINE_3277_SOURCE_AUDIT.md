# Engine 3277 source audit and integration — 05 October 2026

SOURCE AUDIT AND INTEGRATION ONLY. BUILD: **NOT RUN — waiting for incremental build environment**.
No Android/native engine compilation, workflow dispatch, SDK/NDK installation,
dependency reinstall, cache deletion, APK replacement or device installation in
this phase. Small host C++ test fixtures were compiled; they are not engine builds.

## Repository and preserved starting state

- Repository: https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port
- GitHub repository ID: 1398373925 (API verified).
- Branch: `dev/mobile-v4` (already checked out; no reset).
- Expected and freshly verified remote HEAD: `8f234a7dece74f4a682044e08c94f969e7efca98`.
- Actual local START HEAD: `a20f54728616ed3de69e4f25ab6e5092bbec01b2`.
- Local history was already merged and ahead of the remote. Its source tree
  matches the expected remote; the retained APK artifact path differs. Preserved
  this history, the APK and all prior custom source changes. No remote advancement.
- Audited integration HEAD before this report-only commit:
  `b02a30b1116b88fcd89fb0d58254f2122e96449c`.
- Commits here are local. No push or Actions build was triggered. The final
  report commit/HEAD is supplied in the handoff, avoiding self-referential hashes.

## Upstream engine and manifest verification

Upstream: https://github.com/MYSOREZ/GeneralsZH-Android-Port, repository ID
1291365944 (API verified). Added `upstream` and fetched main, updates, the relevant
diagnostics source branch and release tags with blob filtering. No build outputs
were created or removed. Namespaced release tags preserve existing tag names.

- `upstream/main`: `576e2265bf271176028d1cef4f2b3fe8caa20b34`, release v1.4.0.
- `upstream/updates`: `43a023538d399474278889af304e068831e8fb9d`.
- Inspected newer diagnostics source:
  `aa91ac6e928d71a6867dc94df1b426f5bdb777e9`; not merged wholesale.
- Official URL:
  https://raw.githubusercontent.com/MYSOREZ/GeneralsZH-Android-Port/updates/manifest.json
  (`manifest.json` in branch `updates`, not an `updates/` directory in that branch).
- Independently fetched contents agree with Git; a live raw-URL comparison also
  agrees. ECDSA P-256/SHA-256 signature verifies using the existing updater key.
- Schema 1, serial **12**, published 2026-10-04, engine sequence **3277**.
- Manifest SHA-256:
  `257d7527126e9aa6771917859032266c0c0461d18d31c7af700cadf80875b1cf`.
- Advertised 30 Hz engine SHA-256:
  `e597d248ae7264f983561d75dd5bfa6d23b495efff535387a72739bc61390286`.
- Advertised 60 Hz engine SHA-256:
  `db5fbdad1053e5f22b4332e593460727fb10f73a4b0ad78bf96167237ca090fa`.

These engine hashes are signed manifest values, NOT independent binary download
or reproduction verification. No replacement engine binaries were installed.

## Exact source identification and limitation

Upstream diary commit `7f679883314f79c9a302160e1c46e23e816b4f94` explicitly
documents engine 3277 as release `576e2265b` plus **only** the GPU-timer opt-in.
The original hotfix is described as local commit `2cc428d1b` on
`hotfix-1.4.0-gputimer`. It is not advertised by the remote; fetch and the commit
API cannot resolve it. Its full SHA and build tree cannot be independently certified.

The equivalent GPU delta is publicly available at
`5eb288be6119325b430c074a9bb851723a7876bc`. Applied only that file delta to
our release-derived source. Applying the same delta to the release in a temporary
audit directory produces a GPU file with the **same Git blob** as our integrated
file. This verifies the documented source reconstruction, not unpublished commit
identity or byte-for-byte engine binary equivalence.

Serial 12 says **engine 3277 unchanged**: its additional fix is STUN/TURN config
ordering. Published source equivalent:
`c8550a4038e15ee8217d23e148fe1ad53fd6a194`. Integrated its fallback/config
ordering, not the rest of the later diagnostics branch. Later base-Generals,
four-engine, rendering-ring and simulation changes are outside this integration.

## Files different from the documented Engine 3277 tree

The complete path/status/Git-blob inventory is
[ENGINE_3277_SOURCE_INVENTORY.json](ENGINE_3277_SOURCE_INVENTORY.json).
It compares committed integration HEAD `b02a30b11` with the reconstructed release
plus GPU hotfix: **91 paths**, including existing Android assets, APK artifact
differences, tests and documentation. This report, inventory and audit script
are subsequent audit-only additions, not missing engine integrations.

The GPU implementation now matches that baseline. Remaining native source
differences are deliberately retained custom work:

| File | Our retained difference / overlap handling |
| --- | --- |
| `Core/GameEngine/Source/GameClient/GameText.cpp` | Active mod text precedence, ownership, English fallback and empty-table fallback; unchanged this phase. |
| `Core/GameEngine/Include/Common/ModLocalization.h` | Prior alternative resolver retained, not substituted for the working initializer. |
| `GeneralsMD/Code/GameEngine/Source/Common/System/SaveGame/GameStateMap.cpp` | Version-1/2 load alignment and scratch-map cleanup failure guards; unchanged this phase. |
| `GeneralsMD/Code/GameEngine/Include/GameNetwork/GeneralsOnline/NetworkMesh.h` | Prior TURN-wait state removal retained. |
| `GeneralsMD/Code/GameEngine/Source/GameNetwork/GeneralsOnline/NetworkMesh.cpp` | Preserve prior removal of the five-second credential fallback; add only signed-manifest server ordering. |

The Android Mod Manager/importer, preference persistence, launcher/UI, thirteen
locale resources, branding, previous verification reports and test sources are
custom differences to retain, not defects to erase to match upstream. Historical
APK/icon deletions in the inventory predate START HEAD; **nothing was deleted in
this phase**. No textual conflicts occurred: applied narrow verified hunks, not a
whole-branch merge. Overlapping NetworkMesh customization remains intact.

## Save/resume audit

Current save directory:

`/storage/emulated/<userId>/Generals/Command and Conquer Generals Zero Hour Data/Save/`

SDL3Main sets `GENERALSX_USERDATA_DIR` to the shared persistent user-data root;
`GameState::getSaveDirectory()` appends `Save/`. Existing `GameState`, `XferSave`,
`XferLoad` and registered snapshots remain in use. Snapshot blocks cover campaign,
map, terrain logic/visuals, teams, players, game logic, radar, scripts, sides,
tactical view, game client/UI, partition, particles and ghosts. Normal battle
saves use snapshots; mission-progress saves are not the same as full battle saves.
Exact restoration of every supported object/AI/resource field needs real-save QA.

Header and map snapshot current versions remain 2. No field ordering, versions,
RNG, object logic or snapshot structures changed. The already-present map fix
checks the **file** version when loading gameMode: v1 must not consume a v2 field.
Its host alignment and four cleanup-failure/normal cases pass. No duplicate import
of a similar later upstream save fix is needed.

APK engine-update extraction/pruning targets private update-engine storage, not
the shared user-data root. Existing `Save/`, `Maps/`, `Options.ini` and user files
are not moved into APK assets or subjected to new cleanup. Existing uninstall-
surviving storage markers and selected game/mod paths remain unchanged.

Remaining gaps, **not implemented or claimed solved**:

- `XferSave` opens the final target with `w+b`; interruption can truncate an
  overwritten save. `fclose` failure is not propagated. Atomic write/replace and
  late-write error handling need a separately tested change using the same format.
- No explicit active-mod identity is in the save header. Snapshot map/player
  contents are not a reliable mod identity. No mod-safe sidecar/warning was added.
  Smallest follow-up: optional versioned sidecar with mod ID and content identity,
  written only after a successful save; pre-load mismatch warning, and an explicit
  unknown-compatibility warning for legacy saves without metadata. Never silently
  classify missing metadata as Vanilla or copy/import mod archives into saves.
- Rotating autosaves are pending manual save/load and update-persistence device
  verification. Any later request must run at an existing safe engine point,
  use successful temporary-write promotion and preserve earlier slots. No UI-thread
  snapshot calls or multiplayer autosave/resume are introduced here.

## Online flow and evidenced failure points

Preserved existing flow:

`GeneralsOnlineActivity / GeneralsOnlineSession -> launch refresh -> AndroidGlue
-> native NGMP auth/WebSocket -> LobbyInterface host/join -> NetworkMesh /
NextGenTransport / GameNetworkingSockets ICE and UDP -> match / disconnect`

Launcher session/refresh tokens and native rotated-token persistence already
exist. HTTPRequest's default timeout is 5000 ms; the existing join callback owns
response processing and releases the credential wait. The mesh is created before
the HTTP response to receive early signalling. Our existing wait fix prevents an
independent five-second fallback from initiating peers before credentials arrive.
Create/join credential application remains intact. No token logging was added.

The user's supplied excerpt ends with code 0 and does not show a failing peer,
disconnect reason or desync. It cannot identify their exact match-start/in-game
failure. The verified **upstream** issue #37 is nevertheless actionable: the ICE
server walk tried dead port 53 first, costing about 5.3 seconds per server; relay
availability could arrive after the 10-second connect timeout (5008).

Signed serial 12 now requests:

- STUN: GeneralsOnline 3478, Google 19302, GeneralsOnline 53.
- TURN: GeneralsOnline 3478, GeneralsOnline 53.

Bundled `update/config.json` and compiled fallback now agree with these settings.
Only fallback/server selection changed. No packet formats, network command order,
tick semantics, simulation rules, movement, weapons, RNG or deterministic GameLogic
source changed. This is not proof that port ordering solves every user disconnect.

Further investigation needs a complete failed-match log covering ICE status,
relay candidate timing, peer failure code and match transition. Existing lobby
exe/INI CRC comparison, PC CRC override 560676586, logic revision 0, community
patch configuration, LAN separation and 30/60 Hz choice were preserved. No CRC
bypass, forged mismatch result or silent game-data modification was added.

Active mods can still cause incompatible data checksums. A dedicated preflight
warning/guard and runtime Android-PC acceptance remain pending. Existing background,
disconnect/retry and token-renewal code was inspected, not replaced or claimed tested.
No per-frame logging was added.

## Engine Build=1 root cause and fix

The prior workflow intentionally fetched depth 1 to avoid historical APK blobs.
The packager used `git rev-list --count HEAD`, so this checkout yielded **1**;
Git failures could also silently yield zero. The updater compares remote sequence
against that bundled value: official 3277 could supersede a newer customized fork
engine, losing native custom fixes when dependency hashes matched.

Changed build checkout to `fetch-depth: 0` plus `filter: blob:none`: complete
commit graph without downloading historical APK blobs. Added a shared resolver
that rejects shallow/invalid history and emits the actual positive commit count.
Packaging resolves it **before staging** and no longer substitutes zero. The
workflow logs the source SHA and resolved sequence. No constant 3277 is used in
production number generation, and no old APK/asset was edited to pretend a rebuild.

The two implementation commits' HEAD count is 3326; the audit commit increases
it. The eventual workflow derives its own actual source count at packaging time.
Fork counts are monotonic within preserved ancestry, **not** upstream binary
identities. The updater's broader future cross-fork feature-compatibility policy
remains a risk: a later larger official sequence may again offer an engine without
fork customizations. Its trust/selection architecture was not redesigned here.

## Changes and commits

1. `ec641ffead12b5b017ab5fba850a46a5bd2958dc` — GPU timer opt-in,
   STUN/TURN fallback + bundled config, host regression test and diary.
2. `b02a30b1116b88fcd89fb0d58254f2122e96449c` — full filtered Git graph,
   sequence resolver, package integration, host tests, script index and diary.
3. Subsequent audit-only commit — this report, JSON inventory, reproducible
   signature/source audit script, script index and diary. No runtime changes.

Files changed this phase (distinct from all pre-existing inventory differences):

- `Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp`
- `GeneralsMD/Code/GameEngine/Source/GameNetwork/GeneralsOnline/NetworkMesh.cpp`
- `update/config.json`
- `.github/workflows/build-android.yml`
- `scripts/build/android/package-android-zh.sh`
- `scripts/build/android/engine-build-number.sh` (new)
- `scripts/qa/test-engine-3277-hotfix.py` (new)
- `scripts/qa/test-engine-build-number.py` (new)
- `scripts/qa/audit-engine-3277.py` (new)
- `scripts/README.md`
- `docs/DEV_BLOG/2026-10-DIARY.md`
- `docs/WORKDIR/reports/ENGINE_3277_SOURCE_AUDIT.md` (new)
- `docs/WORKDIR/reports/ENGINE_3277_SOURCE_INVENTORY.json` (new)

## Verification results

PASS:

- Official manifest live/Git agreement and signature verification.
- Reconstructed release+hotfix GPU blob matches integrated source exactly.
- Bundled config matches every signed manifest config field.
- GPU host initialization: default off, opt-in, missing extension, missing procs.
- STUN/TURN compiled fallback/config ordering and retained wait-fix source guard.
- Build resolver: full graph, depth-one reproduction/rejection, fetched-history
  recovery, invalid repository; paths with spaces.
- Existing save-map directory failure/normal cleanup and v1/v2 stream alignment.
- Current production GameText fixture regression suite with ASan/UBSan.
- Existing Android validation-library staging tests.
- Workflow YAML parsing, all 27 run-block bash syntax checks, packager/resolver
  bash syntax and `git diff --check`.

FAIL (pre-existing, diagnosed):

`scripts/qa/smoke/test-mod-localization.py` cannot compile its extracted fixture:
it omits `gxActiveModTextInstance` and `gxLogTextSource` and its AsciiString double
lacks `compareNoCase`. Both that harness and GameText match START HEAD exactly.
This older alternative harness was retained and its failure is explicit. The
workflow uses the passing current `scripts/qa/test-mod-localization.py`; no
working loader was altered to satisfy stale expectations.

NOT TESTED:

Android Java/Robolectric tests (Android environment unavailable); native Android
compilation/linkage; actual Mali GPU behavior; Vanilla launch/campaign/skirmish;
real battle saves/loads and historical saves; restart/in-place update persistence;
installed mods/active preference/switching on device; online account/token refresh,
lobby/host/join/match/disconnect and Android-PC desync acceptance; touch, graphics,
audio, settings, languages and game/user-folder acceptance on device.

## Next incremental build and device regression gate

Only the build phase is blocked. When the existing environment/cache scope is
available, use `.github/workflows/build-android.yml` with this mobile source ref,
unchanged SDK/NDK 27.2.12479018, Gradle 8.9, vcpkg/DXVK/ccache/Gradle caches and
existing dual-Hz incremental path. No clean task, cache-key churn or dependency
reinstall was introduced. Expected native source impact is two translation units
for both engine rates, then relink and APK packaging. Existing workflow compiler
caches do not guarantee persistent CMake objects across GitHub runners; report
cache misses honestly rather than promising no compilation of unrelated objects.

After verified APK production, install only `adb install -r <apk>` with unchanged
identity/signature. Never uninstall or clear app data. Acceptance sequence:

1. Vanilla campaign and skirmish launch; all existing saves remain listed.
2. Save a recognizable battle (map, units/health/positions, buildings, money,
   upgrades, teams, AI/scripts/radar), close/reopen and load the same state.
3. In-place update, reopen and load that same save again; include older APK saves.
4. Existing mods remain installed and remembered; mod launch, Vanilla switch and
   switch back without re-import; language and mod faction labels remain correct.
5. Login/token renewal, lobby, host/join, match start and an Android-PC match;
   compare checksums/desync and exercise relay/block-53 and disconnect conditions.
6. Check touch/backends/audio/settings/language, custom maps, Options.ini and
   user-created files. Any failure blocks expanding scope until diagnosed.

BUILD: **NOT RUN — waiting for incremental build environment**.
