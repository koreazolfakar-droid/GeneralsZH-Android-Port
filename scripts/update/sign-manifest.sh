#!/usr/bin/env bash
# GeneralsX @feature Codex 06/10/2026 Sign prepared bytes before publication; prove the secret matches our pinned public key.
set -euo pipefail
set +x
UPDATE_DIRECTORY="${1:?usage: sign-manifest.sh <prepared directory>}"
SOURCE_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PUBLIC_KEY="${SOURCE_ROOT}/android/app/src/main/assets/update-public.pem"
test -n "${UPDATE_SIGNING_KEY:-}" || { echo 'UPDATE_SIGNING_KEY is not configured' >&2; exit 1; }
test -f "${PUBLIC_KEY}" || { echo 'Our public key has not been provisioned; refusing to sign' >&2; exit 1; }
python3 - "${SOURCE_ROOT}" "${PUBLIC_KEY}" <<'PY'
import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('artifacts',Path(sys.argv[1])/'scripts/update/update-artifacts.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
a.public_der(sys.argv[2])
PY
umask 077
KEY_DIRECTORY="$(mktemp -d "${RUNNER_TEMP:-${TMPDIR:-/tmp}}/gx-sign.XXXXXXXX")"
trap 'rm -rf "${KEY_DIRECTORY}"' EXIT
printf '%s\n' "${UPDATE_SIGNING_KEY}" > "${KEY_DIRECTORY}/private.pem"
unset UPDATE_SIGNING_KEY
openssl pkey -in "${KEY_DIRECTORY}/private.pem" -pubout -outform DER > "${KEY_DIRECTORY}/derived.der"
openssl pkey -pubin -in "${PUBLIC_KEY}" -outform DER > "${KEY_DIRECTORY}/pinned.der"
cmp -s "${KEY_DIRECTORY}/derived.der" "${KEY_DIRECTORY}/pinned.der" || {
    echo 'Actions secret and pinned public identity do not match; refusing publication' >&2; exit 1;
}
openssl dgst -sha256 -sign "${KEY_DIRECTORY}/private.pem" "${UPDATE_DIRECTORY}/manifest.json" | base64 -w0 > "${UPDATE_DIRECTORY}/manifest.json.sig"
echo >> "${UPDATE_DIRECTORY}/manifest.json.sig"
# Exact signed manifest bytes and all engine payloads must verify before the branch is touched.
python3 - "${SOURCE_ROOT}" "${UPDATE_DIRECTORY}" "${PUBLIC_KEY}" <<'PY'
import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('artifacts',Path(sys.argv[1])/'scripts/update/update-artifacts.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
m=a.verify_directory(sys.argv[2],sys.argv[3])
print('Verified own signed manifest serial',m['serial'])
PY
