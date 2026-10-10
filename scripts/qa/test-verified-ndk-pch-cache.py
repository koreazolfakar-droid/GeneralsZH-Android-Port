#!/usr/bin/env python3
"""Host-only, isolated checks for authenticated NDK cache and Clang PCH repairs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / ".github/engine-baseline"


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class NdkCacheTests(unittest.TestCase):
    def test_verified_metadata_only_and_reject_changed_file(self):
        cache = module(TOOLS / "ndk_cache.py", "gx_ndk_cache_test")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ndk = root / cache.NDK_REVISION
            base = ndk / "toolchains/llvm/prebuilt/linux-x86_64"
            sysroot = base / "sysroot/usr/include"
            clang = base / "lib/clang/18/include"
            cpp = sysroot / "c++/v1"
            cpp.mkdir(parents=True)
            clang.mkdir(parents=True)
            (ndk / "source.properties").write_text("Pkg.Revision = " + cache.NDK_REVISION + "\n")
            contents = b"verified features header bytes\n"
            (sysroot / "features.h").write_bytes(contents)
            extensionless = cpp / "utility"
            extensionless.write_bytes(b"utility header bytes")
            resource = clang / "stddef.h"
            resource.write_bytes(b"clang resource header bytes")
            # Include count guard, with tiny files; no external SDK accessed.
            for i in range(2000):
                (sysroot / ("fixture-%04d.h" % i)).write_bytes(b"header")
            external = root / "outside.txt"
            external.write_bytes(b"never touch")
            (sysroot / "outside-link.h").symlink_to(external)
            cache.FEATURES_SHA256 = hashlib.sha256(contents).hexdigest()
            for path in (sysroot / "features.h", extensionless, resource):
                os.utime(path, (1791429919, 1791429919))
            before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (sysroot / "features.h", extensionless, resource)}
            verified = {}
            report = cache.prepare(ndk, 1791292742, verified, root / "report")
            self.assertGreaterEqual(report["verified_header_files"], 2003)
            self.assertEqual(report["metadata_only_adjustments"], 3)
            self.assertEqual(extensionless.stat().st_mtime_ns, 1791292742 * 1000000000)
            self.assertEqual(resource.stat().st_mtime_ns, 1791292742 * 1000000000)
            self.assertNotIn(str(external), verified)
            for path, digest in before.items():
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                self.assertEqual(verified[str(path.resolve())], digest)
            # Modified SDK content must fail without further timestamp writes.
            (sysroot / "features.h").write_bytes(b"tampered")
            original_time = resource.stat().st_mtime_ns
            with self.assertRaises(AssertionError):
                cache.prepare(ndk, 1791292742, {}, root / "report2")
            self.assertEqual(resource.stat().st_mtime_ns, original_time)

    def test_wrapper_restores_only_hash_verified_clang_pch_mtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / "utility"
            target.write_bytes(b"verified unchanged header")
            os.utime(target, (1791292742, 1791292742))
            verified = root / "verified.json"
            verified.write_text(json.dumps({
                str(target): hashlib.sha256(target.read_bytes()).hexdigest()}))
            fakebin = root / "bin"
            fakebin.mkdir()
            ccache = fakebin / "ccache"
            ccache.write_text(
                "#!/usr/bin/env python3\n"
                "import os,sys,pathlib\n"
                "p=pathlib.Path(os.environ['PCH_FIXTURE_HEADER'])\n"
                "if int(p.stat().st_mtime)!=1791131946:\n"
                " print(\"fatal error: file '%s' has been modified since the precompiled header '/fixture/pch.hxx.pch' was built: mtime changed (was 1791131946, now %d)\"%(p,int(p.stat().st_mtime)),file=sys.stderr)\n"
                " sys.exit(1)\n"
                "pathlib.Path(sys.argv[sys.argv.index('-o')+1]).write_bytes(b'compiled')\n"
            )
            ccache.chmod(0o755)
            output = root / "object.o"
            env = dict(os.environ,
                       GX_COMPILE_RECORDS=str(root / "records"),
                       GX_VERIFIED_HEADERS=str(verified),
                       GX_BUILD_PHASE="engine-30",
                       PCH_FIXTURE_HEADER=str(target),
                       PATH=str(fakebin) + os.pathsep + os.environ["PATH"])
            run = subprocess.run([sys.executable, str(TOOLS / "compiler.py"),
                                  "clang++", "-o", str(output), "source.cpp"],
                                 env=env, capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(target.stat().st_mtime_ns, 1791131946 * 1000000000)
            self.assertEqual(output.read_bytes(), b"compiled")
            records = list((root / "records/engine-30").glob("*.json"))
            self.assertEqual(len(records), 1)
            record = json.loads(records[0].read_text())
            self.assertEqual(record["attempts"], 2)
            self.assertEqual(len(record["pch_mtime_repairs"]), 1)
            # A different checksum is never trusted.
            target.write_bytes(b"altered")
            os.utime(target, (1791292742, 1791292742))
            second = subprocess.run([sys.executable, str(TOOLS / "compiler.py"),
                                     "clang++", "-o", str(output), "source.cpp"],
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(int(target.stat().st_mtime), 1791292742)


if __name__ == "__main__":
    unittest.main()
