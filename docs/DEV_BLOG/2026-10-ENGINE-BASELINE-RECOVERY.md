# One-time limited engine baseline recovery

2026-10-06: Add an opt-in cache-hosted workflow for source 054b0a3c.
Restore the exact 3333 SDK/NDK, vcpkg, DXVK and compiler caches.
Import the verified retained adrenotools binary and headers, compile missing
direct runtime outputs only once, and stop on a Bootstrap fingerprint mismatch.
Build only z_generals in separate 30/60 Hz directories using the production
history-derived sequence. Preserve complete CMake/Ninja/object and compiler
state. No application source change, clean, APK build or publication.
