#!/usr/bin/env python3
"""Compile the actual GLES recovery and retained-resource invalidation methods.

Driver boundaries are injected. This is a host regression, not an Android
device/real driver context-loss test.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def extract(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    level, pos = 1, brace + 1
    while level:
        level += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos]


def main():
    pipeline = (ROOT / 'Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp').read_text()
    wrappers = (ROOT / 'Core/Libraries/Source/d3d8gles/src/d3d8gles.cpp').read_text()
    recovery = extract(pipeline, 'bool WebGLPipeline::recoverLostContext()')
    forget = extract(wrappers, 'static void forgetLostGpuObjectHandles()\n{')
    code = r'''
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <cstddef>
#include <unordered_map>
#include <unordered_set>
using GLsync=void*;
struct SDL_Window{};static SDL_Window window;
static void*currentContext=reinterpret_cast<void*>(1);
static void*SDL_GL_GetCurrentContext(){return currentContext;}
static bool s_gxGlesReady=true;
static std::atomic<bool> g_gpuResetPending{true};
static int simulatedDeletedFences=0,restoreCalls=0,initCalls=0,virtualBuilds=0;
static bool failPreparation=false,failInitialization=false;
struct GLTextureState {unsigned name=0;bool dirty=true;unsigned fbo=0;};
struct PersistentBufferSet {
 static constexpr int kMaxCopies=8;
 GLsync fences[kMaxCopies]={};
 int count=0;
};
struct GLBufferState {
 unsigned name=0;
 bool dirty=true;
 size_t dirtyBegin=(size_t)-1,dirtyEnd=0,writtenEnd=0,gpuRefEnd=0;
 bool allocated=false,pendingDiscard=false,pendingSync=false;
 PersistentBufferSet*persistent=nullptr;
};
static std::unordered_set<GLTextureState*>g_liveTextureGLStates;
static std::unordered_set<GLBufferState*>g_liveBufferGLStates;
namespace gxrt {
static bool prepareForContextRecovery(){return !failPreparation&&currentContext;}
static void forgetLostContextFences(){}
static void deleteSync(GLsync p){delete static_cast<int*>(p);++simulatedDeletedFences;}
static void resumeAfterContextRecovery(SDL_Window*){}
}
struct GpuFrameTimer {
 static constexpr int kQueries=4;
 bool ok=true,active=true,pending[kQueries]={true,true,true,true};
 void(*begin)()=nullptr,*end=nullptr,*get=nullptr;
 unsigned queries[kQueries]={1,2,3,4};
 int next=2;
 std::atomic<uint64_t>gpuNs{777};
 std::atomic<unsigned>frames{9};
};
static GpuFrameTimer s_gpuTimer;
struct ProgramInfo {static int deleted;~ProgramInfo(){++deleted;}};
int ProgramInfo::deleted=0;
struct WebGLPipeline {
 SDL_Window*m_window=&window;
 bool m_ctxReady=true,m_gpuRecoveryPending=false,m_adoptCurrentContext=false;
 bool m_needsFullClear=false,m_vbActive=true,m_vbGsr=true,m_vbUpscaled=true,m_vbBypass=true,m_vbSceneSeen=true;
 bool m_recoveryVirtualActive=false,m_recoveryGsr=false;
 int m_fbWidth=2340,m_fbHeight=1080,m_vbW=2340,m_vbH=1080,m_vbRW=1560,m_vbRH=720;
 int m_recoveryGameW=0,m_recoveryGameH=0,m_recoveryVirtualW=0,m_recoveryVirtualH=0,m_recoveryRenderW=0,m_recoveryRenderH=0;
 int m_curRTWidth=2340,m_curRTHeight=1080,m_depthRBW=512,m_depthRBH=512;
 unsigned m_depthRBGeneration=5,m_curFBO=111,m_depthRB=112,m_viewProjUBO=113,m_upVBO=114,m_upIBO=115;
 unsigned m_upRingVB=116,m_upRingIB=117,m_indexStream=118,m_vbFBO=119,m_vbTex=120,m_vbDepth=121;
 unsigned m_presentPlainProg=122,m_presentGsrProg=123,m_presentVAO=124;
 int m_presentPlainTex=1,m_presentGsrTex=2,m_presentGsrInfo=3;
 bool m_presentGsrTried=true,m_indexStreamFailed=true;
 size_t m_upRingVBOffset=99,m_upRingIBOffset=98,m_indexStreamOffset=97;
 unsigned char*m_indexStreamPtr=reinterpret_cast<unsigned char*>(0x1337);
 bool m_haveLastVAOKey=true,m_haveFixedStateKey=true,m_haveViewProjKey=true,m_haveTexMatKey=true,m_haveMiscKey=true,
      m_haveMaterialKey=true,m_haveLightingKey=true;
 unsigned m_lastProgram=11,m_lastArrayBuffer=12,m_lastBoundTex[2]={13,14};
 void*m_glDrawElementsBaseVertex=reinterpret_cast<void*>(1);
 void*m_glStencilOpSeparate=reinterpret_cast<void*>(1);
 void*m_glBufferStorage=reinterpret_cast<void*>(1);
 void*m_glFenceSync=reinterpret_cast<void*>(1);
 void*m_glClientWaitSync=reinterpret_cast<void*>(1);
 void*m_glDeleteSync=reinterpret_cast<void*>(1);
 void*m_glGetProgramBinary=reinterpret_cast<void*>(1);
 void*m_glProgramBinary=reinterpret_cast<void*>(1);
 void*m_glProgramParameteri=reinterpret_cast<void*>(1);
 bool m_persistentOK=true;
 std::string m_programCacheDir="previous";
 struct CacheEntry{ProgramInfo*prog=nullptr;};
 CacheEntry m_programs[8];
 int m_programCount=0;
 std::unordered_map<int,int>m_vaoCache;
 bool recoverLostContext();
 bool initContext(int w,int h,SDL_Window*) {
  ++initCalls;
  assert(m_adoptCurrentContext);
  m_adoptCurrentContext=false;
  assert(w==2340&&h==1080);
  if(failInitialization)return false;
  m_fbWidth=w;m_fbHeight=h;m_ctxReady=true;s_gxGlesReady=true;return true;
 }
 bool setVirtualBackbuffer(int w,int h,int rw,int rh,bool gsr) {
  ++virtualBuilds;
  assert(w==2340&&h==1080&&rw==1560&&rh==720&&gsr);
  m_vbActive=true;m_vbFBO=202;m_curFBO=202;
  return true;
 }
 bool refreshDrawable(bool restore){assert(!restore);return true;}
 void restoreSurface(){++restoreCalls;m_needsFullClear=true;}
};
'''
    code += '\n' + forget + '\n' + recovery + '\n'
    code += r'''
int main() {
 GLTextureState texture{42,false,43};
 GLBufferState vb;vb.name=71;vb.dirty=false;vb.allocated=true;vb.writtenEnd=1024;
 vb.persistent=new PersistentBufferSet();
 vb.persistent->count=2;
 vb.persistent->fences[0]=new int(1);
 vb.persistent->fences[1]=new int(2);
 g_liveTextureGLStates.insert(&texture);
 g_liveBufferGLStates.insert(&vb);
 WebGLPipeline p;
 p.m_programs[0].prog=new ProgramInfo();
 p.m_programCount=1;
 p.m_vaoCache[4]=5;
 failPreparation=true;
 assert(!p.recoverLostContext()&&!p.m_gpuRecoveryPending);
 assert(texture.name==42&&vb.name==71&&p.m_programCount==1);
 failPreparation=false;
 failInitialization=true;
 assert(!p.recoverLostContext()&&p.m_gpuRecoveryPending);
 assert(!p.m_ctxReady&&texture.name==0&&texture.fbo==0&&texture.dirty);
 assert(vb.name==0&&vb.dirty&&!vb.allocated&&vb.writtenEnd==1024&&!vb.persistent);
 assert(simulatedDeletedFences==2&&ProgramInfo::deleted==1&&p.m_programCount==0);
 assert(p.m_vaoCache.empty()&&p.m_viewProjUBO==0&&p.m_vbFBO==0);
 assert(!s_gpuTimer.ok&&!s_gpuTimer.active&&s_gpuTimer.gpuNs==0);
 const int deleted=simulatedDeletedFences;
 failInitialization=false;
 assert(p.recoverLostContext());
 assert(!p.m_gpuRecoveryPending&&p.m_ctxReady&&p.m_vbActive&&p.m_curFBO==202);
 assert(p.m_needsFullClear&&!g_gpuResetPending&&s_gxGlesReady);
 assert(p.m_fbWidth==2340&&p.m_fbHeight==1080);
 assert(simulatedDeletedFences==deleted); // retry must not release twice
 assert(virtualBuilds==1&&restoreCalls==1);
 for(int i=0;i<100;++i) {
  currentContext=reinterpret_cast<void*>(uintptr_t(i+100));
  texture.name=4;texture.fbo=7;texture.dirty=false;
  vb.name=8;vb.dirty=false;vb.allocated=true;
  vb.persistent=new PersistentBufferSet();
  vb.persistent->count=1;
  vb.persistent->fences[0]=new int(i);
  p.m_ctxReady=true;
  g_gpuResetPending=true;
  assert(p.recoverLostContext());
  assert(texture.dirty&&texture.name==0&&texture.fbo==0);
  assert(vb.dirty&&vb.name==0&&!vb.allocated&&vb.writtenEnd==1024);
  assert(p.m_ctxReady&&!p.m_gpuRecoveryPending&&p.m_needsFullClear);
 }
 assert(simulatedDeletedFences==102);
 assert(virtualBuilds==101&&restoreCalls==101);
 puts("PASS: production GPU resource invalidation, retries, retained CPU bytes, 100 reconstructions");
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-gpu-recovery-') as tmp:
        source, binary = Path(tmp)/'test.cpp', Path(tmp)/'test'
        source.write_text(code.replace('#include <unordered_set>', '#include <unordered_set>\n#include <string>'))
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror','-O1','-g',
                        '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                        str(source),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1'})


if __name__ == '__main__':
    main()
