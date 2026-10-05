#!/usr/bin/env python3
"""Test extracted production cleanup and legacy map-version read control flow.

Filesystem APIs are doubles; these tests do not run a full snapshot or Android.
"""
# GeneralsX @bugfix Codex 05/10/2026 Protect maps and version-1 stream alignment.
import os
from pathlib import Path
import subprocess
import tempfile


def block(source, start):
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    here = Path(__file__).resolve().parent
    source = (here.parents[1] / 'GeneralsMD/Code/GameEngine/Source/Common/System/SaveGame/GameStateMap.cpp').read_text()
    cleanup = block(source, source.index('void GameStateMap::clearScratchPadMaps()'))
    # Locate the load-only game-mode read; the save branch deliberately uses currentVersion.
    mode = source.index('// get the game mode.')
    conditional = block(source, source.rfind('if (', 0, mode))
    tests = r"""
using Int=int; using GameMode=int;
struct Logic {int mode=-1; void setGameMode(int m){mode=m;}} logic;
Logic*TheGameLogic=&logic;
struct Transfer {int words[2]={123,456}; int cursor=0; void xferInt(int*p){*p=words[cursor++];}};
void readMode(int version, Transfer*xfer){[[maybe_unused]] const int currentVersion=2;
""" + conditional + r"""
}
int main(){
    for(scenario=0;scenario<4;scenario++){
        cwd="assets";deletes=scans=0;
        GameStateMap().clearScratchPadMaps();
        assert(cwd=="assets");
        assert(deletes==(scenario==0?1:0));
        assert(scans==((scenario==1||scenario==2)?0:1));
    }
    Transfer old; readMode(1,&old);
    assert(old.cursor==0 && logic.mode==-1); // first word remains map data
    Transfer current; readMode(2,&current);
    assert(current.cursor==1 && logic.mode==123 && current.words[current.cursor]==456);
}
"""
    with tempfile.TemporaryDirectory(prefix='gx-save-map-') as work:
        work = Path(work)
        unit = work / 'test.cpp'
        unit.write_text('#include "save-map-compat.h"\n' + cleanup + tests)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-I', str(here), str(unit), '-o', str(work / 'test')], check=True)
        subprocess.run([str(work / 'test')], check=True)
    print('PASS: 4 cleanup failure/normal cases and map versions 1/2 stream alignment')


if __name__ == '__main__':
    main()
