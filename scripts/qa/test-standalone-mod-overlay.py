#!/usr/bin/env python3
"""Compile and exercise the REAL mod-overlay helpers extracted from engine sources.

Host-only regression: no Android SDK/NDK, game files, APK, clean, or cache changes.
Run: python3 scripts/qa/test-standalone-mod-overlay.py
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[2]
ARCHIVE = REPO / "Core/GameEngine/Source/Common/System/ArchiveFileSystem.cpp"
LOADER = REPO / "Core/GameEngineDevice/Source/StdDevice/Common/StdBIGFileSystem.cpp"
HEADER = REPO / "Core/GameEngine/Include/Common/ArchiveFileSystem.h"


def extract(source, signature):
    start = source.index(signature)
    first = source.index("{", start)
    level = 0
    for index in range(first, len(source)):
        if source[index] == "{":
            level += 1
        elif source[index] == "}":
            level -= 1
            if level == 0:
                return source[start : index + 1]
    raise AssertionError("Unclosed engine helper: " + signature)


def main():
    gxx = shutil.which("g++") or shutil.which("clang++")
    if not gxx:
        raise SystemExit("A C++17 host compiler is required")
    archive = ARCHIVE.read_text()
    loader = LOADER.read_text()
    header = HEADER.read_text()

    assert "Bool m_standaloneModOverlayActive = FALSE;" in header
    assert "if (!overwrite && isStandaloneModArchiveBelowRoot(dir, *it))" in loader
    assert "if (!modArchives.empty())" in archive
    assert "FilenameList archiveNames;" in archive  # must not erase local-only names

    get_basename = extract(archive, "static AsciiString getBaseFilename(")
    stats = extract(archive, "struct StandaloneModOverlayStats")
    reconcile = extract(archive, "static void reconcileStandaloneModDirectory(")
    mod_folder = extract(loader, "static bool isStandaloneModArchiveBelowRoot(")

    prologue = r"""
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <map>
#include <set>
#include <string>
#include <utility>
#include <vector>
class AsciiString {
    std::string value_;
public:
    AsciiString() {}
    AsciiString(const char* text): value_(text) {}
    bool isEmpty() const { return value_.empty(); }
    const char* str() const { return value_.c_str(); }
    void toLower() { std::transform(value_.begin(), value_.end(), value_.begin(),
        [](unsigned char c) { return (char)std::tolower(c); }); }
    int compareNoCase(const AsciiString& other) const {
        AsciiString lhs = *this, rhs = other;
        lhs.toLower(); rhs.toLower();
        return lhs.value_.compare(rhs.value_);
    }
    bool operator<(const AsciiString& b) const { return value_ < b.value_; }
};
class ArchiveFile {
    AsciiString name_;
public:
    explicit ArchiveFile(const char* name): name_(name) {}
    const AsciiString& getName() const { return name_; }
};
struct ArchivedDirectoryInfo;
using ArchivedFileLocationMap = std::multimap<AsciiString, ArchiveFile*>;
using ArchivedDirectoryInfoMap = std::map<AsciiString, ArchivedDirectoryInfo>;
struct ArchivedDirectoryInfo {
    AsciiString m_path;
    ArchivedFileLocationMap m_files;
    ArchivedDirectoryInfoMap m_directories;
};
static bool equalsIgnoreCase(const char* lhs, const char* rhs) {
    std::string a(lhs), b(rhs);
    std::transform(a.begin(), a.end(), a.begin(),
        [](unsigned char c){ return (char)std::tolower(c); });
    std::transform(b.begin(), b.end(), b.begin(),
        [](unsigned char c){ return (char)std::tolower(c); });
    return a == b;
}
"""
    checks = r"""
static ArchiveFile* winner(const ArchivedDirectoryInfo& tree, const char* name) {
    auto it = tree.m_files.find(AsciiString(name));
    return it == tree.m_files.end() ? nullptr : it->second;
}
int main() {
    assert(isStandaloneModArchiveBelowRoot("/storage/Zero Hour",
        "/storage/Zero Hour/Mods/Project X/a.big"));
    assert(isStandaloneModArchiveBelowRoot("/storage/Zero Hour",
        "/storage/Zero Hour/mOdS/Another/b.BIG"));
    assert(isStandaloneModArchiveBelowRoot(".", "./Mods/ProjectX/part.big"));
    assert(!isStandaloneModArchiveBelowRoot("/storage/Zero Hour",
        "/storage/Zero Hour/Data/INI/INIZH.big"));
    assert(!isStandaloneModArchiveBelowRoot("/storage/Mods/Zero Hour",
        "/storage/Mods/Zero Hour/TexturesZH.big"));
    assert(!isStandaloneModArchiveBelowRoot("/storage/Zero Hour",
        "/storage/Zero Hour/Mods2/part.big"));

    ArchiveFile oldBig("/game/INI.big");
    ArchiveFile modReplacement("/game/Mods/Project/INI.big");
    ArchiveFile modA("/game/Mods/Project/!A.big");
    ArchiveFile modZ("/game/Mods/Project/!Z.big");
    ArchiveFile baseA("/game/INIZH.big");
    ArchiveFile baseB("/game/MapsZH.big");
    ArchivedDirectoryInfo tree;

    // Archive with matching filename is virtually replaced (even if the
    // replacement doesn't contain the original file).
    tree.m_files.emplace("unique-base.ini", &oldBig);
    tree.m_files.emplace("shared-model.w3d", &modReplacement);
    tree.m_files.emplace("shared-model.w3d", &oldBig);

    // Old directory-mod TRUE mount made the LAST mod BIG win duplicate paths.
    tree.m_files.emplace("unit.w3d", &modZ);
    tree.m_files.emplace("unit.w3d", &modA);

    // Active mod must override other base archives without replacing them.
    tree.m_files.emplace("override.ini", &baseA);
    tree.m_files.emplace("override.ini", &modA);

    // Preserve base archive priority on paths the mod doesn't touch.
    tree.m_files.emplace("retail-only.ini", &baseA);
    tree.m_files.emplace("retail-only.ini", &baseB);

    std::set<ArchiveFile*> mods = {&modReplacement, &modA, &modZ};
    std::set<AsciiString> replaced = {"ini.big", "!a.big", "!z.big"};
    StandaloneModOverlayStats stats;
    reconcileStandaloneModDirectory(tree, mods, replaced, stats);
    assert(winner(tree, "unique-base.ini") == nullptr);
    assert(winner(tree, "shared-model.w3d") == &modReplacement);
    assert(winner(tree, "unit.w3d") == &modA);
    assert(winner(tree, "override.ini") == &modA);
    assert(winner(tree, "retail-only.ini") == &baseA);
    assert(stats.maskedBaseEntries == 2);
    assert(stats.affectedPaths >= 3);
    printf("PASS: 6 scan/masking cases, 5 archive resolution cases, real production C++ helpers compiled\n");
}
"""
    cpp = "\n".join((prologue, get_basename, stats, reconcile, mod_folder, checks))
    with tempfile.TemporaryDirectory(prefix="gx-mod-overlay-host-") as td:
        src = Path(td) / "mod_overlay_host.cpp"
        exe = Path(td) / "mod_overlay_host"
        src.write_text(cpp)
        subprocess.run([gxx, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                        "-O1", str(src), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    print("PASS: standalone mod overlay host regression")


if __name__ == "__main__":
    main()
