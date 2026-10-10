#!/usr/bin/env python3
"""Metadata-only NDK cache normalization for the retained incremental PCH state.

Never copies/removes/recompiles an SDK asset. The compiler wrapper will restore
individual verified headers to their exact PCH-recorded second timestamps.
"""
import hashlib
import json
import os
from pathlib import Path

NDK_REVISION = "27.2.12479018"
FEATURES_SHA256 = "0252083e08cd283be6173b62bafb5fa1c5e29991654aae057d4fa613f8236a6b"
MAX_HEADERS = 15000


def prepare(ndk: Path, epoch_seconds: int, verified: dict, report_dir: Path) -> dict:
    ndk = ndk.resolve()
    assert ndk.name == NDK_REVISION, "Wrong NDK root"
    properties = (ndk / "source.properties").read_text()
    assert "Pkg.Revision = " + NDK_REVISION in properties, "NDK revision mismatch"
    base = ndk / "toolchains/llvm/prebuilt/linux-x86_64"
    roots = (
        base / "sysroot/usr/include",  # Includes libc++/v1 headers (often extensionless).
        base / "lib/clang/18/include",
    )
    assert all(root.is_dir() and not root.is_symlink() for root in roots)
    features = roots[0] / "features.h"
    assert features.is_file() and not features.is_symlink()
    def digest(path: Path) -> str:
        with path.open("rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest()
    assert digest(features) == FEATURES_SHA256, "Pinned NDK header contents mismatch"
    epoch_ns = epoch_seconds * 1_000_000_000
    assert 0 < epoch_seconds <= 1791292742, "Unrecognized retained engine epoch"
    paths = []
    for root in roots:
        for path in root.rglob("*"):
            if path.is_symlink() or not path.is_file():
                continue
            resolved = path.resolve()
            assert resolved.is_relative_to(root), "Header escapes verified NDK include root"
            paths.append(path)
            assert len(paths) <= MAX_HEADERS, "Unexpected NDK file count"
    assert len(paths) >= 2000, "Incomplete NDK include tree"

    # Snapshot all contents before any change, including non-.h libc++ files.
    # These hashes authorize compiler.py to apply only Clang-reported PCH mtimes.
    for path in paths:
        resolved = str(path.resolve())
        assert resolved not in verified, "Duplicate protected header"
        verified[resolved] = digest(path)
    count = 0
    for path in paths:
        stat = path.stat()
        if stat.st_mtime_ns > epoch_ns:
            os.utime(path, ns=(stat.st_atime_ns, epoch_ns))
            count += 1
    assert digest(features) == FEATURES_SHA256, "NDK bytes unexpectedly changed"
    result = dict(ndk_revision=NDK_REVISION, features_sha256=FEATURES_SHA256,
                  verified_header_files=len(paths), metadata_only_adjustments=count,
                  normalized_to_epoch_seconds=epoch_seconds, contents_modified=False)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "ndk-cache-normalization.json").write_text(json.dumps(result, indent=2) + "\n")
    print("[GX-NDK-PCH] verified %d pinned SDK headers; normalized %d newer mtimes; bytes unchanged" %
          (len(paths), count), flush=True)
    return result


def restore_recorded_pch_mtimes(ndk: Path, verified: dict, manifest_path=None) -> dict:
    """Seed exact Clang-observed PCH timestamps before any translation unit compiles.

    The existing compiler wrapper remains responsible for all headers not in
    this pinned list. A two-phase all-or-nothing check prevents changing any
    metadata if the NDK revision, source paths, or verified contents differ.
    """
    ndk = ndk.resolve()
    if manifest_path is None:
        manifest_path = Path(__file__).with_name("pch-verified-mtime-seed.json")
    manifest = json.loads(Path(manifest_path).read_text())
    assert manifest.get("schema") == 1
    assert manifest.get("ndk_revision") == NDK_REVISION == ndk.name
    items = manifest.get("expected_unix_seconds")
    assert isinstance(items, dict) and 0 < len(items) <= MAX_HEADERS
    base = ndk / "toolchains/llvm/prebuilt/linux-x86_64"
    roots = (base / "sysroot/usr/include", base / "lib/clang/18/include")
    changes = []
    for relative, timestamp in items.items():
        assert isinstance(relative, str) and not relative.startswith("/")
        assert isinstance(timestamp, int) and 1791131945 <= timestamp <= 1791131947
        path = ndk / relative
        assert path.is_file() and not path.is_symlink(), "Missing or linked verified PCH header: " + relative
        resolved = path.resolve()
        assert resolved.is_relative_to(ndk)
        assert any(resolved.is_relative_to(root) for root in roots)
        assert str(resolved) in verified, "Header not in checked NDK cache inventory: " + relative
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        assert verified[str(resolved)] == digest, "NDK header changed: " + relative
        stat = path.stat()
        if stat.st_mtime_ns != timestamp * 1000000000:
            changes.append((path, stat.st_atime_ns, timestamp))
    for path, atime_ns, timestamp in changes:
        os.utime(path, ns=(atime_ns, timestamp * 1000000000))
    return dict(source="Clang PCH timestamps from prior successful Actions build",
                validated_headers=len(items), metadata_only_adjustments=len(changes),
                contents_modified=False)
