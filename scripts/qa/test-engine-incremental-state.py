#!/usr/bin/env python3
"""Host tests for real backup/restore guards; never compile an Android engine."""
# GeneralsX @build Codex 08/10/2026 Exercise receipt, archive and workflow failure paths.
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / '.github/engine-baseline'
spec = importlib.util.spec_from_file_location('engine_state', TOOLS / 'state.py')
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)


def native_fixture(commit, sequence):
    # A data-only AArch64 ELF with actual file-backed dynamic OBJECT symbols.
    # This is a test vector, never a substitute for an engine/build output.
    data = bytearray(512)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<H', data, 18, 183)
    struct.pack_into('<Q', data, 40, 64)
    struct.pack_into('<HH', data, 58, 64, 4)
    payload = commit.encode() + b'\0' + struct.pack('<i', sequence)
    names = b'\0GitSHA1\0GitRevision\0'
    struct.pack_into('<IIQQQQIIQQ', data, 128, 0, 1, 0, 4096, 320, len(payload), 0, 0, 1, 0)
    struct.pack_into('<IIQQQQIIQQ', data, 192, 0, 3, 0, 0, 384, len(names), 0, 0, 1, 0)
    struct.pack_into('<IIQQQQIIQQ', data, 256, 0, 11, 0, 0, 416, 48, 2, 0, 8, 24)
    data[320:320 + len(payload)] = payload
    data[384:384 + len(names)] = names
    struct.pack_into('<IBBHQQ', data, 416, 1, 0x11, 0, 1, 4096, 41)
    struct.pack_into('<IBBHQQ', data, 440, 9, 0x11, 0, 1, 4137, 4)
    return bytes(data)


class Recovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='engine-state-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.destinations = {
            'common': self.root / 'build/android-vulkan',
            '30': self.root / 'build/engine-baseline-30',
            '60': self.root / 'build/engine-baseline-60',
            **{n: Path(self.temp.name) / n for n in
               ('sdk', 'ccache', 'vcpkg', 'vcpkg-cache', 'host-tools')},
        }
        for name, directory in self.destinations.items():
            directory.mkdir(parents=True)
            (directory / 'retained').write_text(name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.input = self.root / 'input.cpp'
        self.input.write_text('unchanged source input\n')
        self.git('add', 'input.cpp')
        self.git('commit', '-qm', 'fixture baseline')
        self.source = self.git('rev-parse', 'HEAD')
        verifier = self.root / 'scripts/update/update-artifacts.py'
        verifier.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'scripts/update/update-artifacts.py', verifier)
        resolver = self.root / 'scripts/build/android/engine-build-number.sh'
        resolver.parent.mkdir(parents=True)
        shutil.copy2(ROOT / 'scripts/build/android/engine-build-number.sh', resolver)
        for name in state.STATES:
            directory = self.root / 'build' / name
            (directory / 'CMakeFiles').mkdir()
            cache = 'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(self.root) + '\n'
            if name != 'android-vulkan':
                cache += 'SAGE_HIGH_FPS_SIM:BOOL=' + ('ON' if name.endswith('60') else 'OFF') + '\n'
                (directory / 'resources').mkdir()
                (directory / 'resources/gitinfo.cpp').write_text('metadata fixture\n')
                engine = directory / 'GeneralsMD/Code/Main/libmain.so'
                engine.parent.mkdir(parents=True)
                engine.write_bytes(native_fixture(self.source, 1))
            (directory / 'CMakeCache.txt').write_text(cache)
            for filename in ('build.ninja', '.ninja_log', '.ninja_deps', 'CMakeFiles/engine.o'):
                (directory / filename).write_bytes(b'retained test state ' + filename.encode())
        self.compat = 'host-test-compatibility'
        self.patches = [patch.object(state, 'layout', return_value=self.destinations),
                        patch.object(state, 'identity', return_value=(self.compat, 'tools')),
                        patch.object(state, 'activate_tools'), patch.object(state, 'preserve_host_tools')]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.receipt = state.seal(self.root, self.compat)
        self.backup_dir = Path(self.temp.name) / 'backup'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def backup_and_retain(self):
        state.backup(self.root, self.backup_dir, self.receipt)
        retained = Path(self.temp.name) / 'preserved-originals'
        retained.mkdir()
        for name, directory in self.destinations.items():
            directory.rename(retained / name)
        return retained

    def modify_archive(self, member):
        target = self.backup_dir / 'ccache.tar.gz'
        with state.tarfile.open(target, 'w:gz') as archive:
            archive.addfile(member, io.BytesIO(b'bad') if member.isfile() else None)
        meta = json.loads((self.backup_dir / 'backup.json').read_text())
        meta['archives']['ccache']['sha256'] = state.sha(target)
        (self.backup_dir / 'backup.json').write_text(json.dumps(meta))

    def assert_nothing_restored(self):
        self.assertTrue(all(not p.exists() for p in self.destinations.values()))

    def test_roundtrip_all_components_and_links(self):
        cache = self.destinations['ccache']
        (cache / 'symlink').symlink_to('retained')
        os.link(cache / 'retained', cache / 'hardlink')
        original = self.backup_and_retain()
        restored = state.restore(self.root, self.backup_dir, self.compat)
        self.assertEqual(restored['source'], self.source)
        for name, directory in self.destinations.items():
            self.assertEqual((directory / 'retained').read_bytes(), (original / name / 'retained').read_bytes())
        self.assertTrue((cache / 'symlink').is_symlink())
        self.assertEqual((cache / 'hardlink').stat().st_ino, (cache / 'retained').stat().st_ino)
        self.assertEqual(state.inventory(self.root), self.receipt['files'])

    def test_corrupt_archive_stops_before_writes(self):
        self.backup_and_retain()
        with (self.backup_dir / '30.tar.gz').open('ab') as stream:
            stream.write(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            state.restore(self.root, self.backup_dir)
        self.assert_nothing_restored()

    def test_output_nanoseconds_survive_backup_restore(self):
        original = 1791292853781287193
        outputs = [self.destinations[n] / 'CMakeFiles/engine.o' for n in ('30', '60')]
        for path in outputs:
            os.utime(path, ns=(original, original))
        self.backup_and_retain()
        state.restore(self.root, self.backup_dir, self.compat)
        for path in outputs:
            self.assertEqual(path.stat().st_mtime_ns, original)

    def test_invalid_exact_timestamp_rejected_before_writes(self):
        self.backup_and_retain()
        member = state.tarfile.TarInfo('ccache/invalid-time')
        member.size = 3
        member.pax_headers['GX.mtime_ns'] = 'invalid'
        self.modify_archive(member)
        with self.assertRaisesRegex(ValueError, 'Invalid exact backup timestamp'):
            state.restore(self.root, self.backup_dir)
        self.assert_nothing_restored()

    def test_internal_absolute_symlink_restores_same_target(self):
        cache = self.destinations['ccache']
        (cache / 'absolute-src').symlink_to(cache / 'retained')
        self.backup_and_retain()
        state.restore(self.root, self.backup_dir, self.compat)
        link = cache / 'absolute-src'
        self.assertEqual(link.resolve(), cache / 'retained')
        self.assertFalse(os.path.isabs(os.readlink(link)))
        self.assertEqual(link.read_text(), 'ccache')

    def test_populated_directory_is_preserved(self):
        self.backup_and_retain()
        existing = self.destinations['ccache']
        existing.mkdir()
        (existing / 'user-state').write_text('preserve')
        with self.assertRaisesRegex(ValueError, 'overwrite populated'):
            state.restore(self.root, self.backup_dir)
        self.assertEqual((existing / 'user-state').read_text(), 'preserve')
        self.assertFalse(self.destinations['30'].exists())

    def test_archive_traversal_rejected_before_writes(self):
        self.backup_and_retain()
        member = state.tarfile.TarInfo('ccache/../../escape')
        member.size = 3
        self.modify_archive(member)
        with self.assertRaises(state.tarfile.FilterError):
            state.restore(self.root, self.backup_dir)
        self.assert_nothing_restored()

    def test_escaping_links_rejected_before_writes(self):
        self.backup_and_retain()
        for kind, target in ((state.tarfile.SYMTYPE, '/tmp/outside'),
                             (state.tarfile.SYMTYPE, '../../outside'),
                             (state.tarfile.LNKTYPE, 'other/payload')):
            member = state.tarfile.TarInfo('ccache/link')
            member.type, member.linkname = kind, target
            self.modify_archive(member)
            with self.assertRaises((ValueError, state.tarfile.FilterError)):
                state.restore(self.root, self.backup_dir)
            self.assert_nothing_restored()

    def test_workspace_and_toolchain_mismatch(self):
        self.backup_and_retain()
        with self.assertRaisesRegex(ValueError, 'Incompatible backup'):
            state.restore(self.root, self.backup_dir, 'wrong toolchain')
        meta = json.loads((self.backup_dir / 'backup.json').read_text())
        meta['receipt']['workspace'] = '/different/workspace'
        (self.backup_dir / 'backup.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'Incompatible backup'):
            state.restore(self.root, self.backup_dir)
        self.assert_nothing_restored()

    def test_missing_ninja_and_objects(self):
        directory = self.destinations['30']
        (directory / '.ninja_deps').rename(directory / 'original-deps')
        with self.assertRaisesRegex(ValueError, 'INCREMENTAL BUILD ENVIRONMENT REQUIRED'):
            state.inspect(self.root, self.compat)
        (directory / 'original-deps').rename(directory / '.ninja_deps')
        (directory / 'CMakeFiles/engine.o').rename(directory / 'CMakeFiles/engine.saved')
        with self.assertRaisesRegex(ValueError, 'missing objects'):
            state.inspect(self.root, self.compat)

    def test_wrong_variant_and_changed_objects(self):
        directory = self.destinations['60']
        cache = directory / 'CMakeCache.txt'
        saved = cache.read_text()
        cache.write_text(saved.replace('BOOL=ON', 'BOOL=OFF'))
        with self.assertRaisesRegex(ValueError, 'variant configuration mismatch'):
            state.inspect(self.root, self.compat)
        cache.write_text(saved)
        (directory / 'CMakeFiles/engine.o').write_text('different object')
        with self.assertRaisesRegex(ValueError, 'receipt mismatch'):
            state.inspect(self.root, self.compat)

    def test_actual_native_stamp_required(self):
        binary = self.destinations['30'] / 'GeneralsMD/Code/Main/libmain.so'
        binary.write_bytes(native_fixture(self.source, 3302))
        self.receipt['files'] = state.inventory(self.root)
        state.receipt_path(self.root).write_text(json.dumps(self.receipt))
        with self.assertRaisesRegex(ValueError, 'GitRevision'):
            state.inspect(self.root, self.compat)

    def test_sequence_must_match_complete_history(self):
        invalid = dict(self.receipt, sequence=3302)
        state.receipt_path(self.root).write_text(json.dumps(invalid))
        with self.assertRaisesRegex(ValueError, 'real complete-history count'):
            state.inspect(self.root, self.compat)

    def test_nonancestor_and_shallow_history_rejected(self):
        invalid = dict(self.receipt, source='0' * 40)
        state.receipt_path(self.root).write_text(json.dumps(invalid))
        with self.assertRaises(subprocess.CalledProcessError):
            state.inspect(self.root, self.compat)
        state.receipt_path(self.root).write_text(json.dumps(self.receipt))
        (self.root / '.git/shallow').write_text(self.source + '\n')
        with self.assertRaisesRegex(ValueError, 'Complete Git history'):
            state.inspect(self.root, self.compat)

    def test_mtime_restore_requires_identical_bytes(self):
        saved = self.receipt['inputs']['input.cpp']['mtime_ns']
        os.utime(self.input, ns=(saved + 10**9, saved + 10**9))
        state.normalize(self.root, self.receipt)
        self.assertEqual(self.input.stat().st_mtime_ns, saved)
        self.input.write_text('changed source input\n')
        changed = self.input.stat().st_mtime_ns
        state.normalize(self.root, self.receipt)
        self.assertEqual(self.input.stat().st_mtime_ns, changed)

    def test_unknown_archive_component_rejected(self):
        self.backup_and_retain()
        meta = json.loads((self.backup_dir / 'backup.json').read_text())
        meta['archives']['credentials'] = {'file': 'credentials.tar.gz', 'sha256': '0' * 64}
        (self.backup_dir / 'backup.json').write_text(json.dumps(meta))
        with self.assertRaisesRegex(ValueError, 'Incompatible backup'):
            state.restore(self.root, self.backup_dir)
        self.assert_nothing_restored()


class Workflow(unittest.TestCase):
    def test_retained_host_tools_can_be_backed_up_again(self):
        with tempfile.TemporaryDirectory(prefix='engine-host-tools-tests-') as tmp:
            root = Path(tmp)
            pinned = root / 'host-tool-recovery/pinned'
            (pinned / 'bin').mkdir(parents=True)
            (pinned / 'lib').mkdir()
            modules = pinned / 'share/cmake-fixture'
            modules.mkdir(parents=True)
            for name in ('cmake', 'ninja', 'ccache'):
                (pinned / 'bin' / name).write_bytes(b'retained executable')
            library = pinned / 'lib/libhiredis.so.1.1.0'
            library.write_bytes(b'retained host dependency')
            before = state.sha(library)
            def output(*args):
                if args[0] == 'ldd':
                    return 'libhiredis.so.1.1.0 => ' + str(library)
                return 'CMAKE_ROOT "' + str(modules) + '"'
            with patch.object(state.shutil, 'which', side_effect=lambda name: str(pinned / 'bin' / name)), patch.object(state, 'capture', side_effect=output):
                state.preserve_host_tools(root)
                state.preserve_host_tools(root)
            self.assertEqual(state.sha(library), before)

    def test_external_dependency_compile_guard(self):
        with tempfile.TemporaryDirectory(prefix='engine-compiler-tests-') as tmp:
            result = subprocess.run(['python3', str(TOOLS / 'compiler.py'), 'clang++', '-c',
                                     '/test/_deps/sdl3-src/source.cpp'],
                                    env=dict(os.environ, GX_COMPILE_RECORDS=tmp), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('EXTERNAL DEPENDENCY REBUILD REFUSED', result.stderr)
            self.assertFalse(list(Path(tmp).rglob('*.json')))

    def test_retry_accounting_and_hit_is_not_recompile(self):
        with tempfile.TemporaryDirectory(prefix='engine-summary-tests-') as tmp:
            out = Path(tmp) / 'baseline-report/compile-requests'
            out.mkdir(parents=True)
            rows = [(1, 'direct_cache_hit', 0), (2, 'direct_cache_hit\nResult: cache_miss', 0),
                    (1, 'cache_miss', 1)]
            for i, (attempts, results, code) in enumerate(rows):
                (out / (str(i) + '.json')).write_text(json.dumps({'attempts': attempts, 'exit': code, 'sources': [str(i) + '.cpp']}))
                (out / (str(i) + '.log')).write_text('Result: ' + results)
            subprocess.run(['python3', str(TOOLS / 'summarize.py')], cwd=tmp, check=True, capture_output=True)
            report = json.loads((Path(tmp) / 'baseline-report/compiler-summary.json').read_text())
            self.assertEqual(report['total_compile_requests'], 4)
            self.assertEqual(report['cache_hits'], 2)
            self.assertEqual(report['cache_misses'], 2)
            self.assertEqual(report['files_actually_compiled'], ['1.cpp'])
            self.assertEqual(report['failed_requests'], 1)

    def test_workflow_structure_and_shell_syntax(self):
        import yaml
        class Unique(yaml.SafeLoader):
            def construct_mapping(self, node, deep=False):
                result = {}
                for key, value in node.value:
                    k = self.construct_object(key, deep=deep)
                    if k in result:
                        raise ValueError('Duplicate YAML key: ' + str(k))
                    result[k] = self.construct_object(value, deep=deep)
                return result
        workflow = yaml.load((ROOT / '.github/workflows/build-android.yml').read_text(), Loader=Unique)
        template = yaml.load((TOOLS / 'legacy-export.yml').read_text(), Loader=Unique)
        self.assertEqual(set(template['jobs']), {'engine-incremental'})
        self.assertEqual(template[True]['workflow_dispatch']['inputs']['engine_incremental_mode']['options'], ['export-legacy'])
        original_job = dict(workflow['jobs']['engine-incremental'])
        export_job = dict(template['jobs']['engine-incremental'])
        original_job.pop('if'); export_job.pop('if')
        self.assertEqual(original_job, export_job)
        inputs = workflow[True]['workflow_dispatch']['inputs']  # YAML 1.1 treats on as boolean.
        self.assertEqual(inputs['engine_incremental_mode']['default'], 'inspect')
        job = workflow['jobs']['engine-incremental']
        self.assertEqual(job['permissions'], {'contents': 'read', 'actions': 'read'})
        self.assertFalse(job['concurrency']['cancel-in-progress'])
        for step in job['steps']:
            text = step.get('run', '')
            self.assertNotRegex(text, r'(gradlew|sdkmanager|cmake --fresh|ninja clean|rm -rf|publish-update|UPDATE_SIGNING_KEY)')
            if text:
                shell = re.sub(r'\$\{\{.*?\}\}', 'fixture', text)
                subprocess.run(['bash', '-n'], input=shell, text=True, check=True, capture_output=True)
        main = workflow['jobs']['build-android']['if']
        self.assertIn("inputs.engine_incremental_mode == 'off'", main)
        builder = (TOOLS / 'build.py').read_text()
        self.assertLess(builder.index('if not build_requested:'), builder.index('for rate in (30,60):'))
        self.assertIn('VERIFIED RUNTIME STATE REQUIRED', builder)
        self.assertIn('NEW APK REQUIRED', builder)
        self.assertIn('INCREMENTAL REUSE GUARD', builder)


if __name__ == '__main__':
    unittest.main(verbosity=2)
