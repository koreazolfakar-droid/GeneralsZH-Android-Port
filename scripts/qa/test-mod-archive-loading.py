#!/usr/bin/env python3
"""Run production BIG parsing, enumeration, mounting and lookup on host fixtures.

No Android/game installation or build cache is modified. Payloads are synthetic;
this checks resource selection, not rendered models, effects or Android lifecycle.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("overlay", ROOT / "scripts/qa/test-standalone-mod-overlay.py")
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)


def big(path, entries):
    path.parent.mkdir(parents=True, exist_ok=True)
    offset = 16 + sum(9 + len(name.encode()) for name in entries)
    header = offset
    table, data = b"", b""
    for name, value in entries.items():
        value = value.encode()
        table += struct.pack(">II", offset, len(value)) + name.encode() + b"\0"
        data += value
        offset += len(value)
    path.write_bytes(b"BIGF" + struct.pack(">III", offset, len(entries), header) + table + data)


def main():
    sources = {
        "archive": ROOT / "Core/GameEngine/Source/Common/System/ArchiveFile.cpp",
        "index": overlay.ARCHIVE,
        "big": overlay.LOADER,
        "local": ROOT / "Core/GameEngineDevice/Source/StdDevice/Common/StdLocalFileSystem.cpp",
        "filesystem": ROOT / "Core/GameEngine/Source/Common/System/FileSystem.cpp",
    }
    definitions = {
        "archive": ["Bool SearchStringMatches(", "ArchiveFile::~ArchiveFile()", "ArchiveFile::ArchiveFile()",
                    "void ArchiveFile::addFile(", "void ArchiveFile::getFileListInDirectory(const AsciiString&",
                    "void ArchiveFile::getFileListInDirectory(const DetailedArchivedDirectoryInfo",
                    "void ArchiveFile::attachFile(", "const ArchivedFileInfo * ArchiveFile::getArchivedFileInfo("],
        "index": ["static AsciiString getBaseFilename(", "struct StandaloneModOverlayStats",
                  "static void reconcileStandaloneModDirectory(", "ArchiveFileSystem::ArchiveFileSystem()",
                  "ArchiveFileSystem::~ArchiveFileSystem()", "void ArchiveFileSystem::loadIntoDirectoryTree(",
                  "void ArchiveFileSystem::loadMods()", "ArchiveFileSystem::ArchivedDirectoryInfoResult ArchiveFileSystem::getArchivedDirectoryInfo(",
                  "File * ArchiveFileSystem::openFile(", "ArchiveFile* ArchiveFileSystem::getArchiveFile(",
                  "Bool ArchiveFileSystem::doesFileExist(",
                  "void ArchiveFileSystem::getFileListInDirectory("],
        "local": ["void StdLocalFileSystem::getFileListInDirectory("],
        "big": ["static bool isStandaloneModArchiveBelowRoot(", "ArchiveFile * StdBIGFileSystem::openArchiveFile(",
                "Bool StdBIGFileSystem::loadBigFilesFromDirectory("],
        "filesystem": ["static bool gxShouldTraceAsset(", "static Bool gxTraceAssetProbe(",
                       "File*\t\tFileSystem::openFile(", "Bool FileSystem::doesFileExist("],
    }
    implementation = []
    for key, signatures in definitions.items():
        source = sources[key].read_text()
        for signature in signatures:
            text = overlay.extract(source, signature)
            implementation.append(text + (";" if signature.startswith("struct ") else ""))
    # Keep the real boot order and fresh-process lifecycle as explicit source guards.
    engine = (ROOT / "GeneralsMD/Code/GameEngine/Source/Common/GameEngine.cpp").read_text()
    mount = engine.index("TheArchiveFileSystem->loadMods();")
    assert mount < engine.index('initSubsystem(TheGameText,')
    assert mount < engine.index('initSubsystem(TheThingFactory,')
    entry = (ROOT / "GeneralsMD/Code/Main/SDL3Main.cpp").read_text()
    assert "_exit(exitcode);" in entry

    with tempfile.TemporaryDirectory(prefix="gx-mod-archives-") as tmp:
        tmp = Path(tmp)
        (tmp / "production.inc").write_text("\n".join(implementation))
        exe = tmp / "archive-test"
        subprocess.run(["g++", "-std=c++17", "-Wall", "-Wextra", "-Wno-unused-parameter",
                        "-Werror", "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g",
                        "-I", str(tmp), str(ROOT / "scripts/qa/mod-archive-fixture.cpp"), "-o", str(exe)], check=True)
        paths = ["Data/INI/Object/Vehicle.ini", "Art/W3D/Vehicle.w3d", "Art/W3D/Infantry.w3d",
                 "Art/W3D/InfantryRun.w3d", "Art/Textures/Shield.tga", "Art/Textures/Vehicle.dds",
                 "Data/INI/FXList.ini", "Data/INI/ParticleSystem.ini"]
        retail = {name: "vanilla" for name in paths}
        mod = {name.upper().replace("/", "\\"): "mod-first" for name in paths}
        game, manual = tmp / "standalone", tmp / "manual"
        for root in (game, manual):
            big(root / "TexturesZH.big", retail)
            big(root / "INIZH.big", {"Data/INI/OldOnly.ini": "must-be-masked"})
        for root in (game / "Mods/Active", manual):
            big(root / "!A.BIG", mod)
            big(root / "!z.big", {name: "wrong-last" for name in paths})
            big(root / "INIZH.big", {"Data/INI/NewOnly.ini": "replacement"})
        big(game / "Mods/Inactive/!!first.big", {**{name: "inactive-leak" for name in paths},
                                                  "Data/INI/InactiveOnly.ini": "inactive"})
        big(game / "Mods/Nested/Assets/Models.BIG", {"Art/W3D/Nested.w3d": "nested-model"})
        big(game / "Mods/Nested/Patches/Data/INI/INIZH.big", {"Data/INI/Nested.ini": "nested-ini"})
        big(game / "Mods/Single.big", {"Art/W3D/Vehicle.w3d": "single-big"})
        big(tmp / "Generals/INIZH.big", {"Data/INI/SiblingOnly.ini": "sibling"})
        original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp.rglob("*.big")}
        original.update({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in tmp.rglob("*.BIG")})

        def run(root, selection, expected, trace=None):
            env = dict(os.environ)
            env.pop("GX_ASSET_TRACE", None)
            if trace is not None:
                env["GX_ASSET_TRACE"] = trace
            result = subprocess.run([str(exe), str(root), selection, str(tmp / "Generals"), expected],
                                    text=True, capture_output=True, env=env)
            if result.returncode:
                raise RuntimeError(f"{selection}:\n{result.stdout}\n{result.stderr}")
            print(f"PASS (host BIG fixtures): {selection}, {expected}")
            if trace == "ART\\TEXTURES\\SHIELD" or (root / "gx_asset_trace.txt").exists():
                assert "source=" + str(root / "Mods/Active/!A.BIG") + " result=OPEN" in result.stderr
                assert "path=Art/Textures/ShieldMissing.tga instance=0 source=<none> result=UNRESOLVED" in result.stderr
                assert "probe=Art/Textures/ShieldProbeOnly.tga instance=0 source=<none> result=UNRESOLVED" in result.stderr
                assert "[gxasset] path=Art\\W3D\\Vehicle.w3d" not in result.stderr
            elif trace is None and not (root / "gx_asset_trace.txt").exists():
                assert "[gxasset]" not in result.stderr
            elif trace == "*":
                assert "source=<loose> result=OPEN" in result.stderr
                assert "result=UNRESOLVED" in result.stderr
            return result.stdout

        run(game, "vanilla", "vanilla")
        managed = run(game, "Mods/Active", "mod-first")
        copied = run(manual, "manual", "mod-first")
        assert managed == copied, "Root and standalone virtual payloads differ"
        run(game, "vanilla", "vanilla")
        run(game, "Mods/Active", "mod-first")
        run(game, "Mods/Active", "mod-first")  # Same selection after fresh process restart.
        run(game, "Mods/Nested", "nested")
        run(game, "Mods/Single.big", "single-big")
        (game / "loose-shield.txt").write_text("loose")
        run(game, "Mods/Active", "mod-first", "ART\\TEXTURES\\SHIELD")
        run(game, "Mods/Active", "mod-first", "*")
        (game / "gx_asset_trace.txt").write_text("ART\\TEXTURES\\SHIELD\n")
        run(game, "Mods/Active", "mod-first")
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest for p, digest in original.items())
        print("PASS: production archive pipeline; root parity; Vanilla -> Mod -> Vanilla -> Mod; restart; no base mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
