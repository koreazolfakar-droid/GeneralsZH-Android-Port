// GeneralsX @performance Codex 22/10/2026: standalone regression fixture.
// g++ -std=c++17 -Wall -Wextra -Werror -I Core/Libraries/Include scripts/qa/test-terrain-geometry-diff.cpp -o /tmp/test-terrain-geometry-diff
// /tmp/test-terrain-geometry-diff
#include "GXTerrainGeometryDiff.h"
#include <cassert>
#include <cstdint>

struct Vertex {
    float x, y, z;
    uint32_t diffuse;
    float u1, v1, u2, v2;
};

int main()
{
    Vertex before[4] = {}, after[4] = {};
    uint32_t gpu[4] = {};
    for (int i = 0; i < 4; ++i) {
        before[i].x = after[i].x = static_cast<float>(i);
        before[i].u1 = after[i].u1 = 0.25f;
        before[i].diffuse = after[i].diffuse = gpu[i] = 0xff556677u;
    }
    assert(!GXTerrainQuadNeedsUpload(before, after, gpu));
    assert(GXTerrainQuadNeedsUpload(before, after, nullptr));
    assert(GXTerrainQuadNeedsUpload(static_cast<Vertex *>(nullptr), after, gpu));

    // Dynamic lights affect the real VB without modifying the static mirror.
    gpu[2] = 0xffaabbccu;
    assert(GXTerrainQuadNeedsUpload(before, after, gpu));
    gpu[2] = after[2].diffuse;
    assert(!GXTerrainQuadNeedsUpload(before, after, gpu));

    after[1].z += 1.0f;
    assert(GXTerrainQuadNeedsUpload(before, after, gpu));
    after[1].z = before[1].z;
    after[3].u2 += 0.5f;
    assert(GXTerrainQuadNeedsUpload(before, after, gpu));
    after[3].u2 = before[3].u2;
    assert(!GXTerrainQuadNeedsUpload(before, after, gpu));

    // Rebuilding static lighting with new diffuse must still upload.
    after[0].diffuse ^= 0x000000ffu;
    assert(GXTerrainQuadNeedsUpload(before, after, gpu));
}
