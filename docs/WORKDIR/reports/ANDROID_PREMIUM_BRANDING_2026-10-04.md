# Android premium branding — 2026-10-04

## Result and scope

Incremental branding update on `dev/mobile-v4`, based on source commit
`75be939345008ddbacb237f4570204fadf3bc849`. No new project, Activity,
framework migration, dependencies, game or Mod Manager changes.
The supplied ZIP contains only `icon.png` (1254×1254 RGB) and
`splash.png` (1254×1254 RGBA). These originals were used directly with uniform
resampling and padding only. No generative artwork, redraw, or alpha removal.

## Root-cause findings and remaining device verification

The baseline has **no custom splash screen**, no SplashActivity, no `values-v31`
startup theme, no `windowSplashScreenAnimatedIcon`, and no startup width/height
or unequal X/Y animation. SetupActivity is the sole launcher entry. Its launch
theme was the ordinary Material settings theme. Android 12 therefore used the
application's old adaptive launcher icon as the default splash artwork, rather
than a dedicated transparent startup emblem. That old foreground was extracted
from Generals.ico; its canvas is square (432×432), as is its alpha bounding box.
The Home battlefield image uses CENTER_CROP, but is unrelated to a startup emblem
and was not changed. No startup FIT_XY or FillBounds was found.

**The precise cause of the reported wide → vertical effect is not established.**
There is no recording/log from the affected phone and no connected device here.
It would be incorrect to claim a measured stretch or identify an unsupported
layout bug. The confirmed configuration defect (implicit adaptive launcher-icon
fallback instead of explicit startup branding) is corrected. A square bitmap
canvas, preserved source aspect ratio, center gravity, and explicit Android 12
artwork eliminate the application's own opportunity to stretch/swap logos.
Frame-1 and OEM animation behavior still require a real cold-launch recording.

## Launcher resources

Both `ic_launcher` and `ic_launcher_round` raster sets were generated from
`icon.png`. Round raster variants use additional uniform padding for a circle
mask. API 26+ XML adaptive variants share a single new foreground and navy
background. Both are resolved as adaptive icons on this app's minSdk 28+;
the raster sets are provided as requested and for resource completeness.

| Density | Launcher and round raster dimensions |
|---|---|
| mdpi | 48×48 px |
| hdpi | 72×72 px |
| xhdpi | 96×96 px |
| xxhdpi | 144×144 px |
| xxxhdpi | 192×192 px |

Adaptive foreground: `mipmap-xxxhdpi/ic_launcher_foreground.webp`, 432×432 px
(108 dp), with the supplied square artwork uniformly scaled to 256×256 px
(64 dp) and centered. Neutral padding protects the emblem under launcher masks.
No monochrome icon existed; none was fabricated. The existing unused setup gear
icon and other potentially referenced resources were retained.

All twelve new raster resources are **lossless WebP** (`VP8L` verified; no lossy
`VP8` chunks). Foreground and splash WebP preserve alpha. XML remains XML.

## Startup theme and transition

- Manifest: add `android:roundIcon`; change only SetupActivity's launch theme.
  Package, permissions, game Activity and orientation behavior are unchanged.
- `values/themes.xml`: add Theme.GeneralsZHStartup, inheriting the existing
  settings theme, with a centered launch-window layer-list and navy bars.
- `values/colors.xml`: add only `gzh_startup_background` = `#080E18`.
- `values-v31/themes.xml`: add native Android 12+ splash attributes with the
  same background and explicit **non-adaptive** `startup_emblem`. Transparent
  icon ground prevents a separate app-icon tile.
- `drawable-xxxhdpi/startup_emblem.webp`: 1152×1152 px / 288 dp transparent
  canvas; splash.png is uniformly fitted to 560×560 px / 140 dp in the center.
  Every nonzero-alpha pixel is within 80.04 dp of the center, below Android's
  96 dp safe radius. Wings, sword, crest and star remain inside the safe circle.
- `drawable/startup_background.xml`: bitmap with center gravity at intrinsic
  density-correct size, without fill scaling, forced rectangular bounds or crop.
- SetupActivity: restore Theme.GeneralsZHSettings **before super.onCreate** and
  widget creation. This is the native theme handoff equivalent; no AndroidX
  SplashScreen dependency or `postSplashScreenTheme` attribute is needed.
- No additional custom loading screen exists or was added. No duplicated logo
  surface, artificial timer, sleep, startup wait or animation listener.
- Existing platform exit behavior is retained. No custom zoom, rotation,
  nonuniform scale or 400–700 ms holding animation was introduced, because
  startup should enter the existing app as soon as ready.

## Removed assets

The old `mipmap-xxxhdpi/ic_launcher_foreground.png` is replaced with WebP using
exactly the same Android resource ID. References are resource IDs, not filename
extensions; no PNG filename references remain. No other branding assets were
removed. The previous test APK was moved out of apk/ into the fallback copy
`/workspace/scratch/branding/baseline.apk`; apk/ contains only the new test APK.
Original supplied files remain in `/workspace/scratch/branding/`.

## Verification and build

- Local incremental command, reusing the existing Docker build environment:
  `docker exec generalszh-android-build bash /run/run-mod-library-gradle.sh :app:testDebugUnitTest :app:assembleDebug`
- Final result: **BUILD SUCCESSFUL**, 43 seconds, 4 tasks executed / 37 up-to-date.
- All **33 tests pass**, zero failures/errors. New startup test uses Android
  API 28, 31 and 35, native bitmap decoding, square dimensions and real alpha,
  Android 12+ theme resource selection, and restoration of the existing Material
  UI theme. Existing 30 tests cover launcher and Mod Manager regressions.
- Initial test run failed only because Robolectric's legacy bitmap shadow
  reported no alpha for WebP. Switching the new test to native graphics decode
  resolved it; no production change was made for the test failure. Build rerun.
- Resource compilation and Java compilation passed; git diff --check passed.
- All 12 WebP files decode and have the requested dimensions and lossless codec.
- APK ZIP CRC, APK Signature Scheme v2 and 4-byte zipalign checks passed.
- Certificate unchanged: `644a3b0f8234c6ea8960ece9b55a161c00966b8dd522d2558d84883f4f77c48e`.
- All 17 packaged native libraries are byte-identical to the fallback, including
  the distinct 30 Hz `libmain.so` and 60 Hz `libmain60.so`. Ten runtime assets
  are byte-identical. All 43 recorded native output/cache files retain SHA-256,
  sizes and nanosecond modification times. **Native code was not rebuilt.**
- No clean, cache deletion, NDK/CMake/vcpkg operation or CI run.
- Warnings: existing AGP 8.5.2 compileSdk 35 support warning and Java deprecated
  API note on the first compile. No resource/compiler errors in the final run.
  Global lint was not rerun; the baseline's known lint findings are not claimed
  resolved by this task.
- Workspace ADB reports **no devices**. No physical phone installation, actual
  game session, cold/warm frame capture, OEM masking, flicker, or frame-1 visual
  result is claimed. JVM launch tests do not execute Android's system splash
  window. These visual/device acceptance checks remain pending.

## APK

- `/workspace/GeneralsZH-Android-Port/apk/GeneralsZH-PremiumBranding-debug.apk`
- Size: **72,830,203 bytes** (69.46 MiB).
- SHA-256: `b98efde60801691423cc4a311301ac2c881fbb2f7af433eba6bd3217eeb8babe`.
- applicationId, versionCode 10400, versionName 1.4.0 and signing configuration
  unchanged; existing installations can be updated with `adb install -r`.

## Every changed/generated/removed file

- `android/app/src/main/AndroidManifest.xml`
- `android/app/src/main/java/com/generalsx/zerohour/SetupActivity.java`
- `android/app/src/main/res/drawable-xxxhdpi/startup_emblem.webp`
- `android/app/src/main/res/drawable/ic_launcher_background.xml`
- `android/app/src/main/res/drawable/startup_background.xml`
- `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml`
- `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml`
- `android/app/src/main/res/mipmap-hdpi/ic_launcher.webp`
- `android/app/src/main/res/mipmap-hdpi/ic_launcher_round.webp`
- `android/app/src/main/res/mipmap-mdpi/ic_launcher.webp`
- `android/app/src/main/res/mipmap-mdpi/ic_launcher_round.webp`
- `android/app/src/main/res/mipmap-xhdpi/ic_launcher.webp`
- `android/app/src/main/res/mipmap-xhdpi/ic_launcher_round.webp`
- `android/app/src/main/res/mipmap-xxhdpi/ic_launcher.webp`
- `android/app/src/main/res/mipmap-xxhdpi/ic_launcher_round.webp`
- `android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.webp`
- `android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_foreground.png`
- `android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_foreground.webp`
- `android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_round.webp`
- `android/app/src/main/res/values-v31/themes.xml`
- `android/app/src/main/res/values/colors.xml`
- `android/app/src/main/res/values/themes.xml`
- `android/app/src/test/java/com/generalsx/zerohour/StartupBrandingTest.java`
- `apk/GeneralsZH-PremiumBranding-debug.apk`
- `apk/GeneralsZH-TacticalLauncher-dedup-debug.apk`
- `docs/DEV_BLOG/2026-10-DIARY.md` (session note)
- `docs/WORKDIR/reports/ANDROID_PREMIUM_BRANDING_2026-10-04.md` (this report)

No game engine, gameplay, rendering, audio, controls, mod import/validation,
selection/persistence, Vanilla/mod launch, storage, permissions, or unrelated
application UI functionality was changed.

## Diff summary

`git diff --stat`: 26 changed file entries: one production Java source, one JVM
test, one manifest, 20 resource entries, one APK replacement, and two documents.
