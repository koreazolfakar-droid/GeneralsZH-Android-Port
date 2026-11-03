#!/usr/bin/env python3
"""Run actual draw-window sizing against draw-area policy; no GPU/FPS claims."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('gles', ROOT/'scripts/qa/test-gles-upload-regressions.py')
gles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gles)
terrain = (ROOT/'Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp').read_text()
world = (ROOT/'Core/GameEngineDevice/Source/W3DDevice/GameClient/WorldHeightMap.cpp').read_text()
code = r'''
#include <algorithm>
#include <cassert>
#include <cstdio>
using Int=int; using Bool=bool;
constexpr bool FALSE=false;
template<class T> T clamp(T lo,T v,T hi){return std::max(lo,std::min(v,hi));}
struct Global { bool m_stretchTerrain=false,m_drawEntireTerrain=false; } globals;
Global *TheGlobalData=&globals;
struct WorldHeightMap {
 static constexpr int STRETCH_DRAW_WIDTH=65,STRETCH_DRAW_HEIGHT=65;
 struct DrawArea {int sizeX,sizeY,originX,originY;};
 int m_width=513,m_height=385,m_drawWidthX=129,m_drawHeightY=129,m_drawOriginX=0,m_drawOriginY=0;
 int getXExtent(){return m_width;} int getYExtent(){return m_height;}
 int getDrawWidth(){return m_drawWidthX;} int getDrawHeight(){return m_drawHeightY;}
 int getDrawOrgX(){return m_drawOriginX;} int getDrawOrgY(){return m_drawOriginY;}
 void setDrawWidth(int x){m_drawWidthX=x;} void setDrawHeight(int y){m_drawHeightY=y;}
 DrawArea createDrawArea(Int,Int); Bool setDrawArea(const DrawArea&); Bool setDrawOrg(Int,Int);
};
struct Shroud {int resets=0;void reset(){++resets;}};
struct HeightMapRenderObjClass {
 WorldHeightMap *m_map; int m_oversizeDrawWidth=0,m_oversizeDrawHeight=0,m_originX=0,m_originY=0;
 Shroud shroud; Shroud *m_shroud=&shroud; bool m_needFullUpdate=false; int rebuilds=0;
 void initHeightData(int x,int y,WorldHeightMap*,void*,bool){assert(x==m_map->getDrawWidth()&&y==m_map->getDrawHeight());++rebuilds;}
 void setTerrainDrawSize(Int,Int);
};
'''
for signature in ('WorldHeightMap::DrawArea WorldHeightMap::createDrawArea(', 'Bool WorldHeightMap::setDrawArea(', 'Bool WorldHeightMap::setDrawOrg('):
    code += gles.extract(world, signature)+'\n'
code += gles.extract(terrain, 'void HeightMapRenderObjClass::setTerrainDrawSize(')
code += r'''
int main(){
 for(int mode=0;mode<3;++mode)for(bool oversize:{false,true}){
  globals.m_stretchTerrain=mode==1;globals.m_drawEntireTerrain=mode==2;
  WorldHeightMap map;HeightMapRenderObjClass t;t.m_map=&map;
  if(oversize){t.m_oversizeDrawWidth=193;t.m_oversizeDrawHeight=161;}
  // Model the production updateCenter policy after every sizing request.
  t.setTerrainDrawSize(129,97); map.setDrawOrg(40,50);
  int builds=t.rebuilds,shrouds=t.shroud.resets;
  for(int frame=0;frame<1000;++frame){
   t.setTerrainDrawSize(129,97);map.setDrawOrg(frame%250,frame%150);
  }
  if(t.rebuilds!=builds){std::fprintf(stderr,"FAIL mode=%d oversize=%d: unchanged policy rebuilt %d times\n",mode,int(oversize),t.rebuilds-builds);return 1;}
  assert(t.shroud.resets==shrouds);
  int expectedX=mode==2?513:mode==1?65:oversize?193:129;
  int expectedY=mode==2?385:mode==1?65:oversize?161:97;
  assert(map.getDrawWidth()==expectedX&&map.getDrawHeight()==expectedY);
  globals.m_drawEntireTerrain=false;globals.m_stretchTerrain=false;
  t.m_oversizeDrawWidth=t.m_oversizeDrawHeight=0;
  builds=t.rebuilds;t.setTerrainDrawSize(257,193);assert(t.rebuilds==builds+1&&t.m_needFullUpdate);
  t.setTerrainDrawSize(257,193);assert(t.rebuilds==builds+1);
  map.m_width=81;map.m_height=57;t.setTerrainDrawSize(257,193);
  assert(map.getDrawWidth()==81&&map.getDrawHeight()==57);
 }
 puts("PASS: 6000 unchanged sizing/camera requests avoid reinitialization; policy changes, rectangular windows, small maps, shroud and required rebuilds preserved");
}
'''
with tempfile.TemporaryDirectory(prefix='gx-terrain-invalidation-') as temp:
    path=Path(temp)/'test.cpp';exe=Path(temp)/'test';path.write_text(code)
    subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(path),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
