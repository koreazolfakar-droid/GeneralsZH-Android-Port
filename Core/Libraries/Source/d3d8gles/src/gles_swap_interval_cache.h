#pragma once

#include <atomic>

// Applying the same EGL swap interval every present may re-enter the driver.
// Reapply only on a changed request or after an SDL context handoff/recreation.
namespace gxrt {
class SwapIntervalCache {
public:
    bool needsApply(int requested) const {
        return requested >= 0 && applied_.load(std::memory_order_acquire) != requested;
    }
    void applied(int requested) {
        applied_.store(requested, std::memory_order_release);
    }
    void invalidate() {
        applied_.store(-1, std::memory_order_release);
    }
private:
    std::atomic<int> applied_{-1};
};
} // namespace gxrt
