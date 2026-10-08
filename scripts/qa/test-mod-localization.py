#!/usr/bin/env python3
"""Compile the production GameText.cpp against small host test adapters.

No engine implementation is copied. Only platform/framework includes are replaced;
CSF/STR parsing, initialization, lookup and cleanup execute the production source.
Run from any directory; requires a C++17 compiler. These are fixture tests, not
Android real-device or Project X Re compatibility tests.
"""
# GeneralsX @bugfix Codex 05/10/2026 Regression coverage for mod localization ownership.
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='Optional older GameText.cpp to reproduce the bug')
    parser.add_argument('--before', action='store_true', help='Expect the old STR-masking bug')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    source = args.source or root / 'Core/GameEngine/Source/GameClient/GameText.cpp'
    body = '\n'.join(line for line in source.read_text().splitlines()
                     if not line.startswith('#include "'))
    # Trace the unchanged menu consumer and execute its real translation callback.
    player = (root / 'GeneralsMD/Code/GameEngine/Source/Common/RTS/PlayerTemplate.cpp').read_text()
    assert '"DisplayName"' in player and 'INI::parseAndTranslateLabel' in player
    ini = (root / 'Core/GameEngine/Source/Common/INI/INI.cpp').read_text()
    start = ini.index('void INI::parseAndTranslateLabel(')
    end = ini.index('//-------------------------------------------------------------------------------------------------', start)
    translate = ini[start:end]
    with tempfile.TemporaryDirectory(prefix='gx-text-test-') as work:
        work = Path(work)
        unit = work / 'loader.cpp'
        selector = (root / 'Core/GameEngine/Include/Common/ModLocalization.h').read_text()
        selector = '\n'.join(line for line in selector.splitlines() if not line.startswith('#include "'))
        unit.write_text('#include "mod-localization-compat.h"\n'
                        + selector + '\n' + body
                        + '\nstruct INI { const char* token; const char* getNextToken(){return token;} '
                        + 'static void parseAndTranslateLabel(INI*,void*,void*,const void*); };\n'
                        + 'const int INI_INVALID_DATA=1;\n' + translate
                        + '\n#include "mod-localization-test.cpp"\n')
        compiler = os.environ.get('CXX', 'c++')
        subprocess.run([compiler, '-std=c++17', '-O1', '-g', '-Wall', '-Wextra',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I', str(here), str(unit), '-o', str(work / 'loader')], check=True)
        subprocess.run([str(work / 'loader')] + (['before'] if args.before else []), check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
