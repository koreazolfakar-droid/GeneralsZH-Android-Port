#!/usr/bin/env python3
"""Record linked/staged native hashes and verify the resulting APK payload.

This describes packaging provenance, not a substitute for the native build log.
The CI source checkout and linker outputs must also come from the recorded HEAD.
"""
# GeneralsX @build Codex 05/10/2026 Bind APK metadata to complete history and actual native bytes.
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile


def file_identity(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return {'sha256': digest.hexdigest(), 'size': path.stat().st_size}


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments], text=True).strip()


def write(root, destination):
    root = root.resolve()
    resolver = root / 'scripts/build/android/engine-build-number.sh'
    sequence = int(subprocess.check_output(['bash', str(resolver), str(root)], text=True))
    staged = root / 'android/app/src/main/jniLibs/arm64-v8a'
    libraries = {path.name: file_identity(path) for path in sorted(staged.glob('*.so'))}
    primary = root / 'build/android-vulkan/GeneralsMD/Code/Main/libmain.so'
    if libraries.get('libmain.so') != file_identity(primary):
        raise ValueError('Staged libmain.so differs from the exact linked engine output')
    second = os.environ.get('GX_SECOND_GAME_LIB')
    if second:
        if libraries.get('libmain60.so') != file_identity(Path(second)):
            raise ValueError('Staged libmain60.so differs from GX_SECOND_GAME_LIB')
        if libraries['libmain.so']['sha256'] == libraries['libmain60.so']['sha256']:
            raise ValueError('The same engine cannot occupy both simulation-rate slots')
    elif 'libmain60.so' in libraries:
        # Incremental staging may retain an old second engine; never label it as new.
        raise ValueError('libmain60.so is staged but GX_SECOND_GAME_LIB was not selected')
    description = {
        'schema': 1,
        'source_commit': git(root, 'rev-parse', 'HEAD'),
        'source_tree': git(root, 'rev-parse', 'HEAD^{tree}'),
        'engine_build': sequence,
        'native_libraries': libraries,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(description, indent=2, sort_keys=True) + '\n')
    print(f'Engine package: build {sequence}, HEAD {description["source_commit"]}, '
          f'{len(libraries)} native libraries')


def verify(apk, expected):
    expected_bytes = expected.read_bytes()
    description = json.loads(expected_bytes)
    if description.get('schema') != 1 or not description.get('native_libraries'):
        raise ValueError('Unsupported or empty engine package manifest')
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP paths in APK')
        if archive.testzip() is not None:
            raise ValueError('APK ZIP checksum failure')
        if archive.read('assets/engine_provenance.json') != expected_bytes:
            raise ValueError('APK engine provenance differs from the staged manifest')
        if archive.read('assets/engine_build.txt') != (str(description['engine_build']) + '\n').encode():
            raise ValueError('APK Engine Build differs from complete-history sequence')
        prefix = 'lib/arm64-v8a/'
        actual_names = {name[len(prefix):] for name in names if name.startswith(prefix) and name.endswith('.so')}
        if actual_names != set(description['native_libraries']):
            raise ValueError('APK native library set differs from the staged manifest')
        for name, expected_identity in description['native_libraries'].items():
            payload = archive.read(prefix + name)
            actual = {'sha256': hashlib.sha256(payload).hexdigest(), 'size': len(payload)}
            if actual != expected_identity:
                raise ValueError(f'APK native payload mismatch: {name}')
    print(f'PASS: APK engine provenance, build {description["engine_build"]}, '
          f'HEAD {description["source_commit"]}, {len(actual_names)} native libraries')


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in ('write', 'verify'):
        raise ValueError('Usage: engine-package-manifest.py write ROOT OUTPUT_JSON | verify APK EXPECTED_JSON')
    action = write if sys.argv[1] == 'write' else verify
    action(Path(sys.argv[2]), Path(sys.argv[3]))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(1)
