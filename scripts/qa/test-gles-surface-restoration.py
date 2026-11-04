#!/usr/bin/env python3
"""Exercise GLES drawable restoration and viewport production code on the host.

Usage: python3 scripts/qa/test-gles-surface-restoration.py [--source-ref REF]
Only SDL/GL driver boundaries are faked. This is not Android or GPU validation.
Environment: CXX selects the host C++ compiler (default: c++).
"""
# GeneralsX @bugfix Codex 04/11/2026 Regression coverage for physical drawable restoration.
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def extract(source, signature):
    start = source.index(signature)
    pos = source.index('{', start)
    depth, end = 1, pos + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', help='Exercise a Git revision, including the pre-fix revision.')
    args = parser.parse_args()
    path = 'Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp'
    pipeline = (subprocess.check_output(['git', 'show', args.source_ref + ':' + path], cwd=ROOT, text=True)
                if args.source_ref else (ROOT / path).read_text())
    code = r'''
#include <array>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <vector>
using GLint=int;using GLuint=unsigned;using GLenum=unsigned;using GLsizei=int;using DWORD=unsigned;using GLbitfield=unsigned;
constexpr unsigned GL_FRAMEBUFFER=1,GL_SCISSOR_TEST=2,GL_BLEND=3,GL_DEPTH_TEST=4,GL_STENCIL_TEST=5;
constexpr unsigned GL_CULL_FACE=6,GL_TEXTURE0=7,GL_TEXTURE_2D=8,GL_TRIANGLES=9,GL_TRUE=1;
constexpr unsigned D3DCLEAR_TARGET=1,D3DCLEAR_ZBUFFER=2,D3DCLEAR_STENCIL=4;
constexpr unsigned GL_COLOR_BUFFER_BIT=1,GL_DEPTH_BUFFER_BIT=2,GL_STENCIL_BUFFER_BIT=4;
constexpr unsigned GL_RGBA=20,GL_UNSIGNED_BYTE=21,GL_TEXTURE_MIN_FILTER=22,GL_TEXTURE_MAG_FILTER=23;
constexpr unsigned GL_TEXTURE_WRAP_S=24,GL_TEXTURE_WRAP_T=25,GL_LINEAR=26,GL_CLAMP_TO_EDGE=27;
constexpr unsigned GL_RENDERBUFFER=28,GL_DEPTH24_STENCIL8=29,GL_COLOR_ATTACHMENT0=30;
constexpr unsigned GL_DEPTH_STENCIL_ATTACHMENT=31,GL_FRAMEBUFFER_COMPLETE=32;
struct SDL_Window{};static SDL_Window window;
static int drawableW=2340,drawableH=1080,queries=0;static bool queryOK=true;
static bool SDL_GetWindowSizeInPixels(SDL_Window*w,int*x,int*y){assert(w==&window);++queries;*x=drawableW;*y=drawableH;return queryOK;}
static const char*SDL_GetError(){return "injected query failure";}
namespace gxrt {
static bool queued=false;static unsigned drains=0;static std::vector<std::function<void()>> commands;
static void ensureContext(SDL_Window*w,void*){assert(w==&window);}
static void drain(){++drains;auto pending=std::move(commands);commands.clear();for(auto&f:pending)f();}
template<class F>void post(F f){if(queued)commands.push_back(f);else f();}
template<class F>void sync(F f){drain();f();}
}
static unsigned boundFBO=0,drawCalls=0,bindCalls=0;
static std::array<int,4> viewport{};static bool scissor=false;
static void glBindFramebuffer(unsigned target,unsigned fbo){assert(target==GL_FRAMEBUFFER);gxrt::post([fbo]{++bindCalls;boundFBO=fbo;});}
static void glViewport(int x,int y,int w,int h){gxrt::post([=]{viewport={x,y,w,h};});}
static void glDisable(unsigned cap){gxrt::post([cap]{if(cap==GL_SCISSOR_TEST)scissor=false;});}
static std::array<int,4> scissorRect{};static unsigned clearCalls=0,lastClearMask=0;
static bool clearWasScissored=false,colorWrite=false,depthWrite=false;static unsigned stencilWrite=0;
static void glColorMask(unsigned r,unsigned g,unsigned b,unsigned a){gxrt::post([=]{colorWrite=r&&g&&b&&a;});}
static void glEnable(unsigned cap){gxrt::post([cap]{if(cap==GL_SCISSOR_TEST)scissor=true;});}
static void glScissor(int x,int y,int w,int h){gxrt::post([=]{scissorRect={x,y,w,h};});}
static void glClearColor(float,float,float,float){}
static void glDepthMask(unsigned mask){gxrt::post([mask]{depthWrite=mask;});}
static void glClearDepthf(float){}
static void glStencilMask(unsigned mask){gxrt::post([mask]{stencilWrite=mask;});}
static void glClearStencil(int){}
static void glClear(unsigned mask){gxrt::post([mask]{
 ++clearCalls;lastClearMask=mask;clearWasScissored=scissor;
 if(mask&GL_COLOR_BUFFER_BIT)assert(colorWrite);
 if(mask&GL_DEPTH_BUFFER_BIT)assert(depthWrite);
 if(mask&GL_STENCIL_BUFFER_BIT)assert(stencilWrite==~0u);
});}
static void glUseProgram(unsigned){}
static void glActiveTexture(unsigned){}
static void glBindTexture(unsigned,unsigned){}
static void glUniform1i(int,int){}
static void glUniform4f(int,float,float,float,float){}
static void glBindVertexArray(unsigned){}
static void glDrawArrays(unsigned,int,int){gxrt::post([]{++drawCalls;assert(boundFBO==0);assert(!scissor);});}
static unsigned allocations=0,textureStorage=0,depthStorage=0,programBuilds=0,nextName=100;
static std::array<int,2> textureSize{},depthSize{};
static void genObjects(int count,unsigned*names){for(int i=0;i<count;++i){names[i]=nextName++;++allocations;}}
static void glGenFramebuffers(int n,unsigned*p){genObjects(n,p);}
static void glGenTextures(int n,unsigned*p){genObjects(n,p);}
static void glGenRenderbuffers(int n,unsigned*p){genObjects(n,p);}
static void glGenVertexArrays(int n,unsigned*p){genObjects(n,p);}
static void glTexImage2D(unsigned,int,int,int w,int h,int,unsigned,unsigned,const void*){
 gxrt::post([=]{++textureStorage;textureSize={w,h};});
}
static void glTexParameteri(unsigned,unsigned,int){}
static void glBindRenderbuffer(unsigned,unsigned){}
static void glRenderbufferStorage(unsigned,unsigned,int w,int h){gxrt::post([=]{++depthStorage;depthSize={w,h};});}
static void glFramebufferTexture2D(unsigned,unsigned,unsigned,unsigned,int){}
static void glFramebufferRenderbuffer(unsigned,unsigned,unsigned,unsigned){}
static unsigned glCheckFramebufferStatus(unsigned){gxrt::drain();return GL_FRAMEBUFFER_COMPLETE;}
static const char*kPresentVs300="vs300",*kPresentPlainFs="plain",*kPresentVs310="vs310",*kPresentGsrFs="gsr";
static unsigned buildPresentProgram(const char*,const char*){++programBuilds;return nextName++;}
static int glGetUniformLocation(unsigned,const char*){return 1;}
struct D3DVIEWPORT8 {DWORD X=0,Y=0,Width=0,Height=0;float MinZ=0,MaxZ=1;};
class WebGLDevice {public:D3DVIEWPORT8 viewport{0,900,2340,180,0,1};const D3DVIEWPORT8&getViewport(){return viewport;}};
class WebGLPipeline {public:
 SDL_Window*m_window=&window;void*m_glContext=nullptr;bool m_ctxReady=true;
 bool m_vbActive=false,m_vbGsr=false,m_vbUpscaled=false,m_vbBypass=false,m_vbSceneSeen=false;
 int m_winW=2340,m_winH=1080,m_vbW=2340,m_vbH=1080,m_vbRW=1170,m_vbRH=540;
 int m_fbWidth=2340,m_fbHeight=1080,m_curRTWidth=2340,m_curRTHeight=1080;
 unsigned m_curFBO=0,m_vbFBO=9,m_vbTex=10,m_vbDepth=12,m_presentVAO=11;bool m_presentGsrTried=false;
 unsigned m_presentGsrProg=12,m_presentPlainProg=13;int m_presentGsrTex=1,m_presentPlainTex=2,m_presentGsrInfo=3;
 bool m_haveFixedStateKey=true,m_haveLastVAOKey=true,m_needsFullClear=false;D3DVIEWPORT8 m_vbFullVp{};
 unsigned m_lastProgram=7,m_lastArrayBuffer=8,m_lastBoundTex[2]={9,10};
 void resize(int,int);
 void setBackbufferSize(int,int);
 bool setVirtualBackbuffer(int,int,int,int,bool);
 REFRESH_DECL
 void restoreSurface();
 void targetRect(const D3DVIEWPORT8&,GLint*,GLint*,GLsizei*,GLsizei*)const;
 void stretchVirtualBackbuffer();
 const D3DVIEWPORT8&effectiveViewport(WebGLDevice*);
 void clear(WebGLDevice*,unsigned,uint32_t,float,unsigned);
};
'''
    # Extract includes the return type when selecting from the line start.
    start = pipeline.rfind('\n', 0, pipeline.index('WebGLPipeline::refreshDrawable(')) + 1
    refresh = extract(pipeline, pipeline[start:pipeline.index('WebGLPipeline::refreshDrawable(')] + 'WebGLPipeline::refreshDrawable(')
    declaration = refresh.split('{', 1)[0].strip().replace('WebGLPipeline::', '') + ';'
    code = code.replace('REFRESH_DECL', declaration)
    code += extract(pipeline, 'static void argbToFloats(') + '\n'
    for signature in ('const D3DVIEWPORT8 &WebGLPipeline::effectiveViewport(', 'void WebGLPipeline::clear(', 'void WebGLPipeline::resize(', 'void WebGLPipeline::setBackbufferSize(', 'bool WebGLPipeline::setVirtualBackbuffer(', 'void WebGLPipeline::restoreSurface(',
                      'void WebGLPipeline::targetRect(', 'void WebGLPipeline::stretchVirtualBackbuffer('):
        code += extract(pipeline, signature) + '\n'
    code += refresh + '\n'
    code += r'''
static std::array<int,4> rect(WebGLPipeline&p,D3DVIEWPORT8 vp){
 std::array<int,4>r{};p.targetRect(vp,&r[0],&r[1],&r[2],&r[3]);return r;
}
static void run(bool queued){
 gxrt::queued=queued;gxrt::commands.clear();queries=0;bindCalls=drawCalls=0;gxrt::drains=0;
 drawableW=2340;drawableH=1080;queryOK=true;
 WebGLPipeline p;
 const D3DVIEWPORT8 full{0,0,2340,1080,0,1},commandBar{0,900,2340,180,0,1};
 p.resize(0,0);p.resize(-1,1080);assert(p.m_winW==2340&&p.m_winH==1080);
 assert(p.m_haveFixedStateKey);
 const auto base=rect(p,commandBar);
 assert((base==std::array<int,4>{0,0,2340,180}));
 // Repeated lifecycle events with an unchanged drawable do not change logical coordinates.
 for(int i=0;i<3;++i){p.refreshDrawable(false);assert(p.m_winW==2340);}
 assert(p.m_haveFixedStateKey&&bindCalls==0&&gxrt::commands.empty());
 // Invalid and transient portrait sizes must preserve the last usable landscape drawable.
 for(auto wh:std::vector<std::array<int,2>>{{0,0},{0,1080},{-1,1080},{1080,2340}}){
  drawableW=wh[0];drawableH=wh[1];p.refreshDrawable(false);assert(p.m_winW==2340&&p.m_winH==1080);
 }
 queryOK=false;drawableW=2400;drawableH=1080;p.refreshDrawable(false);assert(p.m_winW==2340);queryOK=true;
 // The real physical drawable, not logical event dimensions, controls presentation.
 drawableW=2400;drawableH=1200;p.refreshDrawable(false);
 assert(p.m_winW==2400&&p.m_winH==1200&&!p.m_haveFixedStateKey);
 assert(p.m_fbWidth==2340&&p.m_fbHeight==1080&&p.m_curRTWidth==2340&&p.m_curRTHeight==1080);
 assert((rect(p,full)==std::array<int,4>{0,0,2400,1200}));
 auto bar=rect(p,commandBar);assert(bar[0]==0&&bar[1]==0&&bar[2]==2400&&bar[3]==200);
 // Adjacent UI rectangles stay adjacent through scaling and bottom-origin conversion.
 auto top=rect(p,{0,0,2340,900,0,1});assert(top[1]==bar[3]&&top[3]+bar[3]==1200);
 // Offscreen texture targets keep their own size through drawable changes.
 p.m_curFBO=44;p.m_curRTHeight=512;
 assert((rect(p,{10,20,100,30,0,1})==std::array<int,4>{10,462,100,30}));
 p.m_curFBO=p.m_vbFBO;p.m_curRTHeight=1080;p.m_vbActive=true;
 assert((rect(p,commandBar)==std::array<int,4>{0,0,1170,90}));
 p.refreshDrawable(false);assert(p.m_vbW==2340&&p.m_vbH==1080&&p.m_vbRW==1170&&p.m_vbRH==540);
 // Menus and the already-upscaled UI use the window FBO with the same logical coordinate space.
 p.m_curFBO=0;p.m_vbUpscaled=true;p.m_vbBypass=true;
 assert((rect(p,full)==std::array<int,4>{0,0,2400,1200}));
 assert((rect(p,commandBar)==std::array<int,4>{0,0,2400,200}));
 p.m_curFBO=p.m_vbFBO;p.m_vbUpscaled=p.m_vbBypass=false;
 // A surface restoration drains prior commands and rebinds the intended surviving FBO.
 boundFBO=99;gxrt::post([]{boundFBO=55;});const unsigned before=gxrt::drains;
 p.refreshDrawable(true);gxrt::drain();
 assert(gxrt::drains>before&&boundFBO==p.m_vbFBO);
 assert(p.m_lastProgram==0&&!p.m_haveFixedStateKey&&!p.m_haveLastVAOKey);
 assert(p.m_lastArrayBuffer==~0u&&p.m_lastBoundTex[0]==~0u&&p.m_lastBoundTex[1]==~0u);
 assert(p.m_needsFullClear);
 // An offscreen effect clear must not consume the resumed backbuffer's full-clear request.
 WebGLDevice dev;p.m_curFBO=44;p.m_curRTHeight=512;
 p.clear(&dev,D3DCLEAR_TARGET,0,1,0);gxrt::drain();assert(p.m_needsFullClear);
 // The first resumed backbuffer clear must override a partial viewport and stale scissor/masks.
 p.m_curFBO=p.m_vbFBO;p.m_curRTHeight=1080;
 scissor=true;colorWrite=depthWrite=false;stencilWrite=0;
 p.clear(&dev,D3DCLEAR_TARGET,0,1,0);gxrt::drain();
 assert(!p.m_needsFullClear&&!clearWasScissored&&lastClearMask==7);
 // Later partial clears retain normal game viewport semantics and requested buffers.
 p.clear(&dev,D3DCLEAR_TARGET,0,1,0);gxrt::drain();
 assert(clearWasScissored&&lastClearMask==GL_COLOR_BUFFER_BIT);
 assert((scissorRect==std::array<int,4>{0,0,1170,90}));
 // A regular full viewport clear also must disable any stale scissor before clearing.
 dev.viewport=full;scissor=true;p.clear(&dev,D3DCLEAR_TARGET,0,1,0);gxrt::drain();
 assert(!clearWasScissored&&lastClearMask==GL_COLOR_BUFFER_BIT);
 // Upscaling after resume fills the new drawable and disables stale clipping.
 for(bool gsr:{false,true}){
  p.m_vbGsr=gsr;scissor=true;p.stretchVirtualBackbuffer();gxrt::drain();
  assert((viewport==std::array<int,4>{0,0,2400,1200}));assert(boundFBO==0&&!scissor);
 }
 assert(drawCalls==2);
 // A changed default drawable also requests a complete clear without requiring a resume event.
 WebGLPipeline direct;WebGLDevice directDev;directDev.viewport=full;
 direct.resize(2400,1200);assert(direct.m_needsFullClear);
 scissor=true;direct.clear(&directDev,D3DCLEAR_TARGET,0,1,0);gxrt::drain();
 assert(!direct.m_needsFullClear&&!clearWasScissored&&lastClearMask==7);
 assert(direct.m_fbWidth==2340&&direct.m_fbHeight==1080);
 direct.resize(2400,1200);assert(!direct.m_needsFullClear);
 // Explicit D3D Reset changes logical dimensions; physical resume/resize never does.
 drawableW=2400;drawableH=1200;direct.setBackbufferSize(1280,720);
 assert(direct.m_fbWidth==1280&&direct.m_fbHeight==720&&direct.m_curRTWidth==1280&&direct.m_curRTHeight==720);
 assert(direct.m_winW==2400&&direct.m_winH==1200);
 direct.setBackbufferSize(0,0);assert(direct.m_fbWidth==1280&&direct.m_fbHeight==720);
 // Exercise actual virtual resource setup, reuse and disable with only GL driver operations injected.
 WebGLPipeline v;v.m_vbFBO=v.m_vbTex=v.m_vbDepth=v.m_presentVAO=0;
 v.m_presentPlainProg=v.m_presentGsrProg=0;v.resize(2400,1200);
 allocations=textureStorage=depthStorage=programBuilds=0;
 assert(v.setVirtualBackbuffer(2340,1080,1170,540,false));gxrt::drain();
 assert(v.m_vbActive&&v.m_curFBO==v.m_vbFBO&&allocations==4&&programBuilds==1);
 assert((textureSize==std::array<int,2>{1170,540})&&depthSize==textureSize);
 const auto objectAllocations=allocations;const auto programs=programBuilds;
 const auto texAllocations=textureStorage,depthAllocations=depthStorage;
 for(int i=0;i<5;++i){
  drawableW=(i%2)?2400:2340;drawableH=1080;v.refreshDrawable(true);
  assert(v.setVirtualBackbuffer(2340,1080,1170,540,false));gxrt::drain();
 }
 assert(allocations==objectAllocations&&programBuilds==programs);
 assert(textureStorage==texAllocations&&depthStorage==depthAllocations);
 // Changing virtual render quality reallocates storage exactly once while reusing object IDs.
 const auto originalFBO=v.m_vbFBO,originalTexture=v.m_vbTex,originalDepth=v.m_vbDepth;
 assert(v.setVirtualBackbuffer(2340,1080,1560,720,false));gxrt::drain();
 assert(textureStorage==texAllocations+1&&depthStorage==depthAllocations+1);
 assert(v.m_vbFBO==originalFBO&&v.m_vbTex==originalTexture&&v.m_vbDepth==originalDepth);
 assert(allocations==objectAllocations);
 drawableW=2400;drawableH=1200;v.refreshDrawable(false);
 // Disabling virtual rendering after a physical size change keeps game/UI/touch resolution.
 assert(!v.setVirtualBackbuffer(0,0,0,0,false));gxrt::drain();
 assert(!v.m_vbActive&&v.m_curFBO==0&&boundFBO==0);
 assert(v.m_fbWidth==2340&&v.m_fbHeight==1080&&v.m_curRTWidth==2340&&v.m_curRTHeight==1080);
 assert(v.m_winW==2400&&v.m_winH==1200);
 assert((rect(v,full)==std::array<int,4>{0,0,2400,1200}));
 assert(v.setVirtualBackbuffer(2340,1080,1560,720,false));gxrt::drain();
 v.setBackbufferSize(1920,1080);assert(v.m_fbWidth==1920&&v.m_fbHeight==1080);
 assert(v.m_winW==2400&&v.m_winH==1200);
 assert(v.setVirtualBackbuffer(1920,1080,1280,720,false));gxrt::drain();
 assert(v.m_fbWidth==1920&&v.m_vbW==1920&&v.m_curRTWidth==1920);
 // Rapid app switches, including repeated resume and size changes, retain logical state.
 for(int i=0;i<100;++i){
  drawableW=(i%2)?2340:2400;drawableH=1080;p.refreshDrawable(true);gxrt::drain();
  assert(p.m_winW==drawableW&&p.m_winH==drawableH);
  assert(p.m_fbWidth==2340&&p.m_fbHeight==1080&&p.m_vbW==2340&&p.m_vbH==1080);
  assert(boundFBO==p.m_vbFBO);
 }
 printf("PASS: %s production drawable resize/resume, FBO state, virtual allocation/reuse/disable, UI viewport and 100 rapid switches\n",queued?"queued":"immediate");
}
int main(){run(false);run(true);}
'''
    with tempfile.TemporaryDirectory(prefix='gx-surface-restoration-') as temp:
        work = Path(temp)
        source, exe = work / 'test.cpp', work / 'test'
        source.write_text(code)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-D__ANDROID__', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(source), '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], capture_output=True, text=True,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1'))
        print(result.stdout, end='')
        if result.returncode:
            print(result.stderr, end='')
            result.check_returncode()


if __name__ == '__main__':
    main()
