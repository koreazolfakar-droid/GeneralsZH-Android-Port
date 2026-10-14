// GeneralsX @feature Codex 14/10/2026 Bounded, allocation-free I/O attribution.
// Nested wall times: never sum lookup/BIG costs into the frame a second time.
#pragma once
#include <atomic>
#include <chrono>
#include <cstdint>

namespace GXResourceStats {
enum Kind { Lookup, BigRead, Count };
struct Counters { std::atomic<uint64_t> calls{0}, bytes{0}, us{0}; };
inline Counters *counters() { static Counters values[Count]; return values; }
struct Sample { uint64_t calls, bytes, us; };
inline Sample take(Kind kind) {
	Counters &c = counters()[kind];
	return {c.calls.exchange(0,std::memory_order_relaxed),c.bytes.exchange(0,std::memory_order_relaxed),c.us.exchange(0,std::memory_order_relaxed)};
}
struct Scope {
	bool enabled;
	Kind kind;
	uint64_t bytes = 0;
	std::chrono::steady_clock::time_point start;
	Scope(bool e, Kind k) : enabled(e), kind(k) { if (enabled) start=std::chrono::steady_clock::now(); }
	~Scope() {
		if (!enabled) return;
		Counters &c = counters()[kind];
		c.calls.fetch_add(1,std::memory_order_relaxed);
		c.bytes.fetch_add(bytes,std::memory_order_relaxed);
		c.us.fetch_add(std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count(),std::memory_order_relaxed);
	}
};
}
