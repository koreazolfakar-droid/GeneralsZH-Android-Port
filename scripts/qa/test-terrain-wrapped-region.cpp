// Standalone host test:
// g++ -std=c++17 -O2 -Wall -Wextra -Werror -I Core/GameEngineDevice/Source/W3DDevice/GameClient scripts/qa/test-terrain-wrapped-region.cpp -o /tmp/test-terrain-wrap
#include "GXTerrainWrappedRange.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

static void check(int w, int h, int originX, int originY,
                  int x0, int x1, int y0, int y1)
{
    const auto xr = GXTerrainSplitWrappedRange(x0, x1, originX, w);
    const auto yr = GXTerrainSplitWrappedRange(y0, y1, originY, h);
    assert(xr.count >= 0 && xr.count <= 2);
    assert(yr.count >= 0 && yr.count <= 2);

    std::vector<uint8_t> expected(w*h, 0), actual(w*h, 0);
    const int xx0 = x0 < 0 ? 0 : x0;
    const int xx1 = x1 > w ? w : x1;
    const int yy0 = y0 < 0 ? 0 : y0;
    const int yy1 = y1 > h ? h : y1;
    const auto mod = [](int v, int n) { return ((v % n) + n) % n; };
    for (int y = yy0; y < yy1; ++y) {
        for (int x = xx0; x < xx1; ++x) {
            const auto px = mod(x + originX, w);
            const auto py = mod(y + originY, h);
            expected[py*w+px] = 1;
        }
    }
    for (int iy = 0; iy < yr.count; ++iy) {
        for (int ix = 0; ix < xr.count; ++ix) {
            assert(xr.lo[ix] >= 0 && xr.hi[ix] <= w);
            assert(yr.lo[iy] >= 0 && yr.hi[iy] <= h);
            for (int y = yr.lo[iy]; y < yr.hi[iy]; ++y) {
                for (int x = xr.lo[ix]; x < xr.hi[ix]; ++x) {
                    assert(!actual[y*w+x]); // each physical cell updated once
                    actual[y*w+x] = 1;
                }
            }
        }
    }
    assert(expected == actual);
}

int main()
{
    // Normal, stretched, full-map and small boundary windows.
    for (int i=0; i<12; ++i) {
        for (int j=0; j<12; ++j) {
            check(96, 96, i, j, 0, 96, 0, 96);
            check(128, 96, i, j, 1, 7, 4, 14);
            check(128, 128, i, j, 95, 128, 90, 128);
            check(256, 256, i, j, -5, 5, 252, 261);
        }
    }
    std::mt19937 rng(0x74e217);
    for (int trial=0; trial<6000; ++trial) {
        const int w = (trial%3==0 ? 96 : trial%3==1 ? 127 : 256);
        const int h = (trial%4==0 ? 96 : trial%4==1 ? 128 : trial%4==2 ? 127 : 256);
        const int ox = int(rng()%unsigned(w*3))-w;
        const int oy = int(rng()%unsigned(h*3))-h;
        const int x0 = int(rng()%unsigned(w+10))-5;
        const int x1 = x0 + int(rng()%unsigned(w+1));
        const int y0 = int(rng()%unsigned(h+10))-5;
        const int y1 = y0 + int(rng()%unsigned(h+1));
        check(w,h,ox,oy,x0,x1,y0,y1);
    }
    std::puts("PASS: 6,576 wrapped dirty-region cases; exact coverage and no duplicate writes");
}
