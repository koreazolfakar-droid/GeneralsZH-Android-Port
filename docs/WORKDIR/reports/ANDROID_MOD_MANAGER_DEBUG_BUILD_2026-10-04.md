# Android Mod Manager Debug APK — 2026-10-04

## Result

The required local `./scripts/build/android/build-dual-hz.sh` completed with exit
code 0 on `dev/mobile-v4`. Both native passes linked successfully, and both
Gradle `assembleDebug` invocations reported `BUILD SUCCESSFUL`. The final APK
contains both engines, the Mod Manager, and transactional Safe Mod Import.
No compilation or packaging errors occurred and no source fixes were needed.

Repository: `koreazolfakar-droid/GeneralsZH-Android-Port`.
Built source commit: `e1d2ac7e8032aacddc62d938288308fc6eee1203` (after checkout and
`git pull --ff-only origin dev/mobile-v4`). The APK's `engine_build.txt` contains
`3293`, the commit count at this source revision. The subsequent artifact commit
only replaces the APK and adds build documentation.

No gameplay, AI, renderer, networking, or simulation source changed. The build
ran in a local Ubuntu 24.04 Docker container using this workspace's checkout;
GitHub Actions and CI were not used. Publication attempts targeted only
`dev/mobile-v4`; `main` is untouched. The APK and artifact commit are complete
locally, but remote publication is blocked by the errors recorded below.

## APK

| Field | Value |
|---|---|
| Filename | `GeneralsZH-ModManager-debug.apk` |
| Repository path | `apk/GeneralsZH-ModManager-debug.apk` |
| Absolute workspace path | `/workspace/GeneralsZH-Android-Port/apk/GeneralsZH-ModManager-debug.apk` |
| Size | 71,966,725 bytes (68.63 MiB) |
| SHA-256 | `b908fa5d3b419cbaadaac2e262a2b07df8742fd0bdb1f882ec0185a0bacf342e` |
| Package | `com.generalsx.zerohour` |
| Version | `1.4.0` / versionCode `10400` |
| Variant | Debug (`android:debuggable=true`) |
| ABI | `arm64-v8a` |
| Minimum Android | API 28 / Android 9 |
| Target / compile SDK | API 35 |

The previous `apk/GeneralsXZH-android-v1.4.0.apk` is removed, leaving only this
current test APK in `apk/`.

## Dual-Hz verification

Both engines were built from the same unchanged source tree. The first native
pass used `SAGE_HIGH_FPS_SIM=ON`, with
`GENERALS_ONLINE_HIGH_FPS_SERVER` defined in all 991 engine compilation commands.
The second pass used `SAGE_HIGH_FPS_SIM=OFF`, with the definition absent from all
991 commands. The native preset is `RelWithDebInfo`; the Android application
variant is Debug, as selected by the repository's build script.

| Packaged library | Tick rate | Bytes | SHA-256 |
|---|---|---|---|
| `libmain.so` | 30 Hz | 42,225,624 | `d1d8e97e898afe9ad3fb585627cd724c8f7bf64fd166f4dc862c1ff4dbaba594` |
| `libmain60.so` | 60 Hz | 42,225,784 | `ca9ecadf6b7e80cbc30e5faf165c49d978cae29df876b3c86d08e1fede8b5007` |

The packaged engine hashes match the corresponding completed native build
outputs byte for byte, and the two hashes differ. All 17 packaged native
libraries are ELF64 AArch64. Every `DT_NEEDED` dependency is either packaged or
provided by Android at API 28, including the system `libmediandk.so`.
DXVK D3D8/D3D9 also match their build outputs.

## Package checks

- `apksigner verify --verbose --print-certs`: passes, APK Signature Scheme v2.
- Signing certificate SHA-256:
  `644a3b0f8234c6ea8960ece9b55a161c00966b8dd522d2558d84883f4f77c48e`.
  This matches the previous APK and the repository's fixed Debug signing identity.
- `zipalign -c 4`: passes.
- ZIP CRC verification: passes, with no duplicate entries.
- `aapt dump badging`: Debug application, ARM64 only, minSdk 28, targetSdk 35.
- Compiled manifest: `ModManagerActivity` registered, Debug enabled, and
  `extractNativeLibs=true`.
- DEX includes `ModManagerActivity`, `ModManager`, and `ModImportService`.
- Required runtime assets include all four game fonts and the default driver.

This is an installable, signed APK ready for real-device testing. No physical
Android device was connected, so gameplay and import behavior on a device have
not been exercised during this build session.

## Toolchain

- Ubuntu 24.04, OpenJDK 17.0.20.1, Gradle 8.7, Android Gradle Plugin 8.5.2.
- Android NDK 27.2.12479018 (r27c), native API 28, Android SDK/build-tools 35.0.0.
- CMake 3.28.3, Ninja 1.11.1, Meson 1.3.2.
- Repository-pinned vcpkg commit
  `42e4e33e1505c9f47b58c21e0f557c1571b751ee` and DXVK submodule commit
  `46a3bc018bcae408d49d3c500e4e536a11f6789a`.
- Three build workers; Gradle's environment-level JVM encoding set to UTF-8.
  No repository build script or application source was altered for the host.

## Warnings and recovered setup issues

No native compilation or APK packaging errors occurred. The local build log
contains 27,452 compiler warning occurrences,
including repeated diagnostics from shared headers in both passes. These are
occurrences, not distinct defects. They cover the inherited engine and native
dependencies; no warning-only changes were made.

| Diagnostic category | Occurrences |
|---|---:|
| `-Wsuggest-override` | 13,028 |
| `-Winvalid-offsetof` | 8,450 |
| `-Wswitch` | 2,158 |
| `-Wmacro-redefined` | 1,778 |
| `-Winconsistent-missing-override` | 954 |
| `-Wlogical-not-parentheses` | 458 |
| `-Wconstant-conversion` | 116 |
| `-W#pragma-messages` | 76 |
| `-Wunused-value` | 74 |
| `-Wint-to-void-pointer-cast` | 56 |
| `-Wdeprecated-enum-float-conversion` | 46 |
| `-Wdeprecated-this-capture` | 46 |
| `-Wcomment` | 42 |
| `-Wformat` | 32 |
| `-Wtautological-constant-out-of-range-compare` | 18 |
| `-Wdelete-abstract-non-virtual-dtor` | 16 |
| `-Wimplicit-exception-spec-mismatch` | 12 |
| `-Wdeprecated-declarations` | 11 |
| `-Wdeprecated-enum-compare` | 10 |
| `-Wtautological-pointer-compare` | 10 |
| `-Wundefined-var-template` | 8 |
| `-Wint-to-pointer-cast` | 8 |
| `-Wmissing-field-initializers` | 7 |
| `-Wvexing-parse` | 6 |
| `-Wpointer-bool-conversion` | 6 |
| `-W#warnings` | 4 |
| `-Wparentheses` | 4 |
| `-Wself-assign-field` | 4 |
| `-Wdelete-incomplete` | 4 |
| `-Wliteral-conversion` | 2 |
| `-Wenum-compare-switch` | 2 |
| `-Wdangling-else` | 2 |
| `-Wextra-tokens` | 2 |
| `-Wformat-truncation` | 1 |
| `-Wunused-but-set-variable` | 1 |

Other non-blocking messages:

- Android Gradle Plugin 8.5.2 was tested through compileSdk 34 and recommends a
  newer plugin for compileSdk 35. Both Debug packaging passes succeeded.
- Java compilation reports use of deprecated APIs.
- Gradle reports it cannot strip several native libraries and packages them as
  supplied. The repository script already strips the engines and supporting
  libraries itself and intentionally preserves DXVK symbols. Packaged engine
  and DXVK bytes were checked against the build outputs.
- Initial APT index downloads reported connection refusal because `sudo` did
  not retain the workspace proxy settings. Proxy configuration was corrected
  in the container, and prerequisites were installed without repository edits.
- The auxiliary dependency verifier initially omitted the Android system
  `libmediandk.so` from its allowlist. Its API-28 NDK stub was confirmed, the
  verifier was corrected outside the repository, and all checks passed.
- Git publishing initially lacked a credential helper; a retry using the
  existing GitHub authentication then returned HTTP 401 on the Git transport.
  GitHub CLI REST authentication and repository write permissions were valid;
  documentation blob writes succeeded. The APK blob upload was rejected with
  HTTP 422: "Sorry, your input was too large to process. Consider creating the
  blob in a local clone of the repository and then pushing it to GitHub."
  Further authenticated Git transport attempts also failed. No remote branch
  ref was updated. The final APK and commit remain available in this workspace.

The full build log, both CMake flag snapshots, verification JSON, and signing
output are retained locally under ignored `logs/`. Engine symbol tables are
retained under ignored `build/dual-hz-symbols/` for later device diagnostics.
