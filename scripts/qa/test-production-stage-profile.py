#!/usr/bin/env python3
"""Execute the production stage recorder with a deterministic clock.

Checks actual timing attribution, repeated operation counts, early-return RAII,
disabled cost, and the hard report cap. Does not simulate engine production.
"""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    unit = r'''
#include <cassert>
#include <chrono>
#include "GXProductionProfile.h"
struct TestClock {
    using duration = std::chrono::microseconds;
    using time_point = std::chrono::time_point<TestClock>;
    static long long tick;
    static unsigned calls;
    static time_point now() { ++calls; return time_point(duration(tick)); }
};
long long TestClock::tick = 0;
unsigned TestClock::calls = 0;
int main() {
    using Profile = GXProductionProfile<TestClock>;
    { Profile off(false, 0, 1, "disabled"); off.mark(GXPS_CREATE); }
    assert(TestClock::calls == 0);
    { Profile shortTick(true, 1, 1, "short"); TestClock::tick += 4999; }
    { Profile p(true, 2, 42, "Russia_Barrack");
      TestClock::tick += 100; p.mark(GXPS_CREATE);
      TestClock::tick += 2000; p.mark(GXPS_EXIT);
      TestClock::tick += 300; p.mark(GXPS_CREATE);
      TestClock::tick += 1500; p.mark(GXPS_EXIT);
      TestClock::tick += 1100;
    }
    for (unsigned i = 0; i < 80; ++i) {
        Profile capped(true, 3 + i, 7, "cap");
        TestClock::tick += 5000;
    }
    const unsigned before = TestClock::calls;
    { Profile exhausted(true, 999, 7, "exhausted"); exhausted.mark(GXPS_FLAGS); }
    assert(TestClock::calls == before); // no clocks after budget exhaustion
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-production-profile-') as work:
        work = Path(work)
        cpp = work / 'profile.cpp'
        cpp.write_text(unit)
        exe = work / 'profile'
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra',
                        '-Werror', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-I', str(ROOT / 'Core/Libraries/Include'), str(cpp), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
        lines = result.stderr.splitlines()
        assert len(lines) == 64, (len(lines), result.stderr)
        assert 'template=Russia_Barrack' in lines[0], lines[0]
        for expected in ['wall=5.000ms', 'bookkeeping=0.100', 'create=3.500',
                         'exit=1.400', 'creates=2', 'exits=2']:
            assert expected in lines[0], (expected, lines[0])
        assert all('disabled' not in line and 'short' not in line and 'exhausted' not in line for line in lines)
    print('PASS: exact stage attribution, repeated creations/exits, disabled recorder, early return and 64-report cap')


if __name__ == '__main__':
    main()
