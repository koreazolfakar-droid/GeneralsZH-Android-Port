#!/usr/bin/env python3
"""Run extracted GLES texture/sampler production code with immediate and queued GL.

Usage: python3 scripts/qa/test-gles-texture-state.py [--source-ref HEAD]
No GPU, Android visual-equivalence, or frame-rate claim is made by this host test.
"""
# GeneralsX @performance Codex 03/11/2026 Check draw state while removing redundant texture commands.
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
    parser.add_argument('--source-ref', help='Extract production source from a Git ref; old code must fail the command budget.')
    args = parser.parse_args()

    def read(path):
        if args.source_ref:
            return subprocess.check_output(['git', 'show', args.source_ref + ':' + path], cwd=ROOT, text=True)
        return (ROOT / path).read_text()

    pipeline = read('Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp')
    sampler_declaration = extract(pipeline, 'void WebGLPipeline::applySamplerState(').split('{', 1)[0].strip()
    sampler_declaration = sampler_declaration.replace('WebGLPipeline::', '') + ';'
    code = r'''
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
#include "gles_thread.h"
using GLuint=unsigned;using DWORD=unsigned;
constexpr unsigned GL_TEXTURE0=100,GL_TEXTURE_2D=200;
constexpr unsigned GL_TEXTURE_MIN_FILTER=1,GL_TEXTURE_MAG_FILTER=2,GL_TEXTURE_WRAP_S=3,GL_TEXTURE_WRAP_T=4;
constexpr unsigned GL_NEAREST=10,GL_LINEAR=11,GL_NEAREST_MIPMAP_NEAREST=12,GL_LINEAR_MIPMAP_NEAREST=13;
constexpr unsigned GL_NEAREST_MIPMAP_LINEAR=14,GL_LINEAR_MIPMAP_LINEAR=15;
constexpr unsigned GL_REPEAT=20,GL_MIRRORED_REPEAT=21,GL_CLAMP_TO_EDGE=22;
constexpr unsigned D3DTSS_MINFILTER=0,D3DTSS_MAGFILTER=1,D3DTSS_MIPFILTER=2,D3DTSS_ADDRESSU=3,D3DTSS_ADDRESSV=4;
constexpr unsigned D3DTEXF_NONE=0,D3DTEXF_POINT=1,D3DTEXF_LINEAR=2;
constexpr unsigned D3DTADDRESS_WRAP=1,D3DTADDRESS_MIRROR=2,D3DTADDRESS_CLAMP=3,D3DTADDRESS_BORDER=4;
namespace gxrt {
bool g_active=false;
alignas(16) static unsigned char ring[1u<<20];
static size_t used=0,readPos=0;
void* allocCmd(size_t bytes,uint32_t* rounded) {
 *rounded=(bytes+15)&~15;assert(used+*rounded<=sizeof(ring));return ring+used;
}
void commitCmd(){used+=reinterpret_cast<Cmd*>(ring+used)->bytes;}
void drain(){while(readPos<used){Cmd*c=reinterpret_cast<Cmd*>(ring+readPos);unsigned n=c->bytes;c->run(c);readPos+=n;}used=readPos=0;}
}
struct Texture {unsigned content=0;std::array<unsigned,5> params{};};
static std::array<Texture,128> textures;
static std::array<unsigned,2> bound;
static std::array<std::array<int,8>,4> uniforms;
static unsigned active=0,program=0,activeCalls=0,uniformCalls=0,bindCalls=0,paramCalls=0,draws=0;
static void glActiveTexture(unsigned stage){++activeCalls;gxrt::post([stage]{active=stage-GL_TEXTURE0;assert(active<2);});}
static void glBindTexture(unsigned target,unsigned tex){assert(target==GL_TEXTURE_2D);++bindCalls;gxrt::post([tex]{bound[active]=tex;});}
static void glTexParameteri(unsigned target,unsigned pname,int value){assert(target==GL_TEXTURE_2D);++paramCalls;gxrt::post([pname,value]{assert(bound[active]!=0);textures[bound[active]].params[pname]=value;});}
static void glUniform1i(int location,int value){++uniformCalls;gxrt::post([location,value]{assert(program>0);uniforms[program][location]=value;});}
struct GLTextureState {GLuint name=0;bool dirty=true;uint32_t samplerKey=~0u;};
struct WebGLTexture {GLTextureState m_gl;std::vector<unsigned> m_levels{0};unsigned content=0;};
struct WebGLDevice {
 std::array<WebGLTexture*,2> tex{};
 unsigned stage[2][5]={{2,2,0,1,1},{2,2,0,1,1}};
 WebGLTexture*getTexture2D(unsigned s){return tex[s];}
 DWORD getStageState(unsigned s,unsigned key){return stage[s][key];}
};
class WebGLPipeline {public:
 struct ProgramInfo;
 GLuint m_lastBoundTex[2]={0,0};
 void bindTextures(WebGLDevice*,ProgramInfo*);
 SAMPLER_DECLARATION
 void invalidateTextureBinding(GLuint);
 void uploadTexture(WebGLTexture*t){
  glBindTexture(GL_TEXTURE_2D,t->m_gl.name);
  const unsigned name=t->m_gl.name,content=t->content;
  gxrt::post([name,content]{assert(bound[active]==name);textures[name].content=content;});
  t->m_gl.dirty=false;t->m_gl.samplerKey=~0u;
 }
};
'''.replace('SAMPLER_DECLARATION', sampler_declaration)
    code += extract(pipeline, 'struct WebGLPipeline::ProgramInfo') + ';\n'
    for signature in ('void WebGLPipeline::applySamplerState(', 'void WebGLPipeline::invalidateTextureBinding(',
                      'void WebGLPipeline::bindTextures('):
        code += extract(pipeline, signature) + '\n'
    code += r'''
struct Want {unsigned name,content,min=11,mag=11,s=20,t=20;};
static void draw(WebGLPipeline&p,WebGLDevice&dev,WebGLPipeline::ProgramInfo&prog,Want a,Want b){
 const unsigned name=prog.prog;gxrt::post([name]{program=name;});
 p.bindTextures(&dev,&prog);
 const int loc0=prog.uTex0,loc1=prog.uTex1;
 gxrt::post([a,b,loc0,loc1,name]{
  assert(program==name);
  for(unsigned stage=0;stage<2;++stage){
   Want want=stage?b:a;assert(bound[stage]==want.name);
   if(want.name){const Texture&t=textures[want.name];assert(t.content==want.content);
    assert(t.params[1]==want.min&&t.params[2]==want.mag&&t.params[3]==want.s&&t.params[4]==want.t);}
  }
  if(loc0>=0)assert(uniforms[name][loc0]==0);
  if(loc1>=0)assert(uniforms[name][loc1]==1);
  ++draws;
 });
}
static std::array<unsigned,2> run(bool queued){
 gxrt::g_active=queued;textures={};bound={};for(auto&u:uniforms)u.fill(-1);
 active=program=activeCalls=uniformCalls=bindCalls=paramCalls=draws=0;
 WebGLPipeline p;WebGLDevice dev;
 WebGLPipeline::ProgramInfo first,second,untextured;
 first.prog=1;first.uTex0=2;first.uTex1=5;
 second.prog=2;second.uTex0=1;second.uTex1=6;untextured.prog=3;
 WebGLTexture a,b;a.m_gl.name=11;a.content=101;b.m_gl.name=22;b.content=202;
 dev.tex={&a,&b};draw(p,dev,first,{11,101},{22,202});
 const unsigned beforeActive=activeCalls,beforeUniform=uniformCalls,beforeBind=bindCalls,beforeParam=paramCalls;
 for(unsigned i=0;i<400;++i)draw(p,dev,first,{11,101},{22,202});
 const unsigned redundantActive=activeCalls-beforeActive,redundantUniform=uniformCalls-beforeUniform;
 assert(bindCalls==beforeBind&&paramCalls==beforeParam);
 // Uniform values belong to each linked program and survive switching back.
 draw(p,dev,second,{11,101},{22,202});draw(p,dev,first,{11,101},{22,202});
 dev.stage[0][D3DTSS_MINFILTER]=1;dev.stage[1][D3DTSS_ADDRESSV]=3;
 draw(p,dev,first,{11,101,10},{22,202,11,11,20,22});
 // CPU edits after posting must not alter an older draw or upload.
 b.content=203;b.m_gl.dirty=true;draw(p,dev,second,{11,101,10},{22,203,11,11,20,22});
 b.content=204;b.m_gl.dirty=true;draw(p,dev,first,{11,101,10},{22,204,11,11,20,22});
 // An unrelated render-target bind invalidates both existing binding-cache entries.
 glBindTexture(GL_TEXTURE_2D,77);p.m_lastBoundTex[0]=p.m_lastBoundTex[1]=~0u;
 draw(p,dev,first,{11,101,10},{22,204,11,11,20,22});
 // Delete a texture, then let GL reuse its name for a new texture.
 gxrt::post([]{for(auto&n:bound)if(n==11)n=0;textures[11]={};});p.invalidateTextureBinding(11);
 WebGLTexture replacement;replacement.m_gl.name=11;replacement.content=303;dev.tex[0]=&replacement;
 draw(p,dev,first,{11,303,10},{22,204,11,11,20,22});
 dev.tex={nullptr,nullptr};draw(p,dev,untextured,{0,0},{0,0});
 // The same object on two stages has texture-object sampler state: retain the original final state.
 dev.stage[0][D3DTSS_MINFILTER]=2;dev.tex={&replacement,&replacement};
 draw(p,dev,first,{11,303,11,11,20,22},{11,303,11,11,20,22});
 replacement.m_levels.resize(3);replacement.m_gl.samplerKey=~0u;
 dev.stage[0][D3DTSS_MIPFILTER]=dev.stage[1][D3DTSS_MIPFILTER]=1;
 dev.stage[0][D3DTSS_ADDRESSV]=3;
 draw(p,dev,second,{11,303,13,11,20,22},{11,303,13,11,20,22});
 dev.stage[0][D3DTSS_MIPFILTER]=dev.stage[1][D3DTSS_MIPFILTER]=2;
 draw(p,dev,first,{11,303,15,11,20,22},{11,303,15,11,20,22});
 if(queued)assert(draws==0);
 gxrt::drain();assert(draws==412);
 printf("%s: 412 draw snapshots preserved; repeat commands active=%u uniforms=%u\n",queued?"queued":"immediate",redundantActive,redundantUniform);
 fflush(stdout);
 return {redundantActive,redundantUniform};
}
int main(){
 auto immediate=run(false),queued=run(true);
 assert(immediate[0]==0&&queued[0]==0 && "unchanged draws must not switch texture units");
 assert(immediate[1]==0&&queued[1]==0 && "immutable program sampler selectors must be sent once");
 puts("PASS: production texture state, program selectors, upload/delete/RT ordering and zero repeated texture commands");
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-texture-state-') as temp:
        work = Path(temp)
        (work / 'GLES3').mkdir()
        (work / 'GLES3/gl3.h').write_text('''#pragma once
#include <cstdint>
using GLint=int;using GLenum=unsigned;using GLbitfield=unsigned;using GLuint64=unsigned long long;using GLsync=void*;
using GLintptr=long;using GLsizeiptr=long;
#define GL_APIENTRY
#define GL_APICALL
''')
        (work / 'gles_thread.h').write_text(read('Core/Libraries/Source/d3d8gles/include/gles_thread.h'))
        source, exe = work / 'test.cpp', work / 'test'
        source.write_text(code)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', '-I', str(work), str(source), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True, env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1'))


if __name__ == '__main__':
    main()
