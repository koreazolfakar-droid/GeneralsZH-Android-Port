#!/usr/bin/env python3
"""Verify signed upstream provenance and inventory source differences without a build.

Requires the audit's fetched upstream refs, Git and OpenSSL. --verify-live also
compares the official raw manifest with the fetched updates commit. The hotfix
tree is reconstructed from published evidence, NOT asserted to be the unavailable
local hotfix commit or a reproduction of the official engine binaries.
"""
# GeneralsX @build Codex 05/10/2026 Keep the source-only 3277 audit reproducible.
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.request import urlopen

RELEASE = '576e2265bf271176028d1cef4f2b3fe8caa20b34'
GPU_FIX = '5eb288be6119325b430c074a9bb851723a7876bc'
PROVENANCE = '7f679883314f79c9a302160e1c46e23e816b4f94'
START = 'a20f54728616ed3de69e4f25ab6e5092bbec01b2'
GPU = 'Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-live', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]

    def git(*arguments, **kwargs):
        return subprocess.check_output(['git', '-C', str(root), *arguments], **kwargs)

    def tree(ref):
        entries = {}
        for record in git('ls-tree', '-rz', '--full-tree', ref).split(b'\0'):
            if record:
                info, name = record.split(b'\t', 1)
                entries[name.decode()] = info.decode()
        return entries

    manifest_bytes = git('show', 'upstream/updates:manifest.json')
    manifest = json.loads(manifest_bytes)
    assert manifest['engine']['seq'] == 3277 and manifest['serial'] == 12, manifest
    update_source = (root / 'android/app/src/main/java/com/generalsx/zerohour/UpdateManager.java').read_text()
    public_key = re.search(r'PUBLIC_KEY_B64\s*=\s*"([^"]+)"', update_source).group(1)
    signature = base64.b64decode(git('show', 'upstream/updates:manifest.json.sig').strip())
    baseline = tree(RELEASE)
    with tempfile.TemporaryDirectory(prefix='gx-engine-audit-') as temporary:
        work = Path(temporary)
        (work / 'key.der').write_bytes(base64.b64decode(public_key))
        (work / 'signature.der').write_bytes(signature)
        (work / 'manifest.json').write_bytes(manifest_bytes)
        verified = subprocess.run(['openssl', 'dgst', '-sha256', '-verify', str(work / 'key.der'),
                                   '-keyform', 'DER', '-signature', str(work / 'signature.der'),
                                   str(work / 'manifest.json')], capture_output=True, text=True)
        assert verified.returncode == 0, verified.stderr
        # Apply only the published GPU file delta to the release file. No engine
        # compilation, checkout, reset, caches, APKs or project files are touched.
        candidate = work / GPU
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(git('show', f'{RELEASE}:{GPU}'))
        patch = git('diff', GPU_FIX + '^', GPU_FIX, '--', GPU)
        subprocess.run(['git', 'apply', '--'], input=patch, cwd=work, check=True)
        gpu_hash = git('hash-object', '--stdin', input=candidate.read_bytes()).decode().strip()
        baseline[GPU] = '100644 blob ' + gpu_hash
    live = False
    if args.verify_live:
        with urlopen('https://raw.githubusercontent.com/MYSOREZ/GeneralsZH-Android-Port/updates/manifest.json', timeout=30) as response:
            assert response.read() == manifest_bytes, 'live manifest advanced; re-audit before integration'
        live = True
    current = tree('HEAD')
    changed = [{'path': name, 'status': 'added' if name not in baseline else
                'deleted' if name not in current else 'modified',
                'baseline_entry': baseline.get(name), 'current_entry': current.get(name)}
               for name in sorted(baseline.keys() | current.keys())
               if baseline.get(name) != current.get(name)]
    assert current[GPU] == baseline[GPU], 'GPU file is not the release + documented hotfix'
    config = json.loads((root / 'update/config.json').read_text())
    assert all(config.get(key) == value for key, value in manifest['config'].items())
    integration = git('diff', '--name-only', START, 'HEAD').decode().splitlines()
    assert not any('/GameLogic/' in path or path.endswith(('/XferSave.cpp', '/XferLoad.cpp'))
                   for path in integration), 'unexpected simulation/serialization integration'
    print(json.dumps({
        'branch': git('branch', '--show-current').decode().strip(),
        'audited_head': git('rev-parse', 'HEAD').decode().strip(),
        'start_head': START,
        'manifest_commit': git('rev-parse', 'upstream/updates').decode().strip(),
        'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
        'manifest_signature_verified': True,
        'live_manifest_identical': live,
        'engine_sequence': manifest['engine']['seq'], 'manifest_serial': manifest['serial'],
        'release_commit': RELEASE, 'published_gpu_fix': GPU_FIX, 'provenance_commit': PROVENANCE,
        'unpublished_hotfix_commit': '2cc428d1b (unavailable; documented, not independently resolved)',
        'comparison_basis': 'reconstructed release tree plus only published GPU timer delta',
        'gpu_file_matches_documented_3277': True,
        'bundled_config_matches_signed_manifest': True,
        'full_history_count': int(git('rev-list', '--count', 'HEAD')),
        'integration_files': integration, 'difference_count': len(changed), 'differences': changed,
    }, indent=2))


if __name__ == '__main__':
    main()
