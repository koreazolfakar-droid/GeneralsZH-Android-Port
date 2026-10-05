# Protected mobile baseline to merged-engine APK — 05 October 2026

Repository: `koreazolfakar-droid/GeneralsZH-Android-Port`, branch `dev/mobile-v4`.
Protected START HEAD: `c90627048d34b910949bb4e6cabe17233104226a`.
The existing commits `ec641ffea`, `b02a30b11`, `c90627048` remain ancestors.
Safety tag: `mobile-v4-protected-3277-apk-20261005`, at that exact protected HEAD.

## Differential completed before source edits

[ENGINE_3277_APK_DIFFERENTIAL.json](ENGINE_3277_APK_DIFFERENTIAL.json) records all
94 changed paths at the protected HEAD and function-level classifications.
The independently verified signed upstream manifest is Engine 3277, serial 12.
The documented reconstruction is release `576e2265b` plus only the public GPU
delta `5eb288be6`; full original unpublished `2cc428d1b` content is unverified.
The previous [source audit](ENGINE_3277_SOURCE_AUDIT.md) contains full hashes,
save/online architecture and remaining runtime acceptance gaps.

- Already present: GPU timer opt-in/extension/procedure safety, serial-12 STUN
  3478 -> Google 19302 -> 53 and TURN 3478 -> 53 ordering, complete-history engine
  sequence generation, native release snapshot implementations.
- Newer current behavior retained: GameStateMap file-version-1/2 alignment and
  cleanup-failure guards, removal of the independent five-second TURN credential
  deadline, current active-mod localization/resource ownership and fallbacks.
- Missing verified native behavior: **none**. No redundant cherry-pick, whole-file
  replacement, reset or downgrade is needed. No simulation source is modified.
- Android/mobile differences remain: Mod Manager/imported archives/preferences,
  launcher/locales, graphics/audio/touch, user paths, saves and update architecture.
- Uncertain: original unpublished hotfix identity and real-device save/online
  outcomes. Source equivalence is not binary reproduction or device acceptance.

GameState/XferSave/XferLoad and snapshot registration remain identical to the
release. Map/header versions stay 2 and serialized ordering is unchanged. The
save directory remains external persistent `Generals/Command and Conquer
Generals Zero Hour Data/Save/`; no user-data cleanup or relocation is introduced.
Atomic save promotion, mod-save sidecars and autosave remain separate pending
work, not claimed implemented by this historical-baseline integration.

## Minimal packaging integration

The former `find ... libmain.so | head -1` could select a stale engine in a retained
build directory. Use the exact CMake target output, and verify the staged primary
and selected secondary libraries against those outputs. Add an APK-only provenance
asset containing source HEAD/tree, generated sequence and every native library's
size/SHA-256. Verify that asset, `engine_build.txt`, native set/bytes and ZIP paths
after Gradle packaging. This does not change engine/update manifest schemas.

Older cache-host workflow checkouts have depth 1. CI packaging now fetches only the
complete Git graph (`--unshallow --filter=blob:none`) before the existing strict
sequence resolver. It keeps the checked-out source HEAD and all compiled artifacts;
no fixed engine number, clean task or cache-key change is introduced. Normal full
checkouts need no fetch. The previous Build 1 root cause remains shallow commit
counting; the new engine sequence derives from the final complete Git history.

## Artifact and build protection

The known-working `apk/GeneralsZH-ModLocalization-debug.apk` remains untouched:
SHA-256 `dad623da50f4ecb54d51090249fc833051d636aaebe4e563a30f381565c2a602`.
Other existing APKs, local `build/`, object/PCH files, SDK/NDK, Gradle, vcpkg and
DXVK caches remain untouched. The new APK must use a separate filename.

All five existing GitHub cache entries are scoped to
`refs/heads/debug/android-audio-sfx-v1`. Its unchanged build workflow supports
`source_ref` and `require_existing_caches`; it can build the exact published mobile
commit without modifying that branch or reinstalling cached Android dependencies.
Cache guards must pass before building. Previous CI logs show compiler-cache
reuse, but no uploaded persistent CMake/Ninja object tree. Report the actual
compile actions/cache statistics; do not equate restoring ccache with reusing all
native objects. Dual 30/60 Hz compile definitions naturally invalidate affected
engine commands while preserving gameplay rate semantics.

## Validation and acceptance

Run host fixtures for build sequence, APK packaging, save-map cleanup and old-file
alignment, current Vanilla/mod text loading, GPU initialization, relay ordering,
signed manifest agreement, plus workflow/bash/whitespace validation. The legacy
`qa/smoke/test-mod-localization.py` has a previously diagnosed fixture compile
failure; retain and report it separately from the current passing suite.

After CI produces the APK, independently check both AArch64 engines, native hashes,
source provenance, complete-history count, library closure, package/version/signing
identity and 16 KiB alignment. APK generation is not device acceptance. Vanilla,
real old saves and update persistence, ~1.8 GB imported mods/switching, actual GPU,
audio/touch/settings/locales and Android-PC online start/play are **NOT TESTED**
until run on the real device. Installation may only use `adb install -r <apk>`;
never uninstall or clear application data.

Build results and final artifact hashes belong in the final handoff after the build;
this pre-build report does not claim an APK or runtime result.
