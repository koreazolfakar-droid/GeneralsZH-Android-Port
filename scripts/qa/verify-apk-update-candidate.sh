#!/usr/bin/env bash
# Read-only APK release candidate preflight. No install/build/sign/publish/clean.
set -euo pipefail
if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: bash scripts/qa/verify-apk-update-candidate.sh NEW.apk [PREVIOUS.apk]" >&2
  exit 2
fi
NEW="$1"; OLD="${2:-}"
[[ -f "$NEW" ]] || { echo "BLOCKED: APK not found" >&2; exit 2; }
[[ -z "$OLD" || -f "$OLD" ]] || { echo "BLOCKED: prior APK not found" >&2; exit 2; }
BUILD_TOOLS="${ANDROID_BUILD_TOOLS:-${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}/build-tools/35.0.0}"
AAPT="$BUILD_TOOLS/aapt"; SIGNER="$BUILD_TOOLS/apksigner"
[[ -x "$AAPT" && -x "$SIGNER" ]] || {
  echo "BLOCKED: existing Android SDK build-tools 35 required; no downloads" >&2; exit 2;
}
metadata() {
  "$AAPT" dump badging "$1" | sed -n '1p'
}
field() {
  sed -n "s/.*$1='\([^']*\)'.*/\1/p" | head -1
}
"$SIGNER" verify --verbose "$NEW"
NEW_META="$(metadata "$NEW")"
NEW_PACKAGE="$(printf '%s\n' "$NEW_META" | field name)"
NEW_CODE="$(printf '%s\n' "$NEW_META" | field versionCode)"
NEW_NAME="$(printf '%s\n' "$NEW_META" | field versionName)"
[[ "$NEW_PACKAGE" == "com.generalsx.zerohour" && "$NEW_CODE" =~ ^[0-9]+$ ]] || {
  echo "FAIL: invalid package name or versionCode" >&2; exit 1;
}
cert() {
  "$SIGNER" verify --print-certs "$1" |
    sed -n 's/^Signer #1 certificate SHA-256 digest: //p' | head -1 | tr 'A-F' 'a-f'
}
NEW_CERT="$(cert "$NEW")"
[[ "$NEW_CERT" =~ ^[0-9a-f]{64}$ ]] || {
  echo "FAIL: missing signer SHA-256" >&2; exit 1;
}
if [[ -n "$OLD" ]]; then
  "$SIGNER" verify "$OLD"
  OLD_META="$(metadata "$OLD")"
  OLD_PACKAGE="$(printf '%s\n' "$OLD_META" | field name)"
  OLD_CODE="$(printf '%s\n' "$OLD_META" | field versionCode)"
  [[ "$OLD_PACKAGE" == "$NEW_PACKAGE" && "$OLD_CODE" =~ ^[0-9]+$ ]] || {
    echo "FAIL: old package metadata invalid" >&2; exit 1;
  }
  (( 10#$NEW_CODE > 10#$OLD_CODE )) || {
    echo "FAIL: update versionCode is not higher" >&2; exit 1;
  }
  [[ "$(cert "$OLD")" == "$NEW_CERT" ]] || {
    echo "FAIL: APK signing certificate changed" >&2; exit 1;
  }
fi
echo "PASS: package=$NEW_PACKAGE versionName=$NEW_NAME versionCode=$NEW_CODE"
echo "PASS: signer=$NEW_CERT"
sha256sum "$NEW"
echo "Device install and Mods/Save/30Hz/60Hz regression tests: NOT RUN"
