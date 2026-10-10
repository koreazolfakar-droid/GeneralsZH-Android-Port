#!/usr/bin/env python3
"""Source-level regression checks for offline projectile impact visibility.

These do not replace Android native compilation or gameplay checks with Project X.
"""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "GeneralsMD/Code/GameEngine/Source/GameLogic/Object"
WEAPON = (GAME / "Weapon.cpp").read_text(encoding="utf-8")
DUMB = (GAME / "Behavior/DumbProjectileBehavior.cpp").read_text(encoding="utf-8")
MISSILE = (GAME / "Update/AIUpdate/MissileAIUpdate.cpp").read_text(encoding="utf-8")
FX = (ROOT / "Core/GameEngine/Source/GameClient/FXList.cpp").read_text(encoding="utf-8")


class ProjectileImpactShroudTests(unittest.TestCase):
    def test_both_ballistic_and_guided_missiles_use_shared_entry_point(self):
        self.assertIn("TheWeaponStore->handleProjectileDetonation(", DUMB)
        self.assertIn("TheWeaponStore->handleProjectileDetonation(", MISSILE)
        self.assertNotIn("revealProjectileImpactShroud(", DUMB)

    def test_reveal_precedes_detonation_effects(self):
        body = WEAPON.split("void WeaponStore::handleProjectileDetonation(", 1)[1]
        body = body.split("void WeaponStore::createAndFireTempWeapon(", 1)[0]
        self.assertRegex(body, r"if \(inflictDamage\)\s+revealProjectileImpactShroud\(source, wt, pos\);")
        self.assertLess(body.index("revealProjectileImpactShroud("), body.index("fireProjectileDetonationWeapon("))

    def test_online_guard_and_alliance_only(self):
        body = WEAPON.split("static void revealProjectileImpactShroud(", 1)[1]
        body = body.split("void WeaponStore::handleProjectileDetonation(", 1)[0]
        self.assertIn("TheGameLogic->isInMultiplayerGame()", body)
        self.assertIn("owner->getRelationship(currentPlayer->getDefaultTeam()) == ALLIES", body)
        self.assertIn("if (impactRadius <= 0.0f)", body)
        self.assertIn("MIN_IMPACT_REVEAL_RADIUS = 40.0f", body)
        self.assertIn("MAX_IMPACT_REVEAL_RADIUS = 180.0f", body)
        self.assertLess(body.index("doShroudReveal("), body.index("queueUndoShroudReveal("))

    def test_actual_impact_position_is_used(self):
        body = WEAPON.split("static void revealProjectileImpactShroud(", 1)[1]
        body = body.split("void WeaponStore::handleProjectileDetonation(", 1)[0]
        self.assertIn("const Coord3D *impactPos", WEAPON)
        self.assertIn("impactPos == nullptr", body)
        self.assertIn("doShroudReveal(impactPos->x, impactPos->y", body)
        self.assertNotIn("projectile->getPosition()", body)

    def test_independent_of_faction_names(self):
        # Guards against accidental one-army-only logic; actual mod QA remains required.
        body = WEAPON.split("static void revealProjectileImpactShroud(", 1)[1]
        body = body.split("void WeaponStore::handleProjectileDetonation(", 1)[0]
        for army in ("Russia", "Europe", "China", "America", "GLA"):
            with self.subTest(army=army):
                self.assertNotIn(army, body)
        self.assertIn("owner->getRelationship(currentPlayer->getDefaultTeam()) == ALLIES", body)

    def test_zero_radius_is_not_free_map_reveal(self):
        body = WEAPON.split("static void revealProjectileImpactShroud(", 1)[1]
        body = body.split("void WeaponStore::handleProjectileDetonation(", 1)[0]
        self.assertIn("if (impactRadius <= 0.0f)", body)
        self.assertIn("return;", body)

    def test_impact_fx_are_shroud_gated(self):
        self.assertIn("getShroudStatusForPlayer(playerIndex, primary) != CELLSHROUD_CLEAR", FX)

    def test_exactly_one_shared_reveal_call_site(self):
        self.assertEqual(len(re.findall(r"revealProjectileImpactShroud\(", WEAPON)), 2)


if __name__ == "__main__":
    unittest.main()
