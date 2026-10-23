#!/usr/bin/env python3
"""Test production W3DShroud dirty rectangle accumulation with UBSan.

Full-map first allocation/reset and partial fog reveal must paint identical
destination texels. Do not change shroud gameplay values or interpolation.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
r=Path(__file__).resolve().parents[2]
src=(r/"GeneralsMD/Code/GameEngineDevice/Source/W3DDevice/GameClient/W3DShroud.cpp").read_text()
hdr=(r/"GeneralsMD/Code/GameEngineDevice/Include/W3DDevice/GameClient/W3DShroud.h").read_text()
start=src.index("void W3DShroud::markShroudCellDirty(Int x, Int y)")
end=src.index("\n//---",start)
actual=src[start:end]
assert "void markShroudCellDirty(Int x, Int y);" in hdr
assert "m_shroudFullUpload" in hdr
assert "m_dirtyMaxX >= m_dirtyMinX && m_dirtyMaxY >= m_dirtyMinY" in src
assert "dstPoint.x = m_dirtyMinX + 1;" in src
assert "dstPoint.y = m_dirtyMinY + 1;" in src
assert src.count("markShroudCellDirty(x, y);")==2
assert src.count("m_shroudFullUpload = TRUE;")>=5
assert "m_shroudFullUpload = FALSE;" in src
cpp=r'''
#include <cstdio>
#include <cstdint>
#include <vector>
#include <algorithm>
using Int=int;
constexpr bool TRUE=true;
struct W3DShroud {
 bool m_srcTextureDirty=false;
 int m_dirtyMinX=0,m_dirtyMinY=0,m_dirtyMaxX=-1,m_dirtyMaxY=-1;
 void markShroudCellDirty(int x,int y);
};
''' + actual + r'''
int main() {
 W3DShroud shroud;
 constexpr int w=128,h=96;
 std::vector<uint32_t> pixels(w*h,17);
 std::vector<uint32_t> full((w+2)*(h+2),0), partial((w+2)*(h+2),0);
 auto paint=[&](std::vector<uint32_t>& dst,int minx,int miny,int maxx,int maxy){
   for(int y=miny;y<=maxy;y++)
      for(int x=minx;x<=maxx;x++)
          dst[(y+1)*(w+2)+x+1]=pixels[y*w+x];
 };
 paint(full,0,0,w-1,h-1);
 paint(partial,0,0,w-1,h-1);
 // Moving the camera reveals a few fog cells; partial copy must match full.
 for(int i=0;i<200;i++) {
    int x=(i*71+3)%w,y=(i*43+7)%h;
    pixels[y*w+x] = (uint32_t)(300+i);
    shroud.markShroudCellDirty(x,y);
 }
 if(!shroud.m_srcTextureDirty) return 1;
 if(shroud.m_dirtyMaxX<shroud.m_dirtyMinX || shroud.m_dirtyMaxY<shroud.m_dirtyMinY)return 2;
 paint(full,0,0,w-1,h-1);
 paint(partial,shroud.m_dirtyMinX,shroud.m_dirtyMinY,shroud.m_dirtyMaxX,shroud.m_dirtyMaxY);
 if(full!=partial)return 3;
 shroud.m_dirtyMinX=shroud.m_dirtyMinY=0;
 shroud.m_dirtyMaxX=shroud.m_dirtyMaxY=-1;
 shroud.m_srcTextureDirty=false;
 // A single re-shroud operation must copy exactly one destination texel.
 pixels[42*w+9]=512;
 shroud.markShroudCellDirty(9,42);
 if(shroud.m_dirtyMinX!=9||shroud.m_dirtyMaxX!=9||shroud.m_dirtyMinY!=42||shroud.m_dirtyMaxY!=42)return 4;
 paint(full,0,0,w-1,h-1);
 paint(partial,shroud.m_dirtyMinX,shroud.m_dirtyMinY,shroud.m_dirtyMaxX,shroud.m_dirtyMaxY);
 if(full!=partial)return 5;
 std::puts("PASS: 200 reveals + isolated fog rewrite preserve every pixel and border");
}
'''
compiler=shutil.which("g++") or shutil.which("clang++")
assert compiler
with tempfile.TemporaryDirectory(prefix="gx-shroud-rect-") as temp:
 path=Path(temp)/"main.cpp"
 exe=Path(temp)/"test"
 path.write_text(cpp)
 subprocess.run([compiler,"-std=c++17","-Wall","-Wextra","-Werror",
                 "-fsanitize=undefined","-fno-sanitize-recover=undefined",
                 str(path),"-o",str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print("PASS: production shroud rectangle bounds and full/partial equality")
