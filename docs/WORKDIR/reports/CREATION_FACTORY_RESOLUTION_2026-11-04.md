# Object creation factory resolution — 2026-11-04

## Source finding and change

`ProductionUpdate::update` and `SpawnBehavior::createSpawn` create units through
`ThingFactory::newObject`. This performs variation selection, `Object`
construction (including behavior creation and drawable publication), ordered
`onCreate` callbacks, partition registration, then `Object::initObject`.
No duplicate call among those stages was removed. Constructors, callbacks,
object IDs, update wake frames, RNG calls and save transfer code are unchanged.

Every INI module's registration was already found by
`ModuleFactory::newModuleDataFromINI`. Nevertheless, every later behavior/draw
module instance repeated decorated-name construction, name-key hashing and
lookup, then a registration-map lookup in `newModule`.

`ModuleFactory` now retains a pointer-keyed hash table from its owned
`ModuleData` to the stable `std::map` registration address. `newModule` checks
the requested name and module type before using the registration. The table
only contains data owned by that factory. Manual or null data, foreign-factory
data and mismatched name/type use the original lookup. Updating an existing
registration updates the creator observed by the cache. Inserting registrations
does not invalidate the map entry. The factory owns both data and registrations
for its lifetime; neither is reset during a match.

The table adds an entry per **shared INI ModuleData**, not per object or module
instance. Registrations additionally retain their name and type. Cache entry
allocations happen at INI loading. There is no new per-instance allocation,
preload or asynchronous creation. `Module.h`, `ModuleData` layout and all object
module layouts remain unchanged; only factory implementation/layout changes.

## Focused host validation

Run:

```sh
python3 scripts/qa/test-module-factory-resolution.py
```

The fixture extracts the actual production `ModuleData`, registration class,
`newModuleDataFromINI`, decorated-name lookup, `newModule` and registration
methods. Engine allocation and INI interfaces are small test substitutes. It
checks parsed, manually constructed, null and foreign-factory data; wrong
names/types; empty/missing module names; map growth; replacement registration;
and ordered creator calls. AddressSanitizer and UndefinedBehaviorSanitizer pass.

For the baseline comparison, the fixture replaces only `newModule`'s cache
selection with the original `findModuleTemplate(name, type)` statement. A first
optimized host run (1,000,000 calls, with creation/delete and ordered callback
recording in both variants) measured:

| Variant | Time | Decorated-name/name-key lookups |
|---|---:|---:|
| Original resolution | 181,494 us | 1,000,000 |
| Cached resolution | 43,407 us | 0 |

This proves removal of repeated lookups on this mechanism. The fixture uses
`std::string` for `AsciiString` and a small instrumented name-key generator;
absolute times and ratios are not an engine or phone benchmark.

## Limits

This does **not** establish the dominant source of the reported 31–47 ms
creation stalls. It does not claim elimination of those stalls. Asset loading,
drawable/model creation, arbitrary mod callbacks and partition work remain in
their original synchronous order. No Android native compilation, full-engine
runtime, replay, Vanilla/TEOD device scenario or device timing was performed by
this focused validation. The parent task handles wider build checks. No APK,
commit, push or OTA publication was performed here.
