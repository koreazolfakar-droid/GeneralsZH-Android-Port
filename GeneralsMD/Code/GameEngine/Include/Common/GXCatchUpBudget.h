#pragma once

#include <cmath>

// Sped-up offline matches may consume spare CPU frame time, not monopolize
// the game thread after rendering and the first simulation step already
// exceeded their frame-time allowance. This never skips an ordinary game tick.
namespace GXCatchUpBudget {
inline double remainingMs(double spentMs, int normalFps)
{
    if (normalFps <= 0 || !std::isfinite(spentMs) || spentMs < 0.0)
        return 0.0;
    // Reserve 20% of a normal frame for pacing, input, and renderer progress.
    const double remaining = (800.0 / normalFps) - spentMs;
    if (remaining <= 0.0)
        return 0.0;
    return remaining < 8.0 ? remaining : 8.0;
}
} // namespace GXCatchUpBudget
