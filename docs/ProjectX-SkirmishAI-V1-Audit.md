# Project X Skirmish AI V1 — tactical script integrity baseline

Date: 2026-10-11. Scope: user-provided `Project X remastered.zip` and `!!ProjectXRe_INI(2).big`, audited read-only. This report is **not** a gameplay benchmark and does not assert that every unit/condition is absent from all potentially loaded BIG archives.

## Verified file-level findings

- `Data/Scripts/SkirmishScripts.scb`: 1,235 team dictionaries, 3,018 candidate script entries with valid SCB chunk metadata.
- Relevant team owners: America `SkirmishAmerica` 251; China `SkirmishChina` 257; GLA `SkirmishGLA` 214; Russia mapped to `SkirmishAmericaLaserGeneral` 250; Europe mapped to `SkirmishAmericaSuperWeaponGeneral` 255. There are eight additional neutral/placeholder teams.
- The CkMp script flag inventory includes 404 Hard-only candidate scripts; original Easy/Normal-only teams are expected and must **not** be enabled on Hard just to increase difficulty.
- Invalid/unresolved `teamProductionCondition` references **within this SCB**: America 5, China 10, GLA 6, Russia 1, Europe 0; total 22. Example: Russia Hard Base Expander references `USA Build Base Expander Team`, not found as a script *name* in this SCB.
- Example conditional/behavior mismatches within this SCB: America base-expander scripts; China Big Base Expanders; GLA Hard Base Expander; Europe `ECA Mortar Truck BN Team Follow` on-create hook.
- Object names unresolved in **only the supplied INI BIG**, excluding `<none>` placeholders: America 14 references to `AmericaVehicleChaparral`; GLA 1 to `GLAVehicleDemoTrack`; Russia 10 to `Lazr_AmericaInfantryColonelBurton` and 5 to `RussianInfantryBoris_Machinegun`; Europe 6 to `Lazr_AmericaJetRaptor`, 5 to `EuropeVehicleClaymoreSpecialAI` and 1 to `SupW_AmericaTankAvenger`. Some names may come from Vanilla or other BIG archives; do not delete teams or create fake replacements.

## Source corroboration

- `GeneralsMD/Code/GameEngine/Source/Common/RTS/Team.cpp`: `TeamPrototype::evaluateProductionCondition()` caches an always-false result when its named script cannot be found, thus that team cannot be selected for production by the generic path.
- `GeneralsMD/Code/GameEngine/Source/GameLogic/AI/AIPlayer.cpp`: `selectTeamToBuild()` restricts candidates to the highest currently valid production priority and selects randomly among tied candidates. This is not threat-based tactical unit selection.
- `GeneralsMD/Code/GameEngine/Source/GameLogic/AI/AISkirmishPlayer.cpp`: attack/defense team production delegates to `AIPlayer`; Hard difficulty alone does not repair invalid production conditions.

## Safe follow-up gates (in order)

1. Load all Project X BIGs (including Maps and CloseINI) **in actual resolved archive precedence** and identify the effective AI script and object definitions, not just raw file content.
2. Correlate unresolved production conditions with `TeamPrototype` failure logs and prove which are exercised on Hard skirmish on Android.
3. Fix references in an **optional Project X AI-only overlay** or original mod source, after preserving exact team semantics, action hooks and Hard flags. Do not blindly enable Easy/Normal tactics or substitute units with different balance.
4. Benchmark each faction on Hard on fixed map+seed: time to first attack, completed attack waves, average team size/composition, enemy targets, idle offensive units, resource use and FPS.
5. Verify Vanilla and mod gameplay, 30/60Hz, save/load, Replay/CRC and multiplayer determinism. Do not publish a gameplay-changing engine or mod update without native/device tests.

Tooling: `python3 scripts/qa/audit-projectx-skirmish.py --zip '<user mod zip>' --big '<user INI BIG>' --json report.json`. This script never modifies its input files.
