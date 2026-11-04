#!/usr/bin/env python3
"""Host regression for immutable fixed-grid batching; no device/FPS claim."""
# GeneralsX @performance Codex 04/11/2026 Exact tile-order and index-bound regression.
import os, subprocess, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
header = ROOT/'Core/Libraries/Include/GXTerrainDrawBatch.h'
assert header.exists(), 'fixed-grid draw batching helper must exist'
code = r'''
#include "GXTerrainDrawBatch.h"
#include <cassert>
#include <vector>
#include <cstdio>
int main() {
 static_assert(GXTerrainDrawBatch::tilesPerBatch == 4, "retain <=512 KiB snapshots");
 for(unsigned tiles=1;tiles<=128;++tiles) {
  std::vector<unsigned> before,after;
  for(unsigned t=0;t<tiles;++t)for(unsigned q=0;q<1024;++q)
   for(unsigned v: {0u,2u,3u,0u,1u,2u}) before.push_back(t*4096+q*4+v);
  unsigned calls=0;
  for(unsigned t=0;t<tiles;t+=GXTerrainDrawBatch::tilesPerBatch) {
   unsigned count=GXTerrainDrawBatch::tileCount(tiles,t);++calls;
   std::vector<unsigned short> indices(count*6144);
   GXTerrainDrawBatch::fillIndices(indices.data(),count,4096);
   for(auto index:indices) {assert(index<count*4096);after.push_back(t*4096+index);}
  }
  assert(before==after);assert(calls==(tiles+3)/4);
 }
 puts("PASS: exact ordered triangles, partial final groups and 16-bit bounds for 1..128 tiles");
}
'''
with tempfile.TemporaryDirectory(prefix='gx-terrain-batch-') as temp:
    src=Path(temp)/'test.cpp'; exe=Path(temp)/'test';src.write_text(code)
    subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(header.parent),str(src),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)

# Compile the actual production allocation, draw, offset and release paths.
import importlib.util
spec=importlib.util.spec_from_file_location('gles',ROOT/'scripts/qa/test-gles-upload-regressions.py')
gles=importlib.util.module_from_spec(spec);spec.loader.exec_module(gles)
source=(ROOT/'Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp').read_text()
header_source=(ROOT/'Core/GameEngineDevice/Include/W3DDevice/GameClient/HeightMap.h').read_text()
assert '#if defined(__ANDROID__) && !defined(USE_NORMALS) && !defined(PRE_TRANSFORM_VERTEX)' in header_source
assert 'if (drawTerrainBatches()) continue;' in gles.extract(source,'void HeightMapRenderObjClass::Render(')
assert 'if (drawTerrainBatches()) return;' in gles.extract(source,'void HeightMapRenderObjClass::renderTerrainPass(')
geometry=gles.extract(source,'Int HeightMapRenderObjClass::updateVB(')
assert 'eagerLock.emplace(pVB,getTerrainVertexOffset(data)+firstVertex,endVertex-firstVertex)' in geometry
assert 'changedLock(pVB,getTerrainVertexOffset(data)+first,end-first)' in geometry
allocation=gles.extract(source,'\t\tfor (i=0; i<m_numVertexBufferTiles; i++) {')
code=r'''
#include "GXTerrainDrawBatch.h"
#include <vector>
#include <cassert>
#include <cstdio>
using Int=int;using Bool=bool;
constexpr bool TRUE=true,FALSE=false;
constexpr int HEIGHTMAP_VERTEX_NUM=4096,HEIGHTMAP_POLYGON_NUM=2048,DX8_VERTEX_FORMAT=1,DX8_FVF_XYZNUV2=2;
#define NEW_REF(T,args) new T args
#define REF_PTR_RELEASE(p) do {if(p){(p)->Release_Ref();(p)=nullptr;}}while(0)
struct VERTEX_FORMAT {float x,y,z;unsigned diffuse;float u,v,s,t;};
struct DX8VertexBufferClass {
 static int live;enum {USAGE_DEFAULT};int refs=1;unsigned vertices;
 DX8VertexBufferClass(int,unsigned n,int):vertices(n){++live;}
 void Add_Ref(){++refs;}void Release_Ref(){assert(refs>0);if(!--refs){--live;delete this;}}
};int DX8VertexBufferClass::live=0;
struct DX8IndexBufferClass {void Release_Ref(){delete this;}};
struct Pool {void create(DX8VertexBufferClass*,int,int){} void forget(DX8VertexBufferClass*,int){}};
Pool*gxTerrainLightPool(){static Pool p;return &p;}
bool gxCompleteTerrainTile(int,int,int,int,int){return true;}
struct DX8Wrapper {
 static DX8VertexBufferClass *current;static unsigned calls,vertices;
 static void Set_Vertex_Buffer(DX8VertexBufferClass*p){current=p;}
 static void Draw_Triangles(unsigned first,unsigned polys,unsigned start,unsigned count){
  assert(first==0 && start==0 && polys==count/2 && count==current->vertices);++calls;vertices+=count;
 }
};DX8VertexBufferClass*DX8Wrapper::current=nullptr;unsigned DX8Wrapper::calls=0,DX8Wrapper::vertices=0;
struct HeightMapRenderObjClass {
 DX8IndexBufferClass*m_indexBuffer=nullptr;DX8VertexBufferClass**m_vertexBufferTiles=nullptr;
 VERTEX_FORMAT*m_vertexBufferBackup=nullptr;int m_numVertexBufferTiles=0,m_numVBTilesX=1,m_numVBTilesY=1;
 int m_numBlockColumnsInLastVB=0,m_numBlockRowsInLastVB=0;bool hidden=false;
 bool Is_Hidden(){return hidden;}
 int getTerrainVertexOffset(const VERTEX_FORMAT*)const;bool drawTerrainBatches();void freeIndexVertexBuffers();
 VERTEX_FORMAT*getVertexBufferBackup(int,int);
 void allocate(int count){m_numVertexBufferTiles=count;m_vertexBufferTiles=new DX8VertexBufferClass*[count];
 m_vertexBufferBackup=new VERTEX_FORMAT[count*HEIGHTMAP_VERTEX_NUM];int i;
'''+allocation+r'''
 }
};
'''
for signature in ['Int HeightMapRenderObjClass::getTerrainVertexOffset(', 'Bool HeightMapRenderObjClass::drawTerrainBatches(', 'void HeightMapRenderObjClass::freeIndexVertexBuffers(', 'VERTEX_FORMAT *HeightMapRenderObjClass::getVertexBufferBackup(']:
    code+=gles.extract(source,signature)+'\n'
code+=r'''
int main(){
 for(int count=1;count<34;++count){
  HeightMapRenderObjClass map;map.allocate(count);
  for(int tile=0;tile<count;++tile){
#ifdef GX_TERRAIN_DRAW_BATCHING
   assert(map.getTerrainVertexOffset(map.getVertexBufferBackup(0,tile))==(tile%4)*4096);
   assert(DX8VertexBufferClass::live==(count+3)/4);
#else
   assert(map.getTerrainVertexOffset(map.getVertexBufferBackup(0,tile))==0);
   assert(DX8VertexBufferClass::live==count);
#endif
  }
  DX8Wrapper::calls=DX8Wrapper::vertices=0;
#ifdef GX_TERRAIN_DRAW_BATCHING
  assert(map.drawTerrainBatches());assert(DX8Wrapper::calls==unsigned((count+3)/4));
  assert(DX8Wrapper::vertices==unsigned(count*4096));
  map.hidden=true;map.drawTerrainBatches();assert(DX8Wrapper::calls==unsigned((count+3)/4));
#else
  assert(!map.drawTerrainBatches());assert(DX8Wrapper::calls==0);
#endif
  map.freeIndexVertexBuffers();assert(DX8VertexBufferClass::live==0);map.freeIndexVertexBuffers();
 }
 puts("PASS: production allocation/alias references, per-tile offsets, hidden draws, final groups and idempotent cleanup");
}
'''
with tempfile.TemporaryDirectory(prefix='gx-terrain-batch-paths-') as temp:
    src=Path(temp)/'paths.cpp';exe=Path(temp)/'paths';src.write_text(code)
    for defines in [[],['__ANDROID__','GX_TERRAIN_DRAW_BATCHING'],['__ANDROID__','USE_NORMALS'],['__ANDROID__','PRE_TRANSFORM_VERTEX']]:
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O1','-g','-fsanitize=address,undefined','-I'+str(header.parent),*[f'-D{v}' for v in defines],str(src),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
