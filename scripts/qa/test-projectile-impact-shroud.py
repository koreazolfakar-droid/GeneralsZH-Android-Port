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
        self.assertRegex(body, r"if \(inflictDamage\)\s+revealProjectileImpactShroud\(source, wt\);")
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

    def test_impact_fx_are_shroud_gated(self):
        self.assertIn("getShroudStatusForPlayer(playerIndex, primary) != CELLSHROUD_CLEAR", FX)

    def test_exactly_one_shared_reveal_call_site(self):
        self.assertEqual(len(re.findall(r"revealProjectileImpactShroud\(", WEAPON)), 2)


if __name__ == "__main__":
    unittest.main()
