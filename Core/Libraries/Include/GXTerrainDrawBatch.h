// GeneralsX @performance Codex 04/11/2026 Concatenate consecutive fixed-grid
// tiles without welding vertices or changing triangle order or pass boundaries.
#pragma once
#include <algorithm>
#include <cassert>
namespace GXTerrainDrawBatch {
// Four 4096-vertex, 32-byte tiles retain the 512 KiB terrain snapshot limit.
static constexpr unsigned tilesPerBatch = 4;
inline unsigned tileCount(unsigned total, unsigned first) {
	assert(first < total);
	return std::min(tilesPerBatch, total-first);
}
inline unsigned vertexOffset(unsigned tile, unsigned verticesPerTile) {
	return (tile%tilesPerBatch)*verticesPerTile;
}
inline void fillIndices(unsigned short *out, unsigned tiles, unsigned verticesPerTile) {
	assert(tiles && tiles<=tilesPerBatch && tiles*verticesPerTile<=65535);
	assert(verticesPerTile%4==0);
	for(unsigned tile=0;tile<tiles;++tile)
		for(unsigned quad=0;quad<verticesPerTile;quad+=4) {
			const unsigned base=tile*verticesPerTile+quad;
			for(unsigned corner : {0u,2u,3u,0u,1u,2u}) *out++=static_cast<unsigned short>(base+corner);
		}
}
}
