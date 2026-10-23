#!/usr/bin/env python3
"""Production shader cache async writer: atomic format, bounded queue, shutdown flush.

This compiles the actual header in Core/Libraries/Include and verifies the
original GXPB magic/format/payload for all jobs without invoking GL on worker.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

root=Path(__file__).resolve().parents[2]
header=root/"Core/Libraries/Include/GXProgramCacheWriter.h"
gles=(root/"Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp").read_text()
assert header.exists()
assert 'gxProgramCacheWriter().enqueue(path, (uint32_t)format, std::move(data))' in gles
assert "gxProgramCacheWriter().takeCompleted()" in gles
assert 'written <= 0 || written > length' in gles
assert "void WebGLPipeline::loadCachedProgram" not in gles or 'GLuint WebGLPipeline::loadCachedProgram' in gles
assert "glGetProgramBinary" not in header.read_text().split("class GXProgramCacheWriter",1)[-1]
assert "24u << 20" in header.read_text()
cpp=r'''
#include "GXProgramCacheWriter.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <string>
#include <vector>
int main(int argc, char** argv) {
  if (argc!=2) return 2;
  std::string dir=argv[1];
  {
    GXProgramCacheWriter writer;
    std::vector<uint8_t> oversized((24u << 20)+1u, 0x42);
    if(writer.enqueue(dir+"/oversized.bin",5,std::move(oversized))) return 3;
    if(oversized.size()!=(24u<<20)+1u) return 4; // don't consume fallback
    for(int i=0;i<256;i++){
      std::vector<uint8_t> data(101+(i%97),(uint8_t)(i%253));
      std::string path=dir+"/"+std::to_string(i)+".bin";
      if(!writer.enqueue(path,(uint32_t)(i+40),std::move(data))) return 5;
    }
  } // drains pending jobs, joins worker before file verification
  for(int i=0;i<256;i++){
    std::string path=dir+"/"+std::to_string(i)+".bin";
    std::ifstream f(path,std::ios::binary);
    if(!f.good()) return 6;
    uint32_t header[3]{};
    f.read(reinterpret_cast<char*>(header),sizeof(header));
    if(!f.good()||header[0]!=0x42505847u||header[1]!=(uint32_t)(i+40)
        ||header[2]!=(uint32_t)(101+i%97)) return 7;
    std::vector<uint8_t> data(header[2]);
    f.read(reinterpret_cast<char*>(data.data()),data.size());
    if(!f||data.front()!=i%253||data.back()!=i%253) return 8;
    if(f.peek()!=EOF) return 9;
  }
  std::puts("PASS: async producer/worker, atomic 256 binary files and shutdown drain");
}
'''
compiler=shutil.which("g++") or shutil.which("clang++")
assert compiler,"C++ compiler required"
with tempfile.TemporaryDirectory(prefix="gx-program-cache-") as td:
    src=Path(td)/"cache_test.cpp"
    exe=Path(td)/"cache_test"
    data_dir=Path(td)/"cache"
    data_dir.mkdir()
    src.write_text(cpp)
    subprocess.run([compiler,"-std=c++17","-O1","-pthread","-Wall","-Wextra",
                    "-Werror","-fsanitize=undefined","-fno-sanitize-recover=undefined",
                    "-I",str(header.parent),str(src),"-o",str(exe)],check=True)
    subprocess.run([str(exe),str(data_dir)],check=True,timeout=15)
print("PASS: first-use shader writes are queued without GPU worker access")
