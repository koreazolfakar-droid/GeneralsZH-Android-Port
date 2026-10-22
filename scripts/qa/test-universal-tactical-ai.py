#!/usr/bin/env python3
"""Compile the exact production tactical adapter with bounded engine-interface doubles.

Uses ASan/UBSan and an optimized synthetic cost sample. This is not a real battle,
save-file roundtrip, replay simulation, Android FPS or actual-mod gameplay test.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / 'GeneralsMD/Code/GameEngine/Source/GameLogic/AI/AIPlayer.cpp'
SCRIPT = ROOT / 'GeneralsMD/Code/GameEngine/Source/GameLogic/ScriptEngine/ScriptActions.cpp'
HEADER = ROOT / 'GeneralsMD/Code/GameEngine/Include/GameLogic/UniversalTacticalDirector.h'


class UniversalTacticalTests(unittest.TestCase):
    def test_actual_production_adapter(self):
        source = AI.read_text()
        adapter = source.split('// BEGIN UNIVERSAL TACTICAL ADAPTER', 1)[1].split('\n', 1)[1]
        adapter = adapter.split('// END UNIVERSAL TACTICAL ADAPTER', 1)[0]
        fixture = (ROOT / 'scripts/qa/universal-tactical-fixture.cpp').read_text()
        self.assertEqual(fixture.count('// PRODUCTION_ADAPTER'), 1)
        with tempfile.TemporaryDirectory(prefix='gx-universal-ai-') as tmp:
            path = Path(tmp) / 'fixture.cpp'
            path.write_text(fixture.replace('// PRODUCTION_ADAPTER', adapter))
            for hz in (30, 60):
                executable = Path(tmp) / f'fixture-{hz}'
                command = [os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                           '-I', str(ROOT / 'GeneralsMD/Code/GameEngine/Include'),
                           f'-DLOGICFRAMES_PER_SECOND={hz}', str(path), '-o', str(executable)]
                if hz == 30:
                    command += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
                else:
                    command += ['-O2']
                subprocess.run(command, check=True)
                subprocess.run([str(executable)], check=True)

    def test_original_production_guards_and_rng_are_preserved(self):
        source = AI.read_text().split('Bool AIPlayer::selectTeamToBuild()', 1)[1].split('void AIPlayer::buildSpecificAIBuilding', 1)[0]
        self.assertEqual(source.count('GameLogicRandomValue('), 1)
        self.assertIn('GameLogicRandomValue( 0, count-1 )', source)
        self.assertLess(source.index('isAGoodIdeaToBuildTeam(*t)'), source.index('chooseProduction('))
        self.assertLess(source.index('selectTeamToReinforce(hiPri)'), source.index('chooseProduction('))
        self.assertLess(source.index('m_productionPriority == hiPri'), source.index('chooseProduction('))
        self.assertLess(source.index('chooseProduction('), source.index('buildSpecificAITeam(teamProto, false)'))
        original_guards = AI.read_text()
        for guard in ('proto->evaluateProductionCondition()', 'proto->countTeamInstances()',
                      'isPossibleToBuildTeam( proto, true, needMoney)',
                      'TheBuildAssistant->isPossibleToMakeUnit( factory, thing )',
                      'm_player->getMoney()->countMoney() < cost'):
            self.assertIn(guard, original_guards)

    def test_hunt_keeps_original_command_and_save_format(self):
        hunt = SCRIPT.read_text().split('void ScriptActions::doTeamHunt(', 1)[1].split('void ScriptActions::doTeamHuntWithCommandButton', 1)[0]
        self.assertIn('UniversalTacticalDirector::prepareTeamHunt(theTeam);', hunt)
        self.assertIn('theGroup->groupHunt( CMD_FROM_SCRIPT );', hunt)
        adapter = AI.read_text().split('// BEGIN UNIVERSAL TACTICAL ADAPTER', 1)[1].split('// END UNIVERSAL TACTICAL ADAPTER', 1)[0]
        for forbidden in ('GameLogicRandomValue(', 'rand(', 'time(', 'chrono', 'new ', 'malloc(',
                          'requestPath(', 'findClosestEnemy(', 'xfer->', 'static CapabilityCache'):
            self.assertNotIn(forbidden, adapter)
        self.assertNotIn('Xfer', HEADER.read_text())

    def test_replay_metadata_versions_the_rules_without_a_new_binary_field(self):
        recorder = (ROOT / 'GeneralsMD/Code/GameEngine/Source/Common/Recorder.cpp').read_text()
        self.assertIn('if (originalGameMode == GAME_SKIRMISH) versionTimeString.concat(L" [UTD1]");', recorder)
        self.assertIn('setReplayMode(m_originalGameMode == GAME_SKIRMISH &&', recorder)
        self.assertIn('wcsstr(header.versionTimeString.str(), L" [UTD1]") != nullptr', recorder)
        reset = recorder.split('void RecorderClass::reset()', 1)[1].split('void RecorderClass::update()', 1)[0]
        playback = recorder.split('Bool RecorderClass::playbackFile(', 1)[1].split('ReplayHeader header;', 1)[0]
        self.assertIn('setReplayMode(false)', reset)
        self.assertIn('setReplayMode(false)', playback)
        self.assertIn('gxWriteReplayUnicodeString(m_file, versionTimeString.str());', recorder)
        xfer = AI.read_text().split('void AIPlayer::xfer(', 1)[1].split('void AIPlayer::loadPostProcess()', 1)[0]
        self.assertIn('XferVersion currentVersion = 1;', xfer)
        self.assertNotIn('UniversalTactical', xfer)


if __name__ == '__main__':
    unittest.main()
