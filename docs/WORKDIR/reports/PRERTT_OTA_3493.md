# Engine 3493 signed native OTA

GeneralsX @release Codex 21/10/2026

Source: `a126959e0774ff791256ace21923f7d1cea8804d`, including
`d0b52e04` preRTT attribution/refresh correction, `e80c7428` NameKey cast,
`72d90322` preserve newly raised refresh requests, and `a126959e` regression.
PR [22](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/pull/22)
merged into dev/mobile-v4 at `b6ecdca9a98ce5503b17c821bd5c0c12c755bd34`;
its tree equals the tested source. Publisher controller:
`aa149e155a73c69ca7eccdbb97461a736967054c`. Updates branch:
`62a1c3afd21902072819f2271d85a8872b2e8f88`.

## Work and validation

Whole-map terrain views left m_needFullUpdate set after the early return, causing
repeated base preparation. Consume the old request before the full geometry and
lighting update, preserving a request raised during that update. Missing buffers
and reentrancy retain retries; camera ancillary updates remain. Empty bridge
batches return before two DISCARD locks; nonempty vertex/index bytes and flags
match 3486. This proves condition-specific redundant CPU work, not the dominant
subroutine in the owner's actual 40-44 ms preRTT window.

Bounded preRTT summaries separate CPU/wall time, actual GLES producer waits, views,
terrain, region scans/callbacks, drawable preparation/modules, hierarchy work and
particle loops. Normal summary benchmarks suppress per-event full/net tracing;
opt-in detail and Replay Check CRC remain. No new spatial culling, simulation
scheduling/RNG changes, mod archive changes, quality reductions or APK changes.

Native [CI](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/39656153137)
passes 21 mandatory source suites and both ARM64 30/60 Hz variants. 124 successful
compiler invocations; zero failed requests. Existing checksummed state and caches
retained, no clean build. TLS was NOT TESTED inside CI because host development
libraries are absent; its local trusted/untrusted/hostname/downgrade/plain-HTTP
fixtures pass. Two optional historical source scripts remain absent/NOT TESTED.

ASan/UBSan host fixtures exercise production paths. 1,000 stationary whole-map
refresh checks change from 1,000 base refreshes to one; 1,000 empty bridge fills
avoid 2,000 locks. This does not establish avoided GPU bytes. Region order,
boundaries, NaN membership and current deletion match 3486. Particle tick/RNG/
deletion/smudge order matches both variants. Synthetic vanilla/TEOD BIG switching,
archive precedence, vehicle/Project X AI and save/map tests pass.

Host guard P50/P95 remains 0.020/0.030 us before and after, at clock floor.
Aggregation-only 600-scope overhead is 71.829/124.819 us enabled on x86_64.
These are not game frame times or Android FPS measurements. Physical-device
frame P50/P95 before/after, original vanilla/TEOD/Project X scenes, all-unit/effect
visuals, device crashes, actual installation and multiplayer/replay CRC are
NOT TESTED without assets/ADB. No measured phone FPS gain is claimed.

## Delivery

Actions initially rejected dispatch (422 repository disabled), and the integration
could not edit repository administration (403). A subsequent explicit dispatch
was accepted; no assertion is made about which account-level setting changed.
[Publisher](https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port/actions/runs/39658945517)
succeeded: authenticated native run/source, prepared and P-256 signed serial 17,
published through the existing updates branch, and verified both live payloads.

Local ABI checks match 3486 DT_NEEDED and JNI/SDL entrypoints. Strict preparation
checks all 15 installed-bootstrap runtime fingerprints and the original APK trust
key; new_apk_required=false. Both library payloads match the CI artifact whose
ZIP SHA256 is `05361055ad08f3f63dd762c130b9c3acb1bed42f927ee0bea19404423778615d`.

Exact app manifest:
https://raw.githubusercontent.com/koreazolfakar-droid/GeneralsZH-Android-Port/updates/manifest.json

Independent exact-URL availability proof: PASS after the old max-age=300
response expired. Exact manifest/signature and both gzip URLs were fetched with
no cache-busting query. ECDSA P-256 matches the actual bootstrap APK key; both
decompressed payloads equal CI bytes, source stamps match, all 15 runtime
fingerprints and existing configuration match. Manifest SHA256:
`3d81a23a3d0a200a04501befdfac18059ac9d8472fcfa1fb7c9ea75427950a10`.
Checksums, URLs, changed files and full structured proof: PRERTT_OTA_3493.json.

The installed application's update contract is satisfied and downloads are
available. Actual installation on the owner's phone remains NOT TESTED.
Capture device evidence with docs/HOWTO/ANDROID_BATTLE_PERFORMANCE_CAPTURE.md.
