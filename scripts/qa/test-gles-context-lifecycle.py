#!/usr/bin/env python3
"""Exercise the production render thread against a strict SDL ownership fixture.
Host synchronization tests only: this does not validate EGL or an Android device.
"""
# GeneralsX @bugfix Codex 04/11/2026 Cover pause/resume handoff failures and ordering.
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GLES = ROOT / "Core/Libraries/Source/d3d8gles"


def main():
    with tempfile.TemporaryDirectory(prefix="gx-context-") as temp:
        work = Path(temp)
        (work / "SDL3").mkdir()
        (work / "GLES3").mkdir()
        (work / "GLES3/gl3.h").write_text(r'''#pragma once
#include <cstdint>
using GLenum=unsigned;using GLuint=unsigned;using GLbitfield=unsigned;
using GLuint64=unsigned long long;using GLsync=void*;using GLint=int;
using GLintptr=long;using GLsizeiptr=long;
#define GL_APIENTRY
constexpr GLenum GL_ALREADY_SIGNALED=1,GL_CONDITION_SATISFIED=2,GL_TIMEOUT_EXPIRED=3;
constexpr GLenum GL_WAIT_FAILED=4,GL_SYNC_GPU_COMMANDS_COMPLETE=5;
''')
        (work / "SDL3/SDL.h").write_text(r'''#pragma once
#include <cstdint>
struct SDL_Window {};
struct SDL_GLContextState;using SDL_GLContext=SDL_GLContextState*;using SDL_ThreadID=uint64_t;
struct SDL_Event {unsigned type;};
#define SDLCALL
constexpr unsigned SDL_EVENT_WILL_ENTER_BACKGROUND=1,SDL_EVENT_DID_ENTER_FOREGROUND=2;
bool SDL_GL_MakeCurrent(SDL_Window*,SDL_GLContext);
SDL_GLContext SDL_GL_GetCurrentContext();
SDL_ThreadID SDL_GetCurrentThreadID();
const char*SDL_GetError();
bool SDL_GL_SetSwapInterval(int);
bool SDL_GL_SwapWindow(SDL_Window*);
bool SDL_AddEventWatch(bool(*)(void*,SDL_Event*),void*);
''')
        source=work / "test.cpp"
        source.write_text(r'''
#include <SDL3/SDL.h>
#include "gles_thread.h"
#include <atomic>
#include <cassert>
#include <cstring>
#include <mutex>
#include <thread>
#include <cstdio>
#include <string>
#include <vector>
#include <algorithm>
static std::mutex ownerMutex;
static SDL_ThreadID owner=0,mainThread=0;
static thread_local SDL_GLContext current=nullptr;
static SDL_GLContext original=reinterpret_cast<SDL_GLContext>(1);
static std::atomic<int> failWorkerBind{0},failMainBind{0},failDetach{0};
static std::atomic<unsigned> swaps{0},intervals{0},calls{0},binds{0},detaches{0};
static bool(*watch)(void*,SDL_Event*)=nullptr;
SDL_ThreadID SDL_GetCurrentThreadID(){return std::hash<std::thread::id>{}(std::this_thread::get_id());}
SDL_GLContext SDL_GL_GetCurrentContext(){return current;}
const char*SDL_GetError(){return "injected context failure";}
bool SDL_GL_MakeCurrent(SDL_Window*,SDL_GLContext ctx){
 std::lock_guard<std::mutex> lock(ownerMutex);
 const auto id=SDL_GetCurrentThreadID();
 if(!ctx){if(failDetach.exchange(0))return false;++detaches;if(owner==id)owner=0;current=nullptr;return true;}
 if(current==ctx)return true; // SDL skips EGL for the same current context/window.
 if((id==mainThread?failMainBind:failWorkerBind).exchange(0))return false;
 assert(owner==0||owner==id);++binds;owner=id;current=ctx;return true;
}
bool SDL_GL_SetSwapInterval(int){assert(current==original);++intervals;return true;}
bool SDL_GL_SwapWindow(SDL_Window*){assert(current==original);++swaps;return true;}
bool SDL_AddEventWatch(bool(*fn)(void*,SDL_Event*),void*){watch=fn;return true;}
static void event(unsigned type){assert(watch);SDL_Event e{type};watch(nullptr,&e);}
static void draw(){gxrt::post([]{assert(current==original);++calls;});}
int main(int argc,char**argv){
 mainThread=SDL_GetCurrentThreadID();SDL_Window window;
 assert(SDL_GL_MakeCurrent(&window,original));
 const std::string mode=argc>1?argv[1]:"normal";
 if(mode=="direct"){
  const unsigned beforeBind=binds,beforeDetach=detaches;
  gxrt::ensureContext(&window,original);assert(current==original);
  assert(binds==beforeBind+1&&detaches==beforeDetach+1);
  SDL_GL_MakeCurrent(&window,nullptr);gxrt::ensureContext(&window,original);
  assert(current==original);gxrt::present(&window,-1);assert(intervals==1);
  puts("PASS: direct-mode restoration rebinds original context");return 0;
 }
 assert(gxrt::start(&window));
 if(mode=="uploads"){
  std::vector<unsigned char> payload(131072);
  std::atomic<unsigned> completed{0};
  for(unsigned i=0;i<400;++i){
   std::fill(payload.begin(),payload.end(),i%251);
   gxrt::postBytes([i,&completed](const void*data){
    const auto*b=static_cast<const unsigned char*>(data);
    for(unsigned k=0;k<131072;++k)assert(b[k]==i%251);
    assert(completed.fetch_add(1)==i);
   },payload.data(),payload.size());
  }
  std::fill(payload.begin(),payload.end(),255);gxrt::sync([]{});
  assert(completed==400);auto stats=gxrt::takeStats();
  assert(stats.commandBytes>=400.0*131072&&stats.commands>=400);
  gxrt::stop();assert(current==original);
  printf("PASS: real 16MiB ring wrap, 50MiB owned uploads in FIFO order; host ring wait %.3fms (not device performance)\n",stats.ringWaitUs/1000.0);
  return 0;
 }
 draw();gxrt::sync([]{});assert(calls==1&&SDL_GL_GetCurrentContext()==nullptr);
 if(mode=="surface-detach-failure")failDetach=1;
 if(mode=="surface-bind-failure")failWorkerBind=1;
 const unsigned beforeBind=binds,beforeDetach=detaches;
 gxrt::ensureContext(&window,original);
 assert(binds==beforeBind+1&&detaches==beforeDetach+1);
 if(mode=="release-failure")failDetach=1;
 if(mode=="pause-main-failure")failMainBind=1;
 event(SDL_EVENT_WILL_ENTER_BACKGROUND);
 assert(!gxrt::running()&&current==original&&calls==1);
 if(mode=="replacement"){current=reinterpret_cast<SDL_GLContext>(2);}
 if(mode=="resume-detach-failure")failDetach=1;
 if(mode=="fallback"||mode=="unrecoverable")failWorkerBind=1;
 if(mode=="unrecoverable")failMainBind=1;
 event(SDL_EVENT_DID_ENTER_FOREGROUND);
 gxrt::ensureContext(&window,original);
 if(mode=="fallback"){
  assert(!gxrt::running()&&current==original);draw();assert(calls==2);
 }else{
  assert(gxrt::running()&&current==nullptr);
  for(unsigned i=0;i<100;++i){
   draw();event(SDL_EVENT_WILL_ENTER_BACKGROUND);assert(current==original);
   assert(calls==i+2);event(SDL_EVENT_DID_ENTER_FOREGROUND);
   event(SDL_EVENT_DID_ENTER_FOREGROUND);assert(gxrt::running());
   const unsigned before=intervals;
   gxrt::present(&window,-1);gxrt::sync([]{});
   assert(intervals==before+1); // Reapply retained swap policy after each handoff.
   gxrt::present(&window,-1);gxrt::sync([]{});assert(intervals==before+1);
  }
 }
 gxrt::stop();assert(current==original);puts("PASS: production thread context ownership and command drain");
}
''')
        exe=work / "test"
        subprocess.run([os.environ.get("CXX","c++"),"-std=c++17","-O1","-g","-pthread",
                        "-I",str(work),"-I",str(GLES/"include"),str(source),
                        str(GLES/"src/gles_thread.cpp"),"-o",str(exe)],check=True)
        for mode in ("normal","fallback","direct","uploads"):
            result=subprocess.run([str(exe),mode],capture_output=True,text=True,timeout=20)
            assert result.returncode == 0, result.stderr
            print(result.stdout.strip())
        for mode in ("replacement","release-failure","pause-main-failure","resume-detach-failure","unrecoverable","surface-detach-failure","surface-bind-failure"):
            result=subprocess.run([str(exe),mode],capture_output=True,text=True,timeout=20)
            assert result.returncode != 0, f"{mode}: unsafe continuation accepted"
            assert "context lifecycle failure" in result.stderr, result.stderr
            print(f"PASS: {mode} fails closed before further GL work")


if __name__ == "__main__":
    main()
