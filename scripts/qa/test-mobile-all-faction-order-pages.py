#!/usr/bin/env python3
"""Android Guard/Stop/Attack Move accessibility on real Project X faction slot fixtures.

Fixtures are slot/type metadata from a user-provided mod BIG (not original content).
Covers compact, visible More/Back, displaced command and passenger-seat protection.
This is static model coverage; device/graphics performance still needs on-phone testing.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
SOURCE=(ROOT/"Core/GameEngine/Source/GameClient/GUI/ControlBar/ControlBarCommand.cpp").read_text()
MULTI=(ROOT/"Core/GameEngine/Source/GameClient/GUI/ControlBar/ControlBarMultiSelect.cpp").read_text()


def layout(occupied, passenger=(), builder=False):
    occupied=set(occupied)
    passenger=set(passenger)
    high={n for n in occupied if n>=13}
    free=[i for i in range(1,13) if i not in occupied]
    if not high:
        return {"mode":"normal", "visible":set(occupied), "seats":passenger}
    if not builder and not any(i>=13 for i in passenger) and len(free)>=len(high):
        return {"mode":"compact", "visible":set(occupied), "seats":passenger}
    if builder:
        return {"mode":"original-builder", "visible":set(occupied), "seats":passenger}
    if any(i>=13 for i in passenger):
        return {"mode":"high-passenger-fallback", "visible":set(occupied), "seats":passenger}
    free_page=next((slot for slot in range(12,7,-1) if slot not in occupied),None)
    displaced=None
    if free_page is None:
        displaced=next((slot for slot in range(12,7,-1) if slot in occupied and slot not in passenger),None)
        free_page=displaced
    if free_page is None:
        return {"mode":"unsafe-to-page", "visible":set(range(1,13)), "seats":passenger}
    return {"mode":"visible-page", "arrow":free_page,"displaced":displaced,
            "page2":high|({displaced} if displaced else set()), "seats":passenger}


class AllFactionsCommandBarTests(unittest.TestCase):
    def test_compact_commands_for_generic_troops_and_five_armies(self):
        fixtures={
            "Generic infantry": {15,17,18},
            "America standard infantry": {1,2,15,17,18},
            "China standard tank": {1,2,3,15,17,18},
            "GLA technical": {1,2,3,15,17,18},
            "Russia BMP3": {1,3,4,5,6,7,8,9,15,17,18},
            "Europe Fennek (sparse variant)": {1,3,4,5,6,7,8,15,17,18},
        }
        for name,commands in fixtures.items():
            with self.subTest(name=name):
                result=layout(commands)
                self.assertEqual(result["mode"],"compact")
                self.assertTrue({15,17,18}.issubset(result["visible"]))

    def test_all_faction_full_menu_requires_visible_arrow(self):
        fixtures={
            "America Humvee": ({*range(1,11),15,17,18}, set(range(3,8))),
            "China troop crawler": ({*range(1,10),14,15,16,17,18},set(range(1,9))),
            "GLA upgraded technical": ({*range(1,11),15,17,18},set(range(3,8))),
            "Russia upgraded Hunchback": ({*range(1,11),15,16,17,18},set(range(1,9))),
            "Europe Fennek dense": ({*range(1,11),15,17,18},set(range(1,6))),
        }
        for name,(commands,passengers) in fixtures.items():
            with self.subTest(name=name):
                result=layout(commands,passengers)
                self.assertEqual(result["mode"],"visible-page")
                self.assertIn(result["arrow"],range(8,13))
                self.assertEqual(result["seats"],passengers)
                self.assertTrue({17,18}.issubset(result["page2"]))
                if result["displaced"] is not None:
                    self.assertIn(result["displaced"],result["page2"])

    def test_fully_occupied_vehicle_can_keep_twelve_original_actions(self):
        result=layout(set(range(1,13))|{18})
        self.assertEqual(result["mode"],"visible-page")
        self.assertIn(result["displaced"],result["page2"])
        self.assertEqual(len(result["page2"]),2)

    def test_never_overwrite_twelve_passenger_exit_buttons(self):
        result=layout(set(range(1,13))|{17,18},set(range(1,13)))
        self.assertEqual(result["mode"],"unsafe-to-page")
        self.assertEqual(len(result["seats"]),12)
        self.assertNotIn("displaced",result)

    def test_builder_palettes_preserve_3411_construction(self):
        result=layout(set(range(1,13))|{13,14,15,16,17,18},builder=True)
        self.assertEqual(result["mode"],"original-builder")

    def test_safe_promotion_and_paging_are_mobile_only(self):
        self.assertIn("if( !isBuilderCommandSet( commandSet ) && !highTransportExit )",SOURCE)
        self.assertIn("oldButton->getCommandType() != GUI_COMMAND_EXIT_CONTAINER",SOURCE)
        self.assertIn("commandIndex = ( i == 6 ) ? displacedPageCommand : 12 + i;",SOURCE)
        self.assertIn("if( displacedPageCommand < 0 && m_touchWaypointButton",SOURCE)
        self.assertIn("commandButton = commandSet->getCommandButton(commandIndex);",SOURCE)
        self.assertIn("doTransportInventoryUI( obj, commandSet );",SOURCE)
        self.assertIn("showingOverflowPage ? m_touchBuilderBackButton : m_touchBuilderMoreButton",SOURCE)

    def test_multiselect_cross_faction_scans_command_types_in_all_slots(self):
        for code in ["GUI_COMMAND_GUARD","GUI_COMMAND_STOP","GUI_COMMAND_ATTACK_MOVE",
                     "GUI_COMMAND_GUARD_WITHOUT_PURSUIT","GUI_COMMAND_GUARD_FLYING_UNITS_ONLY"]:
            self.assertIn(code,MULTI)
        self.assertIn("for( Int slot = 0; slot < MAX_COMMANDS_PER_SET; ++slot )",MULTI)
        self.assertIn("common && common != found",MULTI)
        self.assertIn("BitIsSet( candidate->getOptions(), OK_FOR_MULTI_SELECT )",MULTI)
        self.assertIn("m_commonCommands[ freeSlot ] = common;",MULTI)
        self.assertIn("GadgetButtonGetData( m_commandWindows[ i ] ) == common",MULTI)


if __name__=="__main__":
    unittest.main()
