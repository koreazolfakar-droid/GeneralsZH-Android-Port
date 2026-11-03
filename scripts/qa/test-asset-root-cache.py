#!/usr/bin/env python3
"""Host-only regression for changing loose-file asset roots without stale misses."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'Core/GameEngineDevice/Source/StdDevice/Common/StdLocalFileSystem.cpp').read_text()
start = source.index('void StdLocalFileSystem::setAssetRootPath(const AsciiString& path)')
end = source.index('\n#endif', start)
function = source[start:end]
prefix = r'''
#include <cassert>
#include <algorithm>
#include <cstdio>
#include <filesystem>
#include <string>
struct AsciiString {
    std::string s;
    explicit AsciiString(const char* p):s(p){}
    const char* str() const {return s.c_str();}
};
#define DEBUG_LOG(...) do {} while (0)
static std::filesystem::path s_assetFallbackPath;
static int invalidations=0;
static void forgetMissingFiles(){++invalidations;}
struct StdLocalFileSystem {void setAssetRootPath(const AsciiString& path);};
'''
suffix = r'''
int main(){
    StdLocalFileSystem fs;
    fs.setAssetRootPath(AsciiString("game/A"));
    assert(invalidations == 1);
    assert(s_assetFallbackPath == std::filesystem::path("game/A"));
    fs.setAssetRootPath(AsciiString("game/A"));
    assert(invalidations == 1);
    fs.setAssetRootPath(AsciiString("game\\B"));
    assert(invalidations == 2);
    assert(s_assetFallbackPath == std::filesystem::path("game/B"));
    fs.setAssetRootPath(AsciiString("game/B"));
    assert(invalidations == 2);
    puts("PASS: asset root changes invalidate stale negative directory caches");
}
'''
with tempfile.TemporaryDirectory(prefix='gzh-root-cache-') as temp:
    test = Path(temp) / 'asset_root.cpp'
    binary = Path(temp) / 'asset_root'
    test.write_text(prefix + '\n' + function + '\n' + suffix)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-O2',str(test),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
