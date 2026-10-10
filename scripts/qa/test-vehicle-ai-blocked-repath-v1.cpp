// Compile and execute the *same* policy header used by AIStates.cpp.
// No simulated engine or placeholder test results.
#include "GameLogic/VehicleBlockedRepathPolicy.h"
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <vector>
#include <algorithm>

using VehicleBlockedRepathPolicy::shouldRetry;
static_assert(sizeof(std::uint32_t) == 4, "Expected game frame width");

static std::vector<std::uint32_t> runStuckFrames(std::uint32_t from,
                                                  std::uint32_t to,
                                                  std::uint32_t cooldown) {
    std::uint32_t last = 0;
    std::vector<std::uint32_t> attempts;
    for (auto frame = from; frame <= to; ++frame) {
        if (shouldRetry(frame,last,cooldown)) {
            attempts.push_back(frame);
            last = frame;
        }
    }
    return attempts;
}
int main() {
    // Initial/old save timestamp, timeout, exact boundary and before boundary.
    assert(shouldRetry(250,0,10));
    assert(!shouldRetry(259,250,10));
    assert(shouldRetry(260,250,10));
    assert(shouldRetry(261,250,10));
    assert(!shouldRetry(250,250,10));
    // Guard against unsigned underflow after restoring an older state.
    assert(shouldRetry(5,1000,10));
    // No division or wall-clock dependency; same frame inputs, same decisions.
    const auto first = runStuckFrames(100,499,10);
    const auto second = runStuckFrames(100,499,10);
    assert(first == second);
    assert(first.size() == 40); // 400 tick scenario with 10-tick cooldown.
    for (std::size_t i=1; i<first.size(); ++i) assert(first[i]-first[i-1]==10);
    // Both supported frame rates: no continuous blocked-path request storm.
    const auto thirty = runStuckFrames(1,30,10);
    const auto sixty = runStuckFrames(1,60,10);
    assert(thirty.size()==3);
    assert(sixty.size()==6);
    // Largest frame values must not invoke undefined signed math.
    const auto max = std::numeric_limits<std::uint32_t>::max();
    assert(!shouldRetry(max,max-1,10));
    assert(shouldRetry(max,max-10,10));
    assert(shouldRetry(2,max-1,10));
    // Stress randomized *bounded* frame sequences, no more than once/10 ticks.
    std::uint32_t seed=0xC001C0DEU;
    for (int test=0; test<100; ++test) {
        std::uint32_t last=0;
        for (std::uint32_t frame=1; frame<2400; ++frame) {
            seed=seed*1664525u+1013904223u;
            if (seed%3!=0) continue;
            if (shouldRetry(frame,last,10)) {
                if (last!=0) assert(frame-last>=10);
                last=frame;
            }
        }
    }
    return 0;
}
