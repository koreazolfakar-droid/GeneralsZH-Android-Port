#!/usr/bin/env python3
"""Execute production offline catch-up with a deterministic clock and state adapters.
No claim of real replay CRC/save/device validation.
"""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('upload_tests', ROOT/'scripts/qa/test-gles-upload-regressions.py')
extractor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extractor)
source = (ROOT/'GeneralsMD/Code/GameEngine/Source/Common/GameEngine.cpp').read_text()
function = extractor.extract(source, 'static void gxCatchUpSpedUpLogic(')
call = 'gxCatchUpSpedUpLogic(TestClock::now(), regular)' if 'regularLogicUpdated' in function else 'gxCatchUpSpedUpLogic(TestClock::now())'
code = r'''
#define __ANDROID__ 1
#include "Common/GXCatchUpBudget.h"
#include <chrono>
#include <cassert>
#include <functional>
#include <cstdio>
#include <initializer_list>
using Bool=bool;using Int=int;using UnsignedInt=unsigned;
constexpr Bool FALSE=false;
constexpr int BaseFps=TEST_HZ;
struct TestClock {
 using time_point=std::chrono::steady_clock::time_point;
 using duration=std::chrono::steady_clock::duration;
 static time_point value;
 static time_point now(){return value;}
 static void add(double seconds){value+=std::chrono::duration_cast<duration>(std::chrono::duration<double>(seconds));}
};
TestClock::time_point TestClock::value{std::chrono::seconds(1)};
struct Logic {
 bool game=true,paused=false,replay=false;unsigned updates=0;double cost=0.001;
 std::function<void()> action;
 bool isInSkirmishGame(){return true;}bool isInSinglePlayerGame(){return false;}
 bool isInReplayGame(){return replay;}bool isInGame(){return game;}bool isGamePaused(){return paused;}
 void preUpdate(){} void UPDATE(){++updates;TestClock::add(cost);if(action)action();}
} logic,*TheGameLogic=&logic;
struct Recorder {bool playback=false;bool isPlaybackMode(){return playback;}} recorder,*TheRecorder=&recorder;
struct Pacer {
 int fps=TEST_HZ;bool scaled=false,frozen=false,halted=false,limit=true;
 int getFramesPerSecondLimit(){return fps;}int getActualFramesPerSecondLimit(){return fps;}
 bool isActualFramesPerSecondLimitEnabled(){return limit;}bool isLogicTimeScaleEnabled(){return scaled;}
 bool isTimeFrozen(){return frozen;}bool isGameHalted(){return halted;}
} pacer,*TheFramePacer=&pacer;
struct Shell {bool active=false;bool isShellActive(){return active;}} shell,*TheShell=&shell;
struct Client {unsigned steps=0;void step(){++steps;}} client,*TheGameClient=&client;
void *TheNetwork=nullptr;
struct Messages {std::function<void()> action;void propagateMessages(){if(action)action();}} messages,*TheMessageStream=&messages;
static UnsignedInt s_gxCatchUpSteps=0;
'''
code += function.replace('std::chrono::steady_clock', 'TestClock')
code += '\nstatic void run(bool regular=true){ (void)regular; '+call+'; }\n'
code += r'''
static void reset(){
 logic=Logic{};pacer=Pacer{};shell=Shell{};recorder=Recorder{};client=Client{};messages=Messages{};TheNetwork=nullptr;
 logic.paused=true;run();logic.paused=false; // reset the production static debt/clock
}
int main(){
 for(int excluded=0;excluded<8;++excluded){
  reset();
  if(excluded==0)TheNetwork=&logic;
  if(excluded==1)logic.replay=true;
  if(excluded==2)recorder.playback=true;
  if(excluded==3)logic.paused=true;
  if(excluded==4)pacer.frozen=true;
  if(excluded==5)pacer.halted=true;
  if(excluded==6)shell.active=true;
  if(excluded==7)logic.game=false;
  TestClock::add(0.1);run();assert(logic.updates==0&&client.steps==0);
 }
 reset();TestClock::add(10);run();assert(logic.updates<=3); // resume/stall step cap
 reset();logic.cost=0.010;TestClock::add(0.1);run();assert(logic.updates==1); // 6ms admission budget
 for(int transition=0;transition<6;++transition){
  reset();
  logic.action=[&]{
   if(transition==0)logic.game=false;
   if(transition==1)TheNetwork=&logic;
   if(transition==2)recorder.playback=true;
   if(transition==3)pacer.frozen=true;
   if(transition==4)shell.active=true;
   if(transition==5)logic.replay=true;
  };
  TestClock::add(0.1);run();assert(logic.updates==1&&client.steps<=1);
 }
 reset();messages.action=[] {TestClock::add(0.010);};TestClock::add(0.1);run();assert(logic.updates==0); // budget expires in message processing
 reset();messages.action=[] {TheNetwork=&logic;};TestClock::add(0.1);run();assert(logic.updates==0);
 reset();TestClock::add(0.1);run(false);assert(logic.updates==0); // no regular tick: no additional ticks
 for(int fps:{TEST_HZ*2/3,TEST_HZ/2}){
  reset();unsigned ticks=0;logic.cost=0;
  for(int i=0;i<fps*10;++i){++ticks;TestClock::add(1.0/fps);run();}
  ticks+=logic.updates;assert(int(ticks)>=TEST_HZ*10-1&&int(ticks)<=TEST_HZ*10+1);
 }
 puts("PASS: production catch-up 30/60Hz cadence, state transitions, CPU/step bounds and exclusions");
}
'''
with tempfile.TemporaryDirectory(prefix='gx-offline-catchup-') as temp:
    path=Path(temp)/'test.cpp';path.write_text(code)
    for hz in (30,60):
        exe=Path(temp)/str(hz)
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-sanitize-recover=all',f'-DTEST_HZ={hz}','-I',str(ROOT/'GeneralsMD/Code/GameEngine/Include'),str(path),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
