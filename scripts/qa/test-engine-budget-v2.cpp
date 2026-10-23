#include "Common/GXCatchUpBudget.h"
#include "gles_swap_interval_cache.h"
#include <cassert>
#include <cmath>
#include <limits>
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
