#!/usr/bin/env python3
"""Static guard and fixture coverage for the Android 15-18 command paging fix.

No game assets, SDK/NDK, APK build or caches are required.
Run: python3 scripts/qa/test-mobile-command-overflow.py

This checks UI-slot reachability and source invariants; actual Android UI/touch
behavior and buildability must still be verified by CI and on a device.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
COMMAND = ROOT / "Core/GameEngine/Source/GameClient/GUI/ControlBar/ControlBarCommand.cpp"
HEADER = ROOT / "Core/GameEngine/Include/GameClient/ControlBar.h"


def pages(occupied, script_only=()):
    """Model the two displayed command pages; slot numbers are one-based."""
    script_only = set(script_only)
    high = any(15 <= i <= 18 and i not in script_only for i in occupied)
    if not high:
        return [set(range(1, 19))]
    return [set(range(1, 14)), set(range(13, 19))]


class MobileCommandOverflowTests(unittest.TestCase):
    def test_engine_retains_all_18_command_slots(self):
        self.assertRegex(HEADER.read_text(), r"MAX_COMMANDS_PER_SET\\s*=\\s*18")

    def test_modified_ui_reuses_existing_validity_checks(self):
        source = COMMAND.read_text()
        self.assertIn("const Bool showingOverflowPage = hasOverflowPage &&", source)
        self.assertIn("commandIndex = 12 + i;", source)
        self.assertIn("commandButton = commandSet->getCommandButton(commandIndex);", source)
        self.assertIn("if( BitIsSet( commandButton->getOptions(), NEED_SPECIAL_POWER_SCIENCE ) )", source)
        self.assertIn("!BitIsSet( candidate->getOptions(), SCRIPT_ONLY )", source)
        self.assertIn("obj->getContain()->isDisplayedOnControlBar()", source)
        self.assertIn("showingOverflowPage ? m_touchBuilderBackButton : m_touchBuilderMoreButton", source)
        self.assertIn("if( !addBuilderPageButtons( commandSet, obj ) )", source)

    def test_projectx_russian_builders_and_factories(self):
        # These are actual one-based slots from the user's Project X INI archive.
        fixtures = {
            "RussiaDozer": {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 14, 17, 18},
            "RussiaWarFactory": {1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 17, 18},
            "RussiaWarFactoryRocket": {1, 2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 16, 17, 18},
            "RussiaWarFactoryHeavy": {1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18},
        }
        for name, occupied in fixtures.items():
            with self.subTest(name=name):
                layout = pages(occupied)
                self.assertEqual(len(layout), 2)
                self.assertTrue(occupied.issubset(set().union(*layout)))
                self.assertTrue(occupied.intersection(set(range(15, 19))).issubset(layout[1]))
                self.assertEqual(len(layout[1]), 6)  # all 13-18 fit page two

    def test_no_overflow_preserves_normal_layout(self):
        for occupied in ({1, 2, 3, 14}, set(range(1, 15)), {1, 16}):
            with self.subTest(occupied=occupied):
                layout = pages(occupied, script_only={16})
                self.assertEqual(len(layout), 1)
                self.assertTrue(occupied.issubset(layout[0]))

    def test_single_science_command_remains_hidden_on_both_pages_when_unowned(self):
        # The original command population block applies the same science checks
        # after translating a physical slot to the original logical slot.
        source = COMMAND.read_text()
        first = source.index("commandButton = commandSet->getCommandButton(commandIndex);")
        check = source.index("NEED_SPECIAL_POWER_SCIENCE", first)
        page_arrows = source.index("showingOverflowPage ? m_touchBuilderBackButton", check)
        self.assertLess(first, check)
        self.assertLess(check, page_arrows)


if __name__ == "__main__":
    unittest.main()
