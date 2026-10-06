#!/usr/bin/env python3
"""Run the production GPU-timer initialization block against host GL adapters.

Check signed-manifest network ordering in source/config without running networking.
This does not test an Android GPU driver or a real GeneralsOnline match.
"""
# GeneralsX @bugfix Codex 05/10/2026 Verify the documented 3277 timer opt-in and serial-12 network defaults.
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[2]
    pipeline = (root / 'Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp').read_text()
    start = pipeline.rfind('{', 0, pipeline.index('FILE *timerIn = fopen("gx_gles_gputimer.txt"'))
    end = start + 1
    depth = 1
    while depth:
        depth += (pipeline[end] == '{') - (pipeline[end] == '}')
        end += 1
    production = pipeline[start:end]
    adapters = r'''
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
constexpr unsigned GL_EXTENSIONS=1;
struct GpuFrameTimer {
    using PFN_GenQueries=void(*)(int,unsigned*);
    using PFN_BeginQuery=void(*)(unsigned,unsigned);
    using PFN_EndQuery=void(*)(unsigned);
    using PFN_GetQueryObjectuiv=void(*)(unsigned,unsigned,unsigned*);
    static constexpr int kQueries=3;
    bool ok=false;
    unsigned queries[kQueries]{};
    PFN_BeginQuery begin=nullptr;
    PFN_EndQuery end=nullptr;
    PFN_GetQueryObjectuiv get=nullptr;
} s_gpuTimer;
int scenario=0, generated=0, lookedUp=0;
const unsigned char* glGetString(unsigned) {
    return reinterpret_cast<const unsigned char*>(scenario==2 ? "" : "GL_EXT_disjoint_timer_query");
}
void genQueries(int n,unsigned*) { generated+=n; }
void beginQuery(unsigned,unsigned) {}
void endQuery(unsigned) {}
void getQuery(unsigned,unsigned,unsigned*) {}
void* d3d8gles_GetOptionalGLProc(const char* name) {
    ++lookedUp;
    if (scenario==3) return nullptr;
    if (!strcmp(name,"glGenQueriesEXT")) return reinterpret_cast<void*>(genQueries);
    if (!strcmp(name,"glBeginQueryEXT")) return reinterpret_cast<void*>(beginQuery);
    if (!strcmp(name,"glEndQueryEXT")) return reinterpret_cast<void*>(endQuery);
    return reinterpret_cast<void*>(getQuery);
}
void* SDL_GL_GetProcAddress(const char*) { return nullptr; }
void initialize()
'''
    checks = r'''
int main(int argc,char** argv) {
    assert(argc==2);
    scenario=atoi(argv[1]);
    initialize();
    assert(s_gpuTimer.ok==(scenario==1));
    assert(generated==(scenario==1 ? GpuFrameTimer::kQueries : 0));
    assert(lookedUp==((scenario==1 || scenario==3) ? 4 : 0));
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-3277-timer-') as temporary:
        work = Path(temporary)
        unit = work / 'timer.cpp'
        unit.write_text(adapters + production + checks)
        executable = work / 'timer'
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        str(unit), '-o', str(executable)], check=True)
        for scenario in range(4):
            directory = work / str(scenario)
            directory.mkdir()
            if scenario:
                (directory / 'gx_gles_gputimer.txt').touch()
            subprocess.run([str(executable), str(scenario)], cwd=directory, check=True)
    network = (root / 'GeneralsMD/Code/GameEngine/Source/GameNetwork/GeneralsOnline/NetworkMesh.cpp').read_text()
    config = json.loads((root / 'update/config.json').read_text())
    expected = {
        'stun_servers': 'stun:stun.playgenerals.online:3478,stun:stun.l.google.com:19302,stun:stun.playgenerals.online:53',
        'turn_servers': 'turn:turn.playgenerals.online:3478,turn:turn.playgenerals.online:53',
    }
    for key, value in expected.items():
        match = re.search(r'GXRemoteConfig::get\("' + key + r'", "([^"]+)"\)', network)
        assert match and match.group(1) == config[key] == value, key
    assert 'kTurnCredentialWaitMs' not in network, 'previous TURN timeout must remain removed'
    print('PASS: GPU timer default-off, opt-in, absent extension/procs; serial-12 STUN/TURN source/config order')


if __name__ == '__main__':
    main()
