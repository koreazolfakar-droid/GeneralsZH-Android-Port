// GeneralsX @bugfix Codex 23/10/2026 Keep invalid D3D8 index ranges away from GLES.
// CPU-side, backend-independent helpers; no GL calls or allocations.
#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

inline bool gxIndexWindowFits(size_t bufferBytes, size_t firstIndex, size_t indexCount, size_t indexSize)
{
    if (indexSize != 2 && indexSize != 4) return false;
    const size_t available = bufferBytes / indexSize;
    return firstIndex <= available && indexCount <= available - firstIndex;
}

// A terrain mesh whose indices address vertices outside its CPU-shadow VB can
// generate giant, screen-spanning triangles on GLES. Do not ask GL to consume
// that invalid range. All arithmetic is bounds-checked before access.
inline bool gxTerrainIndicesFitVertices(const unsigned char *indices, size_t indexCount,
                                        size_t indexSize, size_t baseVertex,
                                        size_t stride, size_t vertexBufferBytes)
{
    if (!indices || stride == 0 || (indexSize != 2 && indexSize != 4)) return false;
    const size_t availableVertices = vertexBufferBytes / stride;
    if (baseVertex >= availableVertices) return false;
    const size_t countFromBase = availableVertices - baseVertex;
    for (size_t i = 0; i < indexCount; ++i) {
        uint32_t index = 0;
        if (indexSize == 2) {
            uint16_t value;
            std::memcpy(&value, indices + i * indexSize, sizeof(value));
            index = value;
        } else {
            std::memcpy(&index, indices + i * indexSize, sizeof(index));
        }
        if ((size_t)index >= countFromBase) return false;
    }
    return true;
}
