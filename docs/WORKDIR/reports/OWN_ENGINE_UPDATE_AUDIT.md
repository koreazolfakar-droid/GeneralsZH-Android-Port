# Own Engine Update channel audit — 6 October 2026

Repository `koreazolfakar-droid/GeneralsZH-Android-Port` (1398373925), branch
`dev/mobile-v4`, local/remote starting HEAD
`c3043dcfb89570351ca33adfa786bcede8532843`; working tree clean before inspection.
Baseline APK: Debug 1.4.2, native Engine 3333. Previous APKs remain unchanged.

## Existing architecture and findings

- `UpdateManager.java` and `publish-update.py` use the MYSOREZ raw `updates/`
  URL. The launcher embeds the upstream SPKI ECDSA P-256 public key.
- Signature verification covers exact manifest bytes. Downloads validate inflated
  size/SHA-256; `requires_libs` matches installed non-engine libraries. Updates
  live in private `files/update/`, never external user data or the APK.
- `GeneralsZHActivity` selects `libmain.so` for 30 Hz or `libmain60.so` for 60 Hz
  and loads an eligible downloaded engine on the next game start. A native menu
  acknowledgement clears `files/update/boot_pending`; two failed boots fall back.
- Legacy serial, active-engine marker and cached manifest are not channel-bound.
  Switching only the URL/key could reuse legacy state. Config-only checks replace
  the cached manifest used for later dependency checks.
- The existing publisher requires an APK; no direct verified dual-engine publish
  path exists. It trusts `engine_build.txt` without checking provenance/native
  Git symbols. Serial-fetch errors silently become zero. The branch push and
  signing workflow force-replace history and publish unsigned content first.
- Build generation already rejects shallow history. APK provenance verifies
  exact linked/staged hashes. These protections must remain; a launcher-only
  bootstrap can reuse Engine 3333 but must label its native provenance honestly.
- Saves, Maps, Options.ini, imported mods, package identity, game simulation,
  native dependencies and graphics/audio/touch are outside this change.

## Signing prerequisite

Connected GitHub secret metadata access returned HTTP 403. Public-identity-only
Actions audit run 37416307932 reported `UPDATE_SIGNING_KEY` absent. No private key
was generated, printed, committed, exported or embedded. The initial audit
dispatch had a YAML escaping error; the corrected audit succeeded. Neither audit
compiled or changed `dev/mobile-v4`.

The operator must install a P-256 key through an authorized repository-secret
connection before any bootstrap build. Only its public PEM can enter the source
and APK. No Engine 3334 publication is authorized in this phase.

## Minimal integration and validation plan

1. Own URL/public key; separate own serial and downloaded-engine state while
   preserving legacy files and the player's auto-check preference.
2. Verify retained signed engine metadata before native selection; require both
   rate slots and complete dependency identity. Activate only fully verified
   downloads; preserve APK fallback and native boot acknowledgement.
3. Prepare direct engine-only publication from verified binaries/provenance
   against an explicit bootstrap APK dependency baseline. Sign before publishing,
   compare the secret's public key with the pinned key, and use normal fast-forward
   publication with serial/immutable-engine guards.
4. Test altered signatures, wrong keys/curve, rollback/channel migration,
   interrupted download, dependency mismatch, old/new metadata and provenance.
5. Build bootstrap only after secure secret setup, using the existing native
   artifacts and cache. Device install is `adb install -r`; physical Save/Mod/
   Online/update activation tests remain NOT TESTED until actually performed.
