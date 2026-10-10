#!/usr/bin/env python3
"""Prepare an engine-only update from a successful verified incremental run."""
# GeneralsX @build Codex 08/10/2026 Bridge dual-engine reports to the existing secret-only signer.
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_TESTS = ('test-mod-localization.py', 'smoke/test-mod-localization.py',
                  'test-standalone-mod-overlay.py', 'test-mod-archive-loading.py',
                  'test-save-map-safety.py', 'test-engine-build-number.py',
                  'test-engine-packaging.py', 'test-engine-native-version.py',
                  'test-engine-3277-hotfix.py', 'test-engine-security.py')


def prepare(report_dir, baseline_apk, output, source, note='', serial=None):
    spec = importlib.util.spec_from_file_location('update_artifacts', ROOT / 'scripts/update/update-artifacts.py')
    artifacts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(artifacts)
    report = json.loads((report_dir / 'result.json').read_text())
    if (report.get('build') != 'PASS' or report.get('source_head') != source
            or report.get('dependency_compatibility') != 'PASS' or report.get('new_apk_required') is not False):
        raise ValueError('A successful same-source, dependency-compatible engine build is required')
    tests = {r['test']: r for r in report.get('source_tests', [])}
    if any(tests.get(name, {}).get('passed') is not True for name in REQUIRED_TESTS):
        raise ValueError('Required localization/save/provenance/regression checks did not pass')
    sequence = report['resolved_engine_sequence']
    artifacts.validate_source(source, sequence)
    _, _, baseline_libs = artifacts.apk_payload(baseline_apk)
    pinned = json.loads((ROOT / '.github/engine-baseline/bootstrap-native.json').read_text())['native_libraries']
    if {n: artifacts.digest(b) for n, b in baseline_libs.items()} != {n: r['sha256'] for n, r in pinned.items()}:
        raise ValueError('Bootstrap native fingerprint set differs from the verified build baseline')
    with zipfile.ZipFile(baseline_apk) as archive:
        if archive.read('assets/update-public.pem') != (ROOT / 'android/app/src/main/assets/update-public.pem').read_bytes():
            raise ValueError('Bootstrap APK update trust root differs from our pinned public key')
    comparisons = {r['library']: r for r in report['dependency_comparison']}
    required = {'libSDL3.so', 'libSDL3_image.so', 'libopenal.so', 'libgamespy.so',
                'libadrenotools.so', 'libc++_shared.so', 'libEGL_angle.so', 'libGLESv2_angle.so',
                'libdxvk_d3d8.so', 'libdxvk_d3d9.so'}
    if set(comparisons) != required:
        raise ValueError('Incomplete native dependency compatibility evidence')
    for name, row in comparisons.items():
        if row.get('match') is not True or row.get('sha256') != pinned[name]['sha256'] or row.get('bootstrap_sha256') != pinned[name]['sha256']:
            raise ValueError('NEW APK REQUIRED: dependency changed: ' + name)
        copied = report_dir / 'runtime-comparison' / name
        if copied.exists() and hashlib.sha256(copied.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Dependency comparison payload changed: ' + name)
    for hz, name in ((30, 'libmain.so'), (60, 'libmain60.so')):
        row = report['variants'][str(hz)]
        data = (report_dir / name).read_bytes()
        if (row['source_sha'] != source or row['engine_sequence'] != sequence or row['simulation_hz'] != hz
                or row['sha256'] != artifacts.digest(data) or row['size'] != len(data)):
            raise ValueError('Engine report/payload identity mismatch: ' + name)
        artifacts.native_stamp(data, source, sequence)
    command = ['python3', str(ROOT / 'scripts/update/publish-update.py'),
               '--engine-dir', str(report_dir), '--baseline-apk', str(baseline_apk),
               '--source-commit', source, '--out', str(output), '--note', note]
    if serial is not None:
        command += ['--serial', str(serial)]
    subprocess.run(command, check=True)
    manifest = json.loads((output / 'manifest.json').read_text())
    if manifest['engine']['seq'] != sequence or manifest['engine']['source_commit'] != source:
        raise ValueError('Prepared manifest differs from verified build')
    print('PASS: prepared exact dual-engine update; signing/publication remain separate verified steps')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir', type=Path, required=True)
    parser.add_argument('--baseline-apk', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--note', default='')
    parser.add_argument('--serial', type=int)
    args = parser.parse_args()
    prepare(args.report_dir, args.baseline_apk, args.out, args.expected_source, args.note, args.serial)
