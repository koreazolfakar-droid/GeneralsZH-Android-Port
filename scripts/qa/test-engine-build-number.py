#!/usr/bin/env python3
"""Exercise the production sequence resolver with real full and shallow Git graphs.

Host-only tests: no Android tools, dependency installation or engine compilation.
"""
# GeneralsX @build Codex 05/10/2026 Reproduce and reject Engine Build=1 from shallow history.
from pathlib import Path
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[2]
    resolver = root / 'scripts/build/android/engine-build-number.sh'
    with tempfile.TemporaryDirectory(prefix='gx-engine-history-') as temporary:
        work = Path(temporary)
        source = work / 'source with spaces'
        subprocess.run(['git', 'init', '--quiet', '--initial-branch=main', str(source)], check=True)
        for index in range(3):
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Engine sequence test',
                            '-c', 'user.email=engine-test@example.invalid', 'commit', '--quiet',
                            '--allow-empty', '--no-gpg-sign', '-m', str(index)], check=True)
        full = subprocess.run(['bash', str(resolver), str(source)], capture_output=True, text=True)
        assert full.returncode == 0 and full.stdout.strip() == '3', full
        shallow = work / 'shallow'
        subprocess.run(['git', 'clone', '--quiet', '--depth=1', source.as_uri(), str(shallow)], check=True)
        assert subprocess.check_output(['git', '-C', str(shallow), 'rev-list', '--count', 'HEAD'], text=True).strip() == '1'
        rejected = subprocess.run(['bash', str(resolver), str(shallow)], capture_output=True, text=True)
        assert rejected.returncode != 0 and not rejected.stdout.strip(), rejected
        assert 'complete source history' in rejected.stderr, rejected
        subprocess.run(['git', '-C', str(shallow), 'fetch', '--quiet', '--unshallow', '--no-tags'], check=True)
        restored = subprocess.run(['bash', str(resolver), str(shallow)], capture_output=True, text=True)
        assert restored.returncode == 0 and restored.stdout.strip() == '3', restored
        invalid = subprocess.run(['bash', str(resolver), str(work)], capture_output=True, text=True)
        assert invalid.returncode != 0 and not invalid.stdout.strip(), invalid
    print('PASS: full graph count, shallow Build=1 rejection, fetched history recovery, invalid repository')


if __name__ == '__main__':
    main()
