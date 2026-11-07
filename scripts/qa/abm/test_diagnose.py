"""Host tests for ABM v1 telemetry parser.

Run from repository root:
python -m unittest discover -s scripts/qa/abm -p "test_*.py"
"""
import tempfile
import unittest
from pathlib import Path
from diagnose import summarize, number, nearest

SAMPLE = """[d3d8gles] perf-window: t=10000000us durationMs=2000 renderedFrames=120 (CPU/worker/GPU timings overlap)
[d3d8gles] perf-gpu: render thread ms/frame: draw=4.00 swap=30.00 upload=2.00 other=1.00 | gpu=14.00 ms/frame (90 frames timed)
[d3d8gles] perf-draws/frame by source: models=20.0 sorted(particles)=30.0 2d-ui=10.0 terrain=2.0 shadows=3.0 skin=4.0 other=5.0
[GX-PERF-BATTLE-BEGIN] logicFrame=1 firstMainFrameMs=20
[d3d8gles] perf-window: t=12000000us durationMs=2000 renderedFrames=40 (CPU/worker/GPU timings overlap)
[d3d8gles] perf-gpu: render thread ms/frame: draw=2.00 swap=71.46 upload=3.00 other=1.00 | gpu=9.00 ms/frame (38 frames timed)
[d3d8gles] perf-draws/frame by source: models=1000.0 sorted(particles)=200.0 2d-ui=100.0 terrain=100.0 shadows=50.0 skin=20.0 other=317.0
[d3d8gles] perf-upload-source: other=0KB/0.0-calls sync=0.0 terrain=200KB/5.0-calls sync=0.0
[GX-PERF-LOGIC-DETAIL] frame=100 ticks=20 total=12ms worst=100ms modules=11.69 ai=0.2 t=12002000us windowMs=2000
[GX-PERF-PATH-REQUEST] t=12003000us windowMs=2000 requests=1 totalWallMs=352.5 avgMs=352.5 worstMs=352.5
[GX-PERF-TERRAIN-REBUILD] t=12001000us vbUploads=3 uploadedBytes=4096 fullCompleted=1 partialUpdates=0
[GX-PERF-BATTLE-END] seconds=2 samples=40
"""


class DiagnoseTests(unittest.TestCase):
    def test_decimal_fields_and_missing_values(self):
        self.assertEqual(number("gpu=9.25 ms/frame", "gpu"), 9.25)
        self.assertIsNone(number("something=2", "gpu"))
        self.assertIsNone(nearest([], 12_000_000))
        self.assertIsNone(nearest([{"t": 1}], 12_000_000))

    def test_battle_only_and_distinct_units(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.log"
            path.write_text(SAMPLE, encoding="utf-8")
            result = summarize(path, maximum=1, battle_only=True)
            self.assertEqual(result["samples"]["renderWindows"], 1)
            peak = result["peaks"]["swapMs"][0]
            self.assertEqual(peak["swapMs"], 71.46)
            self.assertEqual(peak["gpuMs"], 9.0)
            self.assertEqual(peak["drawCalls"], 1787)
            self.assertEqual(peak["modulesMsPerTick"], 11.69)
            self.assertEqual(peak["pathWorstMsNearby"], 352.5)
            self.assertEqual(result["terrainSubmission"]["bytesSubmittedAcrossIntervals"], 4096)
            self.assertEqual(peak["terrainUploadKBPerFrame"], 200)
            self.assertEqual(summarize(path, 3)["samples"]["renderWindows"], 2)

    def test_partial_log_is_not_fabricated_as_zero(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "partial.log"
            path.write_text("[d3d8gles] perf-window: t=1us durationMs=2000 renderedFrames=20\n", encoding="utf-8")
            result = summarize(path)
            self.assertEqual(result["samples"]["gpuTimingAvailable"], 0)
            self.assertEqual(result["peaks"]["gpuMs"], [])
            self.assertIsNone(result["peaks"]["swapMs"][0]["gpuMs"]) if result["peaks"]["swapMs"] else None


if __name__ == "__main__":
    unittest.main()
