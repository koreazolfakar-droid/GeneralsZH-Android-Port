#!/usr/bin/env python3
"""Exercise production engine provenance against real Git and synthetic APKs.

Host-only fixtures cover packaging mistakes without Android tools, engine builds,
dependency installation, or modifying existing build outputs.
"""
# GeneralsX @build Codex 05/10/2026 Reject stale engines and mismatched APK provenance.
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import warnings
import zipfile


def elf_fixture(label):
    """An identifiable AArch64 ELF header; no executable engine is fabricated."""
    header = bytearray(64)
    header[:7] = b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI', header, 16, 3, 183, 1)
    struct.pack_into('<H', header, 52, 64)
    return bytes(header) + label.encode('ascii')


def git(root, *arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments], text=True).strip()


def command(helper, *arguments, second=None, success=True):
    environment = dict(os.environ)
    environment.pop('GX_SECOND_GAME_LIB', None)
    if second is not None:
        environment['GX_SECOND_GAME_LIB'] = str(second)
    result = subprocess.run([sys.executable, str(helper), *map(str, arguments)],
                            env=environment, capture_output=True, text=True)
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, 'Unsafe packaging unexpectedly succeeded: ' + repr(arguments)
    return result


def apk_fixture(path, manifest, libraries, *, metadata=None, count=None,
                replacements=None, omitted=(), extra=None, duplicate=None):
    """Each mutation changes one boundary checked by the production verifier."""
    description = json.loads(manifest.read_text())
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('assets/engine_provenance.json',
                             manifest.read_bytes() if metadata is None else metadata)
            archive.writestr('assets/engine_build.txt',
                             str(description['engine_build']) + '\n' if count is None else count)
            for name, payload in libraries.items():
                if name not in omitted:
                    archive.writestr('lib/arm64-v8a/' + name,
                                     (replacements or {}).get(name, payload))
            for name, payload in (extra or {}).items():
                archive.writestr('lib/arm64-v8a/' + name, payload)
            if duplicate is not None:
                archive.writestr(duplicate, b'duplicate ZIP payload')
    return path


def main():
    repository = Path(__file__).resolve().parents[2]
    helper = repository / 'scripts/build/android/engine-package-manifest.py'
    assert helper.is_file(), 'Production packaging provenance helper is missing'
    resolver = repository / 'scripts/build/android/engine-build-number.sh'
    passed = []
    with tempfile.TemporaryDirectory(prefix='gx-engine-package-') as temporary:
        work = Path(temporary)
        source = work / 'source with spaces'
        subprocess.run(['git', 'init', '--quiet', '--initial-branch=main', str(source)], check=True)
        local_resolver = source / 'scripts/build/android/engine-build-number.sh'
        local_resolver.parent.mkdir(parents=True)
        shutil.copyfile(resolver, local_resolver)
        (source / '.gitignore').write_text('build/\nandroid/app/src/main/jniLibs/\n')
        for index in range(3):
            (source / 'source-marker.txt').write_text('Fixture revision ' + str(index) + '\n')
            subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Engine package test',
                            '-c', 'user.email=engine-test@example.invalid', 'commit', '--quiet',
                            '--no-gpg-sign', '-m', 'Fixture ' + str(index)], check=True)
        staged = source / 'android/app/src/main/jniLibs/arm64-v8a'
        staged.mkdir(parents=True)
        primary = source / 'build/android-vulkan/GeneralsMD/Code/Main/libmain.so'
        primary.parent.mkdir(parents=True)
        second = source / 'build/libmain60.so'
        libraries = {
            'libmain.so': elf_fixture('newly linked 30 Hz'),
            'libmain60.so': elf_fixture('newly linked 60 Hz'),
            'libSDL3.so': elf_fixture('preserved SDL3 dependency'),
        }
        primary.write_bytes(libraries['libmain.so'])
        second.write_bytes(libraries['libmain60.so'])
        for name, payload in libraries.items():
            (staged / name).write_bytes(payload)
        manifest = work / 'expected-engine.json'
        command(helper, 'write', source, manifest, second=second)
        description = json.loads(manifest.read_text())
        assert description['schema'] == 1
        assert description['source_commit'] == git(source, 'rev-parse', 'HEAD')
        assert description['source_tree'] == git(source, 'rev-parse', 'HEAD^{tree}')
        assert description['engine_build'] == 3
        assert set(description['native_libraries']) == set(libraries)
        for name, payload in libraries.items():
            assert description['native_libraries'][name]['sha256'] == hashlib.sha256(payload).hexdigest()
            assert description['native_libraries'][name]['size'] == len(payload)
        passed.append('complete-history HEAD, tree, sequence and native hashes')

        valid = apk_fixture(work / 'valid.apk', manifest, libraries)
        command(helper, 'verify', valid, manifest)
        passed.append('valid dual-rate APK payload and provenance')

        command(helper, 'write', source, work / 'unselected-secondary.json', success=False)
        passed.append('staged secondary cannot be reused without explicit build selection')

        def reject_apk(label, **mutation):
            apk = apk_fixture(work / (label + '.apk'), manifest, libraries, **mutation)
            command(helper, 'verify', apk, manifest, success=False)
            passed.append(label)

        reject_apk('tampered-primary-engine', replacements={'libmain.so': elf_fixture('old 30 Hz engine')})
        reject_apk('tampered-secondary-engine', replacements={'libmain60.so': elf_fixture('old 60 Hz engine')})
        reject_apk('tampered-dependency', replacements={'libSDL3.so': elf_fixture('wrong SDL3 build')})
        reject_apk('missing-secondary-engine', omitted=('libmain60.so',))
        reject_apk('unexpected-native-library', extra={'libunexpected.so': elf_fixture('stale stage dependency')})
        reject_apk('stale-Build-1-metadata', count='1\n')
        changed = dict(description, source_commit='0' * 40)
        reject_apk('altered-source-provenance', metadata=json.dumps(changed).encode())
        reject_apk('altered-provenance-bytes', metadata=manifest.read_bytes() + b'\n')
        reject_apk('duplicate-engine-ZIP-path', duplicate='lib/arm64-v8a/libmain.so')
        reject_apk('duplicate-unrelated-ZIP-path', duplicate='assets/engine_build.txt')

        (staged / 'libmain.so').write_bytes(elf_fixture('old staged primary'))
        command(helper, 'write', source, work / 'stale-primary.json', second=second, success=False)
        (staged / 'libmain.so').write_bytes(libraries['libmain.so'])
        passed.append('staged primary differs from exact newly linked output')

        (staged / 'libmain60.so').write_bytes(elf_fixture('old staged secondary'))
        command(helper, 'write', source, work / 'stale-secondary.json', second=second, success=False)
        (staged / 'libmain60.so').write_bytes(libraries['libmain60.so'])
        passed.append('staged secondary differs from selected output')

        second.write_bytes(libraries['libmain.so'])
        (staged / 'libmain60.so').write_bytes(libraries['libmain.so'])
        command(helper, 'write', source, work / 'same-engines.json', second=second, success=False)
        second.write_bytes(libraries['libmain60.so'])
        (staged / 'libmain60.so').write_bytes(libraries['libmain60.so'])
        passed.append('same engine copied into both rate slots')

        primary.unlink()
        command(helper, 'write', source, work / 'missing-output.json', second=second, success=False)
        primary.write_bytes(libraries['libmain.so'])
        passed.append('old stage cannot substitute for missing primary build output')

        command(helper, 'write', source, work / 'missing-second.json',
                second=work / 'nonexistent.so', success=False)
        passed.append('selected secondary build output missing')

    print('PASS: engine packaging provenance (' + str(len(passed)) + ' cases)')
    for label in passed:
        print('  ' + label)


if __name__ == '__main__':
    main()
