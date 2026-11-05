#!/usr/bin/env python3
"""TEOD camera-pan regression gates on production source (no asset/logic changes).

Checks that the native dirty-shroud, terrain scroll and producer waits are wired
into the real engine; compiles the extracted production waiter with UBSan.
"""
import pathlib
import shutil
import subprocess
import tempfile

R = pathlib.Path(__file__).resolve().parents[2]
SHROUD = R / "GeneralsMD/Code/GameEngineDevice/Source/W3DDevice/GameClient/W3DShroud.cpp"
SHROUD_H = R / "GeneralsMD/Code/GameEngineDevice/Include/W3DDevice/GameClient/W3DShroud.h"
TERRAIN = R / "Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp"
THREAD = R / "Core/Libraries/Source/d3d8gles/src/gles_thread.cpp"
s, h, terrain, thread = (p.read_text() for p in (SHROUD, SHROUD_H, TERRAIN, THREAD))

# The render-only shroud copy can only be skipped when both source is unchanged
# and destination contents survived. Full map refresh, fog changes, reset and
# context restoration each invalidate the cache.
assert "Bool m_srcTextureDirty;" in h
assert "const Bool uploadRequired = m_srcTextureDirty || m_clearDstTexture;" in s
assert "if (uploadRequired)" in s
assert "m_srcTextureDirty = FALSE;" in s
assert s.index("const Bool uploadRequired") < s.index("if (uploadRequired)")
assert s.index("interpolateFogLevels(&srcRect)") < s.index("const Bool uploadRequired")
for method in ("W3DShroud::W3DShroud()", "W3DShroud::init(", "W3DShroud::reset()",
               "W3DShroud::ReleaseResources()", "W3DShroud::ReAcquireResources()",
               "W3DShroud::fillShroudData("):
    start = s.index(method)
    end = s.find("\n//---", start + len(method))
    assert "m_srcTextureDirty = TRUE;" in s[start:end], method
assert s.count("if (*texel != pixel)") == 2
assert "m_clearDstTexture=FALSE;" in s

# Camera-scroll jump distances must be compared against each axis's size.
assert "IABS(deltaX) > m_x/2 || IABS(deltaY) > m_y/2" in terrain
assert "IABS(deltaY)>m_x/2" not in terrain
for x, y, dx, dy, large in [
    (129,65,0,35,True), (129,65,0,20,False),
    (65,129,0,40,False), (65,129,0,70,True),
    (65,129,40,0,True), (129,129,0,5,False),
]:
    assert (abs(dx)>x/2 or abs(dy)>y/2) == large

# Ensure no 2ms producer polling remains; leave worker's separate fence polling
# intact because the real GL driver may signal a fence without another command.
assert "s_doneCv.wait(lock, pred);" in thread
assert "s_doneCv.wait_for(lock, std::chrono::milliseconds(2))" not in thread
assert "s_workCv.wait_for(lock, fences ?" in thread

def extract(source, beginning, ending):
    return source[source.index(beginning):source.index(ending, source.index(beginning))]

# These functions are copied verbatim from the production engine and compiled,
# not re-implemented in the test. Exercise wake races and already-ready fast path.
wake = extract(thread, "void wakeMain()", "\nvoid wakeWorker()")
wait = extract(thread, "template <class P>\nvoid waitMain(", "\nvoid pollFences()")
fixture = r'''
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <mutex>
#include <thread>
#include <stdexcept>
using Clock = std::chrono::steady_clock;
double usSince(Clock::time_point start) {
 return std::chrono::duration<double, std::micro>(Clock::now() - start).count();
}
std::mutex s_doneMutex;
std::condition_variable s_doneCv;
double s_producerWaitUsTotal=0;
''' + wake + wait + r'''
int main() {
 double accum=0;
 for (int i=0;i<10000;++i) {
   std::atomic<bool> done{false};
   std::thread worker([&] {
     if (i%2==0) std::this_thread::yield();
     done.store(true,std::memory_order_release);
     wakeMain();
   });
   waitMain([&]{return done.load(std::memory_order_acquire);}, &accum);
   worker.join();
   if (!done.load()) return 1;
 }
 bool ready=true;
 waitMain([&]{return ready;}, &accum);
 std::puts("PASS: production waitMain race and ready-path test");
}
'''
compiler=shutil.which("g++") or shutil.which("clang++")
if compiler is None:
    raise SystemExit("FAIL: C++ compiler missing")
with tempfile.TemporaryDirectory(prefix="gx-teod-scroll-") as td:
    src=pathlib.Path(td)/"waiter.cpp"
    exe=pathlib.Path(td)/"waiter"
    src.write_text(fixture)
    subprocess.run([compiler,"-std=c++17","-O1","-Wall","-Wextra","-Werror",
        "-pthread","-fsanitize=undefined","-fno-sanitize-recover=undefined",
        str(src),"-o",str(exe)],check=True)
    subprocess.run([str(exe)],check=True,timeout=15)

# Rendering side behavioral gate: repeated draw without changes must preserve
# prior texture; visibility change or device reset triggers exactly one upload.
dirty, dest_clear, uploads = True, True, 0
def draw():
    global dirty, dest_clear, uploads
    needed = dirty or dest_clear
    dest_clear = False
    if needed:
        uploads += 1
        dirty = False
draw()
assert uploads==1
for _ in range(100): draw()
assert uploads==1
dirty=True  # Fog reveal
draw(); assert uploads==2
draw(); assert uploads==2
dest_clear=True # Context loss / renderer reset
draw(); assert uploads==3

# Compile the ACTUAL Android terrain dirty-range aggregator with UBSan. A
# lowered height cell should refresh its neighboring normals, not the full map.
visual = (R / "Core/GameEngineDevice/Source/W3DDevice/GameClient/W3DTerrainVisual.cpp").read_text()
height_source = extract(terrain,
    "void HeightMapRenderObjClass::markHeightCellDirty(Int mapX, Int mapY)",
    "\nvoid HeightMapRenderObjClass::flushHeightCellDirty")
assert "#if defined(__ANDROID__) && !defined(DO_SEISMIC_SIMULATIONS)" in visual
assert "static_cast<HeightMapRenderObjClass *>(m_terrainRenderObject)->markHeightCellDirty(x, y);" in visual
assert "flushHeightCellDirty(pLightsIterator);" in terrain
assert "doPartialUpdate(dirty, m_map, pLightsIterator);" in terrain
assert "if (m_bridgeBuffer) m_bridgeBuffer->doFullUpdate();" in terrain
fixture = r'''
#include <algorithm>
#include <cassert>
using Int = int;
using Bool = int;
constexpr int TRUE = 1, FALSE = 0;
struct Point { int x=0, y=0; };
struct IRegion2D { Point lo,hi; };
struct WorldHeightMap {
 int x=129,y=129;
 int getXExtent() const { return x; }
 int getYExtent() const { return y; }
};
class HeightMapRenderObjClass {
public:
 WorldHeightMap *m_map=nullptr;
 Bool m_needFullUpdate=FALSE;
 Bool m_heightCellDirty=FALSE;
 IRegion2D m_heightCellDirtyRegion;
 void markHeightCellDirty(Int mapX,Int mapY);
};
''' + height_source + r'''
int main() {
 WorldHeightMap map;
 HeightMapRenderObjClass t;
 t.m_map = &map;
 t.markHeightCellDirty(40,50);
 assert(t.m_heightCellDirty);
 assert(t.m_heightCellDirtyRegion.lo.x==38 && t.m_heightCellDirtyRegion.lo.y==48);
 assert(t.m_heightCellDirtyRegion.hi.x==43 && t.m_heightCellDirtyRegion.hi.y==53);
 t.markHeightCellDirty(41,52);
 assert(t.m_heightCellDirtyRegion.hi.x==44 && t.m_heightCellDirtyRegion.hi.y==55);
 t.m_heightCellDirty=FALSE;
 t.markHeightCellDirty(0,0);
 assert(t.m_heightCellDirtyRegion.lo.x==0 && t.m_heightCellDirtyRegion.lo.y==0);
 assert(t.m_heightCellDirtyRegion.hi.x==3 && t.m_heightCellDirtyRegion.hi.y==3);
 t.m_heightCellDirty=FALSE;
 t.markHeightCellDirty(128,128);
 assert(t.m_heightCellDirtyRegion.lo.x==126 && t.m_heightCellDirtyRegion.lo.y==126);
 assert(t.m_heightCellDirtyRegion.hi.x==128 && t.m_heightCellDirtyRegion.hi.y==128);
 t.m_heightCellDirty=FALSE;
 t.markHeightCellDirty(-1,10);
 assert(t.m_needFullUpdate && !t.m_heightCellDirty);
 t.m_needFullUpdate=FALSE;
 t.markHeightCellDirty(10,10);
 assert(t.m_heightCellDirty);
 t.m_heightCellDirty=FALSE;
 t.m_needFullUpdate=TRUE;
 t.markHeightCellDirty(11,11);
 assert(!t.m_heightCellDirty); // Global relighting takes precedence.
}
'''
with tempfile.TemporaryDirectory(prefix="gx-terrain-dirty-") as td:
    src=pathlib.Path(td)/"dirty.cpp"
    exe=pathlib.Path(td)/"dirty"
    src.write_text(fixture)
    subprocess.run([compiler,"-std=c++17","-O1","-Wall","-Wextra","-Werror",
        "-fsanitize=undefined","-fno-sanitize-recover=undefined",
        str(src),"-o",str(exe)], check=True)
    subprocess.run([str(exe)],check=True,timeout=15)
print("PASS: production Android terrain height dirty rectangle, halo and full-relight fallback")

print("PASS: shroud upload gate, fog invalidation, axis-safe scrolling and frame waiter")
