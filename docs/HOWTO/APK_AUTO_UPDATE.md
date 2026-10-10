# Full Android APK updates (launcher)

This feature is **separate** from the existing `UpdateManager` engine-only signed channel. It never writes engine libraries, the active-mod directory, game files, saves, or configuration.

## Behaviour

- When the launcher opens or resumes after six hours since its previous check, query the latest non-prerelease GitHub Release (if APK auto-check is enabled). The Updates section has its own APK-only check button and auto-check preference; the existing engine-only check button and preference are unchanged.
- Show a blue "Update Now" strip immediately above bottom navigation only for a newer release with an APK asset, SHA-256 digest and sensible size.
- Download on demand into `getCacheDir()/apk-updates/`; interrupted transfers retain a digest-named `.part` file and use HTTP Range on retry.
- Before requesting installation, verify bytes/size against GitHub's SHA-256, Android package name, strictly increasing APK `versionCode`, and the installed APK's actual signing certificates.
- Install via the platform package installer and existing `FileProvider`; on Android 8+ the user may need to approve installation from this source. Silent installation is intentionally unsupported.
- If the network fails, the installed app and all engine/mod state remain untouched.

The installer relies on **the same** `applicationId` and APK signing key on every release. The in-repository debug signing key used for the sideload workflow is not appropriate for a public store distribution.

## Publishing a new app version

1. Bump `android/app/build.gradle` versionName **and** versionCode to values higher than existing installed releases (e.g. after 1.4.7, use at least 1.4.8 / 10408 if not already used).
2. Build with existing cached Android toolchain/native artifacts, **not** a clean native build. Preserve both 30 Hz and 60 Hz engines and the current application ID/certificate.
3. Test installing the newer APK **over** the older signed version on a real phone and verify saved games, mods, settings, both engine modes and re-opening the launcher.
4. Publish the APK in a **non-prerelease, non-draft latest GitHub Release** in `koreazolfakar-droid/GeneralsZH-Android-Port`. The release tag must begin with `vMAJOR.MINOR.PATCH`; the asset must be a `.apk`, size <= 512 MiB, and GitHub must provide `digest: sha256:<64 hex>`.
5. From an **older** installed version, test detection, interrupted/resumed download, malformed/corrupt APK rejection, same-signer and different-signer cases, unknown-sources prompt, and successful user-approved install.

Note: the bootstrap version must itself contain the updater for future releases to show the banner. This branch intentionally **does not** build/publish an APK or bump version numbers ahead of device QA.

## Source and verification

- `android/app/src/main/java/com/generalsx/zerohour/ApkUpdateManager.java`
- `SetupActivity.java` banner, update check, progress, installer permission UX
- `ApkUpdateManagerTest.java` validates tag/version and URL policy

Before publishing a newly built APK, check its package identity, signer and version against the previously distributed APK, without installing anything:

```bash
bash scripts/qa/verify-apk-update-candidate.sh /path/to/new.apk /path/to/previous.apk
```

**Distribution signing caveat:** the existing Android Gradle configuration uses a fixed debug keystore committed in the repository. That enables in-place upgrades between development builds but is not a secure secret for wider public distribution. Plan a separately protected release identity / signed APK update manifest before a general rollout; switching the APK signing certificate without an explicit migration prevents ordinary upgrades of already-installed copies.

Run only launcher JVM tests with existing cached tools and staged SDL Java (no native rebuild):
```bash
bash scripts/qa/test-launcher-apk-updates.sh
```
This fails immediately if the SDK, Gradle cache or SDL Java staging are missing; it intentionally does not download a toolchain or regenerate native binaries.

Static source checks are **not** a substitute for Android Gradle compile, a package-signature fixture, or device testing. Do not merge/publish on the basis of this document alone.
