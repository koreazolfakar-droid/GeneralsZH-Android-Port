#!/usr/bin/env python3
"""Compare production circular dirty-region mapping with per-cell reference."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gles',ROOT/'scripts/qa/test-gles-upload-regressions.py')
gles=importlib.util.module_from_spec(spec);spec.loader.exec_module(gles)
source=(ROOT/'Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp').read_text()
method=gles.extract(source,'void HeightMapRenderObjClass::doPartialUpdate(')
# Only replace the unrelated material/shoreline bookkeeping tail with an end.
method=method[:method.index('\n\tif (!m_extraBlendTilePositions)')]+'\n}\n'
code=r'''
#include <algorithm>
#include <cassert>
#include <cstdio>
#include <vector>
using Int=int;
struct Point{int x,y;};struct IRegion2D{Point lo,hi;};
struct RefRenderObjListIterator{};
struct WorldHeightMap {int x=100,y=200;int getDrawOrgX(){return x;}int getDrawOrgY(){return y;}};
struct HeightMapRenderObjClass {
 int m_x=9,m_y=7,m_originX=0,m_originY=0,calls=0;
 std::vector<int> touched;
 void doPartialUpdate(const IRegion2D&,WorldHeightMap*,RefRenderObjListIterator*);
 int updateBlock(int x0,int y0,int x1,int y1,WorldHeightMap*,RefRenderObjListIterator*){
  assert(x0>=0&&y0>=0&&x1<m_x&&y1<m_y&&x0<=x1&&y0<=y1);++calls;
  for(int y=y0;y<y1;++y)for(int x=x0;x<x1;++x)++touched[y*(m_x-1)+x];return 0;
 }
};
'''+method+r'''
int main(){
 WorldHeightMap map;HeightMapRenderObjClass t;unsigned cases=0;
 unsigned rng=1234;auto random=[&](int n){rng=rng*1664525u+1013904223u;return int(rng%unsigned(n));};
 for(int shape=0;shape<3;++shape){
  t.m_x=shape==0?9:shape==1?33:129;t.m_y=shape==0?7:shape==1?17:65;
  int nx=t.m_x-1,ny=t.m_y-1;
  for(int iteration=0;iteration<1000;++iteration){
   t.m_originX=random(nx);t.m_originY=random(ny);
   int x0=random(nx+10)-5,y0=random(ny+10)-5,x1=x0+random(nx+5),y1=y0+random(ny+5);
   if(iteration%20==0){x0=0;y0=0;x1=nx;y1=ny;}
   IRegion2D dirty{{map.x+x0,map.y+y0},{map.x+x1,map.y+y1}};
   t.touched.assign(nx*ny,0);t.calls=0;t.doPartialUpdate(dirty,&map,nullptr);
   for(int y=0;y<ny;++y)for(int x=0;x<nx;++x){
    int worldX=(x-t.m_originX+nx)%nx,worldY=(y-t.m_originY+ny)%ny;
    int expected=worldX>=x0&&worldX<x1&&worldY>=y0&&worldY<y1?1:0;
    if(t.touched[y*nx+x]!=expected){std::fprintf(stderr,"FAIL shape=%d origin=(%d,%d) dirty=(%d,%d)-(%d,%d) cell=(%d,%d) writes=%d expected=%d\n",shape,t.m_originX,t.m_originY,x0,y0,x1,y1,x,y,t.touched[y*nx+x],expected);return 1;}
   }
   assert(t.calls<=4);++cases;
  }
 }
 std::printf("PASS: %u dirty regions match exact affected cells across both circular seams, clipping, empty/full regions and rectangular maps\n",cases);
}
'''
with tempfile.TemporaryDirectory(prefix='gx-terrain-partial-') as temp:
    path=Path(temp)/'test.cpp';exe=Path(temp)/'test';path.write_text(code)
    subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O1','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined',str(path),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
