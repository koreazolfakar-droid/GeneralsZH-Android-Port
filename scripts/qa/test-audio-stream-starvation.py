#!/usr/bin/env python3
"""Test production stream-starvation observations and window reset."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'Core/GameEngineDevice/Source/OpenALAudioDevice/OpenALAudioStream.cpp').read_text()
assert 'static void gxObserveStreamStarvation(' in s, 'stream starvation diagnostic is missing'
a=s.index('static std::atomic<unsigned> s_gxStreamStarved');b=s.index('// GeneralsX @bugfix Android port 08/09/2026 Wall clock',a)
helpers=s[a:b]
assert 'gxObserveStreamStarvation(gxStarved, m_endOfData, m_paused);' in s
code=r'''
#include <atomic>
#include <cassert>
namespace GXTrace {static bool enabled=true;bool isPerfEnabled(){return enabled;}}
''' + helpers + r'''
int main(){gxObserveStreamStarvation(false,false,false);gxObserveStreamStarvation(true,true,false);gxObserveStreamStarvation(true,false,true);assert(gxAudioTakeStarvedObservations()==0);GXTrace::enabled=false;gxObserveStreamStarvation(true,false,false);GXTrace::enabled=true;gxObserveStreamStarvation(true,false,false);gxObserveStreamStarvation(true,false,false);assert(gxAudioTakeStarvedObservations()==2);assert(gxAudioTakeStarvedObservations()==0);}
'''
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/'test.cpp';p.write_text(code);exe=Path(temp)/'test'
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: stream starvation observations exclude EOF/pause and reset per window')
