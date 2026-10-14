# Verified Engine 3481 signed OTA publication

GeneralsX @build Codex 14/10/2026

Engine **3481**, manifest **serial 15**, is published on the existing
`koreazolfakar-droid/mobile-v4/v1` channel. The owner explicitly requested
publication after reviewing the merged source, unsigned candidate and disclosure
that physical FPS/visual acceptance was unavailable. This is not a claim that
the complete FPS collapse is resolved or that device acceptance has passed.

## Provenance and execution

- Engine source: `c40a361857edfe70842f26ddb2a76d47ebda4ba4`.
- [PR #20](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/pull/20): merged to dev/mobile-v4 at `71c0bc47d57f5a1bed58841fc2fddceffcd60cb5`; its tree equals the tested source.
- [Native CI](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/38535040332): SUCCESS, 19 source suites, ARM64 30/60 pair, unchanged runtime dependencies, new_apk_required=false. Local online TLS fixtures pass; unavailable optional/device checks remain documented in the PR.
- Publisher-only controller: `238879aff9d9241f99182f3697502bdfa7892825`.
- [Signing/publication workflow](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/38538689452): SUCCESS, authenticated exact native-run source, prepared immutable pair, signed with the existing Actions secret, verified before push, then verified live downloads.
- Updates branch commit: `9db7b40425873412f7fedba70fc0b407527474aa`.

The branch-only sign-update.yml remains unregistered; the previously registered
publisher workflow is reused with exact source/run/predecessor/serial pins.
Signing and branch-push helpers, updater protocol and APK are unchanged. No
engine recompilation or APK redistribution occurred during publication. Existing
SDK/NDK/Gradle/CMake/ccache caches and older immutable engine paths are preserved.

## Independently verified public content

[Exact application manifest](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/manifest.json)
and [detached signature](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/manifest.json.sig)
were fetched without query parameters. The exact manifest bytes verify with the
ECDSA P-256 public key embedded in the original bootstrap APK. Native downloads
match the successful CI binaries byte-for-byte, including ARM64 source/build
stamps. All 15 runtime library fingerprints match that APK; JNI/SDL entry points
and DT_NEEDED were already checked against 3477. Configuration is unchanged.

| File | Native bytes | Native SHA256 |
| --- | ---: | --- |
| [libmain.so (30Hz)](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/engine/3481/libmain.so.gz) | 42,288,208 | `2cf558759d1cf4d706f2be4225c30c31cd34288f2ee6ef605a771b844152ae17` |
| [libmain60.so (60Hz)](https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/engine/3481/libmain60.so.gz) | 42,288,368 | `2f592d22b06d8714852c76911236a3e15d65d0db1b15f97bb84f18aede4fe75f` |

Manifest SHA256: `f06d6d98895118844b5925b570f6cc61370bf959819d59833653f63999e3159e`.
Compressed hashes/sizes and detailed evidence are in [verification JSON](TEOD_GLES_OTA_3481.json).
There is no separate GitHub Release/tag in this engine-only delivery protocol.

## Availability and acceptance

The current app's exact UpdateTrust URLs, signed own channel, increasing serial
and engine sequence, and unchanged APK dependency identity are verified. From
the launcher's Updates card choose **Check for updates / البحث عن تحديثات**,
finish download and verification, then restart the game to load engine 3481.
Actual phone installation/boot, FPS, mod visual correctness and multiplayer/replay
CRC are **NOT TESTED**: no ADB target or original mod assets are attached.

After installation use Performance summary only, record at least 125 seconds on
matched vanilla/TEOD/Project X scenes, and export View Logs -> Share. New CPU,
terrain-reuse, resource and nonfinite-AI probes are now downloadable through the
existing application. See [capture guide](../../HOWTO/ANDROID_BATTLE_PERFORMANCE_CAPTURE.md)
and [verified redundancy versus unmeasured critical path](TEOD_CRITICAL_PATH_2026-10-14.md).
