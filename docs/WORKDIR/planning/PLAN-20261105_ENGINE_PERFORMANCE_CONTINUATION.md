# Android engine performance continuation

Continue PR #45 from 0c97b711; preserve the existing eight performance/test/documentation commits.

- [x] Inspect commit changes, native run 41971063496, artifact hashes, and live OTA baseline.
- [x] Reproduce redundant unchanged static-terrain DISCARD uploads in the production extraction fixture. Skip only byte-identical initialized prefixes; retain full uploads for changed bytes, dynamic buffers, undefined tails, and allocation. Keep FIFO ownership and Mali index paths intact.
- [x] Exercise actual catch-up orchestration with a deterministic clock and state transitions. Stop extra ticks when game/network/replay/pause/freeze state changes or the regular tick did not run. Keep per-frame step/time caps.
- [x] Require the catch-up model and orchestration checks in the native report and OTA preparation gate; reject reports missing either check.
- [x] Reproduce CI producer-wait timeout and repair the lost completion wake; validate 100,000 races under ThreadSanitizer.
- [ ] Run host regressions and ASan/UBSan, rendering checks where available, and exact-source dual AArch64 validation. Do not run APK packaging.
- [ ] Verify both library stamps, hashes and dependencies, signed baseline, and rollback retention. Merge and publish only when acceptance gates pass.

Current native artifacts are engine 3676, same source 0c97b711, 30/60Hz. Device evidence is explicitly NOT TESTED. No connected device or newer raw device log is present in this workspace. The live baseline is engine 3667 / serial 32. Do not substitute host byte-count measurements for device performance or gameplay validation.
