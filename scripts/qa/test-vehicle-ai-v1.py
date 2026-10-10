#!/usr/bin/env python3
"""Fail-closed source, compatibility, and movement-state regression checks for Vehicle AI V1."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "GeneralsMD/Code/GameEngine/Source/GameLogic/AI/AIStates.cpp"
STATE = ROOT / "GeneralsMD/Code/GameEngine/Include/GameLogic/AIStateMachine.h"
POLICY = ROOT / "GeneralsMD/Code/GameEngine/Include/GameLogic/VehicleBlockedRepathPolicy.h"

class VehicleAIV1Safety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE.read_text()
        cls.state=STATE.read_text()
        cls.policy=POLICY.read_text()
        a=cls.source.index('StateReturnType AIInternalMoveToState::update()')
        b=cls.source.index('class AIAttackMoveStateMachine',a)
        cls.movement=cls.source[a:b]

    def test_save_format_kept_at_version_one(self):
        segment=self.source.split('void AIInternalMoveToState::xfer( Xfer *xfer )',1)[1].split('void AIInternalMoveToState::loadPostProcess()',1)[0]
        self.assertIn('XferVersion currentVersion = 1;',segment)
        self.assertIn('xfer->xferUnsignedInt(&m_blockedRepathTimestamp);',segment)
        self.assertIn('xfer->xferCoord3D(&m_goalPosition);',segment)
        self.assertIn('xfer->xferBool(&m_waitingForPath);',segment)
        self.assertEqual(segment.count('xfer->xfer'),9) # format remains unchanged
        self.assertIn('m_blockedRepathTimestamp = 0;',self.state)
        self.assertIn('enum { MIN_REPATH_TIME = 10 };',self.state)

    def test_mobile_ground_vehicle_only_and_nonmobile_backcompat(self):
        x=self.movement
        self.assertIn('obj->isKindOf( KINDOF_VEHICLE ) &&',x)
        self.assertIn('ai->isDoingGroundMovement() && thePath != nullptr &&',x)
        self.assertIn('!ai->isWaitingForPath();',x)
        self.assertIn('#if defined(__ANDROID__) || (defined(TARGET_OS_IPHONE) && TARGET_OS_IPHONE)',x)
        self.assertIn('#else\n\t\tforceRecompute = true;\n\t\tm_blockedRepathTimestamp = currentFrame;\n#endif',x)
        self.assertEqual(x.count('VehicleBlockedRepathPolicy::shouldRetry('),1)

    def test_unblocked_path_following_and_new_goal_unchanged(self):
        x=self.movement
        self.assertIn('if (thePath==nullptr) {\n\t\tforceRecompute = true;',x)
        self.assertIn('if (forceRecompute || TheGameLogic->getFrame() - m_pathTimestamp > MIN_REPATH_TIME)',x)
        self.assertIn('!isSamePosition(obj->getPosition(), &m_pathGoalPosition, &m_goalPosition )',x)
        self.assertIn('if (!computePath())',x)
        self.assertIn('if (ai->getCurLocomotor()',x)
        self.assertIn('if (m_waitingForPath)',x)

    def test_policy_pure_with_no_save_schema_or_rng_changes(self):
        p=self.policy
        self.assertIn('#include <cstdint>',p)
        self.assertIn('currentFrame - lastBlockedRepathFrame >= minimumFrames',p)
        self.assertIn('currentFrame < lastBlockedRepathFrame',p)
        for forbidden in ('rand(', 'time(', 'sleep(', 'malloc(', 'new ', 'static std::', 'std::chrono'):
            self.assertNotIn(forbidden,p)
        self.assertNotIn('xfer->xfer',p)

    def test_guards_reuse_original_state_and_preserve_game_orders(self):
        self.assertIn('ai->requestPath(&m_goalPosition, getAdjustsDestination());',self.source)
        self.assertIn('ai->friend_startingMove();',self.source)
        self.assertIn('if (ai->isBlockedAndStuck() || ai->getNumFramesBlocked()>2*LOGICFRAMES_PER_SECOND)',self.movement)
        self.assertNotIn('setDesiredSpeed(',self.movement)
        self.assertNotIn('m_blockedRepathTimestamp = 0;',self.movement)

if __name__=='__main__':
    unittest.main()
