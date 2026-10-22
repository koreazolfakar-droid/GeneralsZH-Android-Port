# Universal tactical AI V1

Recovery baseline: signed Engine 3537 / serial 20, source
`a4a17caa25dc0b643d7d08ecaf073ab6783aace5` (PRs 27 and 28).

## Implemented scope

- Offline skirmish: metadata-based selection within the original highest script
  priority and only after existing production conditions, factory/technology,
  instance/queue restrictions, budget and reinforcement checks. Retains the exact
  original synchronized RNG call and range; utility ties retain its chosen team.
- Loaded KindOf, unconditional auto-selected weapons, anti-air masks, explicit
  vehicle target preferences, attack range and engine detector/stealth modules.
  No faction/unit name lists, new units, INI edits, script replacement or cheats.
- Medium aircraft counters; Hard adds vehicle-preference counters, long-range
  support against observed static defense and detectors when identified.
  Counts existing friendly counters to avoid unlimited specialization. A weapon's
  vehicle preference is a mod-author hint, not proof of damage against every armor.
- Existing common-target team hunts can share nearby visible resource, production,
  technology and superweapon structures. Requires at least two armed members and
  a valid engine attack result for each. Explicit attack priorities, aircraft,
  economy teams and existing objectives keep their original behavior. Existing
  hunt, ammo, pathfinding, attack-range and production/rally commands still run.
- Easy retains original behavior. No new difficulty enum or UI.
- Rebuilds bounded local snapshots only on existing team selection/hunt commands:
  1024 scanned objects, 64 cached templates, 128 candidate teams, 16 types per
  team, 32 armed members/objective candidates/modules. Production falls back
  entirely on incomplete snapshots, cache exhaustion or unsupported teams.

## Compatibility and limits

No tactical history persists between calls; no save layout, CRC fields, random
source, network protocol or AI script loader changed. Offline saves reconstruct
the snapshot from loaded state. Existing team target IDs already use the engine's
serialization. The sole transient replay configuration flag is set/reset by
Recorder using the UTD1 suffix in the existing build-time metadata string; binary
replay layout and version matching remain intact. Old/PC and multiplayer replays
do not opt in. Marked offline recordings use the same policy as their live game.
Actual full replay CRC and save roundtrip remain device validation requirements.

This release does **not** implement autonomous flanking, retreat/counterattack
state machines, persistent failure learning, defensive reserve redistribution,
new support/aircraft missions, upgrade choices or special-power targeting.
Existing mod/engine implementations continue to provide those behaviors.
General weapon preference/range hints do not infer unsupported abilities.

## Verification

`test-universal-tactical-ai.py` compiles the actual adapter extracted unchanged
from AIPlayer.cpp with interface doubles, plus its actual production policy
header, using ASan/UBSan and optimized builds. Cases cover unknown templates,
conditional/unsupported weapons, fog/stealth/disguise exclusion, aircraft/vehicle/
defense responses, friendly counter saturation, lost-unit recovery, protected
economy teams, shared useful objectives, attack validation, explicit script
priorities, aircraft fallback, deterministic repeated calls and cache/scan limits.
The fixture does not test the whole BuildAssistant or execute a real game.

Existing Project X script and production BIG/loose archive tests cover Vanilla,
Project X and TEOD synthetic source precedence and mod switching. Synthetic
fixtures cannot establish real mod battle functionality. Engine security and
save parser suites remain mandatory. Android dual-engine compilation, exact
source/dependency identity and signed manifest/payload verification are release
gates, not substitutes for gameplay QA.

Synthetic host timings establish bounded adapter work only. No real-device FPS,
full Engine 3537 CPU/AI/pathfinding comparison or memory profiling is claimed.
No new pathfinding calls or director-owned heap allocations are present; cache
and snapshot storage are local. Full large-battle and replay/save behavior needs
real Android validation with Vanilla, Project X, TEOD and a custom faction.
