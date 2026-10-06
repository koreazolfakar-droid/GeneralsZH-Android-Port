#!/usr/bin/env python3
"""Record each real ccache request and result without exposing environment values."""
import json, os, pathlib, subprocess, sys, time
directory = pathlib.Path(os.environ['GX_COMPILE_RECORDS']) / os.environ.get('GX_BUILD_PHASE', 'configure')
directory.mkdir(parents=True, exist_ok=True)
identifier = str(time.time_ns()) + '-' + str(os.getpid())
log = directory / (identifier + '.log')
arguments = sys.argv[1:]
result = subprocess.run(['ccache', *arguments], env=dict(os.environ, CCACHE_LOGFILE=str(log)))
output = arguments[arguments.index('-o') + 1] if '-o' in arguments else None
sources = [a for a in arguments if a.endswith(('.cpp', '.c', '.cxx', '.cc'))]
record = {'phase': os.environ.get('GX_BUILD_PHASE'), 'sources': sources,
          'output': output, 'arguments': arguments, 'exit': result.returncode}
(directory / (identifier + '.json')).write_text(json.dumps(record) + '\n')
sys.exit(result.returncode)
