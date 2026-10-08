#!/usr/bin/env python3
"""Versioned full-state receipts and non-destructive artifact backup/restore.

No compilation, dependency installation, key access or publication occurs here.
"""
# GeneralsX @build Codex 08/10/2026 Preserve exact incremental state across workflow branches.
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

TOOLS = Path(__file__).resolve().parent
CONFIG = json.loads((TOOLS / 'config.json').read_text())
STATES = ('android-vulkan', 'engine-baseline-30', 'engine-baseline-60')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def capture(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def identity(root):
    ndk = Path(os.environ['ANDROID_NDK_HOME'])
    tools = '\n'.join(capture(*args) for args in (
        ('cmake', '--version'), ('ninja', '--version'),
        (ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin/clang', '--version')))
    # Include configuration/dependency recipes, not source HEAD: compatible
    # ancestor objects must remain discoverable when engine source changes.
    recipes = ['CMakePresets.json', 'vcpkg.json', 'vcpkg-lock.json']
    recipes += [str(p.relative_to(root)) for p in sorted((root / 'cmake').rglob('*')) if p.is_file()]
    digest = hashlib.sha256((tools + CONFIG['ndk']).encode())
    for name in recipes:
        path = root / name
        digest.update(name.encode())
        digest.update(path.read_bytes() if path.exists() else b'<absent>')
    return digest.hexdigest()[:24], hashlib.sha256(tools.encode()).hexdigest()[:16]


def layout(root):
    return {
        'common': root / 'build/android-vulkan',
        '30': root / 'build/engine-baseline-30',
        '60': root / 'build/engine-baseline-60',
        'ccache': Path(os.environ['CCACHE_DIR']),
        'sdk': Path(os.environ['ANDROID_NDK_HOME']).parent.parent,
        'vcpkg': Path(os.environ['VCPKG_ROOT']),
        'vcpkg-cache': Path.home() / '.cache/vcpkg',
        'host-tools': root / 'host-tool-recovery',
    }


def inventory(root):
    result = {}
    for name in STATES:
        directory = root / 'build' / name
        required = ['CMakeCache.txt', 'build.ninja', '.ninja_deps', '.ninja_log']
        if name != 'android-vulkan':
            required += ['resources/gitinfo.cpp', 'GeneralsMD/Code/Main/libmain.so']
        if not (directory / 'CMakeFiles').is_dir():
            raise ValueError('INCREMENTAL BUILD ENVIRONMENT REQUIRED: ' + str(directory / 'CMakeFiles'))
        files = required + [str(p.relative_to(directory)) for p in sorted(directory.rglob('*.o'))]
        if len(files) == len(required):
            raise ValueError('INCREMENTAL BUILD ENVIRONMENT REQUIRED: missing objects in ' + name)
        for relative in files:
            if not (directory / relative).is_file():
                raise ValueError('INCREMENTAL BUILD ENVIRONMENT REQUIRED: ' + name + '/' + relative)
        cache = (directory / 'CMakeCache.txt').read_text()
        if 'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(root) + '\n' not in cache:
            raise ValueError('Workspace path differs from retained CMake state; do not rebase blindly')
        if name != 'android-vulkan':
            hz = 'ON' if name.endswith('60') else 'OFF'
            if 'SAGE_HIGH_FPS_SIM:BOOL=' + hz + '\n' not in cache:
                raise ValueError('Simulation variant configuration mismatch: ' + name)
        result[name] = {relative: sha(directory / relative) for relative in files}
    return result


def receipt_path(root):
    return root / 'build/android-vulkan/incremental-receipt.json'


def inspect(root, compat, legacy=False):
    # Always validate complete state before any CMake configure or native target.
    actual = inventory(root)
    if legacy:
        _, old_identity = identity(root)
        if old_identity != CONFIG['legacy_identity']:
            raise ValueError('Legacy toolchain identity mismatch; do not regenerate the baseline')
        for name in STATES[1:]:
            if len(actual[name]) < 900:
                raise ValueError('Legacy engine objects are incomplete')
        receipt = {'schema': 1, 'source': CONFIG['legacy_source'],
                   'sequence': CONFIG['legacy_sequence'], 'compatibility': compat,
                   'workspace': str(root), 'files': actual, 'legacy': True}
    else:
        receipt = json.loads(receipt_path(root).read_text())
        if (receipt.get('schema') != 1 or receipt['compatibility'] != compat
                or receipt['workspace'] != str(root) or receipt['files'] != actual):
            raise ValueError('Incremental receipt mismatch/incomplete restore; refusing native build')
    if (not re.fullmatch('[0-9a-f]{40}', receipt['source'])
            or type(receipt['sequence']) is not int or receipt['sequence'] <= 0):
        raise ValueError('Invalid retained source identity')
    if capture('git', '-C', root, 'rev-parse', '--is-shallow-repository') != 'false':
        raise ValueError('Complete Git history required')
    subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', receipt['source'], 'HEAD'], check=True)
    if int(capture('git', '-C', root, 'rev-list', '--count', receipt['source'])) != receipt['sequence']:
        raise ValueError('Retained sequence is not the real complete-history count')
    # Use the existing actual-ELF provenance verifier; strings/JSON alone are insufficient.
    import importlib.util
    spec = importlib.util.spec_from_file_location('update_artifacts', root / 'scripts/update/update-artifacts.py')
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    for name in STATES[1:]:
        verifier.native_stamp((root / 'build' / name / 'GeneralsMD/Code/Main/libmain.so').read_bytes(),
                              receipt['source'], receipt['sequence'])
    return receipt


def seal(root, compat):
    source = capture('git', '-C', root, 'rev-parse', 'HEAD')
    sequence = int(capture('bash', root / 'scripts/build/android/engine-build-number.sh', root))
    inputs = {}
    for name in capture('git', '-C', root, 'ls-files').splitlines():
        path = root / name
        if path.is_file() and not path.is_symlink():
            inputs[name] = {'sha256': sha(path), 'mtime_ns': path.stat().st_mtime_ns}
    receipt = {'schema': 1, 'source': source, 'sequence': sequence,
               'compatibility': compat, 'workspace': str(root),
               'files': inventory(root), 'inputs': inputs}
    receipt_path(root).write_text(json.dumps(receipt) + '\n')
    inspect(root, compat)
    return receipt


def normalize(root, receipt):
    # Only byte-identical source inputs regain their saved timestamps. Changed
    # inputs keep current mtimes so Ninja and PCH invalidation remain effective.
    if receipt.get('legacy'):
        changed = set(capture('git', '-C', root, 'diff', '--name-only', receipt['source'], 'HEAD').splitlines())
        inputs = {p: {'sha256': sha(root / p), 'mtime_ns': CONFIG['legacy_source_epoch'] * 10**9}
                  for p in capture('git', '-C', root, 'ls-files').splitlines()
                  if p not in changed and (root / p).is_file() and not (root / p).is_symlink()}
    else:
        inputs = receipt['inputs']
    for name, record in inputs.items():
        path = root / name
        if path.is_file() and not path.is_symlink() and sha(path) == record['sha256']:
            os.utime(path, ns=(path.stat().st_atime_ns, record['mtime_ns']))


def preserve_host_tools(root):
    # Preserve working host executables/modules too: a runner image update must
    # not silently change CMake/Ninja and invalidate every object next session.
    pinned = root / 'host-tool-recovery/pinned'
    (pinned / 'bin').mkdir(parents=True, exist_ok=True)
    (pinned / 'lib').mkdir(exist_ok=True)
    for name in ('cmake', 'ninja', 'ccache'):
        found = shutil.which(name)
        if found is None:
            raise ValueError('Required retained host tool absent: ' + name)
        executable = Path(found).resolve()
        destination = pinned / 'bin' / name
        if executable != destination.resolve():
            shutil.copy2(executable, destination)
        libraries = capture('ldd', executable)
        for library in re.findall(r'=> (/\S+)', libraries):
            # System ABI is provided by ubuntu-24.04; hiredis is not guaranteed
            # installed and was already recovered for the successful old job.
            if 'hiredis' in library:
                shutil.copy2(library, pinned / 'lib' / Path(library).name)
    info = capture('cmake', '--system-information')
    cmake_root = Path(re.search(r'^CMAKE_ROOT "([^"]+)"', info, re.M)[1])
    modules = pinned / 'share' / cmake_root.name
    if cmake_root.resolve() != modules.resolve():
        shutil.copytree(cmake_root, modules, dirs_exist_ok=True)


def backup(root, output, receipt):
    preserve_host_tools(root)
    output.mkdir(parents=True, exist_ok=True)
    description = {'schema': 1, 'receipt': receipt, 'archives': {}}
    # Fixed whitelist: no source checkout, app/game data, signing key, credential
    # directories or arbitrary environment-selected extra paths can be archived.
    for name, directory in layout(root).items():
        if not directory.is_dir():
            raise ValueError('Required backup directory absent: ' + name)
        destination = output / (name + '.tar.gz')
        with tarfile.open(destination, 'w:gz', compresslevel=1) as archive:
            archive.add(directory, arcname=name)
        description['archives'][name] = {'file': destination.name, 'sha256': sha(destination)}
    (output / 'backup.json').write_text(json.dumps(description) + '\n')


def prepare_member(member, name, destination):
    if member.name == name and member.isdir():
        return None
    if not member.name.startswith(name + '/'):
        raise ValueError('Unexpected backup member')
    member.name = member.name[len(name) + 1:]
    if member.islnk():
        if not member.linkname.startswith(name + '/'):
            raise ValueError('Escaping backup hard link')
        member.linkname = member.linkname[len(name) + 1:]
    # GeneralsX @bugfix Codex 08/10/2026 vcpkg buildtrees use absolute src
    # symlinks inside the retained vcpkg root. Make only those links relative,
    # preserving their target while keeping data_filter's escape protection.
    if member.issym() and os.path.isabs(member.linkname):
        target = Path(member.linkname).resolve()
        if not target.is_relative_to(destination.resolve()):
            raise ValueError('Escaping absolute backup symlink: ' + member.name)
        member.linkname = os.path.relpath(target, destination / Path(member.name).parent)
    return member


def restore(root, directory, compat=None):
    description = json.loads((directory / 'backup.json').read_text())
    expected = layout(root)
    if (description.get('schema') != 1 or set(description['archives']) != set(expected)
            or (compat is not None and description['receipt']['compatibility'] != compat)
            or description['receipt']['workspace'] != str(root)):
        raise ValueError('Incompatible backup layout/toolchain/workspace')
    # Verify every archive before writing any restored bytes.
    for name, info in description['archives'].items():
        if info['file'] != name + '.tar.gz' or sha(directory / info['file']) != info['sha256']:
            raise ValueError('Backup archive checksum mismatch: ' + name)
    for name, destination in expected.items():
        if destination.exists() and any(destination.iterdir()):
            raise ValueError('Refusing to overwrite populated build/cache directory: ' + str(destination))
    # data_filter rejects traversal, devices, absolute/escaping symlinks. Check
    # all members before extraction; no blanket tar extraction into the workspace.
    for name, destination in expected.items():
        with tarfile.open(directory / (name + '.tar.gz'), 'r:gz') as archive:
            for member in archive.getmembers():
                member = prepare_member(member, name, destination)
                if member is not None:
                    tarfile.data_filter(member, str(destination))
    for name, destination in expected.items():
        destination.mkdir(parents=True, exist_ok=True)
        with tarfile.open(directory / (name + '.tar.gz'), 'r:gz') as archive:
            members = [prepare_member(m, name, destination) for m in archive.getmembers()]
            for member in members:
                if member is not None:
                    archive.extract(member, destination, filter='data')
    receipt_path(root).write_text(json.dumps(description['receipt']) + '\n')
    activate_tools(root)
    compat, _ = identity(root)
    return inspect(root, compat)


def activate_tools(root):
    pinned = root / 'host-tool-recovery/pinned'
    if (pinned / 'bin/cmake').is_file():
        os.environ['PATH'] = str(pinned / 'bin') + ':' + os.environ['PATH']
        os.environ['LD_LIBRARY_PATH'] = str(pinned / 'lib') + ':' + os.environ.get('LD_LIBRARY_PATH', '')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['identity', 'inspect', 'seal', 'backup', 'restore', 'normalize'])
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--directory', type=Path, default=Path('incremental-backup'))
    parser.add_argument('--legacy', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if args.operation == 'restore':
        receipt = restore(root, args.directory)
        print(json.dumps({'status': 'PASS', 'source': receipt['source'], 'sequence': receipt['sequence']}))
        return
    activate_tools(root)
    compat, tool = identity(root)
    if args.operation == 'identity':
        print(json.dumps({'compatibility': compat, 'toolchain': tool}))
        return
    if args.operation == 'seal':
        receipt = seal(root, compat)
    else:
        receipt = inspect(root, compat, args.legacy)
        if args.operation == 'backup':
            backup(root, args.directory, receipt)
        elif args.operation == 'normalize':
            normalize(root, receipt)
    print(json.dumps({'status': 'PASS', 'source': receipt['source'], 'sequence': receipt['sequence']}))


if __name__ == '__main__':
    main()
