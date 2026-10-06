# Our signed Engine Update channel

The Android launcher on `dev/mobile-v4` uses only
`https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/`.
It trusts `android/app/src/main/assets/update-public.pem`, a PUBLIC ECDSA P-256 SPKI
key. The old MYSOREZ signing identity is not used by this launcher.

## One-time secure setup — required before bootstrap APK assembly

The connected session cannot administer repository Actions secrets (HTTP 403).
Actions audit run 37416307932 confirmed `UPDATE_SIGNING_KEY` missing.
**Do not build or publish the bootstrap until the key has been securely installed.**

On your trusted computer, authenticate `gh` with permission to manage Actions
secrets for **koreazolfakar-droid/GeneralsZH-Android-Port**, open a source checkout
of `dev/mobile-v4`, then run:

```bash
bash scripts/update/setup-update-key.sh
```

This script checks secret-management permission before generating a key, refuses
to overwrite an existing key, generates P-256 in a mode-0700 temporary directory,
sends the PEM directly through standard input to `gh secret set`, and deletes the
private temporary file on exit. It prints no key value. Only after secret storage
succeeds does it write the PUBLIC PEM into the source asset path for review/commit.
Never paste the private PEM into this conversation, an issue, a commit or artifact.

GitHub location:
**Repository → Settings → Secrets and variables → Actions → Repository secrets →
UPDATE_SIGNING_KEY**. Verify the secret name there; do not copy its value out.

If the secret already exists, do not replace it. Run **Sign update** at
`dev/mobile-v4` with **public_identity_only = true**. The artifact
`own-update-public-identity` contains only `update-public.pem`; place that public
file at the asset path, verify its fingerprint and commit it. Newly added workflow
versions may need dispatch through their file/ref or registration on the default
branch; do not switch or reset the working source branch to fix registration.

The signing workflow compares the secret's derived public key byte-for-byte with
the source-pinned key before signing. A missing key, other curve, private PEM in
assets, upstream identity, or mismatched secret must fail closed.

## Bootstrap APK

Keep `applicationId = com.generalsx.zerohour` and the existing APK signing
certificate. Use the previously verified Engine 3333 APK/artifacts, preserve all
17 native dependency bytes and both engine rate slots. Recompile/package only the
changed launcher using the existing SDK/Gradle caches. Native provenance must
continue to describe the reused Engine 3333 source, separately from the new
launcher commit; do not relabel reused native binaries with the new source count.
Do not run a clean, rebuild native dependencies, delete caches or replace old APKs.
The public-key pre-build gate deliberately blocks an unprovisioned bootstrap.

Verify package/signer/version, public PEM, own URL in DEX, native hashes, both rate
slots, alignment, APK CRC and engine provenance before installation. Then:

```bash
adb install -r <bootstrap.apk>
```

Never uninstall or clear app data. Device launch/Save/Mod/Online/update activation
checks are NOT TESTED until performed on a real device.

## Future engine-only publication — after bootstrap device acceptance

Engine 3334 is **not published** in the bootstrap phase. Future sequence numbers
come from the complete Git history of the actual engine source; example numbers
are not hardcoded. Keep `libmain.so` = 30 Hz and `libmain60.so` = 60 Hz from the
same source commit. Build incrementally using the existing dependency graph and
cache. A changed non-engine native dependency still requires a new APK.

Prepare verified existing dual-engine outputs without building an APK:

```bash
python3 scripts/update/publish-update.py \
  --engine-dir <verified-dual-engine-directory> \
  --baseline-apk <installed-bootstrap.apk> \
  --source-commit <exact-engine-source-commit> \
  --out <new-empty-prepared-directory> --note "Description"
```

The publisher validates baseline provenance, all dependency hashes, the bootstrap
public identity, both actual ELF GitSHA1/GitRevision symbols and complete-history
sequence. It refuses identical rate slots, false Build 1 labels and missing
provenance. It prepares unsigned bytes locally; these are never published unsigned.
The existing `--apk` path remains available but now checks native provenance.
Support-card publication is explicit `--support <our-card.json>`; it does not
republish upstream donation identity by default. Community data stays on the
existing GeneralsOnline CDN; STUN/TURN values/order and PC checksum are unchanged.

Upload only the prepared directory as an Actions artifact named
`prepared-engine-update`; never include a private key. Dispatch **Sign update** at
`dev/mobile-v4` with `public_identity_only = false` and `prepared_run = <run ID>`.
It validates, signs using `UPDATE_SIGNING_KEY`, re-verifies the exact manifest and
engine payloads, and publishes with a normal fast-forward push. Concurrent
publication is serialized; a stale serial or immutable-engine collision fails.
No force-push is used. Settings-only publication retains the verified current
engine so later APK dependency checks continue working.

## Launcher safety

The own channel has independent serial, active-engine marker and download root.
Legacy update files remain untouched; the player's auto-check preference survives.
Private `files/update/remote_config.ini` and native `boot_pending` acknowledgement
remain at their existing paths. External Save/, Maps/, Options.ini, imported mods,
account state and game data are outside publication and update cleanup.

Manifest schema/channel/signature, rollback serial, engine sequence, inflated
size/SHA-256 and complete APK dependency set must verify. Both engines and their
signed metadata must be present before activation. Settings-only updates cannot
replace retained engine metadata. Downloaded files are rechecked before loading;
failed/missing/incompatible metadata uses the APK engine. Two boots that fail to
reach the main menu retain the existing APK fallback behavior.

Run host checks with `python3 scripts/qa/test-own-update-channel.py`. With a JDK,
this also runs the production `UpdateTrust` crypto tests. Android migration tests
are in `UpdateChannelMigrationTest`; they require the Android test environment.
