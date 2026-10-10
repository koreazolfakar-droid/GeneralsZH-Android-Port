// GeneralsX @test Codex 10/10/2026 Host adapters for real production archive functions.
#include <algorithm>
#include <array>
#include <cassert>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <utility>
#include <vector>

using Bool = bool;
using Char = char;
using Int = int;
using FileInstance = unsigned char;
#define TRUE true
#define FALSE false
#define RTS_ZEROHOUR 1
#define NEW new
#define MAYBE_UNUSED [[maybe_unused]]
#define DEBUG_LOG(x) ((void)0)
#define DEBUG_ASSERTLOG(value, message) assert(value)
#define USE_PERF_TIMER(x)
#define ENABLE_FILESYSTEM_EXISTENCE_CACHE 1
using std::max;
using std::min;

class AsciiString {
    std::string value;
public:
    static const AsciiString TheEmptyString;
    AsciiString() = default;
    AsciiString(const char* text): value(text) {}
    static AsciiString temporary(const char* text) { return AsciiString(text); }
    const char* str() const { return value.c_str(); }
    bool isEmpty() const { return value.empty(); }
    bool isNotEmpty() const { return !value.empty(); }
    void clear() { value.clear(); }
    void concat(char c) { value += c; }
    void concat(const AsciiString& s) { value += s.value; }
    char getCharAt(size_t index) const { return value.at(index); }
    const char* find(char c) const { return std::strchr(str(), c); }
    void toLower() { std::transform(value.begin(), value.end(), value.begin(),
        [](unsigned char c) { return static_cast<char>(std::tolower(c)); }); }
    int compareNoCase(const AsciiString& other) const {
        auto a = *this, b = other; a.toLower(); b.toLower(); return a.value.compare(b.value);
    }
    bool endsWith(const AsciiString& suffix) const {
        return value.size() >= suffix.value.size() && value.compare(value.size()-suffix.value.size(), suffix.value.size(), suffix.value)==0;
    }
    bool endsWithNoCase(const AsciiString& suffix) const {
        auto a=*this, b=suffix; a.toLower(); b.toLower(); return a.endsWith(b);
    }
    bool startsWithNoCase(const AsciiString& prefix) const {
        auto a=*this, b=prefix; a.toLower(); b.toLower(); return a.value.rfind(b.value,0)==0;
    }
    bool nextToken(AsciiString* token, const char* delimiters) {
        size_t start=value.find_first_not_of(delimiters);
        if(start==std::string::npos) { token->clear(); value.clear(); return false; }
        size_t end=value.find_first_of(delimiters,start);
        token->value=value.substr(start,end-start);
        value=end==std::string::npos ? "" : value.substr(end+1);
        return true;
    }
    bool operator<(const AsciiString& rhs) const { return value < rhs.value; }
};
const AsciiString AsciiString::TheEmptyString;
struct NoCase { bool operator()(const AsciiString& a,const AsciiString& b) const { return a.compareNoCase(b)<0; } };
using FilenameList = std::set<AsciiString,NoCase>;
using FilenameListIter = FilenameList::iterator;
static std::string physical(const char* name) {
    std::string path(name); std::replace(path.begin(),path.end(),'\\','/'); return path;
}
static bool equalsIgnoreCase(const char* a,const char* b) { return AsciiString(a).compareNoCase(b)==0; }
static uint32_t betoh(uint32_t n) { return __builtin_bswap32(n); }
class File {
    FILE* handle;
public:
    enum { READ=1, BINARY=2, WRITE=4, CREATE=8 };
    Int getAccess() const { return READ; }
    explicit File(FILE* fp):handle(fp) {}
    long size() { long pos=ftell(handle); fseek(handle,0,SEEK_END); long end=ftell(handle); fseek(handle,pos,SEEK_SET); return end; }
    int read(void* target,size_t size) { return static_cast<int>(fread(target,1,size,handle)); }
    std::string payload(uint32_t offset,uint32_t length) {
        std::string value(length,'\0'); fseek(handle,offset,SEEK_SET); assert(read(value.data(),length)==static_cast<int>(length)); return value;
    }
    void close() { fclose(handle); delete this; }
};
struct ArchivedFileInfo {
    AsciiString m_filename,m_archiveFilename;
    uint32_t m_offset=0,m_size=0;
};
class ArchiveFile;
struct DetailedArchivedDirectoryInfo;
using ArchivedFileInfoMap = std::map<AsciiString,ArchivedFileInfo>;
using DetailedArchivedDirectoryInfoMap = std::map<AsciiString,DetailedArchivedDirectoryInfo>;
struct DetailedArchivedDirectoryInfo {
    AsciiString m_directoryName;
    DetailedArchivedDirectoryInfoMap m_directories;
    ArchivedFileInfoMap m_files;
};
struct ArchivedDirectoryInfo;
using ArchivedFileLocationMap = std::multimap<AsciiString,ArchiveFile*>;
using ArchivedDirectoryInfoMap = std::map<AsciiString,ArchivedDirectoryInfo>;
using ArchiveFileMap = std::map<AsciiString,ArchiveFile*>;
struct ArchivedDirectoryInfo {
    AsciiString m_path,m_directoryName;
    ArchivedDirectoryInfoMap m_directories;
    ArchivedFileLocationMap m_files;
};
class ArchiveFile {
    AsciiString name;
protected:
    File* m_file;
    DetailedArchivedDirectoryInfo m_rootDirectory;
public:
    ArchiveFile();
    virtual ~ArchiveFile();
    void setName(const char* n) { name=n; }
    AsciiString getName() { return name; }
    void attachFile(File*);
    void addFile(const AsciiString&, const ArchivedFileInfo*);
    const ArchivedFileInfo* getArchivedFileInfo(const AsciiString&) const;
    void getFileListInDirectory(const AsciiString&,const AsciiString&,const AsciiString&,FilenameList&,Bool) const;
    void getFileListInDirectory(const DetailedArchivedDirectoryInfo*,const AsciiString&,const AsciiString&,FilenameList&,Bool) const;
    File* openFile(const char* path,Int) {
        const auto info=getArchivedFileInfo(path);
        if(!info) return nullptr;
        const auto value=m_file->payload(info->m_offset,info->m_size);
        FILE* fp=tmpfile(); assert(fp);
        assert(fwrite(value.data(),1,value.size(),fp)==value.size()); rewind(fp);
        return new File(fp);
    }
    std::string payload(const char* path) {
        auto info=getArchivedFileInfo(path); assert(info); return m_file->payload(info->m_offset,info->m_size);
    }
};
class StdBIGFile: public ArchiveFile {
public:
    StdBIGFile(const char* name,const AsciiString&) { setName(name); }
};
namespace stl {
template<class Map> struct const_range {
    typename Map::const_iterator selected,end;
    bool valid() const { return selected!=end; }
    typename Map::const_iterator get() const { return selected; }
};
template<class Map> const_range<Map> get_range(const Map& m,const AsciiString& key,FileInstance instance) {
    auto r=m.equal_range(key);
    while(instance-- && r.first!=r.second) ++r.first;
    return {r.first,r.second};
}
}
class StdLocalFileSystem {
public:
    File* openFile(const char* filename,Int,size_t=0) {
        FILE* f=fopen(physical(filename).c_str(),"rb"); return f ? new File(f) : nullptr;
    }
    Bool doesFileExist(const char* filename) { return std::filesystem::exists(physical(filename)); }
    void getFileListInDirectory(const AsciiString&,const AsciiString&,const AsciiString&,FilenameList&,Bool) const;
};
static StdLocalFileSystem local;
static StdLocalFileSystem* TheLocalFileSystem=&local;
struct GlobalData {
    AsciiString m_modDir,m_modBIG;
    AsciiString getPath_UserData() { return ""; }
};
static GlobalData globals;
static GlobalData* TheGlobalData=&globals;
static const char* kCommunityPatchDisableMarker="gx_no_community_patch.txt";
static const char* kCommunityPatchWithModsMarker="gx_community_patch_with_mods.txt";
class ArchiveFileSystem {
public:
    ArchiveFileSystem();
    virtual ~ArchiveFileSystem();
    ArchiveFileMap m_archiveFileMap;
    ArchivedDirectoryInfo m_rootDirectory;
    std::set<ArchiveFile*> m_primaryGameArchives;
    Bool m_standaloneModOverlayActive=FALSE;
    struct ArchivedDirectoryInfoResult {
        ArchivedDirectoryInfo* dirInfo=nullptr;
        AsciiString lastToken;
        Bool valid() const { return dirInfo!=nullptr; }
    };
    ArchivedDirectoryInfoResult getArchivedDirectoryInfo(const Char*);
    void loadIntoDirectoryTree(ArchiveFile*,Bool=FALSE,Bool=FALSE);
    virtual ArchiveFile* openArchiveFile(const Char*)=0;
    virtual Bool loadBigFilesFromDirectory(AsciiString,AsciiString,Bool=FALSE)=0;
    void loadMods();
    File* openFile(const Char*,Int,FileInstance=0);
    ArchiveFile* getArchiveFile(const AsciiString&,FileInstance=0) const;
    Bool doesFileExist(const Char*,FileInstance=0) const;
    void getFileListInDirectory(const AsciiString&,const AsciiString&,const AsciiString&,FilenameList&,Bool) const;
};
class StdBIGFileSystem:public ArchiveFileSystem {
public:
    ArchiveFile* openArchiveFile(const Char*) override;
    Bool loadBigFilesFromDirectory(AsciiString,AsciiString,Bool=FALSE) override;
};
static ArchiveFileSystem* TheArchiveFileSystem=nullptr;
class FastCriticalSectionClass {
public:
    class LockClass { public: explicit LockClass(FastCriticalSectionClass&) {} };
};
class FileSystem {
    struct FileExistData {
        FileInstance instanceExists=0,instanceDoesNotExist=255;
    };
    using FileExistMap=std::map<AsciiString,FileExistData>;
    mutable FileExistMap m_fileExist;
    mutable FastCriticalSectionClass m_fileExistMutex;
public:
    File* openFile(const Char*,Int=File::READ,size_t=0,FileInstance=0);
    Bool doesFileExist(const Char*,FileInstance=0) const;
};
#include "production.inc"

int main(int argc,char** argv) {
    assert(argc==5);
    const std::string selection=argv[2],expected=argv[4];
    // Match Android: cwd is the retail game root, -mod is an absolute path.
    std::filesystem::current_path(argv[1]);
    StdBIGFileSystem fs;
    TheArchiveFileSystem=&fs;
    FileSystem vfs;
    assert(fs.loadBigFilesFromDirectory(argv[1],"*.big"));
    for(auto& item:fs.m_archiveFileMap) fs.m_primaryGameArchives.insert(item.second);
    assert(fs.loadBigFilesFromDirectory(argv[3],"*.big"));
    if(selection!="vanilla" && selection!="manual") {
        const auto mod=(std::filesystem::path(argv[1])/selection).string();
        if(std::filesystem::is_directory(mod)) globals.m_modDir=(mod+"/").c_str();
        else globals.m_modBIG=mod.c_str();
    }
    fs.loadMods();
    auto payload=[&](const char* path) {
        auto file=vfs.openFile(path); assert(file);
        std::string value(file->size(),'\0');
        assert(file->read(value.data(),value.size())==static_cast<int>(value.size()));
        file->close(); return value;
    };
    assert(!vfs.openFile("Art/Textures/ShieldMissing.tga"));
    assert(!vfs.doesFileExist("Art/Textures/ShieldProbeOnly.tga"));
    assert(!vfs.doesFileExist("Art/Textures/ShieldProbeOnly.tga")); // Negative cache hit.
    assert(vfs.doesFileExist("Art/Textures/Shield.tga"));
    assert(vfs.doesFileExist("Art/Textures/Shield.tga")); // Positive cache hit.
    if(std::filesystem::exists("loose-shield.txt")) assert(payload("loose-shield.txt")=="loose");
    assert(!fs.getArchiveFile("Data/INI/InactiveOnly.ini"));
    assert(payload("Data/INI/SiblingOnly.ini")=="sibling");
    if(expected=="nested") {
        assert(payload("Art/W3D/Nested.w3d")=="nested-model");
        assert(payload("Data/INI/Nested.ini")=="nested-ini");
    } else if(expected=="single-big") {
        assert(payload("Art/W3D/Vehicle.w3d")==expected);
    } else {
        for(auto path:{"dAtA/Ini/Object/Vehicle.ini","Art\\W3D\\Vehicle.w3d","Art/W3D/Infantry.w3d",
                       "Art/W3D/InfantryRun.w3d","Art/Textures/Shield.tga","Art/Textures/Vehicle.dds",
                       "Data/INI/FXList.ini","Data/INI/ParticleSystem.ini"}) {
            assert(payload(path)==expected); std::cout<<path<<"="<<payload(path)<<"\n";
        }
        assert((fs.getArchiveFile("Data/INI/OldOnly.ini")!=nullptr)==(expected=="vanilla"));
        FilenameList listing;
        listing.insert("loose-only.ini");
        fs.getFileListInDirectory("","Data\\INI\\","*.ini",listing,TRUE);
        assert(listing.count("loose-only.ini")==1);
        assert(listing.count("Data\\INI\\OldOnly.ini")==static_cast<size_t>(expected=="vanilla"));
        if(expected!="vanilla") {
            assert(payload("Data/INI/NewOnly.ini")=="replacement");
            auto second=fs.getArchiveFile("Art/W3D/Vehicle.w3d",1);
            assert(second && second->payload("Art/W3D/Vehicle.w3d")=="wrong-last");
        }
    }
}
