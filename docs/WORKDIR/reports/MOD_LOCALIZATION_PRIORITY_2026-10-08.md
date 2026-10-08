# Active mod faction/general text selection

Audited `dev/mobile-v4` at `1a9701853821abb18d2530ee43b29fb2dcfd0787`.
The signed published Engine 3339 manifest/payloads were retained separately and
verified before modifying the channel.

## Regression and consumer path

`f0f62a7ec214acf97f5c3ea692d521c637ce4b70` used the generic
`ModLocalization.h` resolver. Integration commit
`9c871191dbe11ecad4861996affba6419722be22` replaced it with
`gxActiveModTextInstance()`. That helper inspected only archive instance zero.
A translation or Vanilla archive preceding the active mod therefore concealed
the mod table. It also omitted loose mod and Data/root alternate layouts.

`ModManager` persists the active mod, and
`GeneralsZHActivity.getArguments()` supplies its absolute `-mod` path.
`CommandLine.cpp::parseMod()` sets `m_modBIG` or `m_modDir`;
`ArchiveFileSystem::loadMods()` mounts the archive or directory BIG files.
`GameTextManager::init()` resolves text before player templates are loaded.
`INI::parseAndTranslateLabel()` fetches that text and writes the Unicode value
used by `PlayerTemplate::DisplayName`. Those consumers, launcher arguments and
archive mount order remain unchanged.

## Targeted correction

Resolve all addressable FileInstances by active-mod archive ownership, with the
loose-file offset included. Compare priority across STR/CSF: requested language,
English, Data layout, root layout; STR precedes CSF at the same priority. Loose
mod paths retain their case for Android file access. Ownership comparisons retain
the existing case/separator-insensitive behavior and directory-boundary check.
The byte-sized FileInstance loop is bounded to prevent wrapping.

Keep the existing primary and fallback lookup tables. Missing mod labels use
a non-mod Vanilla table; skip every BIG owned by the active directory. Reuse the
STR parser for STR-only fallback as well as the existing CSF parser. UTF-8 STR,
Unicode CSF, map text lookup, language packs and deinit cleanup remain in place.
Diagnostics beginning `[GX-MOD-LANG]` identify sources, instance, language and
selected format only during initialization.

No save serialization, save paths, gameplay/simulation, networking, TURN order,
rates, Mod Manager UI or native dependency source changed in this correction.
Previously pending particle/video work is preserved separately and is excluded
from this localization commit.

## Validation

- Reproduced the published-source regression with the actual old GameText.cpp:
  a preceding translation returned `Vanilla translation` instead of `Mod Army`.
- `python3 scripts/qa/test-mod-localization.py`: PASS with ASan/UBSan, including
  all ten requested scenarios, Unicode/UTF-8, requested CSF before English STR,
  alternate layouts, multiple owned BIGs and the actual INI translation callback.
- `python3 scripts/qa/smoke/test-mod-localization.py`: PASS on synthetic real BIG
  files and mixed-case loose paths. Corrected pre-existing fixture drift so it
  executes the current source and reports the active source diagnostics.
- An initial host fixture compilation failed because its extracted parser
  declaration had not been updated for the fallback destination argument. The
  declaration was corrected; both sanitizer suites then passed.
- Save-map versions/alignment, engine numbering/packaging, 3277 GPU/TURN guards,
  native input/security, own-channel signing/publisher and incremental-state host
  checks passed. Android compilation, signed publication and on-device acceptance
  are recorded separately by their actual workflow/runtime results.

Physical Android mod menu testing, retail replay/PC deterministic runtime testing
and manual save/update persistence on a phone are **NOT TESTED** here. Source
guards and host fixtures are not substitutes for those checks.
