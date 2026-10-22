// GeneralsX @performance Codex 22/10/2026: validate a prepared terrain quad
// before locking the D3D buffer. The staging vertices hold the last geometry
// version; the diffuse cache holds the last D3D VB colors (dynamic lighting
// can change colors without changing the staging geometry).
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

template <typename Vertex>
inline bool GXTerrainQuadNeedsUpload(const Vertex *previousGeometry,
    const Vertex *newGeometry, const uint32_t *submittedDiffuse)
{
    // Unknown GPU color state cannot prove equality. The caller only enables
    // the fast path on a fully initialized tile with a valid diffuse cache.
    if (!previousGeometry || !newGeometry || !submittedDiffuse)
        return true;
    if (std::memcmp(previousGeometry, newGeometry, 4 * sizeof(Vertex)) != 0)
        return true;
    for (size_t i = 0; i < 4; ++i) {
        if (submittedDiffuse[i] != newGeometry[i].diffuse)
            return true;
    }
    return false;
}
