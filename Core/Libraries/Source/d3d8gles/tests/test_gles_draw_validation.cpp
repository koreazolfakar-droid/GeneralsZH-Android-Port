// GeneralsX @bugfix Codex 23/10/2026 Regression tests for GLES indexed draws.
// Run: c++ -std=c++17 -Wall -Wextra -Werror -fsanitize=address,undefined
//      tests/test_gles_draw_validation.cpp -o /tmp/gles-draw-check && /tmp/gles-draw-check
#include "../src/gles_draw_validation.h"
#include <cassert>
#include <cstdint>
#include <cstring>

int main()
{
    assert(gxIndexWindowFits(12, 0, 6, 2));
    assert(gxIndexWindowFits(12, 5, 1, 2));
    assert(!gxIndexWindowFits(12, 5, 2, 2));
    assert(!gxIndexWindowFits(12, SIZE_MAX, 1, 2));
    assert(!gxIndexWindowFits(12, 1, SIZE_MAX, 2));
    assert(!gxIndexWindowFits(12, 0, 1, 3));
    assert(gxIndexWindowFits(12, 0, 3, 4));

    const uint16_t valid16[] = {0, 1, 2};
    const uint16_t invalid16[] = {0, 1, 9};
    assert(gxTerrainIndicesFitVertices((const unsigned char *)valid16, 3, 2, 0, 16, 3 * 16));
    assert(!gxTerrainIndicesFitVertices((const unsigned char *)invalid16, 3, 2, 0, 16, 3 * 16));
    assert(gxTerrainIndicesFitVertices((const unsigned char *)valid16, 3, 2, 2, 16, 5 * 16));
    assert(!gxTerrainIndicesFitVertices((const unsigned char *)valid16, 3, 2, 3, 16, 5 * 16));

    const uint32_t valid32[] = {0, 2500, 9999};
    assert(gxTerrainIndicesFitVertices((const unsigned char *)valid32, 3, 4, 0, 16, 10000 * 16));
    assert(!gxTerrainIndicesFitVertices((const unsigned char *)valid32, 3, 4, 1, 16, 10000 * 16));
    assert(!gxTerrainIndicesFitVertices((const unsigned char *)valid16, 3, 2, 0, 0, 100));

    // Unaligned 32-bit indices must not rely on aligned reinterpret_cast.
    unsigned char unaligned[sizeof(valid32) + 1] = {};
    std::memcpy(unaligned + 1, valid32, sizeof(valid32));
    assert(gxTerrainIndicesFitVertices(unaligned + 1, 3, 4, 0, 16, 10000 * 16));
}
