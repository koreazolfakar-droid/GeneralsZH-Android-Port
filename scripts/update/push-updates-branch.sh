#!/usr/bin/env bash
# GeneralsX @feature Codex 06/10/2026 Publish only verified signed content; never force-replace branch history or user data.
set -euo pipefail
SRC="$(cd "${1:?usage: push-updates-branch.sh <signed verified directory>}" && pwd)"
REPO="$(git rev-parse --show-toplevel)"
REMOTE="$(git -C "${REPO}" remote get-url origin)"
case "${REMOTE}" in
    https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port|https://github.com/koreazolfakar-droid/GeneralsZH-Android-Port.git) ;;
    *) echo 'Refusing publication outside our exact repository' >&2; exit 1 ;;
esac
PUBLIC_KEY="${REPO}/android/app/src/main/assets/update-public.pem"
# Validate before creating or mutating the publication worktree.
python3 - "${REPO}" "${SRC}" "${PUBLIC_KEY}" <<'PY'
import importlib.util,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('artifacts',Path(sys.argv[1])/'scripts/update/update-artifacts.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
a.verify_directory(sys.argv[2],sys.argv[3])
# Prevent accidental private-key or arbitrary file publication, including hidden entries.
for f in Path(sys.argv[2]).rglob('*'):
    if f.is_symlink():raise ValueError('Publication symlinks are forbidden')
    if f.is_file() and f.name not in ('manifest.json','manifest.json.sig','libmain.so.gz','libmain60.so.gz','datapack-manifest.json') and not (f.parent.name=='support' and f.suffix=='.json'):
        raise ValueError('Unexpected publication file: '+f.name)
PY
WORK="$(mktemp -d)"
trap 'rm -rf "${WORK}"' EXIT
git -C "${WORK}" init -q
git -C "${WORK}" remote add origin "${REMOTE}"
EXISTS="$(git -C "${WORK}" ls-remote --heads origin refs/heads/updates)"
if [[ -n "${EXISTS}" ]]; then
    git -C "${WORK}" fetch -q --depth=1 origin refs/heads/updates
    git -C "${WORK}" checkout -q -b updates FETCH_HEAD
else
    git -C "${WORK}" checkout -q --orphan updates
fi
python3 - "${SRC}" "${WORK}" <<'PY'
import json,sys,shutil,hashlib
from pathlib import Path
src,dst=map(Path,sys.argv[1:])
new=json.loads((src/'manifest.json').read_bytes())
old=json.loads((dst/'manifest.json').read_bytes()) if (dst/'manifest.json').is_file() else None
if old:
    if new['serial']<=old['serial']:raise ValueError('Serial must strictly increase')
    if old.get('engine') and new.get('engine'):
        if new['engine']['seq']<old['engine']['seq']:raise ValueError('Engine downgrade refused')
        if new['engine']['seq']==old['engine']['seq'] and new['engine']!=old['engine']:raise ValueError('Published engine sequence is immutable')
    elif old.get('engine') and not new.get('engine'):
        raise ValueError('Settings-only publication must explicitly retain the current engine')
for path in src.rglob('*'):
    if not path.is_file():continue
    target=dst/path.relative_to(src)
    if path.relative_to(src).parts[0]=='engine' and target.exists() and target.read_bytes()!=path.read_bytes():
        raise ValueError('Existing engine payload is immutable')
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,target)
PY
git -C "${WORK}" add -A
git -C "${WORK}" -c user.name='github-actions[bot]' -c user.email='41898282+github-actions[bot]@users.noreply.github.com' commit -q -m 'update: publish verified signed manifest'
# A concurrent publish is rejected as non-fast-forward. Rerun preparation with the new serial.
git -C "${WORK}" push -q origin HEAD:refs/heads/updates
echo 'Own signed update published without force-push'
