# Incremental engine updates without rebuilding the APK

Use the `engine-incremental` route in `.github/workflows/build-android.yml` on
`dev/mobile-v4`. It builds neither Java/Gradle nor an APK and never publishes.
Publishing remains a separate signed, provenance-checked operation after engine
and device acceptance. A compatible engine-only update requires every external
runtime dependency to match the installed bootstrap APK baseline.

## One-time migration of existing branch-scoped state

The verified old caches belong to `debug/android-audio-sfx-v1`; GitHub cannot
restore them directly in a workflow on the sibling `dev/mobile-v4` branch. No
full rebuild is needed. Export them into a retained artifact first.

1. Review `.github/engine-baseline/legacy-export.yml` in the mobile checkpoint.
   It contains only the export job, with no APK, native build or publisher job.
2. With owner authorization for this one cache-host exception, add that exact
   file as `.github/workflows/export-engine-state.yml` on
   `debug/android-audio-sfx-v1`. Preserve the branch's existing files and commits;
   do not merge/reset/replace its source or existing Android workflow.
3. Dispatch that new workflow on `debug/android-audio-sfx-v1`, setting
   `source_ref` to the reviewed **mobile checkpoint commit SHA**. Leave mode
   `export-legacy`. The job checks out mobile tooling/source, restores the exact
   old caches, verifies native provenance and dependencies, and uploads the
   `engine-incremental-state` artifact. No engine compilation occurs.
4. Record the successful export run ID. Dispatch `Build Android` on
   `dev/mobile-v4` with `engine_incremental_mode=inspect`,
   `engine_backup_run=<export-run-id>`, and `source_ref=<mobile-checkpoint-sha>`.
   This verifies/imports the full archive and seeds caches visible on mobile.
5. Confirm both workflow results are successful before requesting `build`.
   Cache IDs merely being listed is insufficient proof of restored state.

Example mobile inspection dispatch, after the export succeeded:

```bash
gh workflow run build-android.yml \
  --repo koreazolfakar-droid/GeneralsZH-Android-Port \
  --ref dev/mobile-v4 \
  -f engine_incremental_mode=inspect \
  -f source_ref=<reviewed-mobile-commit-sha> \
  -f engine_backup_run=<successful-export-run-id>
```

Do not add `create_release`, use the old APK job, or publish during migration.
The cache-host exception is not permission to develop game source on that branch.

## Subsequent engine builds

Commit and verify source on `dev/mobile-v4`; use the same immutable source SHA
for both rates. Dispatch `engine_incremental_mode=build` with that `source_ref`.
Leave `engine_backup_run` empty to use compatible branch-visible caches, falling
back to the most recent retained full artifact if any component is unavailable.
The real complete-history sequence is logged before compilation; never force a
specific engine number. The job imports unchanged dependencies, configures only
retained engine state, checks the Ninja plan, and builds `z_generals` for 30/60 Hz.

Download `engine-incremental-report` after each run. Check `result.json` for both
actual ELF source stamps/sequence, dependency comparison and source checks;
`compiler-summary.json` distinguishes ccache hits from successful compilation
and lists files actually compiled. `incremental-state.json` inventories objects,
CMake/Ninja state and engine outputs. The stripped engine pair is in the report
artifact on successful build; it is never automatically published.

A failed preflight is a stop, not permission for a clean build, reinstall or
cache deletion. Wrong workspace/toolchain, missing Ninja/objects, excessive
compile plan or changed dependency fingerprints must be diagnosed first. If
runtime hashes change, a new APK is required; do not bypass `requires_libs`.

## Prepare, sign and publish the verified pair

For an owner-authorized publication, dispatch the existing `Sign update` workflow
on `dev/mobile-v4` with `public_identity_only=false` and
`engine_build_run=<successful-incremental-build-run-id>`. Leave `prepared_run`
empty. The workflow downloads that run's engine report and the retained verified
Bootstrap 1.4.3/Engine 3333 APK, then runs `prepare-engine-run.py`. This refuses
failed regression checks, a different current source SHA, stale/mixed rate slots,
changed dependencies or a different bootstrap trust root. Preparation uses the
existing production publisher; it never compiles native code or builds an APK.

The existing signer checks the Actions secret's public identity against the
pinned own public key, signs the exact manifest and verifies both payloads before
the ordinary fast-forward publication. The previous engine files remain immutable
on `updates`. Download and independently verify the published manifest/signature
and both URLs after success; workflow success alone is not publication acceptance.
Record physical-device tests separately as PASS/FAIL or NOT TESTED.

## Retention

Keep the complete `engine-incremental-state` artifact outside Actions too:

```bash
gh run download <successful-run-id> \
  --repo koreazolfakar-droid/GeneralsZH-Android-Port \
  --name engine-incremental-state \
  --dir <new-empty-backup-directory>
```

Artifacts have 90-day retention and caches may be evicted earlier. Run `inspect`
and keep a fresh artifact before expiration; the workflow does not schedule paid
jobs automatically. It refuses to overwrite existing build/cache directories.
Restore on the same Actions workspace path and `ubuntu-24.04`, using the retained
SDK/NDK/tool versions. Do not unpack blindly or reconstruct state from an APK.

Device testing remains separate: launch Vanilla/mods, save/load, both engine
rates, graphics/audio/touch and online regression checks, then the existing secure
publisher can sign an accepted engine-only update. A workflow success alone is
not a device PASS. APK installs, when actually needed, use `adb install -r` and
never uninstall or clear data.
