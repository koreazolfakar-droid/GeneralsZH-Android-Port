#!/usr/bin/env python3
"""Execute current and 3481 terrain lighting with host adapters; compare exact bytes.
Includes producer dirty ranges, moving/disabled lights, geometry reset and cache release.
No device/GPU/FPS measurement.
"""
# GeneralsX @test Codex 14/10/2026 Differential production lighting regression.
import importlib.util, os, subprocess, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gles',ROOT/'scripts/qa/test-gles-upload-regressions.py')
gles=importlib.util.module_from_spec(spec);spec.loader.exec_module(gles)
PATH='Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp'
source=(ROOT/PATH).read_text()
legacy=subprocess.check_output(['git','show','c40a361857edfe70842f26ddb2a76d47ebda4ba4:'+PATH],cwd=ROOT,text=True)
functions=['Int HeightMapRenderObjClass::updateVBForLight(', 'Int HeightMapRenderObjClass::updateVBForLightOptimized(']

def main():
    code=r'''
#define __ANDROID__ 1
#define OPTIMIZED_HEIGHTMAP_LIGHTING 0
#include "GXTerrainLightColors.h"
#include <map>
#include <optional>
#include <new>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <array>
#include <cmath>
using Int=int;using Real=float;using UnsignedInt=unsigned;using Bool=bool;
constexpr int VERTEX_BUFFER_TILE_LENGTH=32,HEIGHTMAP_VERTEX_NUM=4096;
constexpr float MAP_XY_FACTOR=10,MAP_HEIGHT_SCALE=0.625;
#define DEBUG_CRASH(args) assert(false)
namespace GXTrace { bool isPerfEnabled(){return true;} }
struct VERTEX_FORMAT {float x,y,z;unsigned diffuse;float u1,v1,u2,v2;};
struct Vector3 {
 float X=0,Y=0,Z=0;Vector3()=default;Vector3(float x,float y,float z):X(x),Y(y),Z(z){}
 void Set(float x,float y,float z){X=x;Y=y;Z=z;}
 Vector3&operator-=(const Vector3&v){X-=v.X;Y-=v.Y;Z-=v.Z;return *this;}
 Vector3&operator/=(float v){X/=v;Y/=v;Z/=v;return *this;}
 float Length()const{return std::sqrt(X*X+Y*Y+Z*Z);}
 static float Dot_Product(const Vector3&a,const Vector3&b){return a.X*b.X+a.Y*b.Y+a.Z*b.Z;}
 static void Normalized_Cross_Product(const Vector3&a,const Vector3&b,Vector3*n){
  n->Set(a.Y*b.Z-a.Z*b.Y,a.Z*b.X-a.X*b.Z,a.X*b.Y-a.Y*b.X);float len=std::sqrt(n->X*n->X+n->Y*n->Y+n->Z*n->Z);n->X/=len;n->Y/=len;n->Z/=len;
 }
};
struct FakeMap {int getDrawOrgX(){return 0;}int getDrawOrgY(){return 0;}int getBorderSizeInline(){return 0;}
 int getXExtent(){return 80;}int getYExtent(){return 80;}float getDisplayHeight(int x,int y){return float((x*x+y*17)%31);}};
struct LightClass {enum Type {POINT,SPOT,DIRECTIONAL};};
struct WWMath {static float Clamp(float x,float a,float b){return std::max(a,std::min(x,b));}static int Float_To_Int_Chop(float x){return int(x);}};
struct W3DDynamicLight {
 int m_minX=0,m_maxX=64,m_minY=0,m_maxY=64,m_prevMinX=0,m_prevMaxX=64,m_prevMinY=0,m_prevMaxY=64;
 bool enabled=true;unsigned color=0x102030;int type=LightClass::POINT;Vector3 position{17.25f,9.5f,77.0f};
 bool isEnabled(){return enabled;}int Get_Type(){return type;}Vector3 Get_Position(){return position;}
 void Get_Far_Attenuation_Range(double&mid,double&far){mid=100;far=1000;}
 void Get_Spot_Direction(Vector3&v){v.Set(0,0,-1);}
 void Get_Diffuse(Vector3*v){v->Set(((color>>16)&255)/255.0f,((color>>8)&255)/255.0f,(color&255)/255.0f);}
 void Get_Ambient(Vector3*v){v->Set(0.01f,0.02f,0.03f);}
};
struct DX8VertexBufferClass {
 std::vector<VERTEX_FORMAT> vertices=std::vector<VERTEX_FORMAT>(HEIGHTMAP_VERTEX_NUM);
 unsigned locks=0,first=0,count=0;bool active=false;
 struct WriteLockClass {DX8VertexBufferClass*p;explicit WriteLockClass(DX8VertexBufferClass*b):p(b){assert(!p->active);p->active=true;++p->locks;p->first=0;p->count=p->vertices.size();}~WriteLockClass(){p->active=false;}void* Get_Vertex_Array(){return p->vertices.data();}};
 struct AppendLockClass {DX8VertexBufferClass*p;AppendLockClass(DX8VertexBufferClass*b,unsigned f,unsigned n):p(b){assert(!p->active && f+n<=p->vertices.size());p->active=true;++p->locks;p->first=f;p->count=n;}~AppendLockClass(){p->active=false;}void* Get_Vertex_Array(){return p->vertices.data()+p->first;}};
};
'''
    code+=gles.extract(source,'struct GxTerrainLightPool')+';\n'
    code+=gles.extract(source,'static GxTerrainLightPool *gxTerrainLightPool()')+'\n'
    code+='static size_t gxLightUpdates=0,gxLightUnchanged=0,gxLightFallback=0,gxLightChecked=0,gxLightChanged=0,gxLightLockVertices=0;\n'
    code+=gles.extract(source,'struct GxTerrainLightingWriter')+';\n'
    code+=r'''
struct HeightMapRenderObjClass {
 bool m_vertexBufferTiles=true;FakeMap map;FakeMap*m_map=&map;
 unsigned calculations=0;
 int m_x=65,m_y=65,m_originX=0,m_originY=0;
 int getXWithOrigin(int x);int getYWithOrigin(int y);
 unsigned doTheDynamicLight(VERTEX_FORMAT*,VERTEX_FORMAT*,Vector3*,Vector3*,W3DDynamicLight**,int);
 int updateVBForLight(DX8VertexBufferClass*,VERTEX_FORMAT*,int,int,int,int,int,int,W3DDynamicLight**,int);
 int updateVBForLightOptimized(DX8VertexBufferClass*,VERTEX_FORMAT*,int,int,int,int,int,int,W3DDynamicLight**,int);
 int legacyLight(DX8VertexBufferClass*,VERTEX_FORMAT*,int,int,int,int,int,int,W3DDynamicLight**,int);
 int legacyOptimized(DX8VertexBufferClass*,VERTEX_FORMAT*,int,int,int,int,int,int,W3DDynamicLight**,int);
};
'''
    for signature in functions:code+=gles.extract(source,signature)+'\n'
    math=gles.extract(source,'UnsignedInt HeightMapRenderObjClass::doTheDynamicLight(')
    assert math==gles.extract(legacy,'UnsignedInt HeightMapRenderObjClass::doTheDynamicLight(')
    code+=math.replace('{','{ ++calculations;',1)+'\n'
    code+=gles.extract(source,'Int HeightMapRenderObjClass::getXWithOrigin(')+'\n'
    code+=gles.extract(source,'Int HeightMapRenderObjClass::getYWithOrigin(')+'\n'
    code+=gles.extract(legacy,functions[0]).replace('HeightMapRenderObjClass::updateVBForLight(','HeightMapRenderObjClass::legacyLight(')+'\n'
    code+=gles.extract(legacy,functions[1]).replace('HeightMapRenderObjClass::updateVBForLightOptimized(','HeightMapRenderObjClass::legacyOptimized(')+'\n'
    code+=r'''
static void geometry(DX8VertexBufferClass&vb,std::vector<VERTEX_FORMAT>&mirror,int first,int count,unsigned seed){
 for(int i=first;i<first+count;++i){auto&v=mirror[i];v.x=float(i%128);v.y=float(i/128);v.z=float(i%13);v.diffuse=((unsigned(i+seed)&255)<<24)|(seed*91+unsigned(i));v.u1=v.x/128;v.v1=v.y/32;v.u2=v.u1/3;v.v2=v.v1/2;}
 // Exactly the production geometry writer's memcpy + remember sequence.
 DX8VertexBufferClass::AppendLockClass lock(&vb,first,count);
 memcpy(lock.Get_Vertex_Array(),mirror.data()+first,count*sizeof(VERTEX_FORMAT));
 if(auto*c=gxTerrainLightPool()->find(&vb))c->remember(first,mirror.data()+first,count);
}
int main(){
 auto*pool=gxTerrainLightPool();assert(pool && pool->bytes==0);
 unsigned optimized=0;
 for(int mode=0;mode<2;++mode){
  DX8VertexBufferClass current,old;std::vector<VERTEX_FORMAT> mirror(HEIGHTMAP_VERTEX_NUM),original(HEIGHTMAP_VERTEX_NUM);pool->create(&current,HEIGHTMAP_VERTEX_NUM);
  geometry(current,mirror,0,HEIGHTMAP_VERTEX_NUM,123);geometry(old,original,0,HEIGHTMAP_VERTEX_NUM,123);
  HeightMapRenderObjClass a,b;W3DDynamicLight light;W3DDynamicLight*lights[]={&light};
  auto run=[&](int x0,int y0,int x1,int y1){
   const unsigned ca=a.calculations,cb=b.calculations;
   if(mode){a.updateVBForLightOptimized(&current,mirror.data(),x0,y0,x1,y1,0,0,lights,1);b.legacyOptimized(&old,original.data(),x0,y0,x1,y1,0,0,lights,1);}
   else{a.updateVBForLight(&current,mirror.data(),x0,y0,x1,y1,0,0,lights,1);b.legacyLight(&old,original.data(),x0,y0,x1,y1,0,0,lights,1);}
   assert(a.calculations-ca==b.calculations-cb);
   assert(memcmp(current.vertices.data(),old.vertices.data(),HEIGHTMAP_VERTEX_NUM*sizeof(VERTEX_FORMAT))==0);
   assert(memcmp(mirror.data(),original.data(),HEIGHTMAP_VERTEX_NUM*sizeof(VERTEX_FORMAT))==0); // base lighting immutable
  };
  run(0,0,32,32);const unsigned firstLocks=current.locks;
  for(int i=0;i<70;++i)run(0,0,32,32);
  assert(current.locks==firstLocks);optimized+=70;
  for(int i=0;i<100;++i){
   a.m_originX=b.m_originX=i%64;a.m_originY=b.m_originY=(i*7)%64;
   light.color=unsigned(i*7143);light.enabled=(i%7)!=0;light.type=i%3;light.position.X=i+0.25f;light.m_prevMinX=light.m_minX;light.m_prevMaxX=light.m_maxX;light.m_minX=i%17;light.m_maxX=light.m_minX+3;
   run(0,0,32,32);
   if(i%9==0){int first=(i*113)%(HEIGHTMAP_VERTEX_NUM-24);geometry(current,mirror,first,24,unsigned(i));geometry(old,original,first,24,unsigned(i));run(0,0,32,32);}
   run(4,3,11,9);run(31,31,32,32);
  }
  pool->forget(&current);assert(pool->bytes==0);pool->create(&current,HEIGHTMAP_VERTEX_NUM); // pointer reuse must not retain stale colors
  geometry(current,mirror,0,HEIGHTMAP_VERTEX_NUM,21);geometry(old,original,0,HEIGHTMAP_VERTEX_NUM,21);run(0,0,32,32);
  pool->forget(&current);assert(pool->bytes==0);
  current.locks=0;run(0,0,32,32);assert(current.locks==1); // allocation/cap fallback is ordinary full lock
 }
 {
  std::array<DX8VertexBufferClass,257> tiles;
  for(int i=0;i<256;++i)pool->create(&tiles[i],HEIGHTMAP_VERTEX_NUM);
  assert(pool->bytes==GxTerrainLightPool::budget);pool->create(&tiles[256],HEIGHTMAP_VERTEX_NUM);assert(!pool->find(&tiles[256]));
  for(auto&tile:tiles)pool->forget(&tile);assert(pool->bytes==0 && pool->tiles.empty());
 }
 printf("PASS: %u repeated unchanged terrain lighting calls: zero dirty locks; exact 3481 bytes/calculation count for both paths, moving/disabled lights, alpha, geometry/camera edits, pointer reuse, fallback and 8MiB cap/release\n",optimized);
}
'''
    # Enforce all actual tile-geometry lifecycle writers participate, not only adapters.
    assert 'litColors->remember(offset,pCurVertices,4)' in gles.extract(source,'Int HeightMapRenderObjClass::updateVB(')
    assert 'gxTerrainLightPool()->forget(m_vertexBufferTiles[i])' in source
    assert 'gxTerrainLightPool()->create(m_vertexBufferTiles[i],HEIGHTMAP_VERTEX_NUM)' in source
    with tempfile.TemporaryDirectory(prefix='gx-light-dirty-') as temp:
        p=Path(temp)/'test.cpp';p.write_text(code);exe=Path(temp)/'test'
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(ROOT/'Core/Libraries/Include'),str(p),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)

if __name__=='__main__':main()
