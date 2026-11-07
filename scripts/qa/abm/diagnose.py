#!/usr/bin/env python3
"""ABM phase 1: correlate existing Generals Android performance telemetry.

Read-only; no rendering/AI or frame scheduling changes. Python stdlib only.
"""
import argparse
import bisect
import json
import re
from pathlib import Path

NUMBER = r"([0-9]+(?:\.[0-9]+)?)"


def number(line, key):
    match = re.search(r"(?<![A-Za-z0-9_-])" + re.escape(key) + r"=" + NUMBER, line)
    return float(match.group(1)) if match else None


def fields(line, keys):
    return {key: number(line, key) for key in keys}


def parse_file(path):
    windows, logic, paths, terrain = [], [], [], []
    battle = False
    current = None
    with open(path, encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if "[GX-PERF-BATTLE-BEGIN]" in line:
                battle = True
            elif "[GX-PERF-BATTLE-END]" in line:
                battle = False
            if line.startswith("[d3d8gles] perf-window:"):
                current = {**fields(line, ("t", "durationMs", "renderedFrames")),
                           "battle": battle, "swapMs": None, "gpuMs": None,
                           "drawCalls": None, "terrainUploadKBPerFrame": None}
                windows.append(current)
            elif current is not None and line.startswith("[d3d8gles] perf-gpu:"):
                gpu = number(line, "gpu")
                swap = number(line, "swap")
                current.update(swapMs=swap, gpuMs=gpu,
                               renderThreadDrawMs=number(line, "draw"),
                               renderThreadUploadMs=number(line, "upload"))
            elif current is not None and line.startswith("[d3d8gles] perf-draws/frame by source:"):
                parts = [float(v) for v in re.findall(
                    r"(?<![\w-])(?:models|2d-ui|terrain|shadows|skin|other|sorted\(particles\))=" + NUMBER, line)]
                current["drawCalls"] = round(sum(parts), 2) if len(parts) == 7 else None
            elif current is not None and line.startswith("[d3d8gles] perf-upload-source:"):
                hit = re.search(r"\bterrain=" + NUMBER + r"KB/", line)
                current["terrainUploadKBPerFrame"] = float(hit.group(1)) if hit else None
            elif line.startswith("[GX-PERF-LOGIC-DETAIL]"):
                logic.append({**fields(line, ("t", "frame", "ticks", "modules", "worst")), "battle": battle})
            elif line.startswith("[GX-PERF-PATH-REQUEST]"):
                paths.append({**fields(line, ("t", "windowMs", "requests", "worstMs", "totalWallMs")), "battle": battle})
            elif line.startswith("[GX-PERF-TERRAIN-REBUILD]"):
                terrain.append({**fields(line, ("t", "vbUploads", "uploadedBytes", "fullCompleted", "partialUpdates")), "battle": battle})
    return {"windows": windows, "logic": logic, "paths": paths, "terrain": terrain}


def nearest(events, target_us, tolerance_us=5_000_000):
    """Nearby interval sample, not causal attribution or frame-exact alignment."""
    ordered = [e for e in events if e.get("t") is not None]
    if target_us is None or not ordered:
        return None
    ordered.sort(key=lambda e: e["t"])
    times = [e["t"] for e in ordered]
    index = bisect.bisect_left(times, target_us)
    options = ordered[max(0, index - 1):min(len(ordered), index + 1)]
    best = min(options, key=lambda e: abs(e["t"] - target_us))
    return best if abs(best["t"] - target_us) <= tolerance_us else None


def summarize(path, maximum=10, battle_only=False):
    parsed = parse_file(path)
    windows = [w for w in parsed["windows"] if not battle_only or w["battle"]]
    for window in windows:
        t = window.get("t")
        sample = nearest(parsed["logic"], t)
        window["modulesMsPerTick"] = sample.get("modules") if sample else None
        sample = nearest(parsed["paths"], t)
        window["pathWorstMsNearby"] = sample.get("worstMs") if sample else None
        sample = nearest(parsed["terrain"], t)
        window["terrainSubmittedBytesNearby"] = sample.get("uploadedBytes") if sample else None
        duration, frames = window.get("durationMs"), window.get("renderedFrames")
        window["observedFps"] = round(1000 * frames / duration, 2) if duration and frames is not None else None

    def top(key):
        return [{k: v for k, v in w.items() if k != "battle"} for w in
                sorted((w for w in windows if w.get(key) is not None),
                       key=lambda w: w[key], reverse=True)[:maximum]]

    selected_paths = [p for p in parsed["paths"] if not battle_only or p["battle"]]
    selected_terrain = [t for t in parsed["terrain"] if not battle_only or t["battle"]]
    return {
        "source": str(path),
        "scope": "battle-marked intervals only" if battle_only else "all intervals (battle marked on input)",
        "samples": {
            "renderWindows": len(windows),
            "gpuTimingAvailable": sum(w.get("gpuMs") is not None for w in windows),
            "pathWindows": len(selected_paths),
            "terrainWindows": len(selected_terrain),
        },
        "peaks": {
            "swapMs": top("swapMs"),
            "gpuMs": top("gpuMs"),
            "drawCallsPerFrame": top("drawCalls"),
            "modulesMsPerTick": top("modulesMsPerTick"),
            "terrainUploadKBPerFrame": top("terrainUploadKBPerFrame"),
        },
        "pathHotspots": sorted(
            ({k: v for k, v in p.items() if k != "battle"} for p in selected_paths
             if p.get("worstMs") is not None),
            key=lambda p: p["worstMs"], reverse=True
        )[:maximum],
        "terrainSubmission": {
            "bytesSubmittedAcrossIntervals": int(sum(t.get("uploadedBytes") or 0 for t in selected_terrain)),
            "vbUploadOperations": int(sum(t.get("vbUploads") or 0 for t in selected_terrain)),
        },
        "caveats": [
            "Swap time is CPU wait inside presentation, not GPU execution time.",
            "GPU timer samples may be unavailable or delayed; never infer GPU time from swap.",
            "Nearby logic/path/terrain windows overlap imperfectly; proximity does not prove a causal stall.",
            "Draw-call count alone does not establish a bottleneck.",
            "Terrain submitted bytes and driver upload bytes are different counters; do not add them together.",
            "Do not compare mod or scene FPS without matched workloads and device thermal state.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="generals-stderr.log")
    parser.add_argument("--battle-only", action="store_true", help="only intervals inside explicit battle markers")
    parser.add_argument("--top", type=int, default=10, help="top samples per category")
    parser.add_argument("--output", type=Path, help="write JSON to file instead of stdout")
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be positive")
    result = summarize(args.log, args.top, args.battle_only)
    report = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
