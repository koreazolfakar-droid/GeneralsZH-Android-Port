#!/usr/bin/env python3
"""Summarize Project X Skirmish AI diagnostics from an Android logs ZIP."""
import argparse
import json
import re
import zipfile
from collections import Counter

FIRST_FP = re.compile(r"\[GX-NET\] fp invalid frame (\d+):\s*(.+)")
SUMMARY_FP = re.compile(r"\[GX-NET\] fp invalid frames \d+\.\.\d+:\s*(.+?) x(\d+)$")
PLAYER = re.compile(r"\[GX-NET\] crc players frame 0:\s*(.+)")
SCRIPT = re.compile(r"\[(?:GX-AI-SCRIPT|gxasset)\].*(?:SkirmishScripts|MultiplayerScripts|Scripts\.ini)", re.I)
SIDE = re.compile(r"\[GX-AI-SIDE\]")
SKIRMISH = re.compile(r"\[SKIRMISH_DIAG\]")

def examine(path):
    sessions = []
    with zipfile.ZipFile(path) as archive:
        for filename in sorted(archive.namelist()):
            if not filename.endswith(("stderr.log", "stderr-prev.log")):
                continue
            summary, examples, scripts, sides, skirmish, players = Counter(), [], [], [], [], None
            with archive.open(filename) as stream:
                for raw in stream:
                    line = raw.decode("utf-8", "replace").strip()
                    first = FIRST_FP.search(line)
                    if first and len(examples) < 20:
                        examples.append({"frame": int(first.group(1)), "message": first.group(2)})
                    batch = SUMMARY_FP.search(line)
                    if batch:
                        summary[batch.group(1)] += int(batch.group(2))
                    entry = PLAYER.search(line)
                    if entry:
                        players = entry.group(1)
                    if SCRIPT.search(line) and len(scripts) < 30:
                        scripts.append(line)
                    if SIDE.search(line) and len(sides) < 30:
                        sides.append(line)
                    if SKIRMISH.search(line) and len(skirmish) < 30:
                        skirmish.append(line)
            sessions.append({
                "file": filename,
                "players": players,
                "fp_invalid_summary_counts": dict(summary),
                "fp_invalid_summary_total": sum(summary.values()),
                "first_fp_examples": examples,
                "script_provenance": scripts,
                "script_provenance_available": bool(scripts),
                "side_diagnostics": sides,
                "skirmish_diagnostics": skirmish,
            })
    return sessions

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs_zip")
    parser.add_argument("--fail-on-fp", action="store_true")
    args = parser.parse_args()
    sessions = examine(args.logs_zip)
    print(json.dumps({"sessions": sessions}, indent=2, ensure_ascii=False))
    return int(args.fail_on_fp and any(
        s["fp_invalid_summary_total"] or s["first_fp_examples"] for s in sessions))

if __name__ == "__main__":
    raise SystemExit(main())
