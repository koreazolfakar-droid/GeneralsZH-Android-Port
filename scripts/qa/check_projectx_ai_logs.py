#!/usr/bin/env python3
"""Summarize Project X AI invalid floating-point events from Android log ZIPs."""
import argparse
import json
import re
import zipfile
from collections import Counter

PATTERN = re.compile(r"\[GX-NET\] fp invalid frame (\d+):\s*(.+)")
PLAYER = re.compile(r"\[GX-NET\] crc players frame 0:\s*(.+)")
SCRIPT = re.compile(r"\[gxasset\].*(?:SkirmishScripts|MultiplayerScripts|Scripts\.ini)", re.I)

def examine(path):
    sessions = []
    with zipfile.ZipFile(path) as archive:
        for filename in sorted(archive.namelist()):
            if not filename.endswith(("stderr.log", "stderr-prev.log")):
                continue
            counts, examples, scripts, players = Counter(), [], [], None
            with archive.open(filename) as stream:
                for raw in stream:
                    line = raw.decode("utf-8", "replace").strip()
                    event = PATTERN.search(line)
                    if event:
                        unit = re.search(r"\b(?:Russia|Europe)\w+\b", event.group(2))
                        counts[unit.group(0) if unit else "other"] += 1
                        if len(examples) < 12:
                            examples.append({"frame": int(event.group(1)), "message": event.group(2)})
                    entry = PLAYER.search(line)
                    if entry:
                        players = entry.group(1)
                    if SCRIPT.search(line) and len(scripts) < 20:
                        scripts.append(line)
            sessions.append({"file": filename, "players": players,
                             "fp_invalid_events": dict(counts), "examples": examples,
                             "script_provenance": scripts,
                             "script_provenance_available": bool(scripts)})
    return sessions

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs_zip")
    parser.add_argument("--fail-on-fp", action="store_true")
    args = parser.parse_args()
    sessions = examine(args.logs_zip)
    print(json.dumps({"sessions": sessions}, indent=2, ensure_ascii=False))
    return int(args.fail_on_fp and any(s["fp_invalid_events"] for s in sessions))

if __name__ == "__main__":
    raise SystemExit(main())
