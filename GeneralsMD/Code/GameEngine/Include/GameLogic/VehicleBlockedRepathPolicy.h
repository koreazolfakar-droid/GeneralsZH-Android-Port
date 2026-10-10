// Android Vehicle AI V1: deterministic cooldown for repeated blocked-path requests.
// This is deliberately state-free: the existing serialized pathfind timestamp
// in AIInternalMoveToState remains the sole source of history.
#pragma once

#include <cstdint>

namespace VehicleBlockedRepathPolicy
{
inline bool shouldRetry(std::uint32_t currentFrame,
                        std::uint32_t lastBlockedRepathFrame,
                        std::uint32_t minimumFrames)
{
    // Zero is the existing 'not attempted' sentinel, also used by older saves.
    // A restored timestamp later than the frame may come from a different
    // context; allow a new attempt rather than underflow the difference.
    return lastBlockedRepathFrame == 0 ||
           currentFrame < lastBlockedRepathFrame ||
           currentFrame - lastBlockedRepathFrame >= minimumFrames;
}
} // namespace VehicleBlockedRepathPolicy
