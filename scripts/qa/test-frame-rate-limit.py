#!/usr/bin/env python3
"""Run the production limiter with a deterministic monotonic clock/scheduler.

No wall-clock timing assertions: reproduce oversleep, signal interruption, rate
changes and lifecycle stalls without depending on host scheduling or Android.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TYPES = r'''
#pragma once
#include <cstdint>
using Real = float;
using Int = int;
using Int64 = int64_t;
using UnsignedInt = unsigned;
#define CPP_11(x) x
#define PROFILER_SECTION
#define LOGICFRAMES_PER_SECOND 30
#define GENERALS_ONLINE_HIGH_FPS_LIMIT 30
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#ifdef _WIN32
struct LARGE_INTEGER { int64_t QuadPart; };
using DWORD = unsigned long;
void QueryPerformanceCounter(LARGE_INTEGER *);
void QueryPerformanceFrequency(LARGE_INTEGER *);
void Sleep(DWORD);
#endif
'''
HARNESS = r'''
#include "Common/FrameRateLimit.h"
#include <cassert>
#include <cerrno>
#include <cmath>
#include <cstdio>
#include <time.h>
static int64_t nowNs = 1000000000;
static int64_t oversleepNs = 0;
static bool interruptNext = false;
static int sleeps = 0;
static int reads = 0;
extern "C" int gx_clock_gettime(clockid_t, timespec *out) noexcept {
    nowNs += 10000; // 10 us fake clock-read / spinning cost
    ++reads;
    out->tv_sec = nowNs / 1000000000;
    out->tv_nsec = nowNs % 1000000000;
    return 0;
}
extern "C" int gx_nanosleep(const timespec *delay, timespec *) {
    ++sleeps;
    const int64_t requested = int64_t(delay->tv_sec)*1000000000 + delay->tv_nsec;
    if (interruptNext) {
        interruptNext = false;
        nowNs += requested / 4;
        errno = EINTR;
        return -1;
    }
    nowNs += requested + oversleepNs;
    return 0;
}
#ifdef _WIN32
void QueryPerformanceCounter(LARGE_INTEGER *value) {
    timespec tick;
    gx_clock_gettime(0, &tick);
    value->QuadPart = int64_t(tick.tv_sec)*1000000000+tick.tv_nsec;
}
void QueryPerformanceFrequency(LARGE_INTEGER *value) { value->QuadPart = 1000000000; }
void Sleep(DWORD milliseconds) {
    ++sleeps;
    nowNs += int64_t(milliseconds)*1000000 + oversleepNs;
}
#endif
static void cadence(unsigned hz) {
    FrameRateLimit pacer;
    const int64_t start = nowNs;
    oversleepNs = 3000000; // wake late on every frame
    for (unsigned i = 0; i < hz; ++i) {
        nowNs += 1000000; // frame work
        const float delta = pacer.wait(hz);
        assert(delta > 0.0f);
    }
    const double elapsed = (nowNs - start) / 1e9;
    // One late wake is retained; repeated oversleep must not accumulate.
    if (std::fabs(elapsed - 1.0) >= 0.004) {
        std::fprintf(stderr, "FAIL: %u Hz drifted %.6f seconds in one second\n", hz, elapsed-1.0);
        std::abort();
    }
    oversleepNs = 0;
    // A long background/loading stall must not cause a burst of short frames.
    nowNs += 5000000000LL;
    assert(pacer.wait(hz) >= 5.0f);
    const int64_t resumed = nowNs;
    pacer.wait(hz);
    assert(nowNs-resumed >= int64_t(1e9/hz)-20000);
    // Uncapped values do no sleeping, including the exact preset sentinel.
    for (unsigned limit : {0u, 1000000u, 1000001u}) {
        const int before = sleeps, clocks = reads;
        pacer.wait(limit);
        assert(sleeps == before);
        assert(reads-clocks == 1);
    }
    const int64_t switched = nowNs;
    pacer.wait(hz == 30 ? 60 : 30);
    assert(nowNs-switched >= int64_t(1e9/(hz == 30 ? 60 : 30))-20000);
    const int64_t changed = nowNs;
    pacer.wait(hz);
    assert(nowNs-changed >= int64_t(1e9/hz)-20000);
}
int main() {
    cadence(30);
    cadence(60);

#ifndef _WIN32
    FrameRateLimit pacer;
    interruptNext = true;
    const int before = sleeps, clocks = reads;
    pacer.wait(30);
    assert(sleeps-before >= 2); // Interrupted sleep must resume sleeping.
    assert(reads-clocks < 100); // No multi-ms busy wait after a signal.

#endif
    std::puts("PASS: production limiter cadence, stalls, uncapped, rate changes and POSIX EINTR");
}
'''

def main():
    with tempfile.TemporaryDirectory(prefix='gx-frame-limit-') as directory:
        temp = Path(directory)
        (temp/'Common').mkdir()
        (temp/'Common/GameCommon.h').write_text(TYPES)
        (temp/'PreRTS.h').write_text(TYPES)
        (temp/'test.cpp').write_text('#include <cstdlib>\n#include <initializer_list>\n'+HARNESS)
        for platform in ('posix', 'win32'):
            exe = temp/platform
            defines = ['-D_WIN32'] if platform == 'win32' else []
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-Wall', '-Wextra',
                            '-fsanitize=undefined', '-fno-omit-frame-pointer', *defines,
                            '-Dclock_gettime=gx_clock_gettime', '-Dnanosleep=gx_nanosleep',
                            '-I', str(temp), '-I', str(ROOT/'Core/GameEngine/Include'),
                            str(ROOT/'Core/GameEngine/Source/Common/FrameRateLimit.cpp'),
                            str(temp/'test.cpp'), '-o', str(exe)], check=True)
            print(platform, flush=True)
            subprocess.run([str(exe)], check=True)

if __name__ == '__main__':
    main()
