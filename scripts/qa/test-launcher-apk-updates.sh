#!/usr/bin/env bash
# APK updater verification using the *existing* Android SDK, Gradle caches and
# previously staged SDL Java glue. Intentionally never builds any native engine.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP="$ROOT/android/app"
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"

if [[ -z "$SDK" || ! -f "$SDK/platforms/android-35/android.jar" ]]; then
  echo "BLOCKED: Android SDK platform 35 missing. Reuse an existing SDK; not downloading tools." >&2
  exit 2
fi
if [[ ! -f "$APP/src/main/java-sdl/org/libsdl/app/SDLActivity.java" ]]; then
  echo "BLOCKED: staged SDL Java sources missing. Reuse Java glue from the existing build; do not rebuild C++." >&2
  exit 2
fi
if [[ ! -f "$APP/src/main/assets/update-public.pem" ]]; then
  echo "BLOCKED: pinned engine update public PEM is missing." >&2
  exit 2
fi

if [[ -x "$ROOT/android/gradlew" ]]; then
  GRADLE="$ROOT/android/gradlew"
elif command -v gradle >/dev/null 2>&1; then
  GRADLE="$(command -v gradle)"
else
  echo "BLOCKED: Gradle 8.x is not installed. Do not delete existing caches." >&2
  exit 2
fi

cd "$ROOT/android"
echo "Running Android Java-only APK updater tests (offline; no native rebuild/clean)"
"$GRADLE" --offline :app:testDebugUnitTest \
  --tests 'com.generalsx.zerohour.ApkUpdateManagerTest' \
  --tests 'com.generalsx.zerohour.LauncherHomeUiTest' \
  --tests 'com.generalsx.zerohour.UpdateChannelMigrationTest'
echo "PASS: launcher JVM tests completed. APK in-place/device installation still requires separate QA."
