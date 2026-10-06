#!/usr/bin/env bash
# GeneralsX @feature Codex 06/10/2026 Operator-only provisioning; the private PEM never leaves a secure temporary file except into the Actions secret.
set -euo pipefail
set +x
REPOSITORY='koreazolfakar-droid/GeneralsZH-Android-Port'
SOURCE_ROOT="$(git rev-parse --show-toplevel)"
PUBLIC_KEY="${SOURCE_ROOT}/android/app/src/main/assets/update-public.pem"
# Check authorization and existing identity before generating anything. Never overwrite a key.
SECRETS="$(gh secret list --repo "${REPOSITORY}" --json name)"
if python3 -c 'import json,sys;sys.exit(0 if any(x["name"]=="UPDATE_SIGNING_KEY" for x in json.load(sys.stdin)) else 1)' <<< "${SECRETS}"; then
    echo 'UPDATE_SIGNING_KEY already exists. Derive its PUBLIC key in Actions; do not replace it.' >&2
    exit 1
fi
if [[ -e "${PUBLIC_KEY}" ]]; then
    echo 'A public identity already exists; investigate before generating a replacement.' >&2
    exit 1
fi
umask 077
KEY_DIRECTORY="$(mktemp -d)"
trap 'rm -rf "${KEY_DIRECTORY}"' EXIT
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "${KEY_DIRECTORY}/private.pem"
openssl pkey -in "${KEY_DIRECTORY}/private.pem" -pubout -out "${KEY_DIRECTORY}/public.pem"
# gh encrypts the body with the repository Actions public key before submission.
gh secret set UPDATE_SIGNING_KEY --repo "${REPOSITORY}" < "${KEY_DIRECTORY}/private.pem"
# Only after GitHub accepts the secret is the public-only identity staged for source review.
mkdir -p "$(dirname "${PUBLIC_KEY}")"
cp "${KEY_DIRECTORY}/public.pem" "${PUBLIC_KEY}"
echo 'UPDATE_SIGNING_KEY configured. Public PEM only: android/app/src/main/assets/update-public.pem'
