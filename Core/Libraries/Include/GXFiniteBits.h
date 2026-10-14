// GeneralsX @feature Codex 14/10/2026 Non-finite diagnostics without floating
// comparisons (including signaling NaNs) or changes to the FP exception flags.
#pragma once
#include <cstdint>
#include <cstring>
inline uint32_t GXFloatBits(const float &value)
{
	uint32_t bits;
	static_assert(sizeof(bits) == sizeof(value), "IEEE float32 diagnostics required");
	std::memcpy(&bits, &value, sizeof(bits));
	return bits;
}
inline bool GXFloatFiniteBits(uint32_t bits) { return (bits & 0x7f800000u) != 0x7f800000u; }
