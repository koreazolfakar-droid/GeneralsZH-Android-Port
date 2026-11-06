#!/usr/bin/env python3
"""Execute the production FFmpeg-frame collector with packed/planar adapters."""
from pathlib import Path
import subprocess,sys,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'Core/GameEngineDevice/Source/OpenALAudioDevice/OpenALAudioCache.cpp').read_text()
a=s.index('Bool OpenALAudioFileCache::decodeFFmpeg(');b=s.index('\n//-------------------------------------------------------------------------------------------------',a)
body=s[a:b]
if '--without-accounting' in sys.argv:
 body=body.replace('file->m_decodedBytes = audioData.size();','(void)file;')
code=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <functional>
#include <vector>
using Bool=bool;
enum AVSampleFormat { PACKED=0, PLANAR=1 };
constexpr int AVMEDIA_TYPE_AUDIO=1;
struct AVFrame {int nb_samples=2,format=0;uint8_t*data[2]{};};
int av_sample_fmt_is_planar(AVSampleFormat f){return f==PLANAR;}
struct FFmpegFile {
 AVFrame frame; bool pending=true;void*user=nullptr;
 std::function<void(AVFrame*,int,int,void*)> cb;
 int getSizeForSamples(int n){return n*4;}int getNumChannels(){return 2;}int getBytesPerSample(){return 2;}int getSampleRate(){return 22050;}
 void setFrameCallback(decltype(cb) f){cb=f;}void setUserData(void*p){user=p;}
 bool decodePacket(){if(!pending)return false;pending=false;cb(&frame,0,AVMEDIA_TYPE_AUDIO,user);return true;}
};
struct OpenAudioFile {FFmpegFile*m_ffmpegFile=nullptr;unsigned m_buffer=1,m_fileSize=0;int m_totalSamples=0;float m_duration=0;uint64_t m_decodedBytes=0;};
struct OpenALAudioManager {static int getALFormat(int,int){return 0;}};
std::vector<uint8_t> output;
void alBufferData(unsigned,int,const void*data,size_t size,int){auto*p=static_cast<const uint8_t*>(data);output.assign(p,p+size);}
struct OpenALAudioFileCache {Bool decodeFFmpeg(OpenAudioFile*);};
''' + body + r'''
int main(){
 OpenALAudioFileCache cache;uint8_t packed[]={1,2,5,6,3,4,7,8};uint8_t left[]={1,2,3,4},right[]={5,6,7,8};
 for(bool planar:{false,true}){FFmpegFile ff;ff.frame.format=planar?PLANAR:PACKED;ff.frame.data[0]=planar?left:packed;ff.frame.data[1]=right;OpenAudioFile f;f.m_ffmpegFile=&ff;assert(cache.decodeFFmpeg(&f));assert(f.m_decodedBytes==8 && f.m_fileSize==8 && f.m_totalSamples==2);assert(output==std::vector<uint8_t>(packed,packed+8));}
}
'''
with tempfile.TemporaryDirectory() as temp:
 p=Path(temp)/'test.cpp';p.write_text(code);exe=Path(temp)/'test'
 subprocess.run(['c++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: production packed and planar FFmpeg frames preserve PCM bytes and accounting')
