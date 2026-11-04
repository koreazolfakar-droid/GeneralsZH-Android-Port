#!/usr/bin/env python3
"""Exercise fixed hosted-SDK cleanup; engine inputs and symlink targets survive."""
import importlib.util
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('runner_space', ROOT/'.github/engine-baseline/runner_space.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory(prefix='gx-runner-space-') as temp:
    root = Path(temp)
    protected = ('opt/android-sdk', 'opt/vcpkg', 'home/runner/work/source',
                 'home/runner/.cache/ccache', 'opt/hostedtoolcache/Python')
    for relative in (*module.UNUSED_SDKS, *protected):
        p = root/relative
        p.mkdir(parents=True)
        (p/'fixture').write_bytes(b'kept or removable')
    module.cleanup(root)
    assert all(not (root/p).exists() for p in module.UNUSED_SDKS)
    assert all((root/p/'fixture').read_bytes()==b'kept or removable' for p in protected)
    link=root/module.UNUSED_SDKS[0]
    link.symlink_to(root/protected[0], target_is_directory=True)
    module.cleanup(root)
    assert not link.is_symlink() and (root/protected[0]/'fixture').is_file()
print('PASS: only fixed unused SDK trees removed; pinned engine/cache paths and symlink targets preserved')
