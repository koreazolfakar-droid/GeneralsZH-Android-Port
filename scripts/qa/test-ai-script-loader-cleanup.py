#!/usr/bin/env python3
"""Execute production script-loader ownership on partial parse and retry.

The chunk reader supplies parsed ScriptList instances; production code owns their
transfer/cleanup. This checks allocation balance, stale-list publication, and the
16-list boundary without loading or inventing any faction scripts.
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
    source = (ROOT / 'GeneralsMD/Code/GameEngine/Source/GameLogic/ScriptEngine/Scripts.cpp').read_text()
    functions = '\n'.join(block(source, signature) for signature in [
        'Bool ScriptList::ParseScriptsDataChunk(', 'Int ScriptList::getReadScripts('])
    unit = r'''
#include <cassert>
#include <cstdio>
using Int = int; using Bool = bool;
const int MAX_PLAYER_COUNT = 16;
#define DEBUG_ASSERTCRASH(condition, message) ((void)0)
#define newInstance(type) new type
#define deleteInstance(ptr) delete (ptr)
struct DataChunkInput;
struct DataChunkInfo { int label = 0; };
struct ScriptList {
    static ScriptList* s_readLists[MAX_PLAYER_COUNT];
    static int s_numInReadList;
    static int live;
    ScriptList() { ++live; }
    ~ScriptList() { --live; }
    static Bool ParseScriptListDataChunk(DataChunkInput&, DataChunkInfo*, void*) { return true; }
    static Bool ParseScriptsDataChunk(DataChunkInput&, DataChunkInfo*, void*);
    static Int getReadScripts(ScriptList* [MAX_PLAYER_COUNT]);
};
int ScriptList::live = 0;
int ScriptList::s_numInReadList = 0;
ScriptList* ScriptList::s_readLists[MAX_PLAYER_COUNT] = {};
struct TScriptListReadInfo { int numLists; ScriptList* readLists[MAX_PLAYER_COUNT]; };
struct DataChunkInput {
    int count; bool success;
    void registerParser(const char*, int, Bool (*)(DataChunkInput&, DataChunkInfo*, void*)) {}
    bool parse(void* data) {
        auto* read = static_cast<TScriptListReadInfo*>(data);
        for (int i = 0; i < count; ++i) read->readLists[read->numLists++] = new ScriptList;
        return success;
    }
};
''' + functions + r'''
int main() {
    DataChunkInfo info;
    ScriptList* result[MAX_PLAYER_COUNT] = {};
    DataChunkInput partial{3, false};
    assert(!ScriptList::ParseScriptsDataChunk(partial, &info, nullptr));
    assert(ScriptList::live == 0); // incomplete lists must be destroyed
    assert(ScriptList::getReadScripts(result) == 0);
    DataChunkInput full{MAX_PLAYER_COUNT, true};
    assert(ScriptList::ParseScriptsDataChunk(full, &info, nullptr));
    assert(ScriptList::getReadScripts(result) == MAX_PLAYER_COUNT);
    assert(ScriptList::getReadScripts(result) == 0); // ownership transfers once
    for (auto* p : result) delete p;
    assert(ScriptList::live == 0);
    DataChunkInput previous{2, true};
    assert(ScriptList::ParseScriptsDataChunk(previous, &info, nullptr));
    DataChunkInput retry{0, false};
    assert(!ScriptList::ParseScriptsDataChunk(retry, &info, nullptr));
    assert(ScriptList::live == 0);
    assert(ScriptList::getReadScripts(result) == 0); // no stale null lists
    assert(ScriptList::ParseScriptsDataChunk(previous, &info, nullptr));
    assert(ScriptList::getReadScripts(result) == 2);
    delete result[0]; delete result[1];
    assert(ScriptList::live == 0);
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-ai-script-loader-') as work:
        work = Path(work)
        cpp = work / 'loader.cpp'
        cpp.write_text(unit)
        exe = work / 'loader'
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra',
                        '-Werror', '-Wno-unused-parameter', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print('PASS: partial-read cleanup, 16-list transfer, retry ownership and no stale publication')


if __name__ == '__main__':
    main()
