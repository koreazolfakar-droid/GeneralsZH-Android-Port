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
// GeneralsX @performance Codex 05/11/2026 Repair Android's normal-speed
// single-player tick shortfall when the renderer cannot keep up. The game
// already advances one tick per render; this is *additional* bounded debt,
// not a new source of input events or a replay/network scheduler.
inline bool needsNormalSpeedFloor(int configuredRenderFps, int normalFps, bool logicScaleEnabled)
{
    return !logicScaleEnabled && normalFps > 0 && configuredRenderFps >= normalFps;
}

inline double accrueNormalDebt(double debt, double elapsedSeconds, int normalFps)
{
    if (normalFps <= 0 || !std::isfinite(debt) ||
        !std::isfinite(elapsedSeconds) || elapsedSeconds < 0.0)
        return 0.0;
    // Do not queue seconds of simulation after loading, backgrounding or a
    // GPU stall. The mandatory tick already ran in the normal engine path.
    const double elapsed = elapsedSeconds < 0.1 ? elapsedSeconds : 0.1;
    const double next = debt + elapsed * normalFps - 1.0;
    if (next > 3.0) return 3.0;
    if (next < -1.0) return -1.0;
    return next;
}

inline double normalSpeedBudgetMs(int normalFps)
{
    // GPU-bound TEOD may spend the whole frame rendering. Allow a small,
    // finite CPU recovery budget instead of denying all catch-up.
    if (normalFps <= 0) return 0.0;
    const double fraction = 400.0 / normalFps;
    return fraction < 6.0 ? fraction : 6.0;
}

} // namespace GXCatchUpBudget
