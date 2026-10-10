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




def compact_visible_commands(occupied, script_only=(), physical_windows=range(1, 13)):
    """Model the source's safe, all-or-nothing high-command promotion."""
    scripts = set(script_only)
    mapping = {slot: slot for slot in range(1, 19)}
    moved = 0
    for source in range(13, 19):
        if source not in occupied or source in scripts:
            continue
        vacant = next((slot for slot in physical_windows
                       if slot in mapping and slot not in occupied and mapping[slot] == slot), None)
        if vacant is None:
            return None
        mapping[vacant] = source
        moved += 1
    return mapping if moved else None




def mobile_transport_layout(commands, has_high_passenger_exit=False, available_windows=range(1, 19)):
    """Model safe sparse transport compaction and dense visible paging.

    Commands uses one-based logical CommandSet slots. Passenger exit slots
    are never eligible to receive promoted high commands or page arrows.
    """
    visible = set(available_windows)
    compact = compact_visible_commands(set(commands), physical_windows=range(1, 13)) \
        if not has_high_passenger_exit else None
    if compact is not None:
        return "compact", {k: v for k, v in compact.items() if k in visible and k <= 12}
    if has_high_passenger_exit:
        return "unchanged-inventory", {}
    arrow = next((slot for slot in range(12, 6, -1)
                  if slot in visible and slot not in commands), None)
    if arrow is None:
        return "unchanged-full-inventory", {}
    return "paged", {"arrow": arrow, "high": list(range(13, 19))}


class MobileCommandOverflowTests(unittest.TestCase):
    def test_stock_and_project_x_guard_available_without_page_arrow(self):
        # From the user-provided Project X CommandSet.ini.
        fixtures = {
            "GenericCommandSet": ({16: "AttackMove", 17: "Guard", 18: "Stop"}, 2),
            "AntiAirGenericCommandSet": ({15: "AttackMove", 16: "GuardFlyingUnitsOnly",
                                          17: "Guard", 18: "Stop"}, 3),
            "GenericGroundAttackCommandSet": ({1: "GroundAttack", 15: "AttackMove",
                                                17: "Guard", 18: "Stop"}, 3),
        }
        for name, (controls, guard_position) in fixtures.items():
            with self.subTest(name=name):
                mapping = compact_visible_commands(controls)
                self.assertIsNotNone(mapping)
                visible = {physical: controls[logical] for physical, logical
                           in mapping.items() if physical <= 12 and logical in controls}
                self.assertEqual(visible[guard_position], "Guard")
                self.assertTrue(set(controls.values()).issubset(set(visible.values())))
                self.assertTrue(1 <= guard_position <= 6)

    def test_full_russian_factories_fall_back_to_verified_3402_page(self):
        # The working 3402 construction menus must NEVER lose a command.
        full_factory = set(range(1, 10)) | {13, 14, 15, 17, 18}
        heavy_factory = set(range(1, 10)) | {12, 13, 14, 15, 16, 17, 18}
        for slots in (full_factory, heavy_factory):
            with self.subTest(slots=sorted(slots)):
                self.assertIsNone(compact_visible_commands(slots))
                self.assertTrue(slots.issubset(set().union(*pages(slots))))

    def test_sparse_high_slot_remapping_is_atomic(self):
        full_first_twelve = set(range(1, 13))
        self.assertIsNone(compact_visible_commands(full_first_twelve | {17, 18}))
        self.assertIsNone(compact_visible_commands({1, 2}))
        self.assertEqual(compact_visible_commands({16, 17, 18}, script_only={16})[1], 17)
        # Commands may occupy a physical window even when the underlying INI slot is empty.
        src = COMMAND.read_text()
        self.assertIn("slotTaken || !win->winIsHidden()", src)
        self.assertIn("compactCommandIndices[ physical ] == physical", src)

    def test_mobile_promotion_preserves_native_action_validation(self):
        src = COMMAND.read_text()
        self.assertIn("commandIndex = compactCommandIndices[ i ];", src)
        self.assertIn("commandButton = commandSet->getCommandButton(commandIndex);", src)
        self.assertIn("!isBuilderCommandSet( commandSet )", src)
        self.assertIn("obj->getContain()->isDisplayedOnControlBar()", src)
        self.assertIn("compactPossible && hasCompactCommands", src)
        self.assertIn("if( !compactCommandBar && !highTransportExit &&", src)
        self.assertIn("m_touchBuilderMoreButton && m_touchBuilderBackButton", src)
        self.assertIn("if( BitIsSet( commandButton->getOptions(), NEED_SPECIAL_POWER_SCIENCE ) )", src)

    def test_transport_fighting_units_show_guard_stop_without_overwriting_seats(self):
        # Real inventories from !!ProjectXRe_INI.big CommandSet.ini.
        samples = {
            "RussianVehicleBMP3CommandSet": (
                {1: "smoke", **{k: "passenger" for k in range(3, 9)},
                 9: "evacuate", 15: "attackmove", 17: "guard", 18: "stop"}, 6),
            "RussianVehicleBMD1CommandSet": (
                {1: "smoke", **{k: "passenger" for k in range(3, 8)},
                 9: "evacuate", 15: "attackmove", 16: "upgrade",
                 17: "guard", 18: "stop"}, 5),
            "RussianVehicleBMD4CommandSet": (
                {1: "smoke", **{k: "passenger" for k in range(3, 8)},
                 9: "evacuate", 15: "attackmove", 16: "upgrade",
                 17: "guard", 18: "stop"}, 5),
            "RussianVehicleHindCommandSet": (
                {**{k: "passenger" for k in range(1, 7)},
                 7: "evacuate", 15: "attackmove", 16: "antiair",
                 17: "guard", 18: "stop"}, 6),
        }
        for name, (commands, seats) in samples.items():
            with self.subTest(name=name):
                mode, layout = mobile_transport_layout(commands)
                self.assertEqual(mode, "compact")
                physical = {dst: commands[src] for dst, src in layout.items() if src in commands}
                self.assertEqual(sum(v == "passenger" for v in physical.values()), seats)
                self.assertIn("guard", physical.values())
                self.assertIn("stop", physical.values())
                self.assertTrue(set(physical).issubset(set(range(1, 13))))

    def test_full_transport_uses_empty_visible_slot_for_page_arrow(self):
        fixtures = {
            "AmericaVehicleHumveeCommandSet":
                dict.fromkeys(range(1, 11), "original") | {15: "attackmove", 17: "guard", 18: "stop"},
            "RussianVehicleHunchbackGoliathUpgradedCommandSet":
                dict.fromkeys(range(1, 11), "passenger-or-action") |
                {15: "attackmove", 16: "thermobaric", 17: "guard", 18: "stop"},
        }
        for name, commands in fixtures.items():
            with self.subTest(name=name):
                mode, layout = mobile_transport_layout(commands)
                self.assertEqual(mode, "paged")
                self.assertIn(layout["arrow"], {11, 12})
                self.assertNotIn(layout["arrow"], commands)
                self.assertIn(17, layout["high"])
                self.assertIn(18, layout["high"])

    def test_never_hide_or_move_high_slot_passenger_inventory(self):
        # Guard/Stop cannot be safely promoted by rewriting the physical
        # inventory windows if the CommandSet itself puts exits after slot 12.
        commands = {3: "passenger", 13: "passenger", 17: "guard", 18: "stop"}
        mode, layout = mobile_transport_layout(commands, has_high_passenger_exit=True)
        self.assertEqual(mode, "unchanged-inventory")
        self.assertEqual(layout, {})

    def test_fully_occupied_inventory_preserves_all_passenger_buttons(self):
        commands = dict.fromkeys(range(1, 13), "passenger") | {18: "stop"}
        mode, layout = mobile_transport_layout(commands)
        self.assertEqual(mode, "unchanged-full-inventory")
        self.assertEqual(layout, {})

    def test_transport_source_safety_guards(self):
        src = COMMAND.read_text()
        self.assertIn("const Bool transportInventory = obj->getContain()", src)
        self.assertIn("candidate->getCommandType() == GUI_COMMAND_EXIT_CONTAINER", src)
        self.assertIn("!isBuilderCommandSet( commandSet ) && !highTransportExit", src)
        self.assertIn("if( !isBuilderCommandSet( commandSet ) && !highTransportExit )", src)
        self.assertIn("Int displacedPageCommand = -1;", src)
        self.assertIn("commandIndex = ( i == 6 ) ? displacedPageCommand : 12 + i;", src)
        self.assertIn("slot = 11; slot >= 7; --slot", src)
        self.assertIn("commandSet->getCommandButton( slot ) == nullptr", src)
        self.assertIn("i == overflowPageWindow", src)
        self.assertIn("m_commandWindows[ overflowPageWindow ]", src)
        self.assertIn("doTransportInventoryUI( obj, commandSet );", src)

    def test_engine_retains_all_18_command_slots(self):
        self.assertRegex(HEADER.read_text(), r"MAX_COMMANDS_PER_SET\s*=\s*18")

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
