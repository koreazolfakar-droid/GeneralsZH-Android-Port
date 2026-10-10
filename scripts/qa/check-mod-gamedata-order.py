#!/usr/bin/env python3
"""Verify standalone Android BIG mounts occur before the first GameData read.

Usage: python3 scripts/qa/check-mod-gamedata-order.py generalszh-logs.zip
Does not modify game files, mods, or saves.
"""
import argparse
from pathlib import Path
import sys
import zipfile


def read_log(path: Path) -> str:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith("generals-stderr.log")]
            if len(names) != 1:
                raise ValueError("ZIP must contain exactly one generals-stderr.log")
            return z.read(names[0]).decode("utf-8", "replace")
    return path.read_text(encoding="utf-8", errors="replace")


def check(log: str) -> tuple[bool, str]:
    lines = log.splitlines()
    game_data = next((i for i, s in enumerate(lines) if "[INI] load('Data\\INI\\GameData.ini') START" in s), None)
    early = next((i for i, s in enumerate(lines) if "[gxmod-early] mount before GameData:" in s), None)
    archives = [(i, s) for i, s in enumerate(lines) if "[gxbig] loaded:" in s and "/Mods/" in s.replace('\\', '/')]
    overlay = next((i for i, s in enumerate(lines) if "[gxmod-overlay] active_mod_bigs=" in s), None)
    source = next((s for s in lines if "[gxmod-early] GameData archive candidate:" in s), "(not reported)")
    if game_data is None:
        return False, "FAIL: first GameData.ini read not found"
    if not archives:
        return False, "FAIL: no mounted BIG files from Mods/ found"
    if early is None:
        return False, (f"FAIL: active mod mounted after GameData.ini (first GameData line {game_data + 1}; "
                       f"first mod BIG line {archives[0][0] + 1}). Old startup ordering detected.")
    if not (early < archives[0][0] < game_data):
        return False, "FAIL: the early mount marker, mod BIG files and GameData read are in the wrong order"
    if overlay is None or overlay >= game_data:
        return False, "FAIL: mod overlay reconciliation did not finish before GameData read"
    if any("FAILED TO OPEN" in s and "/Mods/" in s.replace('\\', '/') for s in lines[:game_data]):
        return False, "FAIL: at least one active mod BIG failed to open"
    return True, (f"PASS: {len(archives)} mod BIG(s) mounted and overlay reconciled before first GameData read.\n"
                  f"{source}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="generals-stderr.log or generalszh-logs.zip")
    args = parser.parse_args()
    try:
        ok, message = check(read_log(args.log))
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
