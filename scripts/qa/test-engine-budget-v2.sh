#!/usr/bin/env bash
# Fast host checks only: no Android Gradle/NDK/APK rebuild and no build cache deletion.
set -euo pipefail
cd "$(dirname "$0")/../.."
temp="$(mktemp -d)"
trap 'rm -rf "$temp"' EXIT
c++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -fsanitize=undefined -fno-sanitize-recover=undefined \
  -IGeneralsMD/Code/GameEngine/Include \
  -ICore/Libraries/Source/d3d8gles/src \
  scripts/qa/test-engine-budget-v2.cpp -o "$temp/test-engine-budget-v2"
"$temp/test-engine-budget-v2"
python3 - <<'PY'
from pathlib import Path
engine=Path('GeneralsMD/Code/GameEngine/Source/Common/GameEngine.cpp').read_text()
thread=Path('Core/Libraries/Source/d3d8gles/src/gles_thread.cpp').read_text()
assert 'GXCatchUpBudget::remainingMs(spentMs, normalFps)' in engine
assert 'gxCatchUpSpedUpLogic(gxFrameWorkStart)' in engine
assert 's_debt = 0.0; // never carry a high-speed backlog' in engine
assert 'gxrt::SwapIntervalCache' not in thread  # same-namespace class, no duplicate wrapper
assert thread.count('applySwapInterval(swapInterval);') == 2
assert thread.count('s_swapInterval.invalidate();') >= 3
assert 'SDL_GL_SetSwapInterval(requested)' in thread
print('PASS: implementation wiring + host sanitizer regressions')
PY
