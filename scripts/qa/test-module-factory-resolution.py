#!/usr/bin/env python3
"""Run production module resolution/creation with lookup counters and sanitizers.

The fixture replaces engine allocation/INI interfaces, not the factory methods.
Timing is a host mechanism comparison, not a device or full-object benchmark.
"""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def block(source, signature):
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    source = (ROOT / 'GeneralsMD/Code/GameEngine/Source/Common/Thing/ModuleFactory.cpp').read_text()
    header = (ROOT / 'GeneralsMD/Code/GameEngine/Include/Common/ModuleFactory.h').read_text()
    data_header = (ROOT / 'GeneralsMD/Code/GameEngine/Include/Common/Module.h').read_text()
    cache = source.split('// GX_MODULE_FACTORY_CACHE_BEGIN', 1)[1].split('// GX_MODULE_FACTORY_CACHE_END', 1)[0]
    methods = cache + '\n' + '\n'.join(block(source, signature) for signature in [
        'ModuleFactory::~ModuleFactory()',
        'ModuleData* ModuleFactory::newModuleDataFromINI(',
        '/*static*/ NameKeyType ModuleFactory::makeDecoratedNameKey(',
        'const ModuleFactory::ModuleTemplate* ModuleFactory::findModuleTemplate(',
        'Module *ModuleFactory::newModule(', 'void ModuleFactory::addModuleInternal('])
    preamble = r'''
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include <unordered_map>
using Int = int; using Bool = bool; using NameKeyType = int;
#define DEBUG_CRASH(x) ((void)0)
struct AsciiString {
    std::string value;
    AsciiString(const char* p = "") : value(p) {}
    bool isEmpty() const { return value.empty(); }
    const char* str() const { return value.c_str(); }
    bool operator==(const AsciiString& b) const { return value == b.value; }
};
struct KeyGenerator {
    std::map<std::string, int> keys;
    unsigned long calls = 0;
    int nameToKey(const char* s) {
        ++calls;
        auto result = keys.emplace(s, keys.size() + 1);
        return result.first->second;
    }
} generator;
auto* TheNameKeyGenerator = &generator;
#define NAMEKEY(s) generator.nameToKey((s).str())
struct Xfer {};
struct Snapshot { virtual ~Snapshot() {};
    virtual void crc(Xfer*) {} virtual void xfer(Xfer*) {} virtual void loadPostProcess() {} };
struct MultiIniFieldParse {};
struct W3DModelDrawModuleData; struct W3DTreeDrawModuleData;
enum StaticGameLODLevel { LOW };
enum ModuleType { MODULETYPE_BEHAVIOR, MODULETYPE_DRAW, MODULETYPE_CLIENT_UPDATE };
class ModuleFactory;
''' + block(data_header, 'class ModuleData :') + r''';
struct Thing { int id; };
struct INI {};
struct Module { int id; const ModuleData* data; };
using NewModuleProc = Module* (*)(Thing*, const ModuleData*);
using NewModuleDataProc = ModuleData* (*)(INI*);
class ModuleFactory {
public:
''' + block(header, '\tclass ModuleTemplate\n') + r''';
    using ModuleTemplateMap = std::map<NameKeyType, ModuleTemplate>;
    using ModuleDataList = std::vector<const ModuleData*>;
    ModuleTemplateMap m_moduleTemplateMap;
    ModuleDataList m_moduleDataList;
    ~ModuleFactory();
    ModuleData* newModuleDataFromINI(INI*, const AsciiString&, ModuleType, const AsciiString&);
    static NameKeyType makeDecoratedNameKey(const AsciiString&, ModuleType);
    const ModuleTemplate* findModuleTemplate(const AsciiString&, ModuleType);
    Module* newModule(Thing*, const AsciiString&, const ModuleData*, ModuleType);
    void addModuleInternal(NewModuleProc, NewModuleDataProc, ModuleType, const AsciiString&, Int);
};
'''
    tests = r'''
std::vector<int> order;
Module* createA(Thing* thing, const ModuleData* data) {
    order.push_back(thing->id); return new Module{thing->id, data};
}
Module* createB(Thing* thing, const ModuleData* data) {
    order.push_back(-thing->id); return new Module{-thing->id, data};
}
ModuleData* createData(INI*) { return new ModuleData; }
int main() {
    ModuleFactory factory, other;
    factory.addModuleInternal(createA, createData, MODULETYPE_BEHAVIOR, "A", 0);
    factory.addModuleInternal(createB, createData, MODULETYPE_DRAW, "A", 0);
    factory.addModuleInternal(createB, createData, MODULETYPE_BEHAVIOR, "B", 0);
    other.addModuleInternal(createB, createData, MODULETYPE_BEHAVIOR, "A", 0);
    const auto* data = factory.newModuleDataFromINI(nullptr, "A", MODULETYPE_BEHAVIOR, "tag");
    Thing thing{7};
    auto create = [&](ModuleFactory& f, const char* name, ModuleType type, const ModuleData* d, int id) {
        Module* m = f.newModule(&thing, name, d, type);
        assert(m && m->id == id && m->data == d); delete m;
    };
    auto before = generator.calls;
    create(factory, "A", MODULETYPE_BEHAVIOR, data, 7);
#ifndef BASELINE
    assert(generator.calls == before); // no name-key or map lookup for parsed data
#endif
    before = generator.calls;
    create(factory, "B", MODULETYPE_BEHAVIOR, data, -7);
    create(factory, "A", MODULETYPE_DRAW, data, -7);
    create(other, "A", MODULETYPE_BEHAVIOR, data, -7);
    create(factory, "A", MODULETYPE_BEHAVIOR, nullptr, 7);
    ModuleData manual;
    create(factory, "A", MODULETYPE_BEHAVIOR, &manual, 7);
    assert(generator.calls == before + 5);
    assert(!factory.newModule(&thing, "", data, MODULETYPE_BEHAVIOR));
    assert(!factory.newModule(&thing, "Missing", data, MODULETYPE_BEHAVIOR));
    // Insertion does not invalidate the cached entry. Re-registration must update
    // the creator seen through the cache rather than preserve a stale function.
    for (int i = 0; i < 500; ++i) {
        std::string n = "Extra" + std::to_string(i);
        factory.addModuleInternal(createA, createData, MODULETYPE_BEHAVIOR, n.c_str(), 0);
    }
    factory.addModuleInternal(createB, createData, MODULETYPE_BEHAVIOR, "A", 0);
    create(factory, "A", MODULETYPE_BEHAVIOR, data, -7);
    assert((order == std::vector<int>{7, -7, -7, -7, 7, 7, -7}));
    order.clear(); order.reserve(1000000);
    before = generator.calls;
    const auto start = std::chrono::steady_clock::now();
    for (int i = 0; i < 1000000; ++i)
        create(factory, "A", MODULETYPE_BEHAVIOR, data, -7);
    const auto us = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - start).count();
    assert(order.size() == 1000000);
#ifdef BASELINE
    assert(generator.calls == before + 1000000);
#else
    assert(generator.calls == before);
#endif
    printf("1000000 production newModule calls: %lld us, %lu name lookups\n", (long long)us, generator.calls - before);
}
'''
    old_start = methods.index('\t// GeneralsX @performance Codex 04/11/2026 Avoid rehashing')
    old_end = methods.index('\n\tif (mt)', old_start)
    baseline = methods[:old_start] + '\tconst ModuleTemplate* mt = findModuleTemplate(name, type);' + methods[old_end:]
    with tempfile.TemporaryDirectory(prefix='gx-module-resolution-') as work:
        work = Path(work)
        for variant, body, flags in [
                ('baseline', baseline, ['-O2', '-DBASELINE']),
                ('optimized', methods, ['-O2']),
                ('sanitized', methods, ['-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'])]:
            cpp = work / (variant + '.cpp')
            cpp.write_text(preamble + body + tests)
            exe = work / variant
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra',
                            '-Werror', '-Wno-unused-parameter', '-Wno-unused-but-set-variable',
                            *flags, str(cpp), '-o', str(exe)], check=True)
            print(variant, flush=True)
            subprocess.run([str(exe)], check=True)
    print('PASS: parsed/manual/null/foreign data, name/type mismatches, missing names, registration updates and creation order')


if __name__ == '__main__':
    main()
