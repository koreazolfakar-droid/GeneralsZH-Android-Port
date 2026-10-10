#!/usr/bin/env python3
"""Regression tests for binary audit tooling; never imports copyright assets."""
import importlib.util
import pathlib
import struct
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("projectx_audit", ROOT / "scripts/qa/audit-projectx-skirmish.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def astr(s):
    b = s.encode("latin-1")
    return struct.pack("<H", len(b)) + b

def chunk(id, version, body):
    return struct.pack("<IHi", id, version, len(body)) + body

def stringproperty(id, v):
    return struct.pack("<I", (id << 8) | 3) + astr(v)

def team(name, owner, condition, unit):
    return struct.pack("<H", 4) + stringproperty(3, name) + stringproperty(4, owner) + stringproperty(5, condition) + stringproperty(6, unit)

def script(name, hard=True):
    flags=bytes([1, 1, 1, 1, int(hard), 0])
    return chunk(2, 2, astr(name) + astr("")*3 + flags + struct.pack("<I", 0) + bytes(40))

def fixture():
    names={1:"ScriptTeams",2:"Script",3:"teamName",4:"teamOwner",5:"teamProductionCondition",6:"teamUnitType1",7:"PlayerScriptsList"}
    toc=b"".join(bytes([len(name)])+name.encode("latin-1")+struct.pack("<I",id) for id,name in names.items())
    t=team("USA Defend", "SkirmishAmerica", "Valid Condition", "AmericaVehicleDozer")
    t+=team("USA Missing Attack", "SkirmishAmerica", "Absent Attack Script", "AmericaVehicleChaparral")
    t+=team("ECA Hard Disabled", "SkirmishAmericaSuperWeaponGeneral", "Easy Only", "EuropeVehicleDozer_AI")
    return b"CkMp"+struct.pack("<I",len(names))+toc+chunk(1,1,t)+chunk(7,1,script("Valid Condition")+script("Easy Only",False))

class AuditTests(unittest.TestCase):
    def test_decode_teams_scripts_and_hard_flags(self):
        teams,scripts=audit.read_scb(fixture())
        self.assertEqual(len(teams),3)
        self.assertEqual(set(scripts),{"Valid Condition","Easy Only"})
        self.assertTrue(scripts["Valid Condition"]["hard"])
        self.assertFalse(scripts["Easy Only"]["hard"])
        self.assertEqual(teams[2]["teamName"],"ECA Hard Disabled")

    def test_detect_unavailable_hard_conditions_without_changing_data(self):
        raw=fixture();teams,scripts=audit.read_scb(raw)
        outcome=audit.audit(teams,scripts,{"americavehicledozer","europevehicledozer_ai"})
        self.assertEqual(len(outcome["factions"]["America"]["unresolved_production_conditions"]),1)
        self.assertEqual(len(outcome["factions"]["America"]["unit_names_unresolved_in_supplied_big_only"]),1)
        self.assertEqual(len(outcome["factions"]["Europe"]["not_enabled_on_hard"]),1)
        self.assertEqual(raw,fixture())

    def test_parse_big_with_real_nul_terminated_path_and_object_lines(self):
        name=b"Data\\INI\\Object\\Tanks.ini\\0"
        body=b"Object AmericaVehicleDozer\r\nEnd\r\n"
        start=16+8+len(name)
        data=b"BIGF"+struct.pack(">III",start+len(body),1,0)+struct.pack(">II",start,len(body))+name+body
        self.assertEqual(audit.read_big_objects(data),{"americavehicledozer"})
        with self.assertRaises(ValueError):
            audit.read_big_objects(data[:-3])

    def test_reject_corrupt_or_truncated_scb(self):
        with self.assertRaises(ValueError):audit.read_scb(b"ZZZZ"+fixture()[4:])
        with self.assertRaises(ValueError):audit.read_scb(fixture()[:-2])
        bad=bytearray(fixture())
        bad[-40:-36]=b"\\xff\\xff\\xff\\xff"
        # Sanitized parser must either reject or keep bounds while scanning.
        try:
            teams,scripts=audit.read_scb(bytes(bad))
            self.assertEqual(len(teams),3)
        except ValueError:
            pass

if __name__=="__main__":
    unittest.main()
