#!/usr/bin/env python3
"""Record each real ccache request and result without exposing environment values."""
import json, os, pathlib, subprocess, sys, time, re, hashlib
directory = pathlib.Path(os.environ['GX_COMPILE_RECORDS']) / os.environ.get('GX_BUILD_PHASE', 'configure')
directory.mkdir(parents=True, exist_ok=True)
identifier = str(time.time_ns()) + '-' + str(os.getpid())
log = directory / (identifier + '.log')
arguments = sys.argv[1:]
# GeneralsX @build Codex 08/10/2026 A graph/configure regression must not rebuild
# external packages even if Ninja's human-readable dry-run wording changes.
sources = [a for a in arguments if a.endswith(('.cpp', '.c', '.cxx', '.cc'))]
if any('/_deps/' in str(pathlib.Path(a).resolve()) or '/opt/vcpkg/' in str(pathlib.Path(a).resolve()) for a in sources):
    sys.exit('EXTERNAL DEPENDENCY REBUILD REFUSED')
repairs = []
verified=json.loads(pathlib.Path(os.environ['GX_VERIFIED_HEADERS']).read_text()) if os.environ.get('GX_VERIFIED_HEADERS') else {}
# Clang reports one stale include at a time. The pinned libc++ sysroot alone
# may contain hundreds of PCH inputs; 64 retries was too low for this case.
# Only checksummed, explicitly allowlisted files may be repaired.
for attempt in range(512):
    result = subprocess.run(['ccache', *arguments], env=dict(os.environ, CCACHE_LOGFILE=str(log)), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sys.stdout.write(result.stdout); sys.stderr.write(result.stderr)
    if result.returncode == 0: break
    matches=re.findall(r"fatal error: file '([^']+)' has been modified since the precompiled header '[^']+' was built: mtime changed \(was ([0-9]+), now ([0-9]+)\)",result.stderr)
    if not matches: break
    restored=False
    for name,expected,current in matches:
        path=pathlib.Path(name).resolve()
        if (str(path) not in verified or not path.is_file() or path.is_symlink()
                or hashlib.sha256(path.read_bytes()).hexdigest()!=verified[str(path)]):
            continue
        # No unverified NDK content or future PCH timestamps. All SDK paths
        # must belong to the pinned, hashed header inventory from ndk_cache.py.
        if str(path).startswith('/opt/android-sdk/ndk/'):
            if (not str(path).startswith('/opt/android-sdk/ndk/27.2.12479018/')
                    or int(expected) > 1791292742):
                continue
        # Other compiler processes may have repaired the same include first.
        # Retry when the checksum is still valid and its mtime now matches.
        if path.stat().st_mtime_ns // 1000000000 == int(expected):
            restored = True
            continue
        os.utime(path,(int(expected),int(expected)))
        repairs.append({'path':str(path),'verified_sha256':verified[str(path)],'old_mtime':int(current),'restored_mtime':int(expected),'attempt':attempt})
        print('Verified unchanged PCH input timestamp restored: '+str(path),flush=True)
        restored=True
    if not restored: break

output = arguments[arguments.index('-o') + 1] if '-o' in arguments else None
sources = [a for a in arguments if a.endswith(('.cpp', '.c', '.cxx', '.cc'))]
record = {'phase': os.environ.get('GX_BUILD_PHASE'), 'sources': sources,
          'output': output, 'arguments': arguments, 'exit': result.returncode, 'pch_mtime_repairs':repairs, 'attempts':attempt+1}
(directory / (identifier + '.json')).write_text(json.dumps(record) + '\n')
sys.exit(result.returncode)
