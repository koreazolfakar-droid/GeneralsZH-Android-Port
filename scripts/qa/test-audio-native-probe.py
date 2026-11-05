#!/usr/bin/env python3
"""Exercise the actual native-audio probe against an instrumented file."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'Core/GameEngineDevice/Source/OpenALAudioDevice/OpenALAudioCache.cpp').read_text()
a=s.index('\t// The built-in WAV reader first;')
b=s.index('\n\tif (decodedNatively)',a)
section=s[a:b]
code=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
#include <algorithm>
using Bool=bool; using UnsignedInt=unsigned; using Int=int;
#define FALSE false
struct File { enum { START }; std::vector<uint8_t> data; size_t pos=0,readBytes=0; int read(void* p,int n){size_t k=std::min<size_t>(n,data.size()-pos);memcpy(p,data.data()+pos,k);pos+=k;readBytes+=k;return k;} void seek(int n,int){pos=n;} };
struct OpenAudioFile {};
struct Tester { bool decodeWavNative(const uint8_t* p,size_t n,OpenAudioFile*){return n>=12 && !memcmp(p,"RIFF",4) && !memcmp(p+8,"WAVE",4);} bool probe(File* file){unsigned fileSize=file->data.size();OpenAudioFile openedAudioFile;
''' + section + r'''
 return decodedNatively; }};
int main(){Tester t;File mp3;mp3.data.assign(65536,42);assert(!t.probe(&mp3));assert(mp3.readBytes<=12);File wav;wav.data.assign(4096,0);memcpy(wav.data.data(),"RIFF",4);memcpy(wav.data.data()+8,"WAVE",4);assert(t.probe(&wav));assert(wav.readBytes<=wav.data.size()+12);File shortFile;shortFile.data.assign(4,0);assert(!t.probe(&shortFile));assert(shortFile.readBytes<=12);}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'test.cpp';p.write_text(code);exe=Path(tmp)/'test'
 subprocess.run(['c++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: non-WAV probe bounded to header; WAV remains decoded; short files safe')
