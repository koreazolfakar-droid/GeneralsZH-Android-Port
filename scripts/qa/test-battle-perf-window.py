#!/usr/bin/env python3
"""Test bounded production frame samples and battle lifecycle using a fake clock.
Synthetic times validate accounting; they are not game/device benchmarks.
"""
# GeneralsX @feature Codex 14/10/2026 Check percentiles without changing simulation.
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('gles_tests', ROOT / 'scripts/qa/test-gles-upload-regressions.py')
gles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gles)


def main():
    source = (ROOT / 'GeneralsMD/Code/GameEngine/Source/Common/GameEngine.cpp').read_text()
    body = gles.extract(source, 'static void gxTraceBattleWindow(')
    body = body.replace('typedef std::chrono::steady_clock Clock;', 'typedef FakeClock Clock;')
    with tempfile.TemporaryDirectory(prefix='gx-battle-perf-') as temp:
        work = Path(temp)
        code = r'''
#include "GXFrameTimeStats.h"
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstdarg>
#include <string>
static std::string logText;
static int recordLog(FILE*,const char*format,...) {
 char text[2048];va_list args;va_start(args,format);int n=vsnprintf(text,sizeof(text),format,args);va_end(args);
 assert(n>=0&&n<int(sizeof(text)));logText+=text;return n;
}
struct FakeClock {
 using time_point=std::chrono::steady_clock::time_point;
 static time_point stamp;
 static time_point now(){return stamp;}
};
FakeClock::time_point FakeClock::stamp{};
#define fprintf recordLog
'''
        code += body
        code += r'''
#undef fprintf
int main(){
 GXFrameTimeStats<100> s;for(int i=100;i>=1;--i)s.add(i,1000);
 assert(s.percentile(.5)==50&&s.percentile(.95)==95&&s.percentile(.99)==99);
 assert(s.count==100&&s.dropped==0&&s.worstMs==100&&s.mainUs==100000);
 s.add(1000,2000);assert(s.count==100&&s.dropped==1&&s.worstMs==1000&&s.mainUs==102000);
 s.reset();assert(s.count==0&&s.dropped==0&&s.mainUs==0&&s.percentile(.99)==0);
 gxTraceBattleWindow(false,0,1000);assert(logText.empty());
 gxTraceBattleWindow(true,1,12000);assert(logText.find("firstMainFrameMs=12.000")!=std::string::npos);
 for(unsigned i=1;i<=6000;++i){FakeClock::stamp+=std::chrono::milliseconds(20);gxTraceBattleWindow(true,i+1,7000);}
 assert(logText.find("[GX-PERF-BATTLE-END] seconds=120.000 samples=6000 dropped=0 p50=20.000 p95=20.000 p99=20.000")!=std::string::npos);
 auto completed=logText;FakeClock::stamp+=std::chrono::seconds(2);gxTraceBattleWindow(true,6002,8000);assert(logText==completed);
 gxTraceBattleWindow(false,0,1000);gxTraceBattleWindow(true,1,17000);
 assert(logText.find("firstMainFrameMs=17.000")!=std::string::npos);
 gxTraceBattleWindow(true,0,19000);assert(logText.find("firstMainFrameMs=19.000")!=std::string::npos);
 puts("PASS: exact percentiles, bounded samples, 120-second lifecycle, menu exclusion and match reset (synthetic clock)");
}
'''
        path = work / 'test.cpp'
        path.write_text(code)
        exe = work / 'test'
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-fsanitize=address,undefined',
                        '-I', str(ROOT / 'Core/Libraries/Include'), str(path), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
