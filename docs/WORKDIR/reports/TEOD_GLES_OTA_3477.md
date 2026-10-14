# Verified Engine 3477 OTA release

Published and independently verified on 2026-10-14. No APK rebuild or distribution.

- Engine source: `0c2abdb81c76261f2ced12d5f5b1094a8cef625b`; existing complete-history sequence **3477**.
- [PR #19](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/pull/19): merged into `dev/mobile-v4` at `30aedecd442d3e808d846e681fa45532975a2043`.
- Merged source tree equals the exact native-tested source tree.
- [ARM64 30/60Hz incremental CI](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/38522261320): SUCCESS; all 18 required source checks passed. Existing SDK/NDK/CMake/vcpkg/ccache/native state preserved.
- [Signed OTA publisher](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/38524400292): SUCCESS; publisher-only commit `e3398abdd1c99ee6c258279aae9faef0bb4d7c70`.
- [Live application manifest](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/manifest.json): **serial 14**, engine **3477**, correct channel and source.
- [Detached signature](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/manifest.json.sig): exact manifest bytes verify with the original APK-pinned ECDSA P-256 public key.

## Verified binaries and APK compatibility

| File | Decompressed bytes | SHA-256 |
| --- | ---: | --- |
| [libmain.so, 30Hz](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/engine/3477/libmain.so.gz) | 42,279,920 | `cf3a6c4cd9f7f894a35ad9d8226967372b55285c1a4f3ed553e93ed96f468d20` |
| [libmain60.so, 60Hz](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/engine/3477/libmain60.so.gz) | 42,288,336 | `e16e0e38d2bb6c0a487b4a4fb23bd85d8d0a906b0956e2ac8d66ed885acde59f` |

Both exact public URLs returned HTTP 200. Downloaded gzip payloads decompress to
these sizes/hashes; AArch64 ELF64 dynamic GitSHA1/GitRevision symbols match the
source and 3477. JNI/SDL entry points and DT_NEEDED dependencies match the existing
Bootstrap APK. All 15 non-engine native fingerprints and the update trust root
match the verified APK. Availability is confirmed for installations matching
those dependencies and using this existing update channel. The user's installed
APK was not supplied, so its fingerprint and actual installation are NOT TESTED.

No GitHub Release/tag is part of this engine-only protocol: the live signed
`updates` branch manifest and immutable gzip URLs are the release endpoints.
The `sign-update.yml` dispatch returned GitHub 404 because that branch-only file
was unregistered. The already registered one-time publisher was reused, with the
exact successful run/source, merged predecessor tree, prior Engine 3472/serial 13
and one-file trigger pinned. Original signing/publishing helpers remain unchanged.

## Verified fixes, comparisons and limits

Ordinary buffer streaming over 256 bytes previously allocated a heap Blob for
each upload. Bounded uploads now travel inline through the existing command ring,
with the same FIFO order, mapping flags and large-upload/map-refusal fallback.
491 synthetic ordinary uploads allocate 0 Blobs instead of 491. Static VB/IB reuse
and synchronized/NOOVERWRITE/DISCARD behavior pass production host tests.

Partial terrain updates previously locked a full tile although they wrote a
rectangle. The lock now covers its contiguous enclosing vertex range, retaining
ordinary synchronized flags and all existing geometry/lighting calculations.
The corrected host fixture extracts the actual 32-byte VertexFormatXYZDUV2 and
32x32 tile side: one cell marks 128 bytes instead of 131,072, with exact matching
vertex bytes. 166,464 representative rectangles, 2048 production-sized rectangles
and boundary/full-tile cases pass ASan/UBSan for both old/new source.

The initial CI fixture used generic 44-byte vertices and a representative 16x16
tile (176 vs 45,056 bytes). That proved the same range/FIFO invariants, but did not
match production terrain byte sizes. Corrected the fixture and comparison after
release; its stronger local checks pass, and native engine code is unchanged.
These numbers describe host operation counts, not Android FPS or GPU duration.

PR #18 diagnostics were reused rather than duplicated. The existing GX_PERF
stream now includes bounded exact frame P50/P95/P99 windows and the first ~120
seconds of an active non-shell battle. Logic/AI/pathfinding splits, uploads,
terrain pass counts, shader/cache timings, worker waits and optional GPU timers
remain available. Full device allocation/archive timing and exact first-present
latency require device traces.

Synthetic named TEOD BIGs pass production archive precedence/loading and fresh
process switching checks; actual TEOD/Project X models, textures, factions,
effects, terrain culling, save/replay CRC and multiplayer on a device are NOT
TESTED. No device or original mod assets were available. The dominant battle
critical path and real FPS improvement are NOT MEASURED; this release does not
claim the reported 17–19 FPS collapse is resolved. AI scheduling/gameplay,
rendering order, shaders/effects and texture quality are preserved.

CI skipped TLS because host libcurl development files were absent; production
TLS tests passed locally. Optional video/particle test scripts were absent from
the original source HEAD and were not tested in CI. Cache/state, security,
localization, saves, packaging/native provenance, OTA crypto, mod precedence,
Project X script lookup, AI guards and blocked-path policy regressions passed.

## Changed files

Engine changes, diagnostics, tests and release control compared with the original
`88d5758621658736e652b5fcaa24a3b8531746e0` development head:

- `.github/engine-baseline/build.py`
- `.github/workflows/publish-pinned-projectx-ai-ota.yml`
- `Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp`
- `Core/Libraries/Include/GXFrameTimeStats.h`
- `Core/Libraries/Source/d3d8gles/include/gles_thread.h`
- `Core/Libraries/Source/d3d8gles/src/gles_dispatch.cpp`
- `Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp`
- `GeneralsMD/Code/GameEngine/Source/Common/GameEngine.cpp`
- `GeneralsMD/Code/GameEngine/Source/GameLogic/AI/AI.cpp`
- `GeneralsMD/Code/GameEngine/Source/GameLogic/System/GameLogic.cpp`
- `docs/DEV_BLOG/2026-10-DIARY.md`
- `docs/WORKDIR/reports/ANDROID_GLES_DIAGNOSTIC_PHASE1.md`
- `docs/WORKDIR/reports/TEOD_GLES_UPLOAD_2026-10-14.md`
- `scripts/README.md`
- `scripts/qa/mod-archive-fixture.cpp`
- `scripts/qa/test-battle-perf-window.py`
- `scripts/qa/test-gles-upload-regressions.py`
- `scripts/qa/test-mod-archive-loading.py`
- `scripts/qa/test-vehicle-ai-v1.py`
- `scripts/update/prepare-engine-run.py`

Follow-up evidence: this report, `TEOD_GLES_OTA_3477.json`, and the corrected production-layout host fixture. See [implementation and device A/B procedure](TEOD_GLES_UPLOAD_2026-10-14.md) for the next reproducible device capture.
