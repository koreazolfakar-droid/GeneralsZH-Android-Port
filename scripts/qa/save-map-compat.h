// GeneralsX @bugfix Codex 05/10/2026 Host filesystem doubles for save cleanup failure tests.

#include <cstring>
#include <string>
#include <cassert>
using DWORD=unsigned; using Bool=bool; using Char=char; using HANDLE=int;
constexpr int _MAX_PATH=260, INVALID_HANDLE_VALUE=-1, FILE_ATTRIBUTE_DIRECTORY=1;
constexpr bool TRUE=true,FALSE=false;
struct AsciiString {std::string s; void clear(){s.clear();} void set(const char*p){s=p;} bool isEmpty(){return s.empty();} const char*str(){return s.c_str();}};
struct State {AsciiString getSaveDirectory(){return {"Save/"};}} state; State*TheGameState=&state;
struct WIN32_FIND_DATA {int dwFileAttributes=0; char cFileName[32]="scratch.map";};
int scenario=0,deletes=0,scans=0; std::string cwd="assets";
DWORD GetCurrentDirectory(int,char*b){if(scenario==1)return 0; strcpy(b,cwd.c_str());return cwd.size();}
int SetCurrentDirectory(const char*p){if(scenario==2 && std::string(p)=="Save/")return 0;cwd=p;return 1;}
HANDLE FindFirstFile(const char*,WIN32_FIND_DATA*){scans++;return scenario==3?-1:1;}
int FindNextFile(HANDLE,WIN32_FIND_DATA*){return 0;}
void FindClose(HANDLE){}
int stricmp(const char*a,const char*b){return strcasecmp(a,b);}
void DeleteFile(const char*){assert(cwd=="Save/");deletes++;}
struct GameStateMap {void clearScratchPadMaps();};
