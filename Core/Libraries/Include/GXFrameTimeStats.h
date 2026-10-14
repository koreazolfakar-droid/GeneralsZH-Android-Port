// GeneralsX @feature Codex 14/10/2026 Bounded, allocation-free samples for GX_PERF.
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>

template <size_t Capacity>
struct GXFrameTimeStats
{
	static_assert(Capacity > 0, "Frame sample capacity must be positive");
	std::array<double, Capacity> samples{};
	std::array<double, Capacity> scratch{};
	size_t count = 0;
	size_t dropped = 0;
	double mainUs = 0.0;
	double worstMs = 0.0;

	void add(double intervalMs, double mainDurationUs)
	{
		mainUs += mainDurationUs;
		if (intervalMs > worstMs) worstMs = intervalMs;
		if (count < Capacity) samples[count++] = intervalMs;
		else ++dropped;
	}
	double percentile(double fraction)
	{
		if (count == 0) return 0.0;
		std::copy_n(samples.begin(), count, scratch.begin());
		const double requested = std::max(0.0, std::min(1.0, fraction));
		const size_t rank = (size_t)std::ceil(requested * count);
		const size_t index = rank ? rank - 1 : 0;
		std::nth_element(scratch.begin(), scratch.begin() + index, scratch.begin() + count);
		return scratch[index];
	}
	void reset()
	{
		count = dropped = 0;
		mainUs = worstMs = 0.0;
	}
};
