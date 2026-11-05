#!/usr/bin/env python3
"""Compile the production audio stats format and verify old and new fields."""
from pathlib import Path
import re,subprocess,tempfile
root=Path(__file__).resolve().parents[2]
h=(root/'Core/GameEngineDevice/Source/OpenALAudioDevice/OpenALAudioCache.h').read_text()
s=(root/'Core/GameEngineDevice/Source/OpenALAudioDevice/OpenALAudioManager.cpp').read_text()
a=h.index('struct OpenALAudioCacheStats\n');b=h.index('\n};',a)+3
stats=h[a:b]
a=s.index('\tGX_PERF_TRACE("[GX-PERF-AUDIO]');b=s.index('\n\tc = OpenALAudioCacheStats();',a)
call=s[a:b]
code=r'''
#include <cstdio>
#include <cstring>
#include <vector>
using UnsignedInt=unsigned;
''' + stats + r'''
struct AudioPerf {unsigned frames=60,requests=10; double baseMs=1,requestsMs=2,playingMs=3,streamsMs=4,fadeStopMs=5,worstFrameMs=6;};
struct Cache {unsigned getCurrentlyUsedSize(){return 1024;}unsigned getMaxSize(){return 2048;}unsigned getEntryCount(){return 3;}} cache,*m_audioCache=&cache;
std::vector<int> m_playingSounds(1),m_playing3DSounds(2),m_playingStreams(3);
char output[2048];
#define GX_PERF_TRACE(...) std::snprintf(output,sizeof(output),__VA_ARGS__)
int main(){AudioPerf p; OpenALAudioCacheStats c; c.misses=4;c.nativeWav=1;const double n=p.frames;
''' + call + r'''
 assert(std::strstr(output,"hits=0 misses=4 (native wav 1)"));
 assert(std::strstr(output,"missing=0 ffmpeg=0 decode-failed=0"));
 std::puts("PASS: audio log retains legacy fields and separates missing/fallback failures"); }
'''
code=code.replace('#include <cstdio>', '#include <cassert>\n#include <cstdio>')
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'test.cpp';p.write_text(code);exe=Path(tmp)/'test'
 subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=undefined',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
