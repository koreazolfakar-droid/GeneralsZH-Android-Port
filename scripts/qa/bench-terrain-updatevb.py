#!/usr/bin/env python3
"""CPU-only benchmark for the production HeightMapRenderObjClass::updateVB workload.

This intentionally mirrors the hot arithmetic and circular-origin indexing in
HeightMap.cpp without linking the Android renderer. It is a host benchmark, not
a device FPS/GPU benchmark. The checksum makes baseline/optimized output
comparisons fail loudly if the generated terrain samples differ.
"""
from __future__ import annotations
import argparse
import statistics
import subprocess
import tempfile
from pathlib import Path

CPP = r'''
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>
struct V { float x,y,z,nx,ny,nz; uint32_t c; };
struct P { float x,y,z; };
static inline int wrap(int v, int origin, int extent) {
  const int m=extent-1; v-=origin; if(v<0)v+=m; if(v>=m)v-=m; return v;
}
static inline float h(int x,int y) {
  return std::sin(x*0.071f)*3.0f + std::cos(y*0.053f)*2.0f + std::sin((x+y)*0.017f);
}
static inline void normal(float ax,float ay,float bx,float by,float &nx,float &ny,float &nz) {
  float cx=ay*by, cy=bx*ax, cz=ax*by-ay*bx;
  float l=std::sqrt(cx*cx+cy*cy+cz*cz); float q=l>1e-7f?1.0f/l:0.0f;
  nx=cx*q; ny=cy*q; nz=cz*q;
}
static uint64_t run(bool optimized, int frames, int extent, int region) {
  constexpr float S=0.03125f; const int lights=4;
  P lp[lights]={{-.2f,.7f,.6f},{.3f,-.2f,.8f},{-.5f,-.1f,.4f},{.1f,.4f,.9f}};
  std::vector<V> out((size_t)region*region*4); uint64_t checksum=0;
  int ox=0,oy=0;
  for(int f=0; f<frames; ++f) {
    ox=(ox+1)%(extent-1); oy=(oy+(f&1))%(extent-1);
    auto begin=std::chrono::steady_clock::now();
    float ray[lights][3];
    if(optimized) for(int k=0;k<lights;++k){ray[k][0]=-lp[k].x;ray[k][1]=-lp[k].y;ray[k][2]=-lp[k].z;}
    std::vector<int> xs(region+1), ys(region+1);
    if(optimized) { for(int i=0;i<=region;++i) xs[i]=wrap(i,ox,extent); for(int j=0;j<=region;++j) ys[j]=wrap(j,oy,extent); }
    size_t n=0;
    for(int j=0;j<region;++j){
      int my=optimized?ys[j]:wrap(j,oy,extent), yn=my-1, yp=optimized?ys[j+1]:wrap(j+1,oy,extent);
      for(int i=0;i<region;++i){
        int mx=optimized?xs[i]:wrap(i,ox,extent), xn=mx-1, xp=optimized?xs[i+1]:wrap(i+1,ox,extent);
        for(int q=0;q<4;++q){
          if(!optimized) for(int k=0;k<lights;++k){ray[k][0]=-lp[k].x;ray[k][1]=-lp[k].y;ray[k][2]=-lp[k].z;}
          int sx=(q&1)?xp:mx, sy=(q&2)?yp:my;
          float ax=0.0625f, ay=S*(h(sx,sy)-h((q&1)?mx:xn,sy));
          float bx=0.0625f, by=S*(h(sx,(q&2)?my:yn)-h(sx,my));
          float nx,ny,nz; normal(ax,ay,bx,by,nx,ny,nz);
          float shade=0.18f;
          for(int k=0;k<lights;++k) shade += std::max(0.0f,nx*ray[k][0]+ny*ray[k][1]+nz*ray[k][2])*0.08f;
          V &v=out[n++]; v.x=float(i+q%2); v.y=float(j+(q/2)); v.z=h(sx,sy); v.nx=nx;v.ny=ny;v.nz=nz;
          v.c=(uint32_t(std::clamp(int(shade*255.0f),0,255))<<16) ^ uint32_t(std::abs(int(v.z*1000)));
          checksum = checksum*1315423911u + v.c + uint32_t(sx*17+sy*31);
        }
      }
    }
    auto end=std::chrono::steady_clock::now();
    double us=std::chrono::duration<double,std::micro>(end-begin).count();
    std::printf("%.3f\n",us/1000.0);
  }
  std::fprintf(stderr,"checksum=%llu\n",(unsigned long long)checksum);
  return checksum;
}
int main(int argc,char **argv){
  bool opt=std::atoi(argv[1])!=0; int frames=std::atoi(argv[2]); int extent=std::atoi(argv[3]); int region=std::atoi(argv[4]);
  run(opt,frames,extent,region); return 0;
}
'''

def run(root: Path, optimized: bool, frames: int, extent: int, region: int):
    with tempfile.TemporaryDirectory(prefix="terrain-bench-") as td:
        src = Path(td) / "bench.cpp"
        exe = Path(td) / "bench"
        src.write_text(CPP)
        subprocess.run(["g++", "-O2", "-std=c++17", str(src), "-o", str(exe)], check=True)
        p = subprocess.run([str(exe), "1" if optimized else "0", str(frames), str(extent), str(region)], text=True, capture_output=True, check=True)
    vals = [float(x) for x in p.stdout.splitlines() if x.strip()]
    vals.sort()
    trim = vals[2:-2] if len(vals) > 10 else vals
    def pct(q): return trim[min(len(trim)-1, int((len(trim)-1)*q))]
    return {"mode": "optimized" if optimized else "baseline", "frames": frames,
            "extent": extent, "region": region, "p50_ms": pct(.50),
            "p95_ms": pct(.95), "mean_ms": statistics.mean(trim),
            "checksum": p.stderr.strip().split("=", 1)[-1]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["baseline", "optimized", "both"], default="both")
    ap.add_argument("--frames", type=int, default=180)
    ap.add_argument("--extent", type=int, default=768)
    ap.add_argument("--region", type=int, default=96)
    args = ap.parse_args()
    modes = [False, True] if args.mode == "both" else [args.mode == "optimized"]
    results = []
    for opt in modes:
        r = run(Path.cwd(), opt, args.frames, args.extent, args.region)
        results.append(r)
        print("BENCH terrain-updateVB-scroll " + " ".join(f"{k}={v}" for k,v in r.items()))
    if len(results) == 2 and results[0]["checksum"] != results[1]["checksum"]:
        raise SystemExit("FAIL: baseline/optimized terrain checksum mismatch")

if __name__ == "__main__":
    main()
