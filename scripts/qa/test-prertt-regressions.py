#!/usr/bin/env python3
"""Production preRTT attribution/trace/iteration/particle regressions (host adapters).
Host timings are not Android FPS benchmarks. No retail/mod assets are simulated as real.
"""
# GeneralsX @test Codex 14/10/2026 Preserve pre-render semantics and diagnostic opt-ins.
import argparse, importlib.util, json, os, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gx',ROOT/'scripts/qa/test-gles-upload-regressions.py')
gx=importlib.util.module_from_spec(spec);spec.loader.exec_module(gx)
BASELINE='00dc954e02d1e346caa90e69739012f70ce69a80'
def source(path,old=False):
    return subprocess.check_output(['git','show',BASELINE+':'+path],cwd=ROOT,text=True) if old else (ROOT/path).read_text()
def build(work,label,code,extra=(),sanitize=True):
    p=work/(label+'.cpp');p.write_text(code);exe=work/label
    flags=['-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer'] if sanitize else ['-O2']
    subprocess.run([os.environ.get('CXX','c++'),'-std=c++17',*flags,'-I',str(work),'-I',str(ROOT/'Core/Libraries/Include'),str(p),'-o',str(exe),*extra],check=True)
    return exe
def run(exe,**kwargs):return subprocess.run([str(exe)],check=True,**kwargs)

def test_stats(work):
    header=source('Core/Libraries/Include/GXPreRenderStats.h')
    # Execute actual aggregation/scopes, with deterministic clocks rather than sleeps.
    header=header.replace(gx.extract(header,'inline double wallUs()'),'inline double wallUs(){return fakeWall;}')
    header=header.replace(gx.extract(header,'inline double cpuUs()'),'inline double cpuUs(){return fakeCpu;}')
    (work/'stats-fixture.h').write_text(header)
    code=r'''
#include <cstdio>
#include <cstdarg>
#include <string>
#include <cassert>
#include <vector>
double fakeWall=1000000,fakeCpu=100000;
static std::string text;
int logRecord(FILE*,const char*fmt,...){char b[4096];va_list a;va_start(a,fmt);int n=vsnprintf(b,sizeof(b),fmt,a);va_end(a);assert(n>=0&&n<int(sizeof(b)));text+=b;return n;}
#define fprintf logRecord
#include "stats-fixture.h"
#undef fprintf
int main(){
 using namespace GXPreRTT;
 { Frame disabled(false,10);Scope no(Views,true);assert(!active());}
 assert(state().frames==0);
 { Frame root(true,10,false,12);
   {Frame nested(true,0);assert(!nested.enabled);}
   {Scope views(Views,true);
     {Scope region(Region);state().scanned+=20;state().matched+=2;
      {Scope callback(Callbacks);ModuleScope module(42);++state().drawn;fakeWall+=3000;fakeCpu+=1000;}
      fakeWall+=1000;fakeCpu+=1000;
     }
     {Scope terrain(Terrain,true);++state().fullMapRefreshes;fakeWall+=8000;fakeCpu+=4000;}
   }
   {Scope particles(Particles,true);fakeWall+=8000;fakeCpu+=4000;}
   root.finish(8010);assert(!active());
 }
 assert(state().frames==1 && state().rootWall==20000 && state().rootCpu==10000 && state().queueWait==8000);
 assert(state().phases[Views].wall==12000 && state().phases[Callbacks].wall==3000);
 state().reportReady=true;std::vector<int> keys;
 report([&](int key,double ms,double calls){assert(key==42&&ms==3&&calls==1);keys.push_back(key);},12,false);
 assert(keys.size()==1&&text.find("preP50/P95/P99=20.000/20.000/20.000")!=std::string::npos);
 assert(text.find("scanWall=1.000")!=std::string::npos && text.find("threadCpu=10.000 producerWait=8.000")!=std::string::npos);
 assert(state().frames==0 && state().modules[42].used);
 {Frame f(true,0,false,13);f.finish(0);}
 state().reportReady=true;report([](int,double,double){assert(false);},13,false);
 // A mode change / rewind excludes loading and old match samples.
 {Frame f(true,0,false,13);f.finish(0);}
 {Frame f(true,0,true,13);assert(state().frames==0);f.finish(0);}
 {Frame f(true,0,true,1);assert(state().frames==0);f.finish(0);}
 state().resetWindow(fakeWall);state().hasMode=false;
 {Frame f(true,0);for(int i=0;i<70;++i){ModuleScope m(i);fakeWall+=i+1;}f.finish(0);}
 assert(state().moduleOverflow.calls==6);
 state().reportReady=true;int rows=0;double previous=1e6;
 report([&](int,double ms,double){assert(ms<=previous);previous=ms;++rows;},1,false);
 assert(rows==8&&text.find("type=<overflow>")!=std::string::npos);
 for(int i=0;i<2051;++i)state().pre.add(i,0);
 assert(state().pre.dropped==3);
 fakeCpu=-1;{Frame f(true,0);f.finish(0);}assert(state().cpuFrames==0);
 puts("PASS: nested preRTT phases, exact percentiles, thread CPU vs wall/producer waits, bounded module rows/overflow, load/rewind reset and disabled scopes");
}
'''
    run(build(work,'stats',code))

def test_trace(work):
    code=r'''
#include "GXTrace.h"
#include <cassert>
#include <cstdio>
int main(int argc,char**argv){
 GXTrace::configureDiagnosticArguments(argc,argv);
 printf("%d %d %d %d %d\n",GXTrace::isEnabled(),GXTrace::isPerfEnabled(),GXTrace::isNetEnabled(),GXTrace::isSummaryBenchmark(),GXTrace::detailedPerfRequested());
 int sideEffects=0;
 GX_TRACE("%d\n",++sideEffects);GX_NET_TRACE("%d\n",++sideEffects);
 assert(sideEffects==int(GXTrace::isEnabled())+int(GXTrace::isNetEnabled()));
 GXTrace::configureDiagnosticArguments(0,nullptr);assert(!GXTrace::replayDiagnostics());
}
'''
    exe=build(work,'trace',code)
    tests=[
      ({},[],(), '0 0 0 0 0'),
      ({'GX_PERF':'1'},[],(), '0 1 0 1 0'),
      ({'GX_TRACE':'1','GX_NET_TRACE':'1'},[],(), '1 1 1 0 0'),
      ({'GX_PERF':'1','GX_TRACE':'1','GX_NET_TRACE':'1'},[],(), '0 1 0 1 0'),
      ({'GX_PERF':'1','GX_TRACE':'1','GX_NET_TRACE':'1','GX_PERF_DETAIL':'1'},[],(), '1 1 1 0 1'),
      ({'GX_PERF':'1','GX_NET_TRACE':'1'},['-replay','test.rep'],(), '0 1 1 0 1'),
      ({},[],('gx_perf.txt','gx_trace.txt','gx_net_trace.txt'), '0 1 0 1 0'),
      ({},[],('gx_perf.txt','gx_trace.txt','gx_net_trace.txt','gx_perf_detail.txt'), '1 1 1 0 1'),
    ]
    for i,(vars,args,markers,expected) in enumerate(tests):
        cwd=work/('mode'+str(i));cwd.mkdir()
        for m in markers:(cwd/m).touch()
        env=os.environ.copy()
        for k in ('GX_PERF','GX_TRACE','GX_NET_TRACE','GX_PERF_DETAIL'):env.pop(k,None)
        env.update(vars)
        result=subprocess.run([str(exe),*args],cwd=cwd,env=env,capture_output=True,text=True,check=True)
        assert result.stdout.strip()==expected,(i,result.stdout,result.stderr)
    # Existing APK Replay Check must reach the native diagnostic override.
    main=source('GeneralsMD/Code/Main/SDL3Main.cpp')
    assert 'GXTrace::configureDiagnosticArguments(argc,argv)' in main
    print('PASS: 8 summary/detail/env/marker/Replay Check modes; suppressed per-event arguments do not execute')

def test_region(work):
    path='GeneralsMD/Code/GameEngine/Source/GameClient/GameClient.cpp'
    sig='void GameClient::iterateDrawablesInRegion('
    current=gx.extract(source(path),sig);old=gx.extract(source(path,True),sig).replace('GameClient::iterateDrawablesInRegion','GameClient::legacy')
    code=r'''
#define __ANDROID__ 1
#include "GXPreRenderStats.h"
#include <cassert>
#include <vector>
#include <limits>
using Real=float;
struct Coord3D{Real x,y,z;};struct Region3D{Coord3D lo,hi;};
struct Drawable{Coord3D pos{};Drawable*next=nullptr;int id;const Coord3D*getPosition(){return &pos;}Drawable*getNextDrawable(){return next;}};
using GameClientFuncPtr=void(*)(Drawable*,void*);
struct GameClient{Drawable*m_drawableList=nullptr;void iterateDrawablesInRegion(Region3D*,GameClientFuncPtr,void*);void legacy(Region3D*,GameClientFuncPtr,void*);};
static void collect(Drawable*d,void*p){static_cast<std::vector<int>*>(p)->push_back(d->id);}
'''
    code+=current+'\n'+old+r'''
int main(){
 std::vector<Drawable> objects(2000);for(size_t i=0;i<objects.size();++i){objects[i].id=i;objects[i].pos={float(int(i%51)-25),float(int(i%71)-35),float(int(i%19)-9)};objects[i].next=i+1<objects.size()?&objects[i+1]:nullptr;}
 GameClient c;c.m_drawableList=objects.data();Region3D box{{-5,-5,-5},{5,5,5}};
 objects[0].pos=box.lo;objects[1].pos=box.hi;objects[2].pos.x=std::numeric_limits<float>::quiet_NaN();
 for(Region3D*r:std::vector<Region3D*>{&box,nullptr}){std::vector<int>a,b;c.legacy(r,collect,&a);{GXPreRTT::Frame f(true,0);c.iterateDrawablesInRegion(r,collect,&b);f.finish(0);}assert(a==b);}
 assert(GXPreRTT::state().scanned==4000);
 // Callback deletes its current drawable; cached next must retain legacy lifetime/order.
 auto erase=[](Drawable*d,void*p){collect(d,p);delete d;};
 for(bool legacy:{true,false}){
   auto*a=new Drawable{{},nullptr,1};auto*b=new Drawable{{},nullptr,2};a->next=b;c.m_drawableList=a;
   std::vector<int> ids;if(legacy)c.legacy(nullptr,erase,&ids);else c.iterateDrawablesInRegion(nullptr,erase,&ids);
   assert((ids==std::vector<int>{1,2}));
 }
 puts("PASS: production region callbacks match 3486 order/boundaries/null-region/NaN membership/current deletion; no drawable or offscreen-update policy change");
}
'''
    run(build(work,'region',code))

def test_particles(work):
    path='Core/GameEngine/Source/GameClient/System/ParticleSys.cpp';sig='void ParticleSystemManager::update()'
    current=gx.extract(source(path),sig);old=gx.extract(source(path,True),sig).replace('ParticleSystemManager::update','ParticleSystemManager::legacy')
    code=r'''
#define __ANDROID__ 1
#include "GXPreRenderStats.h"
#include <cassert>
#include <list>
#include <vector>
#include <cstdint>
using Bool=bool;using Int=int;using DWORD=uint32_t;
#define DEBUG_ASSERTCRASH(condition,message) assert(condition)
#define deleteInstance(p) do { m_allParticleSystemList.remove(p); delete p; }while(0)
struct Particle;
struct Coord3D{float x=1,y=2,z=3;};
struct Vector{void Set(float,float,float=0){}};
struct Smudge{Vector m_pos,m_offset;float m_size=0,m_opacity=0;bool m_draw=false;};
struct SmudgeSet{Smudge item;Smudge*addSmudgeToSet(Particle*){return &item;}};
struct SmudgeManager{int resets=0;SmudgeSet set;bool getHardwareSupport(){return false;}void reset(){++resets;}SmudgeSet*addSmudgeSet(){return &set;}}smudge;
SmudgeManager*TheSmudgeManager=&smudge;
struct Global{bool m_headless=false,m_useHeatEffects=false;}global;Global*TheGlobalData=&global;
float GameClientRandomValueReal(float a,float){return a;}
struct Logic{int frame=0;int getFrame(){return frame;}}logic;Logic*TheGameLogic=&logic;
struct Client{bool advanced=true;int getFrameLegacy(){return logic.frame/2;}bool HasLegacyFrameAdvanced(){return advanced;}}client;Client*TheGameClient=&client;
struct Particle{Particle*m_systemNext=nullptr;Coord3D pos;Coord3D*getPosition(){return &pos;}float getSize(){return 1;}float getAlpha(){return 1;}};
struct Name{const char*str(){return "NONE";}};
static std::vector<int> order;static uint32_t rng=1;
struct ParticleSystem{int id=0;bool dying=false;bool update(int){order.push_back(id);rng=rng*1664525+1013904223;return !dying;}bool isUsingDrawables(){return false;}Name getParticleTypeName(){return {};}Particle*getFirstParticle(){return nullptr;}};
struct ParticleSystemManager{using ParticleSystemListIt=std::list<ParticleSystem*>::iterator;std::list<ParticleSystem*>m_allParticleSystemList;int m_lastLogicFrameUpdate=-1,m_localPlayerIndex=3;void update();void legacy();};
'''
    code+=current+'\n'+old+r'''
int main(){
 auto drive=[](bool legacy){
   ParticleSystemManager m;for(int i=0;i<7;++i)m.m_allParticleSystemList.push_back(new ParticleSystem{i,i%3==0});
   order.clear();rng=1;smudge.resets=0;
   for(int f=0;f<8;++f){logic.frame=f;client.advanced=(f%2==0);if(legacy){m.legacy();m.legacy();}else {m.update();m.update();}}
   const auto result=std::make_pair(order,std::make_pair(rng,smudge.resets));
   for(auto*p:m.m_allParticleSystemList)delete p;
   return result;
 };
 assert(drive(false)==drive(true));
 puts("PASS: production particle tick gating, deletion order, RNG calls and smudge resets match 3486; 30/60 fixture");
}
'''
    for high in (False,True):
        extra=['-DGENERALS_ONLINE_HIGH_FPS_RENDER=1'] if high else []
        run(build(work,'particle'+str(int(high)),code,extra))
    # Added emission/step scopes must wrap existing work, not skip/change it.
    sig='Bool ParticleSystem::update('
    new=gx.extract(source(path),sig);baseline=gx.extract(source(path,True),sig)
    assert 'generateParticleInfo(i, count)' in new and 'p->update() == false' in new
    assert new.count('GameClientRandom')==baseline.count('GameClientRandom')
    assert new.count('createParticle(')==baseline.count('createParticle(')

def test_waits(work):
    s=source('Core/Libraries/Source/d3d8gles/src/gles_thread.cpp')
    body=gx.extract(s,'void waitMain(P pred, double *accumUs)')
    code=r'''
#include <cassert>
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <thread>
using Clock=std::chrono::steady_clock;
double usSince(Clock::time_point){return 23;}
std::mutex s_doneMutex;std::condition_variable s_doneCv;std::atomic<bool>s_mainWaiting{false};
double s_producerWaitUsTotal=0;
'''
    code+='template<class P>\n'+body+r'''
int main(){
 double sync=0,ring=0;waitMain([]{return true;},&sync);assert(sync==0&&s_producerWaitUsTotal==0);
 int calls=0;waitMain([&]{return ++calls>=3;},&sync);assert(sync==23&&s_producerWaitUsTotal==23);
 calls=0;waitMain([&]{return ++calls>=18;},&ring);assert(ring==23&&s_producerWaitUsTotal==46);
 sync=ring=0;assert(s_producerWaitUsTotal==46); // interval reporting cannot consume total
}
'''
    run(build(work,'waits',code,['-pthread']))
    assert 's_producerWaitUsTotal' not in gx.extract(s,'Stats takeStats()')
    assert 'return gxrt::s_producerWaitUsTotal' in s
    print('PASS: actual fast/spin/sleep producer waits retain a monotonic counter across interval resets')

def test_full_map(work,benchmark):
    path='Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp';sig='void HeightMapRenderObjClass::updateCenter('
    def prefix(old=False):
        body=gx.extract(source(path,old),sig)
        # Execute unchanged production preconditions/base call and whole-map branch.
        body=body[:body.index('\tconst Real cameraPitch =')]+ '\n}\n'
        if old:body=body.replace('void HeightMapRenderObjClass::updateCenter','void HeightMapRenderObjClass::legacy',1)
        return body
    code=r'''
#define __ANDROID__ 1
#include "GXPreRenderStats.h"
#include <cassert>
#include <cstdio>
#include <chrono>
#include <vector>
#include <algorithm>
using Int=int;
struct CameraClass{};struct Vector3{};struct RefRenderObjListIterator{};
struct GxTerrainCpuScope{GxTerrainCpuScope(int){}};
struct FakeMap{int x=65,y=49;int getXExtent(){return x;}int getYExtent(){return y;}};
struct BaseHeightMapRenderObjClass{bool m_needFullUpdate=true,m_updating=false;unsigned baseCalls=0,bridgeFull=0,treeVis=0,roadVis=0;
 void updateCenter(CameraClass*,const Vector3*,RefRenderObjListIterator*){++baseCalls;++treeVis;++roadVis;if(m_needFullUpdate)++bridgeFull;}
};
struct HeightMapRenderObjClass:BaseHeightMapRenderObjClass{
 FakeMap map;FakeMap*m_map=&map;void*m_vertexBufferTiles=this;int m_x=65,m_y=49;unsigned geometry=0;bool requestDuringUpdate=false;
 void updateCenter(CameraClass*,const Vector3*,RefRenderObjListIterator*);void legacy(CameraClass*,const Vector3*,RefRenderObjListIterator*);
 int updateBlock(int x0,int y0,int x1,int y1,FakeMap*p,RefRenderObjListIterator*){
  assert(x0==0&&y0==0&&x1==m_x-1&&y1==m_y-1&&p==m_map&&m_updating);++geometry;if(requestDuringUpdate)m_needFullUpdate=true;return 0;
 }
};
'''
    code+=prefix()+prefix(True)+r'''
static void view(HeightMapRenderObjClass&h,bool old){if(h.m_needFullUpdate){if(old)h.legacy(nullptr,nullptr,nullptr);else h.updateCenter(nullptr,nullptr,nullptr);}}
int main(){
 HeightMapRenderObjClass a,b;
 for(int i=0;i<1000;++i){view(a,true);view(b,false);}
 assert(a.baseCalls==1000 && a.bridgeFull==1000 && a.m_needFullUpdate);
 assert(b.baseCalls==1 && b.bridgeFull==1 && b.geometry==1 && !b.m_needFullUpdate && !b.m_updating);
 // New static lighting/time-of-day requests each apply exactly once.
 for(int i=0;i<7;++i){b.m_needFullUpdate=true;view(b,false);view(b,false);}
 assert(b.geometry==8 && b.bridgeFull==8);
 // Camera-driven center still performs tree/road/bridge visibility; no blanket skip.
 unsigned before=b.baseCalls;b.updateCenter(nullptr,nullptr,nullptr);assert(b.baseCalls==before+1&&b.geometry==8);
 // A fresh request raised during refresh must not be cleared by acknowledging the old one.
 b.requestDuringUpdate=true;b.m_needFullUpdate=true;view(b,false);assert(b.m_needFullUpdate&&!b.m_updating);
 b.requestDuringUpdate=false;view(b,false);assert(!b.m_needFullUpdate);
 b.m_needFullUpdate=true;b.m_vertexBufferTiles=nullptr;view(b,false);assert(b.m_needFullUpdate);
 b.m_vertexBufferTiles=&b;b.m_updating=true;view(b,false);assert(b.m_needFullUpdate);b.m_updating=false;view(b,false);assert(!b.m_needFullUpdate);
 b.m_needFullUpdate=true;auto*map=b.m_map;b.m_map=nullptr;view(b,false);assert(b.m_needFullUpdate);b.m_map=map;
 puts("PASS: production whole-map branch: 1000 repeated dirty refreshes -> 1; lighting retries, missing resources, camera ancillary updates preserved (host adapters)");
#ifdef BENCHMARK
 for(bool old:{true,false}){
  std::vector<double> frames;frames.reserve(20000);HeightMapRenderObjClass h;
  for(int i=0;i<20000;++i){
    auto start=std::chrono::steady_clock::now();view(h,old);
    auto end=std::chrono::steady_clock::now();frames.push_back(std::chrono::duration<double,std::micro>(end-start).count());
  }
  std::sort(frames.begin(),frames.end());
  printf("BENCH full-map-request %s P50us=%.6f P95us=%.6f refreshes=%u geometry=%u (production guard/branch with counting adapters, not game frame time)\n",old?"3486":"fixed",frames[9999],frames[18999],h.bridgeFull,h.geometry);
 }
#endif
}
'''
    run(build(work,'full-map',code))
    if benchmark:run(build(work,'full-map-bench',code,['-DBENCHMARK'],False))

def test_empty_bridges(work):
    path='GeneralsMD/Code/GameEngineDevice/Source/W3DDevice/GameClient/W3DBridgeBuffer.cpp'
    sig='void W3DBridgeBuffer::loadBridgesInVertexAndIndexBuffers('
    current=gx.extract(source(path),sig)
    old=gx.extract(source(path,True),sig).replace('W3DBridgeBuffer::loadBridgesInVertexAndIndexBuffers','W3DBridgeBuffer::legacy',1)
    code=r'''
#define __ANDROID__ 1
#include "GXPreRenderStats.h"
#include <vector>
#include <cassert>
#include <cstring>
using Int=int;using UnsignedShort=unsigned short;
constexpr int D3DLOCK_DISCARD=8192;
struct RefRenderObjListIterator{};
struct VertexFormatXYZNDUV1 {float x,y,z,nx,ny,nz;unsigned diffuse;float u,v;};
struct DX8VertexBufferClass {
 std::vector<VertexFormatXYZNDUV1> vertices=std::vector<VertexFormatXYZNDUV1>(12004);int locks=0;
 struct WriteLockClass {DX8VertexBufferClass*p;WriteLockClass(DX8VertexBufferClass*b,int flags):p(b){assert(flags==D3DLOCK_DISCARD);++p->locks;}void*Get_Vertex_Array(){return p->vertices.data();}};
};
struct DX8IndexBufferClass {
 std::vector<UnsignedShort> indices=std::vector<UnsignedShort>(24004);int locks=0;
 struct WriteLockClass {DX8IndexBufferClass*p;WriteLockClass(DX8IndexBufferClass*b,int flags):p(b){assert(flags==D3DLOCK_DISCARD);++p->locks;}UnsignedShort*Get_Index_Array(){return p->indices.data();}};
};
struct Bridge {int seed=0;void getIndicesNVertices(UnsignedShort*ib,VertexFormatXYZNDUV1*vb,int*ni,int*nv,RefRenderObjListIterator*){
 for(int i=0;i<3;++i){ib[(*ni)++]=*nv;vb[(*nv)++]={float(seed+i),float(i),3,0,0,1,unsigned(seed+17),.5f,.75f};}
}};
struct W3DBridgeBuffer {
 DX8IndexBufferClass ib;DX8VertexBufferClass vb;
 DX8IndexBufferClass*m_indexBridge=&ib;DX8VertexBufferClass*m_vertexBridge=&vb;
 bool m_initialized=true;int m_curNumBridgeVertices=0,m_curNumBridgeIndices=0,m_numBridges=0;
 Bridge m_bridges[2]={{1},{9}};
 void loadBridgesInVertexAndIndexBuffers(RefRenderObjListIterator*);void legacy(RefRenderObjListIterator*);
};
'''
    code+=current+'\n'+old+r'''
int main(){
 W3DBridgeBuffer a,b;
 for(int i=0;i<1000;++i){a.legacy(nullptr);b.loadBridgesInVertexAndIndexBuffers(nullptr);}
 assert(a.vb.locks==1000&&a.ib.locks==1000&&b.vb.locks==0&&b.ib.locks==0);
 for(int count:{1,2,0,2}){
  a.m_numBridges=b.m_numBridges=count;int locks=b.vb.locks;
  a.legacy(nullptr);b.loadBridgesInVertexAndIndexBuffers(nullptr);
  assert(a.m_curNumBridgeIndices==b.m_curNumBridgeIndices&&a.m_curNumBridgeVertices==b.m_curNumBridgeVertices);
  assert(!memcmp(a.vb.vertices.data(),b.vb.vertices.data(),a.vb.vertices.size()*sizeof(VertexFormatXYZNDUV1)));
  assert(a.ib.indices==b.ib.indices&&b.vb.locks==locks+int(count>0));
 }
 b.m_indexBridge=nullptr;int old=b.m_curNumBridgeIndices;b.loadBridgesInVertexAndIndexBuffers(nullptr);assert(old==b.m_curNumBridgeIndices);
 puts("PASS: production empty bridge batches avoid 2000 DISCARD locks; nonempty vertices/indices, transitions and flags match 3486 (no GPU upload/FPS claim)");
}
'''
    run(build(work,'bridge',code))

def benchmark_aggregation(work):
    code=r'''
#define GX_PRERTT_HOST_TEST 1
#include "GXPreRenderStats.h"
#include <vector>
#include <algorithm>
#include <cstdio>
#include <time.h>
static double hostCpu(){timespec t{};if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))return -1;return double(t.tv_sec)*1000000+double(t.tv_nsec)/1000;}
int main(){
 for(bool enabled:{false,true}){
  std::vector<double> times;times.reserve(1000);
  for(unsigned frame=0;frame<1000;++frame){
   double start=GXPreRTT::wallUs();
   {GXPreRTT::Frame root(enabled,0,false,frame,hostCpu);GXPreRTT::Scope views(GXPreRTT::Views,true);
    {GXPreRTT::Scope region(GXPreRTT::Region);
     for(int i=0;i<600;++i){GXPreRTT::Scope callback(GXPreRTT::Callbacks);GXPreRTT::ModuleScope module(i%12);}
    }
   }
   times.push_back(GXPreRTT::wallUs()-start);
  }
  std::sort(times.begin(),times.end());
  printf("BENCH aggregate-only %s scopes=600 P50us=%.3f P95us=%.3f (host profiler overhead, not game or device frame time)\n",enabled?"enabled":"disabled",times[499],times[949]);
 }
}
'''
    run(build(work,'profile-overhead',code,sanitize=False))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--benchmark',action='store_true');args=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='gx-prertt-') as temp:
        work=Path(temp)
        test_stats(work);test_trace(work);test_region(work);test_particles(work);test_waits(work);test_empty_bridges(work);test_full_map(work,args.benchmark)
        if args.benchmark:benchmark_aggregation(work)
    print('PASS: preRTT host regressions; real Android/mod frames, GPU, visuals and FPS NOT TESTED')
if __name__=='__main__':main()
