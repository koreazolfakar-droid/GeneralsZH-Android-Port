#!/usr/bin/env python3
"""Run the production validation-layer packaging block with an isolated fetcher."""
# GeneralsX @bugfix Codex 05/10/2026 Guard selected-staging-path propagation without an Android build.
from pathlib import Path
import os
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]
source = (repo / 'scripts/build/android/package-android-zh.sh').read_text()
block = source[source.index('VVL_STAGED='):source.index('\necho "==> Staged $(ls')]
for scenario in ('fetch', 'cached', 'unavailable'):
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        project = root / 'project'
        staging = root / 'selected staging'
        jni = root / 'jni'
        fetcher = project / 'scripts/build/android/fetch-vulkan-validation-layer.sh'
        fetcher.parent.mkdir(parents=True)
        jni.mkdir()
        layer = staging / 'vulkan_validation/libVkLayer_khronos_validation.so'
        fetched = root / 'fetched'
        fetcher.write_text('#!/bin/bash\nset -eu\ntouch "$FETCH_MARKER"\n'
                           'if [ "$SCENARIO" = unavailable ]; then exit 1; fi\n'
                           'mkdir -p "$GX_VULKAN_VALIDATION"\n'
                           'printf fixture > "$GX_VULKAN_VALIDATION/libVkLayer_khronos_validation.so"\n')
        fetcher.chmod(0o755)
        if scenario == 'cached':
            layer.parent.mkdir(parents=True)
            layer.write_text('cached fixture')
        env = dict(os.environ, PROJECT_ROOT=str(project), STAGING=str(staging),
                   JNILIBS=str(jni), FETCH_MARKER=str(fetched), SCENARIO=scenario,
                   GX_VULKAN_VALIDATION=str(root / 'wrong inherited path'))
        run = subprocess.run(['bash', '-euc', block], env=env, text=True,
                             capture_output=True, check=True)
        bundled = jni / layer.name
        if scenario == 'unavailable':
            assert not bundled.exists() and 'WARNING:' in run.stdout
        else:
            assert bundled.read_bytes() == layer.read_bytes()
        assert fetched.exists() == (scenario != 'cached')
        assert not (root / 'wrong inherited path').exists()
print('PASS: selected staging, cached layer and unavailable-layer warning')
