#!/usr/bin/env bash
set -euo pipefail

# Stable Android/mod baseline proven before the mobile-engine optimization work.
# Changing this SHA is a deliberate compatibility decision, not routine maintenance.
BASELINE_COMMIT="b21ec5d94d456e2078229436e6c4e676edd9dd04"

PROTECTED_PATHS=(
  "Core/GameEngine/Source/Common/INI/INI.cpp"
  "Core/GameEngine/Source/Common/System/ArchiveFile.cpp"
  "Core/GameEngine/Source/Common/System/ArchiveFileSystem.cpp"
  "Core/GameEngine/Source/Common/System/FileSystem.cpp"
  "Core/GameEngine/Source/Common/System/LocalFileSystem.cpp"
  "Core/GameEngineDevice/Source/StdDevice/Common/StdBIGFile.cpp"
  "Core/GameEngineDevice/Source/StdDevice/Common/StdBIGFileSystem.cpp"
  "Core/GameEngineDevice/Source/StdDevice/Common/StdLocalFileSystem.cpp"
  "GeneralsMD/Code/GameEngine/Source/Common/CommandLine.cpp"
  "GeneralsMD/Code/GameEngineDevice/Source/W3DDevice/GameClient/W3DFileSystem.cpp"
  "Core/GameEngine/Source/Common/System/Xfer.cpp"
  "Core/GameEngine/Source/Common/System/XferCRC.cpp"
  "Core/GameEngine/Source/Common/System/XferLoad.cpp"
  "Core/GameEngine/Source/Common/System/XferSave.cpp"
  "GeneralsMD/Code/GameEngine/Source/Common/System/SaveGame/GameState.cpp"
  "GeneralsMD/Code/GameEngine/Source/Common/System/SaveGame/GameStateMap.cpp"
  "android/app/src/main/java/com/generalsx/zerohour/ModManager.java"
)

if ! git cat-file -e "${BASELINE_COMMIT}^{commit}" 2>/dev/null; then
  echo "::error::Compatibility baseline commit ${BASELINE_COMMIT} is unavailable."
  exit 1
fi

if ! git merge-base --is-ancestor "${BASELINE_COMMIT}" HEAD; then
  echo "::error::HEAD no longer descends from the approved mobile baseline ${BASELINE_COMMIT}."
  echo "Do not move the compatibility baseline casually. Review the divergence first."
  exit 1
fi

failed=0

for path in "${PROTECTED_PATHS[@]}"; do
  if ! git cat-file -e "${BASELINE_COMMIT}:${path}" 2>/dev/null; then
    echo "::error file=${path}::Protected path does not exist in compatibility baseline."
    failed=1
    continue
  fi

  if [[ ! -f "${path}" ]]; then
    echo "::error file=${path}::Protected compatibility file was deleted or moved."
    failed=1
    continue
  fi

  expected="$(git rev-parse "${BASELINE_COMMIT}:${path}")"
  actual="$(git hash-object "${path}")"

  if [[ "${actual}" != "${expected}" ]]; then
    echo "::error file=${path}::Compatibility-critical file changed (baseline blob ${expected}, current ${actual})."
    failed=1
  else
    echo "OK  ${path}"
  fi
done

if [[ "${failed}" -ne 0 ]]; then
  cat <<'EOF'

Mobile engine compatibility gate FAILED.

The current optimization branch is intentionally forbidden from changing the
legacy file/mod/save loading surfaces while profiling and low-risk performance
work is being established.

If a future change truly requires one of these files:
  1. isolate it in its own change,
  2. run Vanilla + mod import/launch/switch + replay determinism tests,
  3. review file search/override semantics,
  4. only then deliberately advance the approved compatibility baseline.
EOF
  exit 1
fi

echo "Compatibility gate passed: protected legacy loading/serialization surfaces match ${BASELINE_COMMIT}."
