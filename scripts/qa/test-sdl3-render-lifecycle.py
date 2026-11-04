#!/usr/bin/env python3
"""Run actual SDL engine lifecycle watcher/gate methods with an injected event source.

The host fixture does not validate Android, EGL or a physical device.
"""
# GeneralsX @bugfix Codex 04/11/2026 Prevent even one frame after EGL pause.
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATH = 'GeneralsMD/Code/GameEngineDevice/Source/SDL3GameEngine.cpp'


def extract(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref')
    args = parser.parse_args()
    source = (subprocess.check_output(['git', 'show', args.source_ref + ':' + PATH], cwd=ROOT, text=True)
              if args.source_ref else (ROOT / PATH).read_text())
    watcher = extract(source, 'static bool SDLCALL mobileLifecycleWatcher(')
    gate = extract(source, 'static inline bool mobileShouldPauseRendering(')
    update = extract(source, 'void SDL3GameEngine::update(')
    events = sorted(set(re.findall(r'SDL_EVENT_\w+', watcher)))
    code = '''
#include <atomic>
#include <cassert>
#include <cstdio>
#define __ANDROID__ 1
#define SAGE_MOBILE_PLATFORM 1
#define SDLCALL
struct SDL_Window{};static SDL_Window window;
struct SDL_DisplayMode {float refresh_rate=60;};
static SDL_DisplayMode mode;
static SDL_DisplayMode* SDL_GetCurrentDisplayMode(int){return &mode;}
static int SDL_GetDisplayForWindow(SDL_Window*){return 1;}
static unsigned SDL_GetWindowID(SDL_Window*){return 7;}
struct Pacer{bool isActualFramesPerSecondLimitEnabled(){return true;}int getActualFramesPerSecondLimit(){return 60;}};
static Pacer* TheFramePacer=nullptr;
static void d3d8gles_SetPresentUncapped(bool){}
static void gxRequestSurfaceFrameRate(SDL_Window*){}
static void SDL_Delay(int){}
static void logMobileLifecycleEvent(const char*){}
static std::atomic<bool>s_appBackgrounded{false},s_appInactive{false},s_surfaceRestorePending{false};
static unsigned renders=0,repairs=0;static bool validSurface=true;
static bool d3d8gles_restore_surface(){++repairs;return validSurface;}
struct GameEngine{void update(){++renders;}};
struct SDL_WindowEvent{unsigned type=0,windowID=7;};
struct SDL_Event{unsigned type;};
'''
    code += 'enum {' + ','.join(events) + '};\n'
    code += gate + '\n' + watcher + '\n'
    # The first-paused-frame assertion is meaningful against the original source too.
    if 'static void serviceMobileSurfaceRestoration()' in source:
        code += extract(source, 'static void serviceMobileSurfaceRestoration()') + '\n'
    else:
        code += 'static void serviceMobileSurfaceRestoration(){}\n'
    code += '''
struct SDL3GameEngine:GameEngine{
 SDL_Window*m_SDLWindow=&window;
 void pollSDL3Events(){serviceMobileSurfaceRestoration();}
 void update();void handleWindowEvent(const SDL_WindowEvent&);
};
'''
    code += update + '\n' + extract(source, 'void SDL3GameEngine::handleWindowEvent(') + '\n'
    wrapper_path = 'Core/Libraries/Source/WWVegas/WW3D2/dx8wrapper.cpp'
    wrapper = (subprocess.check_output(['git', 'show', args.source_ref + ':' + wrapper_path], cwd=ROOT, text=True)
               if args.source_ref else (ROOT / wrapper_path).read_text())
    code += r'''
static void*D3DDevice=&window;
struct {unsigned BackBufferWidth=2340,BackBufferHeight=1080;} _PresentParameters;
static int ResolutionWidth=2340,ResolutionHeight=1080;
static bool IsWindowed=false,vulkan=false;
static int physicalW=2340,physicalH=1080,resizeCalls=0,resetCalls=0,cleanupCalls=0,setupCalls=0;
static bool d3d8gles_ShouldUseVulkanBackend(){return vulkan;}
static void d3d8gles_resize(int w,int h){assert(w==physicalW&&h==physicalH);++resizeCalls;}
static bool GetWindowSize(int&w,int&h,float&density){w=physicalW;h=physicalH;density=1;return true;}
static bool GetNativeDisplaySize(int&,int&,float&){return false;}
static void Pillarbox_Cleanup(){++cleanupCalls;}
static bool Reset_Device(){++resetCalls;return true;}
static void Pillarbox_Setup(int,int){++setupCalls;}
struct DX8Wrapper{static void Pillarbox_Process_Resize();};
'''
    code += extract(wrapper, 'void DX8Wrapper::Pillarbox_Process_Resize()') + '\n'
    code += '''
static void event(unsigned type){SDL_Event e{type};mobileLifecycleWatcher(nullptr,&e);}
int main(){
 // GLES size-only changes never enter the full D3D Reset path; return to
 // the original size must still reach the physical renderer mapping.
 physicalW=2264;DX8Wrapper::Pillarbox_Process_Resize();
 physicalW=2340;DX8Wrapper::Pillarbox_Process_Resize();
 assert(resizeCalls==2&&resetCalls==0&&cleanupCalls==0&&setupCalls==0);
 physicalW=0;DX8Wrapper::Pillarbox_Process_Resize();assert(resizeCalls==2&&resetCalls==0);
 physicalW=1080;physicalH=2340;DX8Wrapper::Pillarbox_Process_Resize();assert(resizeCalls==2);
 physicalW=2264;physicalH=1080;vulkan=true;DX8Wrapper::Pillarbox_Process_Resize();
 assert(resetCalls==1&&cleanupCalls==1&&setupCalls==1);
 SDL3GameEngine engine;
 engine.update();assert(renders==1);
 for(int i=0;i<100;i++){
  const unsigned before=renders;
  event(SDL_EVENT_WILL_ENTER_BACKGROUND);
  engine.update();assert(renders==before); // SDL has already detached EGL here.
  event(SDL_EVENT_DID_ENTER_BACKGROUND);engine.update();assert(renders==before);
  event(SDL_EVENT_WINDOW_FOCUS_LOST);
  event(SDL_EVENT_DID_ENTER_FOREGROUND);
  unsigned r=repairs;engine.update();assert(repairs==r);assert(renders==before);
  event(SDL_EVENT_WINDOW_FOCUS_GAINED);
  validSurface=false;engine.update();assert(renders==before);assert(s_surfaceRestorePending);
  validSurface=true;engine.update();assert(renders==before+1);assert(!s_surfaceRestorePending);
 }
 unsigned before=renders,r=repairs;
 engine.handleWindowEvent({SDL_EVENT_WINDOW_RESIZED,8});engine.update();assert(repairs==r);
 engine.handleWindowEvent({SDL_EVENT_WINDOW_RESIZED,7});
 engine.handleWindowEvent({SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED,7});
 engine.handleWindowEvent({SDL_EVENT_WINDOW_RESTORED,7});
 engine.handleWindowEvent({SDL_EVENT_WINDOW_EXPOSED,7});
 engine.update();assert(repairs==r+1); // one restore for a batch of window events
 event(SDL_EVENT_DID_ENTER_FOREGROUND);event(SDL_EVENT_DID_ENTER_FOREGROUND);
 engine.update();assert(repairs==r+2);
 assert(renders==before+3);
 puts("PASS: production SDL watcher/gate, first paused frame, retries, event coalescing, 100 switches");
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-sdl-lifecycle-') as tmp:
        cpp = Path(tmp) / 'test.cpp'
        cpp.write_text(code)
        binary = Path(tmp) / 'test'
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-g',
                        '-fsanitize=undefined', str(cpp), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    main()
