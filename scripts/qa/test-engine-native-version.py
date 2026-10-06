#!/usr/bin/env python3
"""Verify Android Git history recovery and the production native version fields.

Uses temporary Git/CMake resource fixtures; never builds the engine, installs an
Android toolchain or changes existing build artifacts. GX_TEST_CMAKE may select an
already installed CMake executable when it is not on PATH.
"""
# GeneralsX @build Codex 06/10/2026 Reject native revision 1 even when APK metadata is correct.
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def run(arguments, *, ci=False, success=True):
    environment = dict(os.environ, GITHUB_ACTIONS='true' if ci else 'false')
    result = subprocess.run(list(map(str, arguments)), env=environment,
                            text=True, capture_output=True)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    return result


def git(root, *arguments):
    return run(['git', '-C', root, *arguments]).stdout.strip()


def main():
    root = Path(__file__).resolve().parents[2]
    cmake = os.environ.get('GX_TEST_CMAKE') or shutil.which('cmake')
    assert cmake, 'Set GX_TEST_CMAKE to an existing CMake executable'
    helper = root / 'scripts/build/android/prepare-engine-history.sh'
    cases = []
    with tempfile.TemporaryDirectory(prefix='gx-native-history-') as temporary:
        work = Path(temporary)
        source = work / 'source with spaces'
        run(['git', 'init', '--quiet', '--initial-branch=main', source])
        for relative in ['scripts/build/android/prepare-engine-history.sh',
                         'scripts/build/android/engine-build-number.sh',
                         'resources/CMakeLists.txt',
                         'resources/gitinfo/git_watcher.cmake',
                         'resources/gitinfo/gitinfo.cpp.in',
                         'resources/gitinfo/gitinfo.h']:
            target = source / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        # Only production resources are configured. No game/dependency targets exist.
        (source / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.25)\n'
            'project(NativeVersionFixture LANGUAGES CXX)\n'
            'add_subdirectory(resources)\n')
        for index in range(3):
            (source / 'marker.txt').write_text(str(index) + '\n')
            run(['git', '-C', source, 'add', '.'])
            run(['git', '-C', source, '-c', 'user.name=Native version fixture',
                 '-c', 'user.email=fixture@example.invalid', 'commit', '--quiet',
                 '--no-gpg-sign', '-m', 'Fixture ' + str(index)])
        expected_head = git(source, 'rev-parse', 'HEAD')
        assert run(['bash', helper, source]).stdout.strip() == '3'
        cases.append('full history yields actual revision')

        shallow = work / 'shallow source'
        run(['git', 'clone', '--quiet', '--depth=1', source.as_uri(), shallow])
        rejected = run(['bash', helper, shallow], success=False)
        assert 'complete source history' in rejected.stderr
        assert git(shallow, 'rev-list', '--count', 'HEAD') == '1'
        cases.append('shallow local source rejected without network or HEAD change')

        # The actual Android resources guard must recover BEFORE the Git watcher runs.
        build = work / 'resource fixture outputs'
        run([cmake, '-S', shallow, '-B', build, '-DANDROID=ON'], ci=True)
        assert git(shallow, 'rev-parse', '--is-shallow-repository') == 'false'
        assert git(shallow, 'rev-parse', 'HEAD') == expected_head
        assert git(shallow, 'rev-list', '--count', 'HEAD') == '3'
        cases.append('production Android configure recovers complete graph and retains HEAD')
        run([cmake, '--build', build, '--target', 'check_git'], ci=True)
        generated = (build / 'resources/gitinfo.cpp').read_text()
        assert re.search(r'int GitRevision = 3;', generated)
        assert f'const char GitSHA1[] = "{expected_head}";' in generated
        assert run(['bash', helper, shallow], ci=True).stdout.strip() == '3'
        cases.append('production native GitRevision and GitSHA1 agree with packaging sequence')

        offline = work / 'offline shallow source'
        run(['git', 'clone', '--quiet', '--depth=1', source.as_uri(), offline])
        run(['git', '-C', offline, 'remote', 'remove', 'origin'])
        run(['bash', helper, offline], ci=True, success=False)
        assert git(offline, 'rev-parse', '--is-shallow-repository') == 'true'
        assert git(offline, 'rev-parse', 'HEAD') == expected_head
        cases.append('missing-origin CI recovery fails safely without relabeling revision 1')
        run(['bash', helper, work], ci=True, success=False)
        cases.append('invalid source repository rejected')
    print('PASS: native engine version (' + str(len(cases)) + ' cases)')
    for case in cases:
        print('  ' + case)


if __name__ == '__main__':
    main()
