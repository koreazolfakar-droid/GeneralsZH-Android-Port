# Project X Remastered — impact visibility cross-faction acceptance matrix

**Status:** SOURCE CHECKS PASS; on-device, gameplay, actual mod asset checks NOT RUN.
**Scope:** Project X Remastered and vanilla; 30Hz/60Hz Android engines. Do not merge/publish on source checks alone.

## Engine path inventory (reviewed at this branch)

| Impact mechanism | Current coverage | Notes |
| --- | --- | --- |
| `DumbProjectileBehavior::detonate` | Covered | Ballistic/projectile shells call `WeaponStore::handleProjectileDetonation` |
| `MissileAIUpdate::detonate` | Covered | Guided missiles call the same entry point; `inflictDamage=false` is intentionally excluded |
| `WeaponStore::handleProjectileDetonation` | Covered for single-player damage projectiles with nonzero blast radius | Uses actual passed impact position; reveals before shroud-gated positional FX |
| `NeutronMissileUpdate::detonate` -> `Object::kill` / `NeutronMissileSlowDeathBehavior` | **Not covered by the shared hook** | Special death-module FX and delayed nuclear blasts use a different lifecycle |
| `FireWeaponWhenDeadBehavior` -> `WeaponStore::createAndFireTempWeapon` | **Not covered by shared hook** | Some special projectiles / death weapons; must inspect mod INI and order of FX callbacks |
| Non-projectile ranged weapons / `FXListDie` | **Not guaranteed** | May be fully hidden without extra coverage |
| Blast templates with zero primary/secondary/shockwave radii | Intentionally excluded | Avoid making ordinary bullets reveal new terrain; investigate per mod |
| Missing FX, particles, meshes, textures, `ProjectileDetonationFX` or `ProjectileDetonationOCL` in Project X BIG archives | Not fixable by shroud-only code | Audit the actual mod assets and overlay precedence |

The shared code has no faction-specific branches. This **does not establish that every actual Project X weapon uses one of the covered paths**.

## Project X faction smoke tests — all NOT RUN

Run on a real Android device with the full current Project X mod, after an incremental native rebuild. For every **available** faction and its generals/subfactions, choose at least one long-range cannon, one MLRS/heavy rocket vehicle, and one guided or ballistic missile weapon if that faction has them.

| Faction selection | Long-range cannon | Heavy artillery/MLRS | Guided missile / special weapon |
| --- | --- | --- | --- |
| America + generals | NOT RUN | NOT RUN | NOT RUN |
| China + generals | NOT RUN | NOT RUN | NOT RUN |
| GLA + generals | NOT RUN | NOT RUN | NOT RUN |
| Russia (Project X) | NOT RUN | NOT RUN | NOT RUN |
| Europe (Project X) | NOT RUN | NOT RUN | NOT RUN |
| Other Project X selections, if present | NOT RUN | NOT RUN | NOT RUN |

### Required test steps

1. In **offline skirmish**, start with an unexplored distant enemy area behind the black shroud. Verify mod files mounted properly and the relevant unit & command button are visible.
2. Fire each available long-range weapon at an unseen coordinate, with a scout providing target acquisition only where required. Check shroud clears for the attacking player's alliance **at the actual impact point**, not launch point.
3. Observe initial impact flash, explosion, smoke, particle systems, crater/scorch decals, and actual enemy health/structure destruction. Verify the mark survives the transient reveal and shows when area is scouted later.
4. Ensure the shroud returns after the configured `UnlookPersistDuration`; don't permanently expose enemy bases. Verify enemy artillery does not disclose hidden territory to the local player.
5. Repeat with multiple rockets arriving simultaneously, hits on structures/bridges/ground, target move, scatter, and target disappearing before impact.
6. Test no-damage/jammed/dud/intercepted missiles: no surprise free scouting.
7. Compare Vanilla and Project X, both 30Hz and 60Hz, Android save/resume, frame rate under salvos, and at least one recorded replay.
8. **Multiplayer:** do not expect the new reveal (deliberately disabled to preserve PC parity). Confirm unchanged networking/CRC before any separate online fix.
9. Capture screenshots/videos and engine logs for every missing impact effect. Link exact projectile/weapon INI names, not just faction labels.

### Exit criteria

- No missing blast visuals across all **tested** faction/weapon combinations.
- No unintentional radar reveal, permanent shroud holes, mod loading regressions, crashes, or major FPS regression.
- All newly discovered special projectile/death-weapon paths covered or explicitly documented with a targeted safe fix.
- Successful incremental native builds for the retained 30Hz and 60Hz caches, on-device QA and release verification. **Source QA alone is never a release gate substitute.**
