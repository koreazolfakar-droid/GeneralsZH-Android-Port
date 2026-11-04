#!/usr/bin/env python3
"""Production GLES program-query batch: exact results and one synchronous boundary."""
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def extract(source, signature):
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    source = (ROOT / 'Core/Libraries/Source/d3d8gles/src/gles_dispatch.cpp').read_text()
    function = extract(source, 'void gxrt::getProgramBindings(')
    code = r'''
#include <cassert>
#include <cstddef>
#include <cstring>
#include <cstdio>
using GLuint=unsigned;using GLint=int;
constexpr GLuint GL_INVALID_INDEX=~0u;
static bool worker=false,active=false;static unsigned syncs=0,queries=0;
namespace gxrt {
 template<class F>void sync(F f){++syncs;worker=active;f();worker=false;}
 void getProgramBindings(GLuint,const char*const*,GLint*,size_t,const char*,GLuint*);
}
static GLint d3d8gles_pfn_glGetUniformLocation(GLuint p,const char*name){
 assert(worker==active&&p==17);++queries;
 return !strcmp(name,"missing")?-1:int(strlen(name));
}
static GLuint d3d8gles_pfn_glGetUniformBlockIndex(GLuint p,const char*name){
 assert(worker==active&&p==17);++queries;
 return !strcmp(name,"ViewProjBlock")?3:GL_INVALID_INDEX;
}
'''
    code += function
    code += r'''
int main(){
 for(bool threaded:{false,true}){
  active=threaded;syncs=queries=0;
  const char*names[]={"uWorld","uViewportPos","missing","uMat[0]","uLit[0]"};
  GLint locations[5]={};GLuint block=0;
  gxrt::getProgramBindings(17,names,locations,5,"ViewProjBlock",&block);
  assert(syncs==1&&queries==6&&block==3);
  assert(locations[0]==6&&locations[1]==12&&locations[2]==-1&&locations[3]==7&&locations[4]==7);
  gxrt::getProgramBindings(17,nullptr,nullptr,0,"absent",&block);
  assert(syncs==2&&queries==7&&block==GL_INVALID_INDEX);
 }
 puts("PASS: production uniform/block results including absent bindings; one ordered round trip for all queries");
}
'''
    code = '#include <initializer_list>\n' + code
    with tempfile.TemporaryDirectory(prefix='gx-bindings-') as temp:
        cpp, exe = Path(temp)/'test.cpp', Path(temp)/'test'
        cpp.write_text(code)
        subprocess.run([os.environ.get('CXX','c++'),'-std=c++17','-O1','-g','-fsanitize=address,undefined',str(cpp),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    pipeline=(ROOT/'Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp').read_text()
    program=extract(pipeline,'WebGLPipeline::ProgramInfo *WebGLPipeline::getProgram(')
    assert 'gxrt::getProgramBindings(' in program
    assert 'glGetUniformLocation(' not in program and 'glGetUniformBlockIndex(' not in program


if __name__=='__main__':
    main()
