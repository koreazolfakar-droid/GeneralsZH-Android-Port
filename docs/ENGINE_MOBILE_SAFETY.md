# Mobile Engine Safety Baseline

This branch starts mobile-engine optimization from the known-good Android/mod baseline:

`b21ec5d94d456e2078229436e6c4e676edd9dd04`

## Zero-regression rule

Profiling and performance work must not silently change the legacy content contract. The first compatibility gate therefore freezes the source entry points that control:

- BIG archive access
- generic/local filesystem search
- INI parsing
- Zero Hour command-line/mod loading
- W3D filesystem lookup
- save/replay transfer serialization
- Android Mod Manager active-mod resolution

The gate is intentionally source-level and fast. Existing build and replay workflows remain the deeper runtime checks.

## Development order

1. Keep the approved baseline unchanged.
2. Add observation-only profiling.
3. Build and run CI.
4. Test Vanilla and the known-good Android mod flow on device.
5. Optimize one subsystem at a time.
6. Do not advance the compatibility baseline merely to make CI green.

A protected compatibility file may be changed later only as an isolated, deliberate compatibility change with explicit runtime and replay validation.
