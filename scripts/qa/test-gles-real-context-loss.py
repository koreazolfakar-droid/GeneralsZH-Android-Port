#!/usr/bin/env python3
"""Real headless EGL context destruction + D3D GPU-state invalidation.

Uses the actual production forgetLostGpuObjectHandles() method. Reconstructs
CPU-backed media into fresh Mesa GLES3 context and checks framebuffer pixels.
This is host EGL/GLES validation, not Android device verification.
"""
from pathlib import Path
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'Core/Libraries/Source/d3d8gles/src/d3d8gles.cpp'


def extract(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth, pos = 1, brace + 1
    while depth:
        depth += (source[pos] == '{') - (source[pos] == '}')
        pos += 1
    return source[start:pos]


def main():
    fn = extract(SRC.read_text(), 'static void forgetLostGpuObjectHandles()\n{')
    fixture = r'''
#include <EGL/egl.h>
#include <GLES3/gl3.h>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <unordered_set>

struct GLTextureState {
 GLuint name=0;
 bool dirty=true;
 GLuint fbo=0;
};
struct PersistentBufferSet {
 static constexpr int kMaxCopies=8;
 GLsync fences[kMaxCopies]={};
 int count=0;
};
struct GLBufferState {
 GLuint name=0;
 bool dirty=true;
 size_t dirtyBegin=(size_t)-1,dirtyEnd=0,writtenEnd=0,gpuRefEnd=0;
 bool allocated=false,pendingDiscard=false,pendingSync=false;
 PersistentBufferSet*persistent=nullptr;
};
static std::unordered_set<GLTextureState*>g_liveTextureGLStates;
static std::unordered_set<GLBufferState*>g_liveBufferGLStates;
namespace gxrt {
static void deleteSync(GLsync){assert(false && "no stale GPU fence can be deleted in new context");}
}
'''
    fixture += '\n' + fn + '\n'
    fixture += r'''
static EGLDisplay display=EGL_NO_DISPLAY;
static EGLConfig config=nullptr;
static EGLSurface surface=EGL_NO_SURFACE;
static EGLContext context=EGL_NO_CONTEXT;

static void createContext() {
 constexpr EGLint pbuffer[]={EGL_WIDTH,16,EGL_HEIGHT,16,EGL_NONE};
 constexpr EGLint attr[]={EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
 surface=eglCreatePbufferSurface(display,config,pbuffer);
 assert(surface!=EGL_NO_SURFACE);
 context=eglCreateContext(display,config,EGL_NO_CONTEXT,attr);
 assert(context!=EGL_NO_CONTEXT);
 assert(eglMakeCurrent(display,surface,surface,context));
}
static void destroyContext() {
 assert(eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT));
 assert(eglDestroyContext(display,context));
 assert(eglDestroySurface(display,surface));
 context=EGL_NO_CONTEXT;surface=EGL_NO_SURFACE;
}
int main() {
 display=eglGetPlatformDisplay((EGLenum)0x31DD /* SURFACELESS_MESA */,nullptr,nullptr);
 EGLint major=0,minor=0,count=0;
 assert(display!=EGL_NO_DISPLAY&&eglInitialize(display,&major,&minor));
 assert(eglBindAPI(EGL_OPENGL_ES_API));
 constexpr EGLint attrs[]={EGL_SURFACE_TYPE,EGL_PBUFFER_BIT,
  EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,
  EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_NONE};
 assert(eglChooseConfig(display,attrs,&config,1,&count)&&count==1);
 GLTextureState tex;
 GLBufferState vb;vb.writtenEnd=4;
 g_liveTextureGLStates.insert(&tex);
 g_liveBufferGLStates.insert(&vb);
 const unsigned char cpuTexel[4]={255,80,40,255};
 const unsigned char cpuVertices[4]={5,6,7,8};
 for(int n=0;n<20;++n) {
  createContext();
  // All GPU names from the previous context are invalid; new GPU IDs must
  // be generated from the retained CPU bytes rather than reused by number.
  forgetLostGpuObjectHandles();
  assert(tex.name==0&&tex.fbo==0&&tex.dirty);
  assert(vb.name==0&&vb.dirty&&!vb.allocated&&vb.writtenEnd==4);
  glGenTextures(1,&tex.name);
  glBindTexture(GL_TEXTURE_2D,tex.name);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
  glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,cpuTexel);
  tex.dirty=false;
  glGenFramebuffers(1,&tex.fbo);
  glBindFramebuffer(GL_FRAMEBUFFER,tex.fbo);
  glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,tex.name,0);
  assert(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE);
  unsigned char pixel[4]={};
  glReadPixels(0,0,1,1,GL_RGBA,GL_UNSIGNED_BYTE,pixel);
  assert(std::memcmp(pixel,cpuTexel,4)==0);
  glGenBuffers(1,&vb.name);
  glBindBuffer(GL_ARRAY_BUFFER,vb.name);
  glBufferData(GL_ARRAY_BUFFER,4,cpuVertices,GL_STATIC_DRAW);
  vb.dirty=false;vb.allocated=true;
  void*ptr=glMapBufferRange(GL_ARRAY_BUFFER,0,4,GL_MAP_READ_BIT);
  assert(ptr&&std::memcmp(ptr,cpuVertices,4)==0);
  assert(glUnmapBuffer(GL_ARRAY_BUFFER));
  assert(glGetError()==GL_NO_ERROR);
  destroyContext();
 }
 g_liveTextureGLStates.erase(&tex);
 g_liveBufferGLStates.erase(&vb);
 assert(eglTerminate(display));
 puts("PASS: 20 real EGL context destructions and GLES3 CPU-backed GPU texture/buffer reconstructions");
 puts("Host Mesa GLES3 only; no real Android screenshot/TEOD device check.");
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-real-context-') as temp:
        source, binary = Path(temp)/'test.cpp', Path(temp)/'test'
        source.write_text(fixture)
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17',
                        '-Wall','-Wextra','-Werror','-O1',
                        str(source),'-lEGL','-lGLESv2','-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)


if __name__ == '__main__':
    main()
