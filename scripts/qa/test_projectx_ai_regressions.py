#!/usr/bin/env python3
"""Focused Project X AI regression tests (no Android SDK required)."""
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from check_projectx_ai_logs import examine


class ProjectXAILogTests(unittest.TestCase):
    def test_parse_realistic_ai_diagnostics(self):
        lines = "\n".join([
            "[GX-NET] crc players frame 0: 2:Hussein(local) 3:Hard Army",
            "[GX-NET] fp invalid frame 70: AI state 7 - on EuropeVehicleDozer id=1150",
            "[GX-NET] fp invalid frames 0..99: AI state 7  EuropeVehicleDozer x4",
            "[GX-NET] fp invalid frames 0..99: update PhysicsBehavior GenericDebris x9",
            "[GX-AI-SCRIPT] path=Data\\Scripts\\SkirmishScripts.scb instance=0 source=Mods/ProjectX/AI.big result=OPEN",
            "[GX-AI-SIDE] imported name=Europe faction=FactionAmericaSuperWeaponGeneral",
        ])
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "logs.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("generals-stderr.log", lines)
            session = examine(archive)[0]
        self.assertIn("Hard Army", session["players"])
        self.assertEqual(session["fp_invalid_summary_total"], 13)
        self.assertEqual(len(session["first_fp_examples"]), 1)
        self.assertTrue(session["script_provenance_available"])
        self.assertEqual(len(session["side_diagnostics"]), 1)

    def test_legacy_logs_are_distinguished_from_new_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            archive = Path(d) / "logs.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("generals-stderr-prev.log", "No script diagnostics here\n")
            session = examine(archive)[0]
        self.assertFalse(session["script_provenance_available"])
        self.assertEqual(session["fp_invalid_summary_total"], 0)


class ScriptPrecedenceCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "Core/GameEngine/Source/Common/System/FileSystem.cpp").read_text()
        cls.archive = (ROOT / "Core/GameEngine/Source/Common/System/ArchiveFileSystem.cpp").read_text()
        cls.sides = (ROOT / "GeneralsMD/Code/GameEngine/Source/GameLogic/Map/SidesList.cpp").read_text()

    def test_cplusplus_script_path_gate(self):
        compiler = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            self.skipTest("C++ compiler unavailable")
        start = self.source.index("static bool gxIsAIOverrideScriptPath(")
        end = self.source.index("// GeneralsX @feature Codex 10/10/2026", start)
        excerpt = self.source[start:end]
        cpp = (
            "#include <algorithm>\n#include <cctype>\n#include <string>\n"
            "using FileInstance = unsigned int;\n"
            "struct ArchiveFileSystem { unsigned count=2; FileInstance getFileCount(const char*) const { return count; } };\n"
            "ArchiveFileSystem* TheArchiveFileSystem = nullptr;\n"
            + excerpt +
            "\nint main() {\n"
            " ArchiveFileSystem a; TheArchiveFileSystem=&a;\n"
            ' if(gxAIOverrideArchiveCount("Data\\\\Scripts\\\\SkirmishScripts.scb") != 2) return 1;\n'
            ' if(gxAIOverrideArchiveCount("DATA/SCRIPTS/MULTIPLAYERSCRIPTS.SCB") != 2) return 2;\n'
            ' if(gxAIOverrideArchiveCount("Data/Scripts/Scripts.ini") != 2) return 3;\n'
            ' if(gxAIOverrideArchiveCount("Data/INI/OtherScripts.ini") != 0) return 4;\n'
            ' if(gxAIOverrideArchiveCount("Data/INI/AIData.ini") != 0) return 5;\n'
            ' a.count=0; if(gxAIOverrideArchiveCount("Data/Scripts/SkirmishScripts.scb") != 0) return 6;\n'
            " TheArchiveFileSystem=nullptr;\n"
            ' if(gxAIOverrideArchiveCount("Data/Scripts/SkirmishScripts.scb") != 0) return 7;\n'
            " return 0;\n}\n"
        )
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "lookup.cpp"
            executable = Path(d) / "lookup"
            source.write_text(cpp)
            subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(executable)],
                           check=True, capture_output=True, text=True)
            subprocess.run([str(executable)], check=True, capture_output=True, text=True)

    def test_read_metadata_and_existence_share_script_priority(self):
        self.assertIn("instance < scriptCopies", self.source)
        self.assertIn("TheArchiveFileSystem->getFileInfo(filename, fileInfo, instance)", self.source)
        self.assertIn("scriptCopies == 0 && TheArchiveFileSystem->doesFileExist", self.source)
        self.assertIn("(access & File::WRITE) == 0 ? gxAIOverrideArchiveCount", self.source)
        self.assertIn("m_files.count(result.lastToken)", self.archive)

    def test_mod_sides_are_bounded_and_validated(self):
        self.assertIn("SidesList::MAX_SKIRMISH_SIDES", self.sides)
        self.assertIn("dictName != playerName", self.sides)
        self.assertIn("faction.isEmpty()", self.sides)


if __name__ == "__main__":
    unittest.main()
