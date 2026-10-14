#!/usr/bin/env python3
"""Execute production GLES queue/upload code and terrain range code on the host.
No device/GPU/FPS claim. --legacy-ref demonstrates the old allocation/range costs.
"""
# GeneralsX @performance Codex 14/10/2026 Preserve upload ordering and exact terrain bytes.
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def extract(source, signature):
    start = source.index(signature)
    pos = source.index('{', start)
    depth = 1
    end = pos + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy-ref')
    args = parser.parse_args()

    def read(path):
        if args.legacy_ref:
            return subprocess.check_output(['git', 'show', args.legacy_ref + ':' + path], cwd=ROOT, text=True)
        return (ROOT / path).read_text()

    header = read('Core/Libraries/Source/d3d8gles/include/gles_thread.h')
    dispatch = read('Core/Libraries/Source/d3d8gles/src/gles_dispatch.cpp')
    terrain = extract(read('Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp'),
                      'Int HeightMapRenderObjClass::updateVB(')
    begin = terrain.index('const Int firstVertex') if not args.legacy_ref else terrain.index('DX8VertexBufferClass::WriteLockClass lockVtxBuffer')
    end = terrain.index('VERTEX_FORMAT *vBase = data;', begin)
    lock = terrain[begin:end]
    copy = next(line.strip() for line in terrain.splitlines() if 'memcpy(vbHardware' in line)
    with tempfile.TemporaryDirectory(prefix='gx-gles-regression-') as temp:
        work = Path(temp)
        (work / 'GLES3').mkdir()
        (work / 'GLES3/gl3.h').write_text('''#pragma once
#include <cstdint>
typedef int GLint; typedef unsigned GLenum; typedef unsigned GLbitfield; typedef unsigned long long GLuint64;
typedef void* GLsync; typedef long GLintptr; typedef long GLsizeiptr;
#define GL_APIENTRY
''')
        (work / 'gles_thread.h').write_text(header)
        code = r'''
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <algorithm>
static unsigned allocs=0, frees=0;
static void* countedMalloc(size_t n) { ++allocs; return std::malloc(n); }
static void countedFree(void* p) { if(p)++frees; std::free(p); }
#define malloc countedMalloc
#define free countedFree
#include "gles_thread.h"
#undef malloc
#undef free
namespace gxrt {
bool g_active = true;
alignas(16) static unsigned char ring[16u<<20];
static size_t used=0, read=0;
void* allocCmd(size_t bytes, uint32_t* rounded) {
 *rounded=(bytes+15)&~15; assert(used+*rounded<=sizeof(ring)); return ring+used;
}
void commitCmd() { used+=reinterpret_cast<Cmd*>(ring+used)->bytes; }
void drain() { while(read<used) { Cmd*c=reinterpret_cast<Cmd*>(ring+read); unsigned n=c->bytes; c->run(c); read+=n; } used=read=0; }
void addWork(int,uint64_t) {}
}
static std::vector<unsigned char> gpu(2u<<20, 0);
static bool refuse=false;
static unsigned maps=0, unmaps=0, fallbacks=0;
static GLintptr lastOffset=0;
static GLsizeiptr lastLength=0;
static GLbitfield lastAccess=0;
static void* d3d8gles_pfn_glMapBufferRange(GLenum target, GLintptr offset, GLsizeiptr length, GLbitfield access) {
 assert(target==7); ++maps; lastOffset=offset; lastLength=length; lastAccess=access;
 return refuse ? nullptr : gpu.data()+offset;
}
static void d3d8gles_pfn_glUnmapBuffer(GLenum) { ++unmaps; }
static void d3d8gles_pfn_glBufferSubData(GLenum,GLintptr offset,GLsizeiptr length,const void* data) {
 ++fallbacks; std::memcpy(gpu.data()+offset,data,length);
}
'''
        code += extract(dispatch, 'void gxrt::bufferWrite(')
        code += r'''
using Int=int;
struct VERTEX_FORMAT { unsigned char bytes[44]; };
struct DX8VertexBufferClass {
 std::vector<VERTEX_FORMAT> vertices;
 unsigned first=0,count=0;
 explicit DX8VertexBufferClass(unsigned n):vertices(n) {}
 struct WriteLockClass {
  DX8VertexBufferClass*p;
  explicit WriteLockClass(DX8VertexBufferClass*b):p(b) { p->first=0;p->count=p->vertices.size(); }
  void* Get_Vertex_Array() {return p->vertices.data();}
 };
 struct AppendLockClass {
  DX8VertexBufferClass*p;
  AppendLockClass(DX8VertexBufferClass*b,unsigned first,unsigned count):p(b) {
   assert(first+count<=p->vertices.size());p->first=first;p->count=count;
  }
  void* Get_Vertex_Array() {return p->vertices.data()+p->first;}
 };
};
static unsigned terrainUpdate(int x0,int y0,int x1,int y1,int originX,int originY,int width) {
 const Int vertsPerRow=width*4;
 DX8VertexBufferClass buffer(width*width*4); auto*pVB=&buffer;
 std::vector<VERTEX_FORMAT> mirror(buffer.vertices.size()), expected(buffer.vertices.size());
 for(unsigned i=0;i<mirror.size();++i)std::memset(&mirror[i],i%253+1,sizeof(VERTEX_FORMAT));
 auto*data=mirror.data();auto*vBase=data;
'''
        code += lock
        code += r'''
 for(int j=y0;j<y1;++j)for(int i=x0;i<x1;++i) {
  auto*pCurVertices=data+(j-originY)*vertsPerRow+4*(i-originX);
  Int offset=pCurVertices-vBase;
  assert(unsigned(offset)>=buffer.first && unsigned(offset+4)<=buffer.first+buffer.count);
'''
        code += copy
        code += r'''
  std::memcpy(expected.data()+offset,pCurVertices,4*sizeof(VERTEX_FORMAT));
 }
 assert(std::memcmp(buffer.vertices.data(),expected.data(),expected.size()*sizeof(VERTEX_FORMAT))==0);
 return buffer.count;
}
int main() {
 std::vector<unsigned char> source(400000,77);
 allocs=frees=0;
 for(unsigned i=0;i<491;++i) { // same append count as the historical report; no FPS assertion
  gxrt::bufferWrite(7,128,1024,source.data(),0x22);
  gxrt::post([]{ assert(gpu[128]==77); }); // draw/state work retains FIFO order
 }
 std::fill(source.begin(),source.end(),99);
 assert(maps==0); gxrt::drain();
 assert(maps==491 && unmaps==491 && fallbacks==0 && lastOffset==128 && lastLength==1024 && lastAccess==0x22);
 const unsigned ordinaryAllocs=allocs;
 assert(ordinaryAllocs==EXPECTED_ALLOCS && frees==allocs);
 refuse=true; gxrt::bufferWrite(7,0,2048,source.data(),0x22);
 std::fill(source.begin(),source.end(),100);gxrt::drain();assert(gpu[0]==99 && fallbacks==1);
 refuse=false; gxrt::g_active=false;allocs=frees=0;
 gxrt::bufferWrite(7,0,source.size(),source.data(),0x22);
 assert(gpu[0]==100 && allocs==EXPECTED_IMMEDIATE_ALLOCS);
 gxrt::g_active=true;
 std::vector<unsigned char> large((1u<<20)+100,123);allocs=frees=0;
 gxrt::bufferWrite(7,0,large.size(),large.data(),0x22);
 std::fill(large.begin(),large.end(),1);gxrt::drain();
 assert(gpu[0]==123 && gpu[(1u<<20)+99]==123 && allocs==1 && frees==1);
 for(int oy: {0,16,64})for(int ox:{0,16,64})
  for(int y=0;y<16;++y)for(int x=0;x<16;++x)
   for(int h=1;h<=16-y;++h)for(int w=1;w<=16-x;++w)
    terrainUpdate(ox+x,oy+y,ox+x+w,oy+y+h,ox,oy,16);
 const unsigned narrow=terrainUpdate(7,12,8,13,0,0,16);
 assert(narrow==EXPECTED_TERRAIN_VERTICES);
 std::printf("PASS: production upload queue FIFO, lifetime, map fallback, large writes; ordinary allocations=%u/491; one-cell terrain upload=%u bytes (full tile 45056 bytes)\n",ordinaryAllocs,narrow*44);
}
'''
        code = code.replace('EXPECTED_ALLOCS', '491' if args.legacy_ref else '0')
        code = code.replace('EXPECTED_IMMEDIATE_ALLOCS', '1' if args.legacy_ref else '0')
        code = code.replace('EXPECTED_TERRAIN_VERTICES', '1024' if args.legacy_ref else '4')
        path = work / 'test.cpp'
        path.write_text(code)
        exe = work / 'test'
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', '-I', str(work), str(path), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1'))
        pipeline = read('Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp')
        state = extract(read('Core/Libraries/Source/d3d8gles/src/gles_pipeline.h'), 'struct GLBufferState') + ';'
        buffers = r'''#include <cassert>
#include <cstdio>
#include <cstddef>
#include <cstring>
#include <vector>
using GLuint=unsigned;using GLenum=unsigned;using GLintptr=long;using GLsizeiptr=long;
constexpr unsigned D3DUSAGE_DYNAMIC=1,GL_COPY_WRITE_BUFFER=1,GL_DYNAMIC_DRAW=2,GL_MAP_WRITE_BIT=4,GL_MAP_UNSYNCHRONIZED_BIT=8;
constexpr int GX_UPLOAD_IB_FULL=1,GX_UPLOAD_VB_FULL=2,GX_UPLOAD_IB_APPEND=3,GX_UPLOAD_VB_APPEND=4,GX_DRAWCAT_COUNT=7;
static int s_gxDrawCategory=0;static unsigned s_gxSyncCallsByCategory[7]={};
struct PersistentBufferSet {};
struct GxUploadTimer {GxUploadTimer(int,size_t){}};
'''
        buffers += state
        buffers += r'''
struct WebGLVertexBuffer {GLBufferState m_gl;unsigned m_usage=0;std::vector<unsigned char> m_bits;};
using WebGLIndexBuffer=WebGLVertexBuffer;
static std::vector<unsigned char> gpu;
static unsigned uploads=0,binds=0,names=0,lastAccess=0;
void glGenBuffers(int,GLuint*n){*n=++names;}
void glBindBuffer(GLenum,GLuint){++binds;}
void glBufferData(GLenum,size_t n,const void* data,unsigned){gpu.assign(n,0);if(data)memcpy(gpu.data(),data,n);++uploads;}
void glBufferSubData(GLenum,size_t off,size_t n,const void* data){assert(off+n<=gpu.size());memcpy(gpu.data()+off,data,n);++uploads;}
namespace gxrt {void bufferWrite(GLenum target,GLintptr off,GLsizeiptr n,const void* data,unsigned flags){lastAccess=flags;glBufferSubData(target,off,n,data);}}
class WebGLPipeline {public:
 struct {bool persistentIB=false;}m_opt;
 unsigned m_perfSyncUploads=0;
 bool persistentUpload(GLBufferState&,const unsigned char*,size_t,bool){return false;}
 void fullBufferUpload(GLBufferState&,const unsigned char*,size_t,int);
 void ensureVBUploaded(WebGLVertexBuffer*);
 void ensureIBUploaded(WebGLIndexBuffer*);
};
'''
        for signature in ('void WebGLPipeline::fullBufferUpload(', 'void WebGLPipeline::ensureVBUploaded(', 'void WebGLPipeline::ensureIBUploaded('):
            buffers += extract(pipeline, signature) + '\n'
        buffers += r'''
int main(){
 WebGLPipeline p;
 for(bool index:{false,true})for(bool dynamic:{false,true}){
  WebGLVertexBuffer b;b.m_bits.assign(4096,7);b.m_gl.markRange(0,4096);b.m_usage=dynamic?D3DUSAGE_DYNAMIC:0;
  auto ensure=[&]{if(index)p.ensureIBUploaded(&b);else p.ensureVBUploaded(&b);};
  ensure();assert(gpu==b.m_bits && !b.m_gl.dirty && b.m_gl.allocated);
  unsigned count=uploads,binding=binds,name=b.m_gl.name;
  for(int i=0;i<120;++i)ensure();assert(uploads==count && binds==binding && b.m_gl.name==name);
  b.m_bits[128]=9;b.m_bits[129]=10;b.m_gl.markRange(128,130);b.m_gl.pendingSync=true;
  ensure();assert(gpu==b.m_bits && uploads==count+1 && !b.m_gl.pendingSync);
  b.m_bits[300]=11;b.m_gl.markRange(300,301);lastAccess=0;ensure();
  assert(gpu==b.m_bits && lastAccess==(GL_MAP_WRITE_BIT|GL_MAP_UNSYNCHRONIZED_BIT));
  b.m_bits[0]=20;b.m_gl.markRange(0,1);b.m_gl.pendingDiscard=true;ensure();
  assert(gpu==b.m_bits && !b.m_gl.pendingDiscard); // older ranges must survive for sorted draws
 }
 GLBufferState range;range.markRange(128,256);range.markRange(64,160);
 assert(range.dirtyBegin==64&&range.dirtyEnd==256&&range.writtenEnd==256);
 range.clearRange();assert(range.dirtyBegin>=range.dirtyEnd&&range.writtenEnd==256);
 PersistentBufferSet ps;range.persistent=&ps;range.noteGpuRead(2048,1024);assert(range.gpuRefEnd==1024);
 puts("PASS: production static VB/IB reuse, dynamic synchronized/NOOVERWRITE/DISCARD bytes and range accounting");
}
'''
        path.write_text(buffers)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(path), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)



if __name__ == '__main__':
    main()
