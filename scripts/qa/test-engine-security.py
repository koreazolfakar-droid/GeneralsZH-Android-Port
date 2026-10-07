#!/usr/bin/env python3
"""Host tests of exact production parser/save functions and Online message bounds.
Not a complete engine/device test. No native dependencies are rebuilt.
"""
# GeneralsX @bugfix Codex 07/10/2026 Regression coverage for malformed external inputs.
import os, pathlib, subprocess, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
def function(source, signature):
    start=source.index(signature);opening=source.index('{',start);depth=1;end=opening+1
    while depth:
        depth+=(source[end]=='{')-(source[end]=='}');end+=1
    return source[start:end]
def compile_run(name, code, work, sanitizer=False):
    source=work/(name+'.cpp');source.write_text(code)
    command=[os.environ.get('CXX','c++'),'-std=c++17','-Wall','-Wextra','-Werror','-g','-O0',str(source),'-o',str(work/name)]
    if sanitizer:command+=['-fsanitize=address,undefined','-fno-omit-frame-pointer']
    subprocess.run(command,check=True);subprocess.run([str(work/name)],check=True)
    print('PASS:',name)
COMMON=r'''
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include <memory>
#include <array>
#include <algorithm>
#include <filesystem>
#include <chrono>
using Int=int;using Char=char;
#define NEW new
struct AsciiString {std::string value;AsciiString()=default;AsciiString(const char*p):value(p){};const char*str()const{return value.c_str();}void toLower(){std::transform(value.begin(),value.end(),value.begin(),[](unsigned char c){return std::tolower(c);});}AsciiString&operator=(const char*p){value=p;return *this;}static AsciiString TheEmptyString;};
AsciiString AsciiString::TheEmptyString;
'''
BIG=r'''
uint32_t betoh(uint32_t v){return __builtin_bswap32(v);}
int closed=0;
struct File{enum{READ=1,BINARY=2};std::vector<char> bytes;size_t pos=0;Int virtualSize=0;Int size(){return virtualSize?virtualSize:bytes.size();}Int read(void*p,Int n){if(n<0 || pos+size_t(n)>bytes.size())return 0;memcpy(p,bytes.data()+pos,n);pos+=n;return n;}void close(){++closed;delete this;}};
struct FS{std::vector<char> bytes;Int size=0;File*openFile(const char*,int){return new File{bytes,0,size};}} fs;FS*TheLocalFileSystem=&fs;
struct ArchivedFileInfo {AsciiString m_archiveFilename,m_filename;Int m_offset=0,m_size=0;};
struct ArchiveFile {File*file=nullptr;std::vector<ArchivedFileInfo>entries;std::vector<std::string>paths;virtual~ArchiveFile(){if(file)file->close();}void addFile(AsciiString path,const ArchivedFileInfo*info){entries.push_back(*info);paths.push_back(path.str());}void attachFile(File*p){file=p;}};
struct StdBIGFile:ArchiveFile{StdBIGFile(const char*,AsciiString){}};
struct StdBIGFileSystem {ArchiveFile*openArchiveFile(const Char*);};
void be(std::vector<char>&v,uint32_t n){for(int shift=24;shift>=0;shift-=8)v.push_back(n>>shift);}
std::vector<char> big(const std::string&name,const char*magic="BIGF") {std::vector<char>v(magic,magic+4);be(v,0);be(v,1);be(v,25+name.size());be(v,25+name.size());be(v,1);v.insert(v.end(),name.begin(),name.end());v.push_back(0);v.push_back('x');return v;}
void rejected(std::vector<char>v){fs.bytes=v;fs.size=0;int before=closed;std::unique_ptr<ArchiveFile>a(StdBIGFileSystem().openArchiveFile("mod.big"));assert(!a && closed==before+1);}
'''
BIGTEST=r'''
int main(){
 for(const char*magic:{"BIGF","BIG4"})for(size_t len:{size_t(4),size_t(1100),size_t(4095)}){std::string name(len,'a');fs.bytes=big("dir/"+name,magic);if(name.size()+4>4095){rejected(fs.bytes);continue;}std::unique_ptr<ArchiveFile>a(StdBIGFileSystem().openArchiveFile("mod.big"));assert(a && a->entries.size()==1 && a->entries[0].m_filename.value==name && a->paths[0]=="dir/");}
 fs.bytes=big("a");fs.size=1880000000;{std::unique_ptr<ArchiveFile>a(StdBIGFileSystem().openArchiveFile("large.big"));assert(a);}fs.size=0;
 auto valid=big("file");for(size_t n=0;n<valid.size()-1;++n)rejected({valid.begin(),valid.begin()+n});
 rejected(big(std::string(4096,'a')));rejected(big(""));rejected(big("dir/"));
 auto offset=valid;offset[16]=char(0xff);rejected(offset);
 auto size=valid;size[20]=char(0xff);rejected(size);
 auto header=valid;header[12]=char(0xff);rejected(header);
 auto count=valid;count[8]=char(0xff);rejected(count);
 // Deterministic malformed-table corpus: no simulation RNG or live input involved.
 for(size_t i=0;i<valid.size();++i){auto mutated=valid;mutated[i]=char(0xff);fs.bytes=mutated;std::unique_ptr<ArchiveFile>a(StdBIGFileSystem().openArchiveFile("mutated.big"));}
}
'''
SAVE=r'''
using XferBlockSize=Int;
enum{XFER_READ_ERROR=1,SC_INVALID_DATA=2};
#define DEBUG_ASSERTCRASH(c,m) ((void)0)
#define DEBUG_CRASH(m) ((void)0)
struct Xfer{FILE*m_fileFP=nullptr;AsciiString m_identifier;int failAfter=-1,reads=0;bool ended=false;virtual~Xfer()=default;virtual Int beginBlock()=0;void xferUser(void*p,Int n){if(failAfter>=0 && reads++==failAfter)throw XFER_READ_ERROR;if(fread(p,n,1,m_fileFP)!=1)throw XFER_READ_ERROR;}void endBlock(){ended=true;}};
struct XferLoad:Xfer{Int beginBlock()override;};
void create(const std::string&path,Int declared,const std::string&payload){FILE*f=fopen(path.c_str(),"wb");assert(f);fwrite(&declared,sizeof declared,1,f);fwrite(payload.data(),1,payload.size(),f);fclose(f);}
std::string read(const std::string&p){FILE*f=fopen(p.c_str(),"rb");assert(f);std::string out;char b[8192];size_t n;while((n=fread(b,1,sizeof b,f)))out.append(b,n);fclose(f);return out;}
'''
SAVETEST=r'''
int main(){auto dir=std::filesystem::current_path();const std::string save=(dir/"fixture.sav").string(),map=(dir/"destination.map").string();
 for(Int length:{-1,2147483647,20}){create(save,length,"abc");XferLoad x;x.m_fileFP=fopen(save.c_str(),"rb");bool rejected=false;try{x.beginBlock();}catch(...){rejected=true;}fclose(x.m_fileFP);assert(rejected);}
 for(size_t size:{size_t(1),size_t(65535),size_t(65536),size_t(65537),size_t(2097152)}){std::string payload(size,'x');create(save,payload.size(),payload);XferLoad x;x.m_fileFP=fopen(save.c_str(),"rb");extractAndSaveMap(AsciiString(map.c_str()),&x);fclose(x.m_fileFP);assert(read(map)==payload && x.ended);}
 std::string old=read(map);create(save,131072,std::string(131072,'z'));XferLoad fail;fail.failAfter=1;fail.m_fileFP=fopen(save.c_str(),"rb");bool rejected=false;try{extractAndSaveMap(AsciiString(map.c_str()),&fail);}catch(...){rejected=true;}fclose(fail.m_fileFP);assert(rejected && read(map)==old);
 for(auto&entry:std::filesystem::directory_iterator(dir))assert(entry.path().filename().string().find(".loading-")==std::string::npos);
 create(save,0,"");XferLoad empty;empty.m_fileFP=fopen(save.c_str(),"rb");rejected=false;try{extractAndSaveMap(AsciiString(map.c_str()),&empty);}catch(...){rejected=true;}fclose(empty.m_fileFP);assert(rejected && read(map)==old);
 std::filesystem::remove(save);std::filesystem::remove(map);
}
'''
def main():
    parser=function((ROOT/'Core/GameEngineDevice/Source/StdDevice/Common/StdBIGFileSystem.cpp').read_text(),'ArchiveFile * StdBIGFileSystem::openArchiveFile(')
    block=function((ROOT/'Core/GameEngine/Source/Common/System/XferLoad.cpp').read_text(),'Int XferLoad::beginBlock()')
    extract=function((ROOT/'GeneralsMD/Code/GameEngine/Source/Common/System/SaveGame/GameStateMap.cpp').read_text(),'static void extractAndSaveMap(')
    with tempfile.TemporaryDirectory(prefix='gx-security-') as temporary:
        work=pathlib.Path(temporary)
        compile_run('big-parser',COMMON+BIG+parser+BIGTEST,work,True)
        # A temporary work directory contains every test-created save/map.
        previous=os.getcwd();os.chdir(work)
        try:compile_run('save-block-streaming',COMMON+SAVE+block+extract+SAVETEST,work,True)
        finally:os.chdir(previous)
        bounds=ROOT/'GeneralsMD/Code/GameEngine/Include/GameNetwork/GeneralsOnline/HTTP/OnlineMessageBounds.h'
        test='#include <cassert>\n#include <limits>\n#include "'+str(bounds)+'"\n'+r'''
int main(){std::vector<char>b;assert(GXAppendOnlineFragment(b,"abc",3));assert(GXAppendOnlineFragment(b,"def",3));assert(std::string(b.begin(),b.end())=="abcdef");assert(!GXAppendOnlineFragment(b,nullptr,1));assert(!GXAppendOnlineFragment(b,"x",std::numeric_limits<size_t>::max()));std::vector<char>data(GX_MAX_ONLINE_MESSAGE_BYTES,'x');b.clear();assert(GXAppendOnlineFragment(b,data.data(),data.size()));assert(!GXAppendOnlineFragment(b,"x",1));assert(b.size()==GX_MAX_ONLINE_MESSAGE_BYTES);b.clear();assert(GXAppendOnlineFragment(b,nullptr,0));}
'''
        compile_run('websocket-fragments','#include <string>\n'+test,work,True)
if __name__=='__main__':main()
