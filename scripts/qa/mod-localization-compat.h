// GeneralsX @bugfix Codex 05/10/2026 Host-only adapters for production GameText regression tests.
// Filesystem mounts are fixtures; the engine parser/selection/lookup are not replaced.
#pragma once
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <map>
#include <string>
#include <vector>
#include <strings.h>
using Char=char; using WideChar=wchar_t; using Int=int; using UnsignedInt=unsigned; using Bool=bool; using FileInstance=uint8_t; using LanguageID=int;
#define TRUE true
#define FALSE false
#define NEW new
#define __cdecl
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define DEBUG_LOG(x) ((void)0)
#define DEBUG_LOG_RAW(x) ((void)0)
#define DEBUG_CRASH(x) assert(false)
#define DEBUG_ASSERTCRASH(x,y) assert(x)
#define stricmp strcasecmp
#define LANGUAGE_ID_US 0
using std::max;
struct AsciiString { std::string s; AsciiString(){} AsciiString(const char* p):s(p?p:""){} const char* str()const{return s.c_str();} bool isEmpty()const{return s.empty();} bool isNotEmpty()const{return !s.empty();} void toLower(){for(auto&c:s)c=std::tolower((unsigned char)c);} void format(const char*f,...){char b[4096];va_list a;va_start(a,f);vsnprintf(b,sizeof(b),f,a);va_end(a);s=b;} int compareNoCase(const AsciiString&o)const{return strcasecmp(str(),o.str());} };
struct UnicodeString { std::wstring s; UnicodeString(){} UnicodeString(const wchar_t*p):s(p?p:L""){} const wchar_t* str()const{return s.c_str();} bool isEmpty()const{return s.empty();} void set(const wchar_t*p){s=p?p:L"";} bool operator==(const UnicodeString&o)const{return s==o.s;} void format_va(const wchar_t*f,va_list a){wchar_t b[32768];vswprintf(b,32768,f,a);s=b;} void format(const wchar_t*f,...){va_list a;va_start(a,f);format_va(f,a);va_end(a);} };
using AsciiStringVec=std::vector<AsciiString>;
class GameTextInterface { public: virtual ~GameTextInterface(){} virtual void init()=0; virtual void update()=0;virtual void reset()=0;virtual UnicodeString fetch(const Char*,Bool* =nullptr)=0;virtual UnicodeString fetch(AsciiString,Bool* =nullptr)=0;virtual UnicodeString fetchFormat(const Char*,...)=0; virtual UnicodeString fetchOrSubstitute(const Char*,const WideChar*)=0;virtual UnicodeString fetchOrSubstituteFormat(const Char*,const WideChar*,...)=0;virtual UnicodeString fetchOrSubstituteFormatVA(const Char*,const WideChar*,va_list)=0;virtual AsciiStringVec& getStringsWithLabelPrefix(AsciiString)=0;virtual void initMapStringFile(const AsciiString&)=0;};
struct GlobalData { AsciiString m_modBIG,m_modDir; }; inline GlobalData gd; inline GlobalData* TheGlobalData=&gd;
inline AsciiString GetRegistryLanguage(){return "english";}
struct LanguageFilter { void filterLine(UnicodeString&){} }; inline LanguageFilter* TheLanguageFilter=nullptr;
class File { std::vector<unsigned char> bytes; size_t pos=0; public: enum{READ=1,BINARY=2,TEXT=4,BUFFERSIZE=4096,CURRENT=1}; File(std::vector<unsigned char> b):bytes(std::move(b)){} int read(void*p,size_t n){n=std::min(n,bytes.size()-pos);memcpy(p,bytes.data()+pos,n);pos+=n;return n;} void seek(int n,int){pos+=n;}void close(){delete this;} };
inline std::string key(const char*p){std::string s=p;for(auto&c:s){if(c=='\\')c='/';c=std::tolower((unsigned char)c);}return s;}
struct ArchiveFile { AsciiString name; std::map<std::string,std::vector<unsigned char>> entries;AsciiString getName(){return name;} };
struct ArchiveFileSystem { std::vector<ArchiveFile*> archives; ArchiveFile* getArchiveFile(AsciiString p,FileInstance i=0){for(auto*a:archives)if(a->entries.count(key(p.str()))){if(!i--)return a;}return nullptr;} }; inline ArchiveFileSystem afs; inline ArchiveFileSystem* TheArchiveFileSystem=&afs;
struct LocalFileSystem { std::map<std::string,std::vector<unsigned char>> entries;bool doesFileExist(const char*p){return entries.count(key(p));} }; inline LocalFileSystem lfs; inline LocalFileSystem* TheLocalFileSystem=&lfs;
struct FileSystem { std::vector<std::string> opened;File* openFile(const char*p,int,size_t=4096,FileInstance i=0){opened.emplace_back(p);auto k=key(p);if(lfs.entries.count(k)){if(!i)return new File(lfs.entries[k]);--i;}auto*a=afs.getArchiveFile(p,i);return a?new File(a->entries[k]):nullptr;} };inline FileSystem fs;inline FileSystem* TheFileSystem=&fs;

#define FALLTHROUGH [[fallthrough]]
