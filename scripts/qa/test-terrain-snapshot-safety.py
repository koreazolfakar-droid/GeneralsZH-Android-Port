#!/usr/bin/env python3
"""Production snapshot version/prefix/budget and IEEE diagnostic tests; no GPU/FPS claim."""
import os
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]


def main():
    with tempfile.TemporaryDirectory(prefix='gx-snapshot-') as temp:
        work=Path(temp);path=work/'test.cpp';exe=work/'test'
        path.write_text(r'''
#include "gles_buffer_snapshot.h"
#include "GXFiniteBits.h"
#include <cassert>
#include <array>
#include <cfenv>
#include <cstdio>
#include <cstdint>
#include <cstring>
int main(){
 std::array<unsigned char,4096> b{};
 {
  GxBufferSnapshot s;assert(s.rememberFull(b.data(),b.size(),64));
  size_t begin=0,end=128;s.trim(b.data(),begin,end);assert(begin==64&&end==128);
  s.rememberRange(b.data(),64,128);begin=0;end=128;s.trim(b.data(),begin,end);assert(begin==end);
  b[16]=1;begin=0;end=128;s.trim(b.data(),begin,end);assert(begin==16&&end==17);
  s.rememberRange(b.data(),begin,end);begin=0;end=128;s.trim(b.data(),begin,end);assert(begin==end);
  b[16]=0;begin=0;end=128;s.trim(b.data(),begin,end);assert(begin==16&&end==17); // restoration is a new version too
  s.rememberRange(b.data(),begin,end);
  s.rememberRange(b.data(),256,257);begin=128;end=257;s.trim(b.data(),begin,end);assert(begin==128&&end==257); // undefined gap is not cached
  assert(s.rememberFull(b.data(),b.size(),b.size()));
  b[10]=1;b[4090]=2;begin=0;end=b.size();s.trim(b.data(),begin,end);assert(begin==10&&end==4091);
  assert(s.rememberFull(b.data(),b.size(),32));begin=0;end=b.size();s.trim(b.data(),begin,end);assert(begin==32&&end==b.size()); // storage renamed; old tail invalid
 }
 assert(GxBufferSnapshot::memoryBytes()==0);
 {
  std::array<GxBufferSnapshot,257> buffers;
  std::array<unsigned char,131072> data{};
  for(int i=0;i<256;++i)assert(buffers[i].rememberFull(data.data(),data.size(),data.size()));
  assert(GxBufferSnapshot::memoryBytes()==GxBufferSnapshot::budgetBytes);
  assert(!buffers[256].rememberFull(data.data(),data.size(),data.size()));
 }
 assert(GxBufferSnapshot::memoryBytes()==0);
 for(uint32_t word:{0u,0x80000000u,0x3f800000u,0x7f7fffffu,0x7f800000u,0xff800000u,0x7fc00001u,0x7f800001u}){
  float value;memcpy(&value,&word,4);feclearexcept(FE_ALL_EXCEPT);
  bool finite=GXFloatFiniteBits(GXFloatBits(value));assert(finite==((word&0x7f800000u)!=0x7f800000u));
  assert(!fetestexcept(FE_INVALID));assert(GXFloatBits(value)==word);
 }
 puts("PASS: initialized-prefix safety, changed/restored/renamed versions, bounded memory/release and NaN/Inf bit diagnostics without FP flag changes");
}
''')
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O1','-g','-fsanitize=address,undefined',
                        '-I',str(ROOT/'Core/Libraries/Source/d3d8gles/include'),'-I',str(ROOT/'Core/Libraries/Include'),
                        str(path),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)


if __name__=='__main__':main()
