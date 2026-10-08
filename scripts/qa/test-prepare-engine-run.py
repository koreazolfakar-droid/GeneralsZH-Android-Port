#!/usr/bin/env python3
"""Publication bridge fixtures; no signing, private key or remote branch writes.

Uses the already verified published 3339 pair as public native test vectors.
Synthetic report records exercise validation, never constitute build evidence.
"""
# GeneralsX @build Codex 08/10/2026 Refuse stale, untested or dependency-incompatible publication inputs.
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT.parent / 'artifacts/bootstrap-3333/GeneralsZH-Bootstrap-1.4.3-Engine3333-debug.apk'
OLD = ROOT.parent / 'artifacts/mod-localization-update/rollback-3339'
spec = importlib.util.spec_from_file_location('prepare_run', ROOT / 'scripts/update/prepare-engine-run.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class Prepare(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='engine-prepare-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.report_dir = Path(self.temp.name) / 'report'
        self.report_dir.mkdir()
        manifest = json.loads((OLD / 'manifest.json').read_text())
        self.source = manifest['engine']['source_commit']
        pinned = json.loads((ROOT / '.github/engine-baseline/bootstrap-native.json').read_text())['native_libraries']
        required = ('libSDL3.so','libSDL3_image.so','libopenal.so','libgamespy.so',
                    'libadrenotools.so','libc++_shared.so','libEGL_angle.so','libGLESv2_angle.so',
                    'libdxvk_d3d8.so','libdxvk_d3d9.so')
        self.report = {'build': 'PASS', 'source_head': self.source, 'dependency_compatibility': 'PASS',
                       'new_apk_required': False, 'resolved_engine_sequence': 3339,
                       'source_tests': [{'test': n, 'passed': True} for n in bridge.REQUIRED_TESTS],
                       'dependency_comparison': [{'library': n, 'sha256': pinned[n]['sha256'],
                                                 'bootstrap_sha256': pinned[n]['sha256'], 'match': True} for n in required],
                       'variants': {}}
        for hz, name in ((30, 'libmain.so'), (60, 'libmain60.so')):
            data = gzip.decompress((OLD / f'engine/3339/{name}.gz').read_bytes())
            (self.report_dir / name).write_bytes(data)
            self.report['variants'][str(hz)] = {'source_sha': self.source, 'engine_sequence': 3339,
                                              'simulation_hz': hz, 'sha256': hashlib.sha256(data).hexdigest(), 'size': len(data)}

    def run_prepare(self):
        (self.report_dir / 'result.json').write_text(json.dumps(self.report))
        out = Path(self.temp.name) / 'prepared'
        bridge.prepare(self.report_dir, BASELINE, out, self.source, serial=1)
        return json.loads((out / 'manifest.json').read_text())

    def test_actual_native_vectors_prepare_exact_manifest(self):
        result = self.run_prepare()
        self.assertEqual(result['engine']['seq'], 3339)
        self.assertEqual(result['engine']['source_commit'], self.source)
        for hz, name in ((30, 'libmain.so'), (60, 'libmain60.so')):
            self.assertEqual(result['engine']['files'][name]['sha256'], self.report['variants'][str(hz)]['sha256'])
        self.assertFalse((Path(self.temp.name) / 'prepared/manifest.json.sig').exists())

    def test_failed_build_or_test_refused(self):
        self.report['build'] = 'FAIL'
        with self.assertRaisesRegex(ValueError, 'successful same-source'):
            self.run_prepare()
        self.report['build'] = 'PASS'
        self.report['source_tests'][0]['passed'] = False
        with self.assertRaisesRegex(ValueError, 'checks did not pass'):
            self.run_prepare()

    def test_mixed_source_and_simulation_variant_refused(self):
        self.report['source_head'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'same-source'):
            self.run_prepare()
        self.report['source_head'] = self.source
        self.report['variants']['60']['simulation_hz'] = 30
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.run_prepare()

    def test_dependency_mismatch_or_missing_evidence_refused(self):
        self.report['dependency_comparison'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'NEW APK REQUIRED'):
            self.run_prepare()
        self.report['dependency_comparison'].pop()
        with self.assertRaisesRegex(ValueError, 'Incomplete native dependency'):
            self.run_prepare()

    def test_stale_engine_or_report_hash_refused(self):
        self.report['variants']['30']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.run_prepare()
        data = (self.report_dir / 'libmain.so').read_bytes().replace(self.source.encode(), b'0' * 40)
        (self.report_dir / 'libmain.so').write_bytes(data)
        self.report['variants']['30']['sha256'] = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(ValueError, 'GitSHA1'):
            self.run_prepare()


if __name__ == '__main__':
    if not BASELINE.is_file() or not (OLD / 'engine/3339/libmain.so.gz').is_file():
        raise SystemExit('NOT TESTED: verified public 3339 vectors and Bootstrap APK required')
    unittest.main(verbosity=2)
