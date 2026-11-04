#!/usr/bin/env python3
"""Host microbenchmark of production snapshot/range selection, NOT a game/FPS benchmark.

Static: unchanged tiles. Moving: all vertex bytes change. Sparse: separated edits.
Same 132 x 128 KiB tile set for both paths, 120 frames, medians of 5 runs.
The baseline is the existing leading/trailing trim; candidate adds changedRanges.
"""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CODE = r'''
#include "gles_buffer_snapshot.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cassert>
#include <vector>
#include <array>
struct Tile {std::vector<unsigned char> cpu,gpu;GxBufferSnapshot submitted;
 Tile():cpu(131072,0),gpu(cpu){assert(submitted.rememberFull(cpu.data(),cpu.size(),cpu.size()));}};
int main(){
 for(int mode=0;mode<3;++mode)for(bool sparse:{false,true}){
  std::vector<double> samples;size_t lastBytes=0,lastCalls=0;
  for(int run=0;run<5;++run){
   std::array<Tile,132> tiles;size_t bytes=0,calls=0;
   auto start=std::chrono::steady_clock::now();
   for(unsigned frame=1;frame<=120;++frame)for(auto&t:tiles){
    if(mode==1)std::fill(t.cpu.begin(),t.cpu.end(),frame);
    if(mode==2){t.cpu[16]=frame;t.cpu[120000]=frame;}
    size_t begin=0,end=t.cpu.size();t.submitted.trim(t.cpu.data(),begin,end);
    GxBufferSnapshot::Range ranges[8]={{begin,end}};
    size_t n=begin<end?(sparse?t.submitted.changedRanges(t.cpu.data(),begin,end,ranges):1):0;
    for(size_t i=0;i<n;++i){auto r=ranges[i];memcpy(t.gpu.data()+r.begin,t.cpu.data()+r.begin,r.end-r.begin);bytes+=r.end-r.begin;++calls;}
    if(begin<end)t.submitted.rememberRange(t.cpu.data(),begin,end);
   }
   auto finish=std::chrono::steady_clock::now();
   for(auto&t:tiles)assert(t.gpu==t.cpu);
   samples.push_back(std::chrono::duration<double,std::milli>(finish-start).count()/120);
   lastBytes=bytes/120;lastCalls=calls/120;
  }
  std::sort(samples.begin(),samples.end());
  printf("%s,%s,%zu,%zu,%.6f\n",mode==0?"static":mode==1?"moving-all-bytes":"sparse-two-edits",sparse?"candidate":"baseline",lastBytes,lastCalls,samples[2]);
 }
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix='gx-sparse-bench-') as temp:
        cpp = Path(temp) / 'bench.cpp'
        exe = Path(temp) / 'bench'
        cpp.write_text(CODE)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O2', '-I',
                        str(ROOT / 'Core/Libraries/Source/d3d8gles/include'), str(cpp), '-o', str(exe)], check=True)
        print('host_fixture,path,bytes_per_iteration,uploads_per_iteration,cpu_ms_per_iteration', flush=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
