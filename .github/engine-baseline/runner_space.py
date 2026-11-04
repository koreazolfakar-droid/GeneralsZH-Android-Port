#!/usr/bin/env python3
"""Free only unused hosted-runner SDKs before checksummed engine-state restore."""
# GeneralsX @build Codex 04/11/2026 The verified state cannot fit the default runner image.
import argparse
import os
from pathlib import Path
import shutil

UNUSED_SDKS = ('usr/local/lib/android', 'usr/share/dotnet', 'opt/ghc',
               'usr/local/share/boost', 'opt/hostedtoolcache/CodeQL')


def cleanup(root):
    # Fixed image paths only. No environment-selected paths or recursive glob.
    # Never remove /opt/android-sdk, vcpkg, sources, objects or compiler caches.
    for relative in UNUSED_SDKS:
        path = root / relative
        if path.is_symlink():
            path.unlink()  # Never follow a hosted image's symlink target.
        elif path.is_dir():
            shutil.rmtree(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print('\n'.join('/' + p for p in UNUSED_SDKS))
        return
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_OS') != 'Linux':
        raise SystemExit('Cleanup is restricted to the Linux GitHub Actions runner')
    print('Runner free bytes before:', shutil.disk_usage('/').free, flush=True)
    cleanup(Path('/'))
    print('Runner free bytes after:', shutil.disk_usage('/').free, flush=True)


if __name__ == '__main__':
    main()
