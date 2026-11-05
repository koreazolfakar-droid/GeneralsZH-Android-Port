#!/usr/bin/env python3
"""Exercise the production PCM/IMA WAV decoder and decoded byte accounting."""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'Core/GameEngineDevice/Source/OpenALAudioDevice/OpenALAudioCache.cpp').read_text()
a=s.index('namespace {\n\ninline UnsignedInt readLE16');b=s.index('} // namespace',a)+len('} // namespace')
helpers=s[a:b]
a=s.index('Bool OpenALAudioFileCache::decodeWavNative(');b=s.index('\n//-------------------------------------------------------------------------------------------------',a)
decoder=s[a:b]
code=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <vector>
using UnsignedInt=unsigned;using Bool=bool;using ALsizei=int;
#define FALSE false
#define TRUE true
struct OpenAudioFile {unsigned m_buffer=1,m_channels=0,m_freq=0;int m_totalSamples=0;float m_duration=0;uint64_t m_decodedBytes=0;};
struct OpenALAudioManager {static int getALFormat(unsigned,unsigned){return 0;}};
static size_t uploaded=0;
void alBufferData(unsigned,int,const void*,ALsizei size,unsigned){assert(size>=0);uploaded=size;}
struct OpenALAudioFileCache {Bool decodeWavNative(const uint8_t*,size_t,OpenAudioFile*);};
''' + helpers + '\n' + decoder + r'''
void le16(std::vector<uint8_t>&d,int p,unsigned v){d[p]=v;d[p+1]=v>>8;}
void le32(std::vector<uint8_t>&d,int p,unsigned v){le16(d,p,v);le16(d,p+2,v>>16);}
std::vector<uint8_t> wave(unsigned format,unsigned channels,unsigned bits,unsigned align,unsigned size){
 std::vector<uint8_t>d(44+size);memcpy(d.data(),"RIFF",4);le32(d,4,36+size);memcpy(d.data()+8,"WAVEfmt ",8);le32(d,16,16);le16(d,20,format);le16(d,22,channels);le32(d,24,22050);le32(d,28,22050*align);le16(d,32,align);le16(d,34,bits);memcpy(d.data()+36,"data",4);le32(d,40,size);return d;
}
int main(){OpenALAudioFileCache cache;unsigned expected[]={8,16,18};int i=0;for(auto d:{wave(1,1,8,1,8),wave(1,2,16,4,16),wave(0x11,1,4,8,8)}){OpenAudioFile f;uploaded=0;assert(cache.decodeWavNative(d.data(),d.size(),&f));assert(uploaded==expected[i++] && f.m_decodedBytes==uploaded);} }
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'test.cpp';p.write_text(code);exe=Path(tmp)/'test'
 subprocess.run(['c++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: PCM8, stereo PCM16 and IMA WAV report their actual uploaded PCM byte counts')
