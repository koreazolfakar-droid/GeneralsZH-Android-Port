#!/usr/bin/env bash
# Resolve the existing updater's engine sequence from the complete source history.
# Usage: bash engine-build-number.sh <source-repository>
# No network, compilation, or cache changes. A shallow checkout is an error.
# GeneralsX @build Codex 05/10/2026 Do not publish a shallow-history commit count as Engine Build.
set -euo pipefail

if [[ "$#" != 1 ]]; then
    echo "Usage: $0 <source-repository>" >&2
    exit 1
fi
SOURCE_REPOSITORY="$1"
if [[ "$(git -C "${SOURCE_REPOSITORY}" rev-parse --is-shallow-repository)" != false ]]; then
    echo "ERROR: Engine Build requires complete source history; fetch commit history with --filter=blob:none before packaging." >&2
    exit 1
fi
ENGINE_SEQUENCE="$(git -C "${SOURCE_REPOSITORY}" rev-list --count HEAD)"
if [[ ! "${ENGINE_SEQUENCE}" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: could not resolve a positive engine sequence for the source HEAD." >&2
    exit 1
fi
printf '%s\n' "${ENGINE_SEQUENCE}"
