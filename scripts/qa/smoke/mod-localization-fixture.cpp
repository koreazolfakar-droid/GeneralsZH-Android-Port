// GeneralsX @bugfix Codex 05/10/2026 Host harness for production localization selection/parsing.
// Engine API doubles below supply real fixture bytes; no renderer or Android runtime is built.
#include <algorithm>
#include <cassert>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdarg>
#include <filesystem>
#include <fstream>
#include <map>
#include <memory>
#include <string>
#include <strings.h>
#include <vector>
using Bool = bool;
using Char = char;
using WideChar = wchar_t;
using Int = int;
using UnsignedInt = unsigned;
using FileInstance = uint8_t;
using LanguageID = int;
#define TRUE true
#define FALSE false
#define LANGUAGE_ID_US 0
#define NEW new
#define __cdecl
#define stricmp strcasecmp
#define DEBUG_LOG(x) ((void)0)
#define DEBUG_LOG_RAW(x) ((void)0)
#define DEBUG_CRASH(x) assert(false)
#define DEBUG_ASSERTCRASH(condition, message) assert(condition)
#define ARRAY_SIZE(array) (sizeof(array) / sizeof(array[0]))
#define FALLTHROUGH [[fallthrough]]
using std::max;
class AsciiString {
    std::string value;
public:
    AsciiString(const char* s = "") : value(s) {}
    const char* str() const { return value.c_str(); }
    int compareNoCase(const AsciiString& other) const { return strcasecmp(str(), other.str()); }
    bool isEmpty() const { return value.empty(); }
    bool isNotEmpty() const { return !value.empty(); }
    void format(const char* fmt, ...) {
        char buffer[8192]; va_list args; va_start(args, fmt);
        vsnprintf(buffer, sizeof(buffer), fmt, args); va_end(args); value = buffer;
    }
};
struct UnicodeString {
    std::wstring value;
    UnicodeString(const wchar_t* s = L"") : value(s) {}
    bool operator==(const UnicodeString& other) const { return value == other.value; }
    void format(const wchar_t* fmt, const char* label) {
        wchar_t buffer[8192]; swprintf(buffer, 8192, fmt, label); value = buffer;
    }
    UnicodeString& operator=(const wchar_t* s) { value = s; return *this; }
    const wchar_t* str() const { return value.c_str(); }
};
std::string folded(std::string path) {
    std::replace(path.begin(), path.end(), '\\', '/');
    std::transform(path.begin(), path.end(), path.begin(), [](unsigned char c) { return std::tolower(c); });
    return path;
}
std::string bytes(const std::filesystem::path& path) {
    std::ifstream stream(path, std::ios::binary);
    return std::string(std::istreambuf_iterator<char>(stream), {});
}
class File {
    std::string data;
    size_t cursor = 0;
public:
    enum { READ = 1, TEXT = 2, BINARY = 4, BUFFERSIZE = 65536, CURRENT = 1 };
    explicit File(std::string input) : data(std::move(input)) {}
    int read(void* output, size_t size) {
        size = std::min(size, data.size() - cursor);
        memcpy(output, data.data() + cursor, size); cursor += size; return size;
    }
    void seek(int offset, int) { cursor += offset; }
    void close() { delete this; }
};
class LocalFileSystem {
public:
    std::filesystem::path resolve(const char* filename) const {
        std::string slashed(filename); std::replace(slashed.begin(), slashed.end(), '\\', '/');
        std::filesystem::path path(slashed), current = path.is_absolute() ? path.root_path() : std::filesystem::current_path();
        for (const auto& part : path.relative_path()) {
            if (std::filesystem::exists(current / part)) { current /= part; continue; }
            bool found = false;
            std::error_code ec;
            for (const auto& entry : std::filesystem::directory_iterator(current, ec)) {
                if (folded(entry.path().filename().string()) == folded(part.string())) {
                    current = entry.path(); found = true; break;
                }
            }
            if (!found) return {};
        }
        return std::filesystem::is_regular_file(current) ? current : std::filesystem::path();
    }
    bool doesFileExist(const char* path) const { return !resolve(path).empty(); }
    File* openFile(const char* path) const {
        auto resolved = resolve(path); return resolved.empty() ? nullptr : new File(bytes(resolved));
    }
};
struct GlobalData { AsciiString m_modBIG, m_modDir; };
class ArchiveFile {
    AsciiString name;
public:
    std::map<std::string, std::string> entries;
    explicit ArchiveFile(const char* path) : name(path) {
        const auto input = bytes(path);
        assert(input.substr(0, 4) == "BIGF" || input.substr(0, 4) == "BIG4");
        auto be32 = [&](size_t offset) {
            uint32_t value = 0; for (size_t i = offset; i < offset + 4; ++i) value = (value << 8) | (unsigned char)input.at(i);
            return value;
        };
        const auto count = be32(8); size_t cursor = 16;
        for (unsigned i = 0; i < count; ++i) {
            auto offset = be32(cursor), size = be32(cursor + 4); cursor += 8;
            auto end = input.find('\0', cursor); assert(end != std::string::npos);
            entries[folded(input.substr(cursor, end - cursor))] = input.substr(offset, size); cursor = end + 1;
        }
    }
    AsciiString getName() { return name; }
};
class ArchiveFileSystem {
public:
    std::vector<std::unique_ptr<ArchiveFile>> archives;
    void mount(const char* path, bool overwrite) {
        auto archive = std::make_unique<ArchiveFile>(path);
        if (overwrite) archives.insert(archives.begin(), std::move(archive));
        else archives.push_back(std::move(archive));
    }
    ArchiveFile* getArchiveFile(const AsciiString& path, FileInstance instance = 0) {
        for (auto& archive : archives) {
            if (archive->entries.count(folded(path.str())) && instance-- == 0) return archive.get();
        }
        return nullptr;
    }
};
LocalFileSystem local;
ArchiveFileSystem archives;
GlobalData globals;
auto* TheLocalFileSystem = &local;
auto* TheArchiveFileSystem = &archives;
auto* TheGlobalData = &globals;
class FileSystem {
public:
    File* openFile(const char* path, int, size_t = File::BUFFERSIZE, FileInstance instance = 0) {
        if (local.doesFileExist(path)) {
            if (instance == 0) return local.openFile(path);
            --instance;
        }
        auto* archive = archives.getArchiveFile(path, instance);
        return archive ? new File(archive->entries.at(folded(path))) : nullptr;
    }
} filesystem;
auto* TheFileSystem = &filesystem;
#include "Common/ModLocalization.h"
#define MAX_UITEXT_LENGTH (10*1024)
#define STRING_FILE 0
#define CSF_FILE 1
#define CSF_ID 0x43534620
#define CSF_LABEL 0x4c424c20
#define CSF_STRING 0x53545220
#define CSF_STRINGWITHWAVE 0x53545257
struct CSFHeader { int id, version, num_labels, num_strings, skip, langid; };
struct StringInfo { AsciiString label; UnicodeString text; AsciiString speech; };
struct StringLookUp { AsciiString* label; StringInfo* info; };
struct NoString { NoString* next; UnicodeString text; };
const Char* g_csfFile = "data/%s/generals.csf";
const Char* g_strFile = "data/%s/generals.str";
AsciiString GetRegistryLanguage() { return "English"; }
static int compareLUT(const void*, const void*);
class GameTextManager {
public:
    Int m_textCount = 0, m_maxLabelLen = 0, m_fallbackTextCount = 0;
    Char m_buffer[MAX_UITEXT_LENGTH] = {}, m_buffer2[MAX_UITEXT_LENGTH] = {}, m_buffer3[MAX_UITEXT_LENGTH] = {};
    WideChar m_tbuffer[MAX_UITEXT_LENGTH*2] = {};
    StringInfo *m_stringInfo = nullptr, *m_fallbackStringInfo = nullptr;
    StringLookUp *m_stringLUT = nullptr, *m_fallbackStringLUT = nullptr;
    Bool m_initialized = FALSE, m_useStringFile = TRUE;
    NoString* m_noStringList = nullptr;
    LanguageID m_language = LANGUAGE_ID_US;
    StringLookUp* m_mapStringLUT = nullptr;
    Int m_mapTextCount = 0;
    UnicodeString m_failed = L"FAILED";
    UnicodeString fetch(const Char*, Bool* = nullptr);
    void init(); void deinit();
    void stripSpaces(WideChar*);
    void removeLeadingAndTrailing(Char*);
    void readToEndOfQuote(File*, Char*, Char*, Char*, Int);
    void translateCopy(WideChar*, Char*);
    Bool readLine(char*, Int, File*);
    Char readChar(File*);
    Bool getStringCount(const char*, Int&, FileInstance = 0);
    Bool getCSFInfo(const Char*, Int&, LanguageID&, FileInstance = 0);
    Bool parseCSF(const Char*, StringInfo*, Int, Int&, FileInstance = 0);
    Bool parseStringFile(const char*, FileInstance = 0, StringInfo* = nullptr);
    ~GameTextManager() { deinit(); }

};
// The runner inserts the current production init, CSF/STR parsers and their helpers here.
#include "production-localization.inc"
int main(int argc, char** argv) {
    assert(argc == 7);
    std::filesystem::current_path(argv[1]);
    if (std::string(argv[2]) != "Vanilla") {
        const auto path = std::filesystem::absolute(argv[2]).string();
        if (std::filesystem::is_directory(path)) {
            globals.m_modDir = (path + "\\").c_str();
            for (const auto& entry : std::filesystem::directory_iterator(path)) {
                if (folded(entry.path().extension().string()) == ".big") archives.mount(entry.path().c_str(), true);
            }
        } else { globals.m_modBIG = path.c_str(); archives.mount(path.c_str(), true); }
    }
    archives.mount("EnglishZH.big", false);
    archives.mount("English.big", false);
    GameTextManager manager; manager.init();
    assert(manager.fetch("FACTION:America").value == std::wstring(argv[3], argv[3] + strlen(argv[3])));
    assert(manager.fetch("GENERAL:Army").value == std::wstring(argv[4], argv[4] + strlen(argv[4])));
    assert(manager.fetch("GUI:VanillaOnly").value == L"Vanilla fallback");
    const auto source = resolveModLocalization("data/English/generals.csf", "English", "generals.csf");
    assert(source.description.str() == std::string(argv[5]));
    const auto strSource = resolveModLocalization("data/English/generals.str", "English", "generals.str");
    assert((source.activeMod || strSource.activeMod) == (std::string(argv[6]) == "true"));
    puts("fixture PASS: custom faction and army text parsed from selected resource");
}
