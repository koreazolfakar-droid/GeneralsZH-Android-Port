#!/usr/bin/env python3
"""Compile and run current localization selection/CSF/STR parsing with engine API doubles.

Uses synthetic BIGF and mixed-case loose files, plus fresh processes for
switching/restart. This is a host resource regression test, not Android device QA.
Usage: python3 scripts/qa/smoke/test-mod-localization.py
Requires Python 3 and g++ (C++17). No engine build or game data required.
"""
import hashlib
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile


def production_function(source: str, name: str) -> str:
    """Copy the production definition verbatim, up to the next section marker."""
    pattern = r"^(?:static )?(?:inline )?(?:void|Bool|Char|UnsignedInt|int|UnicodeString)\s+(?:__cdecl\s+)?" + re.escape(name) + r"\s*\([^;]*?\)\s*\{"
    match = re.search(pattern, source, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Production function not found: {name}")
    end = source.find("\n//============================================================================", match.end())
    following = re.search(r"^(?:static )?(?:inline )?(?:void|Bool|Char|UnsignedInt|int|UnicodeString)\s+(?:__cdecl\s+)?[\w:]+\s*\([^;]*?\)\s*\{", source[match.end():], re.MULTILINE)
    if following:
        next_start = match.end() + following.start()
        end = min(end, next_start) if end != -1 else next_start
    return source[match.start():end if end != -1 else len(source)]


def csf(labels: dict[str, str]) -> bytes:
    data = struct.pack("<6I", 0x43534620, 3, len(labels), len(labels), 0, 0)
    for label, text in labels.items():
        encoded = text.encode("utf-16le")
        data += struct.pack("<3I", 0x4c424c20, 1, len(label)) + label.encode()
        data += struct.pack("<2I", 0x53545220, len(encoded) // 2)
        data += bytes(b ^ 255 for b in encoded)
    return data


def big(path: Path, entries: dict[str, bytes], magic: bytes = b"BIGF") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    offset = 16 + sum(8 + len(name.encode()) + 1 for name in entries)
    header_size = offset
    index, payload = b"", b""
    for name, content in entries.items():
        index += struct.pack(">2I", offset, len(content)) + name.encode() + b"\0"
        payload += content
        offset += len(content)
    path.write_bytes(magic + struct.pack(">3I", offset, len(entries), header_size) + index + payload)


def main() -> int:
    repo = Path(__file__).resolve().parents[3]
    source = (repo / "Core/GameEngine/Source/GameClient/GameText.cpp").read_text()
    names = ["isAsciiSpace", "decodeUtf8", "compareLUT"] + [
        f"GameTextManager::{name}" for name in (
            "init", "deinit", "stripSpaces", "removeLeadingAndTrailing",
            "readToEndOfQuote", "translateCopy", "readLine", "readChar",
            "getStringCount", "getCSFInfo", "parseCSF", "parseStringFile", "fetch",
        )
    ]
    with tempfile.TemporaryDirectory(prefix="gx-mod-lang-") as temporary:
        root = Path(temporary)
        defaults = source[source.index("struct GXLabelAlias"):source.index("GameTextInterface *TheGameText")]
        (root / "production-localization.inc").write_text(defaults + "\n".join(production_function(source, n) for n in names))
        # The production selector includes engine API headers; the harness supplies
        # those APIs above the include, using fixture file/BIG bytes as backing data.
        for header in ("ArchiveFile", "FileSystem", "GlobalData", "LocalFileSystem"):
            path = root / "Common" / f"{header}.h"
            path.parent.mkdir(exist_ok=True)
            path.write_text("#pragma once\n")
        executable = root / "mod-localization-test"
        subprocess.run([
            "g++", "-std=c++17", "-D__ANDROID__", "-Wall", "-Wextra",
            "-Wno-unused-variable", "-Wno-sign-compare", "-Wno-unused-but-set-variable",
            "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g",
            "-I", str(root), "-I", str(repo / "Core/GameEngine/Include"),
            str(repo / "scripts/qa/smoke/mod-localization-fixture.cpp"), "-o", str(executable),
        ], check=True)
        game = root / "game"
        vanilla = {"FACTION:America": "America", "GENERAL:Army": "Vanilla Army", "GUI:VanillaOnly": "Vanilla fallback"}
        custom = {"FACTION:America": "Mod Faction", "GENERAL:Army": "Mod Army"}
        big(game / "EnglishZH.big", {"Data\\English\\Generals.csf": csf(vanilla)})
        big(game / "English.big", {"Data/English/Generals.csf": csf({"FACTION:America": "Wrong base Generals"})})
        big(game / "Mods/ArchiveMod/Custom.big", {"DATA\\ENGLISH\\GENERALS.CSF": csf(custom)})
        big(game / "Mods/Root.big", {"Generals.csf": csf(custom)})
        big(game / "Mods/LooseMod/Gameplay.big", {"Data/INI/test.ini": b"fixture"})
        loose = game / "Mods/LooseMod/Data/English/Generals.csf"
        loose.parent.mkdir(parents=True)
        loose.write_bytes(csf(custom))
        big(game / "Mods/StrMod/Text.big", {"Generals.str": b'FACTION:America\n"Mod Faction"\nEND\nGENERAL:Army\n"Mod Army"\nEND\n'})
        # Multiple mod tables must not be mistaken for the vanilla fallback.
        big(game / "Mods/ArchiveMod/Other.big", {"Data/English/Generals.csf": csf(custom)})
        protected = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in game.rglob("*") if p.is_file()}

        def run(label: str, mod: str, source: str, override: bool, expected: tuple[str, str] = ("Mod Faction", "Mod Army")) -> None:
            result = subprocess.run([str(executable), str(game), mod, *expected, source, str(override).lower()], text=True, capture_output=True)
            if result.returncode:
                raise RuntimeError(f"{label} failed:\n{result.stdout}\n{result.stderr}")
            for marker in ("activeMod=", "language=English", "csfSource=", "strSource=", f"overrideVanilla={str(override).lower()}"):
                assert f"[GX-MOD-LANG] {marker}" in result.stderr, (label, marker, result.stderr)
            print(f"PASS (host fixture): {label}")

        vanilla_source = "big:EnglishZH.big!data/English/generals.csf"
        # Harness mounts in directory iteration order; the last mod table wins,
        # as with the existing overwrite mount calls. Read whichever was last.
        last = list((game / "Mods/ArchiveMod").iterdir())[-1]
        archive_source = f"big:{last}!data/English/generals.csf"
        run("1. Vanilla Zero Hour", "Vanilla", vanilla_source, False, ("America", "Vanilla Army"))
        run("2. BIG mod custom faction and army names", "Mods/ArchiveMod", archive_source, True)
        run("3. Vanilla -> Mod", "Mods/ArchiveMod", archive_source, True)
        run("4. Mod -> Vanilla", "Vanilla", vanilla_source, False, ("America", "Vanilla Army"))
        run("5. Fresh process with mod still selected", "Mods/ArchiveMod", archive_source, True)
        run("Loose mixed-case Data/English/Generals.csf", "Mods/LooseMod", f"loose:{game}/Mods/LooseMod/data/English/generals.csf", True)
        run("Root Generals.csf in direct BIG", "Mods/Root.big", f"big:{game}/Mods/Root.big!generals.csf", True)
        run("Root Generals.str in mod BIG", "Mods/StrMod", vanilla_source, True)
        # Reproduce both shadows: base loose CSF before BIG, and base STR before CSF.
        base_csf = game / "Data/English/Generals.csf"
        base_csf.parent.mkdir(parents=True)
        base_csf.write_bytes(csf(vanilla))
        base_str = game / "Data/English/Generals.str"
        base_str.write_text('\n'.join(f'{label}\n"{text}"\nEND' for label, text in vanilla.items()) + '\n')
        run("Mod BIG CSF beats base loose CSF and STR", "Mods/ArchiveMod", archive_source, True)
        run("Loose mod CSF beats base loose STR", "Mods/LooseMod", f"loose:{game}/Mods/LooseMod/data/English/generals.csf", True)
        run("Vanilla restored with base loose STR", "Vanilla", "loose:data/English/generals.csf", False, ("America", "Vanilla Army"))
        # STR counting and parsing must address the same mod archive instance.
        big(game / "Mods/StrMod/Text.big", {"Data/English/Generals.str": b'FACTION:America\n"Mod Faction"\nEND\nGENERAL:Army\n"Mod Army"\nEND\n'})
        run("Mod BIG STR beats same-path base loose STR", "Mods/StrMod", "loose:data/English/generals.csf", True)
        # Selected non-English language pack must not hide English mod faction names.
        russian = game / "data/Russian/generals.str"
        russian.parent.mkdir(parents=True)
        russian.write_text('FACTION:America\n"Wrong pack faction"\nEND\n')
        (russian.parent / "generals.csf").write_bytes(csf(vanilla))
        os.environ["GENERALSX_TEXT_LANGUAGE"] = "Russian"
        result = subprocess.run([str(executable), str(game), "Mods/Root.big", "Mod Faction", "Mod Army", f"big:{game}/Mods/Root.big!generals.csf", "true"], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        del os.environ["GENERALSX_TEXT_LANGUAGE"]
        print("PASS (host fixture): English mod CSF beats selected Russian base STR")
        for path, digest in protected.items():
            if path.name == "Text.big":  # deliberately rewritten STR fixture above
                continue
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
        print("PASS (host fixture): base BIGs and mod payloads unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
