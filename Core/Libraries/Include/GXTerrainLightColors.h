// GeneralsX @performance Codex 14/10/2026 Producer-side diffuse versions.
// Geometry writers must remember exactly the vertices copied to the real VB.
// Dynamic lighting keeps all calculations; only unchanged writes are omitted.
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <vector>

struct GXTerrainLightColors {
	std::vector<uint32_t> colors, pending;
	bool initialized = false, disabled = false;
	size_t begin, end = 0, checked = 0, changed = 0;
	explicit GXTerrainLightColors(size_t count) : colors(count,0), pending(count,0), begin(count) {}
	void resetRange() { begin=colors.size(); end=checked=changed=0; }
	void write(size_t index, uint32_t value) {
		++checked;
		if (pending[index]==value) return;
		pending[index]=value;
		begin=std::min(begin,index); end=std::max(end,index+1);
	}
	// The optimized legacy lighting loop can overwrite the same corner several
	// times. Only its final value matters; A -> B -> A within this one update
	// must leave the tile clean. No extra scan occurs when no write changed.
	void finishRange() {
		const size_t first=begin, last=end; begin=colors.size(); end=0;
		for(size_t i=first;i<last;++i) if(colors[i]!=pending[i]) {
			colors[i]=pending[i]; begin=std::min(begin,i); end=i+1; ++changed;
		}
	}
	template<class Vertex> void remember(size_t first, const Vertex *vertices, size_t count) {
		for (size_t i=0;i<count;++i) colors[first+i]=pending[first+i]=vertices[i].diffuse;
	}
};
