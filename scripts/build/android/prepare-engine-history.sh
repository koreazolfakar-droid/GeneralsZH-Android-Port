#!/usr/bin/env bash
# Recover Git history before native version generation or APK staging in older CI.
# GeneralsX @build Codex 05/10/2026 Native GitRevision and APK Engine Build must use the same full graph.
set -euo pipefail
if [[ "$#" != 1 ]]; then
    echo "Usage: $0 <source-repository>" >&2
    exit 1
fi
SOURCE_REPOSITORY="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${GITHUB_ACTIONS:-false}" == "true" ]] && \
   [[ "$(git -C "${SOURCE_REPOSITORY}" rev-parse --is-shallow-repository)" == "true" ]]; then
    SOURCE_HEAD="$(git -C "${SOURCE_REPOSITORY}" rev-parse HEAD)"
    # Fetch graph objects only; never check out another tree or touch build caches.
    git -C "${SOURCE_REPOSITORY}" fetch --unshallow --filter=blob:none --no-tags origin
    if [[ "$(git -C "${SOURCE_REPOSITORY}" rev-parse HEAD)" != "${SOURCE_HEAD}" ]]; then
        echo "ERROR: source HEAD changed while recovering engine history." >&2
        exit 1
    fi
fi
bash "${SCRIPT_DIR}/engine-build-number.sh" "${SOURCE_REPOSITORY}"
