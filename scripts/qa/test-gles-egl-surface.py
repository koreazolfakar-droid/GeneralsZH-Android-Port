#!/usr/bin/env python3
"""Validate extracted production GLES restoration against a real host EGL pbuffer.

Usage: python3 scripts/qa/test-gles-egl-surface.py --headers PATH
PATH contains EGL/, GLES3/ and KHR/ (system SDK or an Android NDK sysroot).
Environment: CXX selects the host C++ compiler; ANDROID_NDK_HOME can supply headers.
A missing EGL/GLES3 host driver is reported as SKIP, never device validation.
"""
# GeneralsX @bugfix Codex 04/11/2026 Check real framebuffer pixels after surface recreation.
import argparse
import os
from pathlib import Path
import shutil
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
    parser.add_argument('--headers', type=Path, help='Directory containing EGL, GLES3 and KHR headers.')
    parser.add_argument('--require-egl', action='store_true', help='Treat missing host EGL capability as a failure.')
    args = parser.parse_args()
    headers = args.headers
    if not headers and os.environ.get('ANDROID_NDK_HOME'):
        candidates = list((Path(os.environ['ANDROID_NDK_HOME']) / 'toolchains/llvm/prebuilt').glob('*/sysroot/usr/include'))
        if candidates:
            headers = candidates[0]
    headers = headers or Path('/usr/include')
    if not all((headers / folder).is_dir() for folder in ('EGL', 'GLES3', 'KHR')):
        if args.require_egl:
            raise SystemExit('FAIL: EGL/GLES3 headers unavailable; pass --headers PATH')
        print('SKIP: EGL/GLES3 headers unavailable; pass --headers PATH')
        return
    pipeline = (ROOT / 'Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp').read_text()
    egl = ('eglGetProcAddress eglGetPlatformDisplay eglInitialize eglBindAPI eglChooseConfig '
           'eglCreateContext eglCreatePbufferSurface eglMakeCurrent eglDestroySurface '
           'eglDestroyContext eglTerminate eglQuerySurface eglGetCurrentContext eglGetCurrentSurface').split()
    gl = ('glBindFramebuffer glEnable glDisable glScissor glColorMask glClearColor glDepthMask '
          'glClearDepthf glStencilMask glClearStencil glClear glReadPixels glGetError glGetString '
          'glGenTextures glBindTexture glTexImage2D glIsTexture glDeleteTextures '
          'glGenFramebuffers glFramebufferTexture2D glCheckFramebufferStatus glDeleteFramebuffers').split()
    code = r'''
#define ANDROID 1
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#undef ANDROID
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <dlfcn.h>
#include <vector>
'''
    code += '\n'.join(f'static decltype(&{name}) p_{name}=nullptr;' for name in egl + gl) + '\n'
    code += '\n'.join(f'#define {name} p_{name}' for name in egl + gl) + '\n'
    code += r'''
static bool loadDriver(){
 void*lib=dlopen("libEGL.so.1",RTLD_NOW|RTLD_LOCAL);if(!lib){puts("SKIP: libEGL.so.1 unavailable");return false;}
'''
    code += '\n'.join(f' p_{name}=reinterpret_cast<decltype(p_{name})>(dlsym(lib,"{name}"));if(!p_{name})return false;' for name in egl)
    code += '\n' + '\n'.join(f' p_{name}=reinterpret_cast<decltype(p_{name})>(eglGetProcAddress("{name}"));if(!p_{name})return false;' for name in gl)
    code += r'''
 return true;
}
static EGLDisplay display=EGL_NO_DISPLAY;static EGLSurface surface=EGL_NO_SURFACE;
static EGLContext context=EGL_NO_CONTEXT;static EGLConfig config;
static std::atomic<bool> g_gpuResetPending{false};
struct SDL_Window{};static SDL_Window window;
static bool SDL_GetWindowSizeInPixels(SDL_Window*w,int*x,int*y){
 assert(w==&window);return eglQuerySurface(display,surface,EGL_WIDTH,x)&&eglQuerySurface(display,surface,EGL_HEIGHT,y);
}
namespace gxrt {
template<class F>void sync(F f){f();}
static bool contextReplaced(){return false;}
static void ensureContext(SDL_Window*w,void*expected){
 assert(w==&window&&eglGetCurrentContext()==expected&&eglGetCurrentSurface(EGL_DRAW)==surface);
}
}
using DWORD=unsigned;
constexpr unsigned D3DCLEAR_TARGET=1,D3DCLEAR_ZBUFFER=2,D3DCLEAR_STENCIL=4;
struct D3DVIEWPORT8{DWORD X=0,Y=0,Width=234,Height=108;float MinZ=0,MaxZ=1;};
struct WebGLDevice {D3DVIEWPORT8 viewport;const D3DVIEWPORT8&getViewport(){return viewport;}};
class WebGLPipeline {public:
 SDL_Window*m_window=&window;void*m_glContext=nullptr;bool m_ctxReady=true,m_needsFullClear=false,m_gpuRecoveryPending=false;
 bool recoverLostContext(){return false;}
 bool m_vbActive=false;int m_winW=234,m_winH=108,m_fbWidth=234,m_fbHeight=108;
 int m_curRTWidth=234,m_curRTHeight=108,m_vbW=234,m_vbH=108,m_vbRW=117,m_vbRH=54;
 unsigned m_curFBO=0,m_vbFBO=0,m_lastProgram=0,m_lastArrayBuffer=0,m_lastBoundTex[2]{};
 bool m_haveFixedStateKey=false,m_haveLastVAOKey=false;D3DVIEWPORT8 m_vbFullVp;
 void resize(int,int);bool refreshDrawable(bool);void restoreSurface();
 void targetRect(const D3DVIEWPORT8&,GLint*,GLint*,GLsizei*,GLsizei*)const;
 const D3DVIEWPORT8&effectiveViewport(WebGLDevice*);
 void clear(WebGLDevice*,unsigned,uint32_t,float,unsigned);
};
'''
    for signature in ('static void argbToFloats(', 'void WebGLPipeline::resize(',
                      'bool WebGLPipeline::refreshDrawable(', 'void WebGLPipeline::restoreSurface(',
                      'void WebGLPipeline::targetRect(', 'const D3DVIEWPORT8 &WebGLPipeline::effectiveViewport(',
                      'void WebGLPipeline::clear('):
        code += extract(pipeline, signature) + '\n'
    code += r'''
static void replaceSurface(int w,int h){
 assert(eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT));
 if(surface!=EGL_NO_SURFACE)assert(eglDestroySurface(display,surface));
 const EGLint attrs[]={EGL_WIDTH,w,EGL_HEIGHT,h,EGL_NONE};
 surface=eglCreatePbufferSurface(display,config,attrs);assert(surface!=EGL_NO_SURFACE);
 assert(eglMakeCurrent(display,surface,surface,context));
 assert(eglGetCurrentContext()==context);
}
static void expectPixels(int w,int h,int boundary){
 std::vector<unsigned char>pixels(w*h*4);glReadPixels(0,0,w,h,GL_RGBA,GL_UNSIGNED_BYTE,pixels.data());
 for(int y=0;y<h;++y)for(int x=0;x<w;++x){
  const auto*p=&pixels[(y*w+x)*4];
  assert(p[0]==(y<boundary?255:0)&&p[1]==(y<boundary?0:255)&&p[2]==0&&p[3]==255);
 }
 assert(glGetError()==GL_NO_ERROR);
}
int main(){
 if(!loadDriver()){puts("SKIP: EGL/GLES3 entry points unavailable");return 77;}
 display=eglGetPlatformDisplay(0x31DD /* EGL_PLATFORM_SURFACELESS_MESA */,nullptr,nullptr);
 EGLint major=0,minor=0;
 if(display==EGL_NO_DISPLAY||!eglInitialize(display,&major,&minor)){puts("SKIP: surfaceless host EGL unavailable");return 77;}
 assert(eglBindAPI(EGL_OPENGL_ES_API));
 const EGLint configAttrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,
  EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_DEPTH_SIZE,24,EGL_STENCIL_SIZE,8,EGL_NONE};
 EGLint count=0;
 if(!eglChooseConfig(display,configAttrs,&config,1,&count)||count<1){puts("SKIP: GLES3 pbuffer config unavailable");return 77;}
 const EGLint contextAttrs[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
 context=eglCreateContext(display,config,EGL_NO_CONTEXT,contextAttrs);
 if(context==EGL_NO_CONTEXT){puts("SKIP: host GLES3 context unavailable");return 77;}
 replaceSurface(234,108);
 printf("Host EGL %d.%d, GLES renderer: %s\n",major,minor,glGetString(GL_RENDERER));
 GLuint texture=0;glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
 const unsigned char texel[4]={255,255,0,255};glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,texel);
 GLuint textureFBO=0;glGenFramebuffers(1,&textureFBO);glBindFramebuffer(GL_FRAMEBUFFER,textureFBO);
 glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
 assert(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE);
 WebGLPipeline p;p.m_glContext=context;WebGLDevice dev;
 for(int cycle=0;cycle<12;++cycle){
  const int w=(cycle%3==0)?234:240,h=(cycle%3==0)?108:120;
  replaceSurface(w,h);assert(glIsTexture(texture));
  glBindFramebuffer(GL_FRAMEBUFFER,textureFBO);unsigned char saved[4]={};
  glReadPixels(0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,saved);
  for(int channel=0;channel<4;++channel)assert(saved[channel]==texel[channel]);
  // The renderer must restore its own FBO after SDL/EGL and unrelated GL bindings.
  assert(p.refreshDrawable(true));
  assert(p.m_winW==w&&p.m_winH==h&&p.m_fbWidth==234&&p.m_fbHeight==108);
  // Simulate hostile stale clipping and write masks inherited at the surface boundary.
  glEnable(GL_SCISSOR_TEST);glScissor(0,0,1,1);glColorMask(GL_FALSE,GL_FALSE,GL_FALSE,GL_FALSE);
  glDepthMask(GL_FALSE);glStencilMask(0);
  dev.viewport={0,90,234,18,0,1};p.clear(&dev,D3DCLEAR_TARGET,0xff0000ff,1,0);
  // Production resumed clear must initialize every pixel blue despite the partial UI viewport.
  std::vector<unsigned char>blue(w*h*4);glReadPixels(0,0,w,h,GL_RGBA,GL_UNSIGNED_BYTE,blue.data());
  for(int pixel=0;pixel<w*h;++pixel)assert(blue[pixel*4]==0&&blue[pixel*4+1]==0&&blue[pixel*4+2]==255&&blue[pixel*4+3]==255);
  // Actual production targetRect/scissor conversions must leave no gaps between HUD and scene.
  p.clear(&dev,D3DCLEAR_TARGET,0xffff0000,1,0);
  dev.viewport={0,0,234,90,0,1};p.clear(&dev,D3DCLEAR_TARGET,0xff00ff00,1,0);
  expectPixels(w,h,h/6);
  assert(!p.m_needsFullClear);
 }
 glDeleteFramebuffers(1,&textureFBO);glDeleteTextures(1,&texture);
 assert(eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT));
 assert(eglDestroySurface(display,surface));assert(eglDestroyContext(display,context));assert(eglTerminate(display));
 puts("PASS: real host EGL/GLES3 pixels, 12 recreated surfaces, preserved texture, full clears and contiguous UI regions");
 puts("Host software-driver validation only; Android SDL/EGL lifecycle and physical device remain unverified.");
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-egl-surface-') as temp:
        work = Path(temp)
        # Copy only Khronos headers so Android libc headers cannot shadow host libc.
        for folder in ('EGL', 'GLES3', 'KHR'):
            shutil.copytree(headers / folder, work / folder)
        source, exe = work / 'test.cpp', work / 'test'
        source.write_text(code)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-g', '-I', str(work),
                        str(source), '-ldl', '-o', str(exe)], check=True)
        result = subprocess.run([str(exe)], capture_output=True, text=True,
                                env=dict(os.environ, LIBGL_ALWAYS_SOFTWARE='1'))
        print(result.stdout, end='')
        if result.returncode == 77 and not args.require_egl:
            return
        if result.returncode:
            print(result.stderr, end='')
            result.check_returncode()


if __name__ == '__main__':
    main()
