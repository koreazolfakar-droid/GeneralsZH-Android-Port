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
