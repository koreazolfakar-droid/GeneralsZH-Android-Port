#include "Common/GXCatchUpBudget.h"
#include "gles_swap_interval_cache.h"
#include <cassert>
#include <cmath>
#include <limits>
#include <initializer_list>
int main() {
    using GXCatchUpBudget::remainingMs;
    assert(remainingMs(0.0, 30) == 8.0);
    assert(remainingMs(0.0, 60) == 8.0);
    assert(std::fabs(remainingMs(20.0, 30) - (800.0 / 30.0 - 20.0)) < 1e-8);
    assert(remainingMs(27.0, 30) == 0.0);
    assert(remainingMs(14.0, 60) == 0.0);
    assert(remainingMs(100.0, 30) == 0.0);
    assert(remainingMs(-1.0, 30) == 0.0);
    assert(remainingMs(1.0, 0) == 0.0);
    assert(remainingMs(std::numeric_limits<double>::quiet_NaN(), 30) == 0.0);
    // GeneralsX @performance Codex 05/11/2026 A 40-FPS renderer must
    // maintain the 60-Hz simulation floor in offline gameplay.
    assert(GXCatchUpBudget::needsNormalSpeedFloor(60, 60, false));
    assert(GXCatchUpBudget::needsNormalSpeedFloor(1000000, 60, false));
    assert(!GXCatchUpBudget::needsNormalSpeedFloor(30, 60, false));
    assert(!GXCatchUpBudget::needsNormalSpeedFloor(60, 60, true));
    assert(GXCatchUpBudget::normalSpeedBudgetMs(60) == 6.0);
    assert(GXCatchUpBudget::normalSpeedBudgetMs(30) == 6.0);
    assert(GXCatchUpBudget::normalSpeedBudgetMs(0) == 0.0);
    assert(GXCatchUpBudget::accrueNormalDebt(1.0, 3.0, 60) == 3.0);
    assert(std::fabs(GXCatchUpBudget::accrueNormalDebt(0.0, 0.001, 60) + 0.94) < 1e-12);
    assert(GXCatchUpBudget::accrueNormalDebt(0.0, -1.0, 60) == 0.0);
    assert(GXCatchUpBudget::accrueNormalDebt(0.0, std::numeric_limits<double>::quiet_NaN(), 60) == 0.0);
    for (int hz : {30, 60}) {
        const int renderFps = hz == 60 ? 40 : 20;
        double debt = 0.0;
        int simTicks = 0;
        for (int i = 0; i < renderFps * 10; ++i) {
            debt = GXCatchUpBudget::accrueNormalDebt(debt, 1.0/renderFps, hz);
            ++simTicks; // the regular mandatory game tick
            for (int extra=0; extra<3 && debt>=1.0; ++extra) {
                --debt;
                ++simTicks;
            }
            if (debt > 1.0) debt=1.0;
        }
        assert(std::abs(simTicks-hz*10) <= 1);
    }

    gxrt::SwapIntervalCache cache;
    assert(!cache.needsApply(-1));
    assert(cache.needsApply(1));
    cache.applied(1);
    assert(!cache.needsApply(1));
    assert(cache.needsApply(0));
    cache.applied(0);
    assert(!cache.needsApply(0));
    cache.invalidate();
    assert(cache.needsApply(0));
    return 0;
}
