#!/usr/bin/env python3
"""Read-only Project X Zero Hour skirmish script/team audit.

Usage: python3 scripts/qa/audit-projectx-skirmish.py --zip 'Project X remastered.zip' --big '!!ProjectXRe_INI.big' --json report.json

This tool does not rewrite any mod or engine data. Team references not found in
the selected BIG are *unresolved*, NOT proven missing from all loaded archives.
SkirmishScripts.scb uses CkMp script and ScriptTeams tables.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import struct
import zipfile

MAX_FILE_BYTES = 512 * 1024 * 1024
MAX_CHUNK_ITEMS = 100000
OWNER_LABELS = {
    "SkirmishAmerica": "America",
    "SkirmishChina": "China",
    "SkirmishGLA": "GLA",
    "SkirmishAmericaLaserGeneral": "Russia",
    "SkirmishAmericaSuperWeaponGeneral": "Europe",
}

class Reader:
    def __init__(self, data: bytes, offset: int = 0):
        self.data, self.offset = data, offset

    def take(self, size: int) -> bytes:
        if size < 0 or self.offset + size > len(self.data):
            raise ValueError("truncated CkMp field")
        v = self.data[self.offset:self.offset + size]
        self.offset += size
        return v

    def num(self, fmt: str):
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def text(self):
        size = self.num("<H")
        if size > 16384:
            raise ValueError("oversized script text")
        return self.take(size).decode("latin-1")

def read_toc(data: bytes):
    if data[:4] != b"CkMp":
        raise ValueError("not a CkMp script file")
    r = Reader(data, 4)
    count = r.num("<I")
    if count > MAX_CHUNK_ITEMS:
        raise ValueError("invalid name table count")
    names = {}
    for _ in range(count):
        name = r.take(r.num("<B")).decode("latin-1")
        names[r.num("<I")] = name
    return names, r.offset

def chunks(data: bytes, start: int, end: int):
    pos = start
    while pos < end:
        if pos + 10 > end:
            raise ValueError("truncated CkMp chunk header")
        chunk_id, version, size = struct.unpack_from("<IHi", data, pos)
        body = pos + 10
        if size < 0 or body + size > end:
            raise ValueError("invalid CkMp chunk length")
        yield chunk_id, version, body, body + size
        pos = body + size

def read_dict(reader: Reader, names: dict) -> dict:
    result = {}
    n = reader.num("<H")
    for _ in range(n):
        key_type = reader.num("<I")
        key, kind = names.get(key_type >> 8, "?"), key_type & 0xff
        if kind == 0:
            value = reader.num("<B")
        elif kind == 1:
            value = reader.num("<i")
        elif kind == 2:
            value = reader.num("<f")
        elif kind == 3:
            value = reader.text()
        elif kind == 4:
            size = reader.num("<H")
            value = reader.take(size * 2).decode("utf-16-le", errors="replace")
        else:
            raise ValueError("unknown CkMp dictionary type: %s" % kind)
        result[key] = value
    return result

def read_scb(data: bytes):
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("oversized SCB")
    names, offset = read_toc(data)
    script_id = next((id for id, name in names.items() if name == "Script"), None)
    if script_id is None:
        raise ValueError("SCB missing Script name table entry")
    team_chunks = [(body, end) for id, _, body, end in chunks(data, offset, len(data))
                   if names.get(id) == "ScriptTeams"]
    if len(team_chunks) != 1:
        raise ValueError("expected exactly one ScriptTeams chunk")
    team_reader = Reader(data, team_chunks[0][0])
    teams = []
    while team_reader.offset < team_chunks[0][1]:
        if len(teams) > MAX_CHUNK_ITEMS:
            raise ValueError("too many teams")
        teams.append(read_dict(team_reader, names))
    if team_reader.offset != team_chunks[0][1]:
        raise ValueError("team table overflow")

    # Script structures are nested inside script-list chunks. Match their exact
    # CkMp ID + validated bounds/metadata without reinterpreting action bodies.
    matches = {}
    signature = struct.pack("<I", script_id)
    for hit in re.finditer(re.escape(signature), data):
        start = hit.start()
        if start + 10 > len(data):
            continue
        _, version, length = struct.unpack_from("<IHi", data, start)
        if not 1 <= version <= 10 or not 30 < length < 20000 or start + 10 + length > len(data):
            continue
        r = Reader(data, start + 10)
        try:
            name = r.text()
            for _ in range(3):
                r.text()  # comments, condition comment, action comment
            flags = [r.num("<B") for _ in range(6)]
            if not name or any(v not in (0, 1) for v in flags):
                continue
            if r.offset > start + 10 + length:
                continue
            matches.setdefault(name, {
                "easy": bool(flags[2]), "normal": bool(flags[3]),
                "hard": bool(flags[4]), "active": bool(flags[0]),
            })
        except (ValueError, struct.error, UnicodeDecodeError):
            continue
    if not matches:
        raise ValueError("no valid script entries decoded")
    return teams, matches

def read_big_objects(data: bytes):
    """Read only names in this BIG; vanilla and other mod archives can add more."""
    if len(data) > MAX_FILE_BYTES or data[:4] not in (b"BIGF", b"BIG4"):
        raise ValueError("not a bounded BIG archive")
    count = struct.unpack_from(">I", data, 8)[0]
    if count > MAX_CHUNK_ITEMS:
        raise ValueError("too many BIG entries")
    cursor, available = 16, set()
    for _ in range(count):
        if cursor + 8 > len(data):
            raise ValueError("truncated BIG file table")
        offset, size = struct.unpack_from(">II", data, cursor)
        cursor += 8
        end = data.find(b"\0", cursor, min(len(data), cursor + 65536))
        if end < 0 or offset + size > len(data):
            raise ValueError("invalid BIG entry")
        path = data[cursor:end].decode("latin-1").lower().replace("/", "\\")
        cursor = end + 1
        if path.startswith("data\\ini\\") and path.endswith(".ini"):
            source = data[offset:offset + size].decode("latin-1")
            for m in re.finditer(r"^\s*(?:Object|ChildObject|ObjectReskin)\s+([A-Za-z0-9_]+)",
                                 source, flags=re.M | re.I):
                available.add(m.group(1).lower())
    return available

def audit(teams: list, scripts: dict, objects=None):
    by_owner = defaultdict(list)
    for team in teams:
        if team.get("teamOwner") in OWNER_LABELS:
            by_owner[team["teamOwner"]].append(team)
    result = {}
    for owner, faction in OWNER_LABELS.items():
        groups = by_owner[owner]
        missing_conditions = []
        hard_disabled_conditions = []
        unresolved = []
        for team in groups:
            tname = team.get("teamName", "")
            cond = team.get("teamProductionCondition")
            if cond and cond not in scripts:
                missing_conditions.append({"team": tname, "script": cond})
            if cond in scripts and not scripts[cond]["hard"]:
                hard_disabled_conditions.append({"team": tname, "script": cond})
            if objects is not None:
                for key, unit in team.items():
                    if (key.startswith("teamUnitType") and unit and
                            unit.lower() != "<none>" and unit.lower() not in objects):
                        unresolved.append({"team": tname, "slot": key, "unit": unit})
        result[faction] = {
            "teams": len(groups),
            "unresolved_production_conditions": missing_conditions,
            "not_enabled_on_hard": hard_disabled_conditions,
            "unit_names_unresolved_in_supplied_big_only": unresolved,
        }
    return {
        "team_count": len(teams),
        "script_count": len(scripts),
        "hard_script_count": sum(bool(s["hard"]) for s in scripts.values()),
        "factions": result,
        "scope": "Read-only source audit; does not assert runtime AI behaviour or global missing assets.",
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True, type=Path, help="User-supplied mod ZIP containing Data/Scripts/SkirmishScripts.scb")
    ap.add_argument("--big", type=Path, help="Optional user-supplied mod INI BIG for partial object coverage")
    ap.add_argument("--json", type=Path, help="Optional JSON report destination")
    args = ap.parse_args()
    with zipfile.ZipFile(args.zip) as archive:
        entry = archive.getinfo("Data/Scripts/SkirmishScripts.scb")
        if entry.file_size > MAX_FILE_BYTES:
            raise ValueError("SCB entry too large")
        script_bytes = archive.read(entry)
    teams, scripts = read_scb(script_bytes)
    objects = read_big_objects(args.big.read_bytes()) if args.big else None
    result = audit(teams, scripts, objects)
    report = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.json:
        args.json.write_text(report + "\n", encoding="utf-8")
    print("Project X skirmish teams:", result["team_count"],
          "valid script names:", result["script_count"],
          "hard-enabled scripts:", result["hard_script_count"])
    for name, row in result["factions"].items():
        print("%-8s teams=%d unresolved conditions=%d hard-disabled=%d unresolved unit refs=%d" % (
            name, row["teams"], len(row["unresolved_production_conditions"]),
            len(row["not_enabled_on_hard"]),
            len(row["unit_names_unresolved_in_supplied_big_only"])))
    if not args.json:
        print(report)

if __name__ == "__main__":
    main()
