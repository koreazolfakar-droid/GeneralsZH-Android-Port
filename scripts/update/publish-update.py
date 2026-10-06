#!/usr/bin/env python3
# GeneralsX @feature Android port 27/09/2026 Build a signed update for the launcher's updater
# (android/.../UpdateManager.java). See docs/HOWTO/PUBLISH_UPDATE.md.
#
# Produces, in --out, exactly what the `updates` branch holds:
#   manifest.json        what the launcher reads (config, optional engine)
#   manifest.json.sig    added separately by sign-manifest.sh inside Actions
#   datapack-manifest.json  when config's datapack_manifest_url points at the updates branch: the
#                        GeneralsOnline CDN manifest with its fields trimmed, for launchers up to
#                        1.3.0 that fail on the CDN's " 0E45..." sha256 (newer ones read the CDN)
#   support/<sha>.json   the launcher's "Support the project" card (with --support; its SHA-256
#                        is in the manifest, so the manifest's signature covers it)
#   engine/<seq>/libmain.so.gz, libmain60.so.gz   (with --apk)
#
# The engine entry names the SHA-256 of every other native library in the APK
# (requires_libs): the launcher runs a downloaded engine only on an install whose libraries
# are exactly those, so an engine linked against a different SDL/OpenAL/DXVK never loads.
import importlib.util
from pathlib import Path
import datetime
import urllib.error
import argparse, base64, gzip, hashlib, json, os, subprocess, sys, tempfile, urllib.request, zipfile

spec = importlib.util.spec_from_file_location('update_artifacts', Path(__file__).with_name('update-artifacts.py'))
artifacts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(artifacts)
BASE_URL = artifacts.BASE_URL
ENGINE_LIBS = ("libmain.so", "libmain60.so")
DATAPACK_CDN_MANIFEST = "https://cdn.playgenerals.online/manifest.json"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def current_serial():
    try:
        with urllib.request.urlopen(BASE_URL + "manifest.json", timeout=20) as r:
            return int(json.load(r).get("serial", 0))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return 0
        raise


def fetch(url, timeout):
    # The CDN answers 403 to urllib's default User-Agent.
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "GeneralsX-publish/1"}),
                                  timeout=timeout)


def mirror_datapack_manifest(out_dir, name):
    """The CDN manifest with every string trimmed, after checking that the trimmed sha256 and the
    size really are those of the package it names -- a mirror must never be what breaks installs."""
    with fetch(DATAPACK_CDN_MANIFEST, 30) as r:
        cdn = json.load(r)
    fixed = {k: v.strip() if isinstance(v, str) else v for k, v in cdn.items()}
    h = hashlib.sha256()
    size = 0
    with fetch(fixed["download_url"], 120) as r:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
    if h.hexdigest().lower() != fixed["sha256"].lower() or size != fixed.get("size", size):
        sys.exit("data package %s does not match its own manifest (sha256 %s, size %d)"
                 % (fixed.get("version"), h.hexdigest(), size))
    with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
        json.dump(fixed, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("data package manifest mirrored: %s" % fixed.get("version"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "..", "update", "config.json"))
    ap.add_argument("--support", default=None,
                    help="explicit own support card; omit to withdraw it (never republish upstream donation identity)")
    ap.add_argument("--apk", help="APK whose engine to publish; omit for a settings-only update")
    ap.add_argument("--engine-dir", type=Path, help="verified incremental libmain.so and libmain60.so, no new APK required")
    ap.add_argument("--baseline-apk", type=Path, help="installed Bootstrap APK supplying the unchanged dependency identity")
    ap.add_argument("--source-commit", help="exact full-history source commit embedded in both incremental engines")
    ap.add_argument("--out", required=True)
    ap.add_argument("--serial", type=int, help="default: the published serial + 1")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    serial = a.serial if a.serial is not None else current_serial() + 1
    if serial <= 0:
        sys.exit("serial must be positive")
    manifest = {"schema": 1, "channel": artifacts.CHANNEL, "serial": serial}
    # What the launcher shows players ("Network settings: from 27.09.2026"); the serial is only
    # the anti-rollback counter.
    manifest["published"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if a.note:
        manifest["note"] = a.note
    with open(a.config, encoding="utf-8") as f:
        manifest["config"] = json.load(f)
    datapack_url = manifest["config"].get("datapack_manifest_url", "")
    if datapack_url.startswith(BASE_URL):
        mirror_datapack_manifest(a.out, datapack_url[len(BASE_URL):])

    if a.support and os.path.isfile(a.support):
        with open(a.support, "rb") as f:
            data = f.read()
        doc = json.loads(data.decode("utf-8"))
        if not doc.get("entries") or "en" not in doc.get("text", {}):
            sys.exit("support.json needs entries and an \"en\" text (the fallback language)")
        # Named by its digest, like the engine files by seq: raw.githubusercontent caches every
        # path for five minutes on its own, so a fixed name could pair a fresh manifest with the
        # previous file, which the launcher then (rightly) refuses -- and keeps the old card.
        rel = "support/%s.json" % sha256(data)[:16]
        os.makedirs(os.path.join(a.out, "support"), exist_ok=True)
        with open(os.path.join(a.out, rel), "wb") as f:
            f.write(data)
        manifest["support"] = {"url": BASE_URL + rel, "sha256": sha256(data), "size": len(data)}

    if a.apk and a.engine_dir:
        sys.exit("Select --apk OR --engine-dir, not both")
    if (a.baseline_apk or a.source_commit) and not a.engine_dir:
        sys.exit("--baseline-apk/--source-commit require --engine-dir")
    if a.engine_dir and (not a.baseline_apk or not a.source_commit):
        sys.exit("--engine-dir requires --baseline-apk and --source-commit")
    if a.apk or a.engine_dir:
        baseline_seq, source, libraries = artifacts.apk_payload(a.apk or a.baseline_apk)
        seq = baseline_seq
        if a.engine_dir:
            with zipfile.ZipFile(a.baseline_apk) as z:
                baseline_public = z.read('assets/update-public.pem')
            pinned_public = (artifacts.ROOT / 'android/app/src/main/assets/update-public.pem').read_bytes()
            if baseline_public != pinned_public:
                sys.exit('Baseline APK does not pin our current update identity')
            source = a.source_commit
            seq = int(subprocess.check_output(['git', '-C', str(artifacts.ROOT), 'rev-list', '--count', source], text=True))
            artifacts.validate_source(source, seq)
            if seq <= baseline_seq:
                sys.exit("engine-only build must be newer than the Bootstrap APK engine")
            for name in ENGINE_LIBS:
                libraries[name] = (a.engine_dir / name).read_bytes()
                artifacts.native_stamp(libraries[name], source, seq)
        if sha256(libraries[ENGINE_LIBS[0]]) == sha256(libraries[ENGINE_LIBS[1]]):
            sys.exit("Both rate slots cannot contain the same engine")
        engine = {"seq": seq, "source_commit": source, "files": {}, "requires_libs": {}}
        for name, data in sorted(libraries.items()):
            if name in ENGINE_LIBS:
                rel = "engine/%d/%s.gz" % (seq, name)
                dest = os.path.join(a.out, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(gzip.compress(data, 9, mtime=0))
                engine["files"][name] = {"url": BASE_URL + rel, "sha256": sha256(data), "size": len(data)}
            else:
                engine["requires_libs"][name] = sha256(data)
        manifest["engine"] = engine

    if not a.apk and not a.engine_dir:
        try:
            with urllib.request.urlopen(BASE_URL + 'manifest.json', timeout=20) as response:
                previous = response.read(256 * 1024 + 1)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        else:
            with urllib.request.urlopen(BASE_URL + 'manifest.json.sig', timeout=20) as response:
                sig = response.read(16 * 1024 + 1)
            with tempfile.TemporaryDirectory(prefix='gx-current-update-') as temporary:
                old_dir = Path(temporary)
                (old_dir / 'manifest.json').write_bytes(previous)
                (old_dir / 'manifest.json.sig').write_bytes(sig)
                old = artifacts.verify_manifest(old_dir, artifacts.ROOT / 'android/app/src/main/assets/update-public.pem')
                if old.get('engine'):
                    for name in ENGINE_LIBS:
                        entry = old['engine']['files'][name]
                        rel = f"engine/{old['engine']['seq']}/{name}.gz"
                        if entry['url'] != BASE_URL + rel or not 0 < entry['size'] <= 256 * 1024 * 1024:
                            sys.exit('Invalid retained engine identity')
                        target = old_dir / rel
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with urllib.request.urlopen(entry['url'], timeout=60) as response:
                            data = response.read(256 * 1024 * 1024 + 1)
                            if len(data) > 256 * 1024 * 1024:
                                sys.exit('Retained engine exceeds transfer limit')
                            target.write_bytes(data)
                artifacts.verify_directory(old_dir, artifacts.ROOT / 'android/app/src/main/assets/update-public.pem')
                if manifest['serial'] <= old['serial']:
                    sys.exit('Serial must strictly increase')
                if old.get('engine'):
                    import shutil
                    shutil.copytree(old_dir / 'engine', Path(a.out) / 'engine')
                    manifest['engine'] = old['engine']

    body = (json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    mpath = os.path.join(a.out, "manifest.json")
    with open(mpath, "wb") as f:
        f.write(body)
    print("Prepared only: sign and verify with our Actions secret before publishing")
    print("serial %d%s -> %s" % (manifest["serial"],
          ", engine %d" % manifest["engine"]["seq"] if "engine" in manifest else "", a.out))


if __name__ == "__main__":
    main()
