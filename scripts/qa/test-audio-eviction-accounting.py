#!/usr/bin/env python3
"""Exercise the real eviction selection and decoded-size bookkeeping."""
from pathlib import Path
import subprocess,sys,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'Core/GameEngineDevice/Source/OpenALAudioDevice/OpenALAudioCache.cpp').read_text()
a=s.index('Bool OpenALAudioFileCache::freeEnoughSpaceForSample(')
body=s[a:]
start=s.index('\topenedAudioFile.m_openCount = 1;')
end=s.index('\n}',start)
insertion=s[start:end]
if '--without-insertion' in sys.argv:
 insertion=insertion.replace('m_currentlyDecodedSize += openedAudioFile.m_decodedBytes;', '(void)openedAudioFile;')
if '--without-accounting' in sys.argv:
 body=body.replace('m_currentlyDecodedSize -= itToErase->second.m_decodedBytes;', '(void)itToErase;')
code=r'''
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <limits>
#include <list>
#include <map>
#include <string>
#include <utility>
#include <vector>
using Int=int;using UnsignedInt=unsigned;using Bool=bool;using AsciiString=std::string;
#define TRUE true
#define FALSE false
struct AudioEventInfo {int m_priority=0;};
struct OpenAudioFile {unsigned m_openCount=0,m_fileSize=0,m_lastUse=0,m_buffer=0;uint64_t m_decodedBytes=0;const AudioEventInfo*m_eventInfo=nullptr;};
using OpenFilesHash=std::map<AsciiString,OpenAudioFile>;using OpenFilesHashIt=OpenFilesHash::iterator;
struct Stats {unsigned evicted=0,evictedActive=0;};
struct OpenALAudioFileCache {
 OpenFilesHash m_openFiles;unsigned m_currentlyUsedSize=120,m_maxSize=100,m_useClock=0;uint64_t m_currentlyDecodedSize=40;Stats m_stats;unsigned releases=0;
 void releaseOpenAudioFile(OpenAudioFile*){++releases;}
 unsigned insert(const AsciiString&,OpenAudioFile);
 Bool freeEnoughSpaceForSample(const OpenAudioFile&);
};
''' + body + '\nunsigned OpenALAudioFileCache::insert(const AsciiString& strToFind, OpenAudioFile openedAudioFile){\n' + insertion + '\n}\n' + r'''
int main(){
 OpenALAudioFileCache added;added.m_currentlyDecodedSize=0;OpenAudioFile fresh;fresh.m_buffer=7;fresh.m_decodedBytes=18;assert(added.insert("fresh",fresh)==7);assert(added.m_currentlyDecodedSize==18 && added.m_openFiles.at("fresh").m_openCount==1);
 AudioEventInfo low{1},high{10};OpenAudioFile incoming;incoming.m_eventInfo=&high;
 OpenALAudioFileCache c;
 OpenAudioFile idle;idle.m_fileSize=20;idle.m_decodedBytes=24;idle.m_lastUse=1;
 OpenAudioFile active;active.m_openCount=1;active.m_fileSize=20;active.m_decodedBytes=16;active.m_eventInfo=&low;
 c.m_openFiles["idle"]=idle;c.m_openFiles["active"]=active;
 assert(c.freeEnoughSpaceForSample(incoming));assert(c.m_currentlyDecodedSize==16 && c.m_stats.evicted==1 && c.m_stats.evictedActive==0 && c.m_openFiles.count("active"));
 c.m_currentlyUsedSize=120;assert(c.freeEnoughSpaceForSample(incoming));assert(c.m_currentlyDecodedSize==0 && c.m_stats.evicted==2 && c.m_stats.evictedActive==1);
 OpenALAudioFileCache pinned;pinned.m_currentlyDecodedSize=16;active.m_eventInfo=&high;pinned.m_openFiles["active"]=active;
 assert(!pinned.freeEnoughSpaceForSample(incoming));assert(pinned.m_currentlyDecodedSize==16 && pinned.m_stats.evictedActive==0 && pinned.releases==0);
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'test.cpp';p.write_text(code);exe=Path(tmp)/'test'
 subprocess.run(['c++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: idle eviction, active-voice eviction, pinned failure and PCM cache accounting')
