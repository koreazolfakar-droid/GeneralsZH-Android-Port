#!/usr/bin/env python3
"""Reject OTA build reports missing the offline pacing regression evidence."""
import importlib.util
import json
from pathlib import Path
import tempfile
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('prepare', ROOT/'scripts/update/prepare-engine-run.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
required = ('test-engine-budget-v2.py', 'test-offline-catchup.py')
for name in required:
    assert name in bridge.REQUIRED_TESTS, 'OTA gate omits '+name
    assert repr(name) in (ROOT/'.github/engine-baseline/build.py').read_text(), 'Native report omits '+name
with tempfile.TemporaryDirectory(prefix='gx-pacing-release-gates-') as temp:
    path = Path(temp)
    for missing in required:
        for status in ('missing', 'failed', 'not-tested'):
            rows = [{'test': n, 'passed': True} for n in bridge.REQUIRED_TESTS if n != missing]
            if status != 'missing':
                rows.append({'test': missing, 'passed': False, 'status': status})
            (path/'result.json').write_text(json.dumps({'build':'PASS','source_head':'a'*40,
                'dependency_compatibility':'PASS','new_apk_required':False,'source_tests':rows}))
            try:
                bridge.prepare(path, path/'absent.apk', path/'out', 'a'*40)
            except ValueError as error:
                assert 'checks did not pass' in str(error)
            else:
                raise AssertionError('Untested timing report accepted')
print('PASS: missing/failed/unrun pacing tests block OTA preparation before native or APK access')

workflow = (ROOT/'.github/workflows/build-android.yml').read_text()
assert "!(github.event_name == 'push' && contains(github.event.head_commit.message, '[engine-ota-only]'))" in workflow
print('PASS: engine-only commits suppress APK builds on performance and development branches')
