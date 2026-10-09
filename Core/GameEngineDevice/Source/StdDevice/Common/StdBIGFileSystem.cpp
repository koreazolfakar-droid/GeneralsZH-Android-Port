/*
**	Command & Conquer Generals Zero Hour(tm)
**	Copyright 2025 Electronic Arts Inc.
**
**	This program is free software: you can redistribute it and/or modify
**	it under the terms of the GNU General Public License as published by
**	the Free Software Foundation, either version 3 of the License, or
**	(at your option) any later version.
**
**	This program is distributed in the hope that it will be useful,
**	but WITHOUT ANY WARRANTY; without even the implied warranty of
**	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
**	GNU General Public License for more details.
**
**	You should have received a copy of the GNU General Public License
**	along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

////////////////////////////////////////////////////////////////////////////////
//																																						//
//  (c) 2001-2003 Electronic Arts Inc.																				//
//																																						//
////////////////////////////////////////////////////////////////////////////////

//////// StdBIGFileSystem.h ///////////////////////////
// Stephan Vedder, April 2025
/////////////////////////////////////////////////////////////

#include "Common/AudioAffect.h"
#include "Common/ArchiveFile.h"
#include "Common/ArchiveFileSystem.h"
#include "Common/file.h"
#include "Common/GameAudio.h"
#include "Common/GameMemory.h"
#include "Common/LocalFileSystem.h"
#include "Common/Registry.h"

#include "StdDevice/Common/StdBIGFile.h"
#include "StdDevice/Common/StdBIGFileSystem.h"
#include "Utility/endian_compat.h"

#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <memory>
#include <array>
#include <cstdint>
#include <algorithm>
#include <filesystem>
#include <string>

#if defined(_UNIX)
#include <strings.h>
#endif

#if defined(_UNIX)
#include <unistd.h>
#endif

#if defined(__APPLE__)
#include <mach-o/dyld.h>
#endif

namespace {

static const char* kPrimaryAssetEnvGenerals = "CNC_GENERALS_PATH";
static const char* kPrimaryAssetEnvZH = "CNC_GENERALS_ZH_PATH";
static const char* kPrimaryAssetIniKey = "AssetPath";
static const char* kAssetPathSection = "Paths";

#if RTS_ZEROHOUR
static const char* kBaseGeneralsAssetEnv = "CNC_GENERALS_PATH";
static const char* kBaseGeneralsAssetIniKey = "GeneralsAssetPath";
#endif

static Bool equalsIgnoreCase(const char* lhs, const char* rhs)
{
	if (lhs == nullptr || rhs == nullptr) {
		return FALSE;
	}

#ifdef _WIN32
	return _stricmp(lhs, rhs) == 0;
#else
	return strcasecmp(lhs, rhs) == 0;
#endif
}

// The retail game root can contain the Android Mod Manager's Mods/ folder.
// When enumerating primary/secondary retail BIGs recursively, NEVER mount
// inactive mod archives from that folder as if they were game data. Active mod
// directories still mount explicitly through ArchiveFileSystem::loadMods().
static bool isStandaloneModArchiveBelowRoot(const AsciiString& rootPath, const AsciiString& archivePath)
{
	std::string rootText(rootPath.str());
	std::string fileText(archivePath.str());
	std::replace(rootText.begin(), rootText.end(), '\\', '/');
	std::replace(fileText.begin(), fileText.end(), '\\', '/');
	const std::filesystem::path root = std::filesystem::path(rootText).lexically_normal();
	const std::filesystem::path file = std::filesystem::path(fileText).lexically_normal();

	std::filesystem::path relative;
	if (!rootPath.isEmpty() && root.is_absolute() == file.is_absolute())
		relative = file.lexically_relative(root);
	else if (file.is_relative())
		relative = file;
	if (relative.empty())
		return false;
	const std::filesystem::path::const_iterator segment = relative.begin();
	return segment != relative.end() && equalsIgnoreCase(segment->string().c_str(), "Mods");
}

static const char* trimLeft(const char* text)
{
	while (*text != '\0' && (*text == ' ' || *text == '\t' || *text == '\r' || *text == '\n')) {
		++text;
	}

	return text;
}

static void trimRight(char* text)
{
	Int len = static_cast<Int>(strlen(text));

	while (len > 0) {
		const char c = text[len - 1];
		if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
			text[len - 1] = '\0';
			--len;
			continue;
		}

		break;
	}
}

static Bool extractIniValue(const char* iniPath, const char* sectionName, const char* keyName, AsciiString& value)
{
	FILE* fp = fopen(iniPath, "r");
	if (fp == nullptr) {
		return FALSE;
	}

	Bool inSection = FALSE;
	char line[2048] = { 0 };

	while (fgets(line, sizeof(line), fp) != nullptr) {
		trimRight(line);

		const char* leftTrimmed = trimLeft(line);
		if (*leftTrimmed == '\0' || *leftTrimmed == ';' || *leftTrimmed == '#') {
			continue;
		}

		if (*leftTrimmed == '[') {
			const char* sectionEnd = strchr(leftTrimmed, ']');
			if (sectionEnd != nullptr) {
				char sectionBuffer[256] = { 0 };
				const size_t sectionLen = static_cast<size_t>(sectionEnd - (leftTrimmed + 1));
				if (sectionLen < sizeof(sectionBuffer)) {
					strncpy(sectionBuffer, leftTrimmed + 1, sectionLen);
					sectionBuffer[sectionLen] = '\0';
					trimRight(sectionBuffer);
					const char* sectionNameTrimmed = trimLeft(sectionBuffer);
					inSection = equalsIgnoreCase(sectionNameTrimmed, sectionName);
				}
				else {
					inSection = FALSE;
				}
			}
			else {
				inSection = FALSE;
			}

			continue;
		}

		if (!inSection) {
			continue;
		}

		const char* equalsPos = strchr(leftTrimmed, '=');
		if (equalsPos == nullptr) {
			continue;
		}

		char keyBuffer[256] = { 0 };
		const size_t keyLen = static_cast<size_t>(equalsPos - leftTrimmed);
		if (keyLen >= sizeof(keyBuffer)) {
			continue;
		}

		strncpy(keyBuffer, leftTrimmed, keyLen);
		keyBuffer[keyLen] = '\0';
		trimRight(keyBuffer);
		const char* keyTrimmed = trimLeft(keyBuffer);
		if (!equalsIgnoreCase(keyTrimmed, keyName)) {
			continue;
		}

		char valueBuffer[2048] = { 0 };
		strncpy(valueBuffer, equalsPos + 1, sizeof(valueBuffer) - 1);
		trimRight(valueBuffer);
		const char* valueTrimmed = trimLeft(valueBuffer);
		if (*valueTrimmed == '\0') {
			continue;
		}

		size_t valueLen = strlen(valueTrimmed);
		if (valueLen >= 2 && ((valueTrimmed[0] == '"' && valueTrimmed[valueLen - 1] == '"') || (valueTrimmed[0] == '\'' && valueTrimmed[valueLen - 1] == '\''))) {
			char unquotedValue[2048] = { 0 };
			const size_t copyLen = valueLen - 2;
			if (copyLen >= sizeof(unquotedValue)) {
				continue;
			}

			strncpy(unquotedValue, valueTrimmed + 1, copyLen);
			unquotedValue[copyLen] = '\0';
			value = unquotedValue;
		}
		else {
			value = valueTrimmed;
		}
		fclose(fp);
		return TRUE;
	}

	fclose(fp);
	return FALSE;
}

static Bool getExecutableDirectory(AsciiString& exeDirectory)
{
	char pathBuffer[4096] = { 0 };

#ifdef _WIN32
	DWORD len = GetModuleFileNameA(nullptr, pathBuffer, sizeof(pathBuffer));
	if (len == 0 || len >= sizeof(pathBuffer)) {
		return FALSE;
	}
#elif defined(__APPLE__)
	uint32_t bufferSize = static_cast<uint32_t>(sizeof(pathBuffer));
	if (_NSGetExecutablePath(pathBuffer, &bufferSize) != 0) {
		return FALSE;
	}
#else
	ssize_t len = readlink("/proc/self/exe", pathBuffer, sizeof(pathBuffer) - 1);
	if (len <= 0) {
		return FALSE;
	}
	pathBuffer[len] = '\0';
#endif

	char* lastSlash = strrchr(pathBuffer, '/');
	char* lastBackslash = strrchr(pathBuffer, '\\');
	char* split = lastSlash;
	if (split == nullptr || (lastBackslash != nullptr && lastBackslash > split)) {
		split = lastBackslash;
	}

	if (split == nullptr) {
		return FALSE;
	}

	*split = '\0';
	exeDirectory = pathBuffer;
	return exeDirectory.isNotEmpty();
}

static Bool sanitizeConfiguredPath(const char* rawValue, AsciiString& sanitizedPath)
{
	if (rawValue == nullptr) {
		return FALSE;
	}

	char pathBuffer[4096] = { 0 };
	strncpy(pathBuffer, rawValue, sizeof(pathBuffer) - 1);
	trimRight(pathBuffer);

	const char* trimmedPath = trimLeft(pathBuffer);
	if (*trimmedPath == '\0') {
		return FALSE;
	}

	const size_t trimmedLen = strlen(trimmedPath);
	if (trimmedLen >= 2 && ((trimmedPath[0] == '"' && trimmedPath[trimmedLen - 1] == '"') || (trimmedPath[0] == '\'' && trimmedPath[trimmedLen - 1] == '\''))) {
		char unquotedPath[4096] = { 0 };
		const size_t copyLen = trimmedLen - 2;
		if (copyLen >= sizeof(unquotedPath)) {
			return FALSE;
		}

		strncpy(unquotedPath, trimmedPath + 1, copyLen);
		unquotedPath[copyLen] = '\0';
		sanitizedPath = unquotedPath;
	}
	else {
		sanitizedPath = trimmedPath;
	}

	return sanitizedPath.isNotEmpty();
}

template <typename TBigFileSystem>
static Bool tryLoadBigFiles(TBigFileSystem* fileSystem, const AsciiString& directory, const char* sourceTag, Bool overwrite = FALSE)
{
	if (directory.isEmpty()) {
		return FALSE;
	}

	DEBUG_LOG(("StdBIGFileSystem::init - trying '%s' assets directory: %s", sourceTag, directory.str()));
	const Bool loaded = fileSystem->loadBigFilesFromDirectory(directory, "*.big", overwrite);
	if (loaded) {
		DEBUG_LOG(("StdBIGFileSystem::init - loaded BIG files from %s (%s)", directory.str(), sourceTag));
	}

	return loaded;
}

static Bool tryResolveFromIni(const AsciiString& exeDirectory, const char* keyName, AsciiString& resolvedPath)
{
	static const char* iniCandidates[] = {
		"Options.ini"
	};

	for (UnsignedInt i = 0; i < ARRAY_SIZE(iniCandidates); ++i) {
		if (extractIniValue(iniCandidates[i], kAssetPathSection, keyName, resolvedPath)) {
			return TRUE;
		}

		if (exeDirectory.isNotEmpty()) {
			AsciiString iniPath = exeDirectory;
			iniPath.concat('/');
			iniPath.concat(iniCandidates[i]);
			if (extractIniValue(iniPath.str(), kAssetPathSection, keyName, resolvedPath)) {
				return TRUE;
			}
		}
	}

	return FALSE;
}

template <typename TBigFileSystem>
static Bool loadPrimaryGameAssets(TBigFileSystem* fileSystem, AsciiString* loadedDirectory)
{
	AsciiString exeDirectory;
	getExecutableDirectory(exeDirectory);

	// GeneralsX @feature GitHubCopilot 16/03/2026 Resolve primary asset directory by ENV > INI > default > current.
#if RTS_ZEROHOUR
	const char* primaryEnvName = kPrimaryAssetEnvZH;
	const char* primaryEnvValue = getenv(kPrimaryAssetEnvZH);
#else
	const char* primaryEnvName = kPrimaryAssetEnvGenerals;
	const char* primaryEnvValue = getenv(kPrimaryAssetEnvGenerals);
#endif
	AsciiString sanitizedPrimaryEnvPath;
	if (sanitizeConfiguredPath(primaryEnvValue, sanitizedPrimaryEnvPath)) {
		fprintf(stderr, "[ASSET_ROOT] Trying env %s='%s'\n", primaryEnvName, sanitizedPrimaryEnvPath.str());
		if (tryLoadBigFiles(fileSystem, sanitizedPrimaryEnvPath, "env")) {
			fprintf(stderr, "[ASSET_ROOT] Selected source=env path='%s'\n", sanitizedPrimaryEnvPath.str());
			if (loadedDirectory != nullptr) {
				*loadedDirectory = sanitizedPrimaryEnvPath;
			}
			return TRUE;
		}
		fprintf(stderr, "[ASSET_ROOT] Env path '%s' did not provide BIG files\n", sanitizedPrimaryEnvPath.str());
	}

	// Backward compatibility with previous env naming.
	const char* compatibilityEnvValue = getenv("GENERALSX_ASSET_PATH");
	AsciiString sanitizedCompatibilityEnvPath;
	if (sanitizeConfiguredPath(compatibilityEnvValue, sanitizedCompatibilityEnvPath)) {
		if (tryLoadBigFiles(fileSystem, sanitizedCompatibilityEnvPath, "env-compat")) {
			fprintf(stderr, "[ASSET_ROOT] Selected source=env-compat path='%s'\n", sanitizedCompatibilityEnvPath.str());
			if (loadedDirectory != nullptr) {
				*loadedDirectory = sanitizedCompatibilityEnvPath;
			}
			return TRUE;
		}
	}

#if RTS_ZEROHOUR
	const char* legacyEnvValue = getenv("CNC_ZH_INSTALLPATH");
#else
	const char* legacyEnvValue = getenv("CNC_GENERALS_INSTALLPATH");
#endif
	if (legacyEnvValue != nullptr && legacyEnvValue[0] != '\0') {
		if (tryLoadBigFiles(fileSystem, AsciiString(legacyEnvValue), "legacy-env")) {
			if (loadedDirectory != nullptr) {
				*loadedDirectory = legacyEnvValue;
			}
			return TRUE;
		}
	}

	AsciiString iniPath;
	if (tryResolveFromIni(exeDirectory, kPrimaryAssetIniKey, iniPath)) {
		fprintf(stderr, "[ASSET_ROOT] Trying ini [Paths]%s='%s'\n", kPrimaryAssetIniKey, iniPath.str());
		if (tryLoadBigFiles(fileSystem, iniPath, "ini")) {
			fprintf(stderr, "[ASSET_ROOT] Selected source=ini path='%s'\n", iniPath.str());
			if (loadedDirectory != nullptr) {
				*loadedDirectory = iniPath;
			}
			return TRUE;
		}
	}

	AsciiString defaultPath;
	if (GetStringFromRegistry("", "InstallPath", defaultPath)) {
		if (tryLoadBigFiles(fileSystem, defaultPath, "default-registry")) {
			fprintf(stderr, "[ASSET_ROOT] Selected source=default path='%s'\n", defaultPath.str());
			if (loadedDirectory != nullptr) {
				*loadedDirectory = defaultPath;
			}
			return TRUE;
		}
	}

#if RTS_ZEROHOUR
	if (exeDirectory.isNotEmpty()) {
		AsciiString resourcesPath = exeDirectory;
		resourcesPath.concat("/../Resources");
		if (tryLoadBigFiles(fileSystem, resourcesPath, "default-resources")) {
			return TRUE;
		}
	}
#endif

	if (exeDirectory.isNotEmpty()) {
		if (tryLoadBigFiles(fileSystem, exeDirectory, "default-exedir")) {
			if (loadedDirectory != nullptr) {
				*loadedDirectory = exeDirectory;
			}
			return TRUE;
		}
	}

	DEBUG_LOG(("StdBIGFileSystem::init - trying current working directory as last-resort assets path"));
	if (fileSystem->loadBigFilesFromDirectory("", "*.big")) {
		fprintf(stderr, "[ASSET_ROOT] Selected source=current-working-directory\n");
		if (loadedDirectory != nullptr) {
			*loadedDirectory = AsciiString::TheEmptyString;
		}
		return TRUE;
	}

	return FALSE;
}

#if RTS_ZEROHOUR
template <typename TBigFileSystem>
static void loadBaseGeneralsAssetsForZH(TBigFileSystem* fileSystem, const AsciiString& zhAssetDirectory)
{
	// GeneralsX @feature GitHubCopilot 16/03/2026 Resolve base Generals asset directory for ZH by ENV > INI > default.
	const char* baseEnvValue = getenv(kBaseGeneralsAssetEnv);
	if (baseEnvValue != nullptr && baseEnvValue[0] != '\0') {
		if (tryLoadBigFiles(fileSystem, AsciiString(baseEnvValue), "env-generals")) {
			return;
		}
	}

	const char* compatibilityBaseEnvValue = getenv("GENERALSX_GENERALS_ASSET_PATH");
	if (compatibilityBaseEnvValue != nullptr && compatibilityBaseEnvValue[0] != '\0') {
		if (tryLoadBigFiles(fileSystem, AsciiString(compatibilityBaseEnvValue), "env-generals-compat")) {
			return;
		}
	}

	const char* legacyGeneralsEnvValue = getenv("CNC_GENERALS_INSTALLPATH");
	if (legacyGeneralsEnvValue != nullptr && legacyGeneralsEnvValue[0] != '\0') {
		if (tryLoadBigFiles(fileSystem, AsciiString(legacyGeneralsEnvValue), "legacy-env-generals")) {
			return;
		}
	}

	AsciiString exeDirectory;
	getExecutableDirectory(exeDirectory);

	AsciiString iniPath;
	if (tryResolveFromIni(exeDirectory, kBaseGeneralsAssetIniKey, iniPath)) {
		if (tryLoadBigFiles(fileSystem, iniPath, "ini-generals")) {
			return;
		}
	}

	AsciiString installPath;
	GetStringFromGeneralsRegistry("", "InstallPath", installPath);
	if (tryLoadBigFiles(fileSystem, installPath, "default-registry-generals")) {
		return;
	}

	if (zhAssetDirectory.isNotEmpty()) {
		AsciiString siblingGenerals = zhAssetDirectory;
		siblingGenerals.concat("/../Generals");
		if (tryLoadBigFiles(fileSystem, siblingGenerals, "default-sibling-generals")) {
			return;
		}

		AsciiString steamGenerals = zhAssetDirectory;
		steamGenerals.concat("/ZH_Generals");
		if (tryLoadBigFiles(fileSystem, steamGenerals, "default-zh-generals")) {
			return;
		}
	}
}
#endif

}

StdBIGFileSystem::StdBIGFileSystem() : ArchiveFileSystem() {
}

StdBIGFileSystem::~StdBIGFileSystem() {
}

void StdBIGFileSystem::init() {
	DEBUG_ASSERTCRASH(TheLocalFileSystem != nullptr, ("TheLocalFileSystem must be initialized before TheArchiveFileSystem."));
	if (TheLocalFileSystem == nullptr) {
		return;
	}

	AsciiString primaryAssetsDirectory;
	const Bool loadedPrimaryAssets = loadPrimaryGameAssets(this, &primaryAssetsDirectory);
	DEBUG_ASSERTCRASH(loadedPrimaryAssets, ("No BIG files were loaded for the primary game assets."));

	// GeneralsX @bugfix felipebraz 23/03/2026 Propagate the resolved asset root to the local file system.
	// On Linux/macOS the binary cwd and the game data directory (asset root) are separate. Loose files like
	// Data\Scripts\SkirmishScripts.scb must be resolvable from the asset root, not just from cwd.
	if (primaryAssetsDirectory.isNotEmpty()) {
		TheLocalFileSystem->setAssetRootPath(primaryAssetsDirectory);
	}

#if RTS_ZEROHOUR
	loadBaseGeneralsAssetsForZH(this, primaryAssetsDirectory);
#endif
}

void StdBIGFileSystem::reset() {
}

void StdBIGFileSystem::update() {
}

void StdBIGFileSystem::postProcessLoad() {
}

// GeneralsX @bugfix Codex 07/10/2026 Bound untrusted BIG table reads without limiting normal large mod payloads.
ArchiveFile * StdBIGFileSystem::openArchiveFile(const Char *filename) {
    auto closeFile = [](File* file) { if (file != nullptr) file->close(); };
    std::unique_ptr<File, decltype(closeFile)> fp(
        TheLocalFileSystem->openFile(filename, File::READ | File::BINARY), closeFile);
    if (!fp || fp->size() < 16) return nullptr;
    const uint64_t actualSize = static_cast<uint64_t>(fp->size());
    char magic[4];
    uint32_t archiveSize, count, headerSize;
    if (fp->read(magic, 4) != 4 ||
        (std::memcmp(magic, "BIGF", 4) != 0 && std::memcmp(magic, "BIG4", 4) != 0) ||
        fp->read(&archiveSize, 4) != 4 || fp->read(&count, 4) != 4 ||
        fp->read(&headerSize, 4) != 4) return nullptr;
    (void)archiveSize; // Retail header byte order differs; actual file length is authoritative.
    count = betoh(count);
    headerSize = betoh(headerSize);
    if (headerSize < 16 || headerSize > actualSize || count > 200000 ||
        count > (headerSize - 16) / 9) return nullptr;

    AsciiString archiveName(filename);
    archiveName.toLower();
    std::unique_ptr<ArchiveFile> archive(NEW StdBIGFile(filename, AsciiString::TheEmptyString));
    uint64_t tablePosition = 16;
    for (uint32_t i = 0; i < count; ++i) {
        uint32_t offset, size;
        if (headerSize - tablePosition < 9 || fp->read(&offset, 4) != 4 ||
            fp->read(&size, 4) != 4) return nullptr;
        tablePosition += 8;
        offset = betoh(offset);
        size = betoh(size);
        if (offset > actualSize || size > actualSize - offset) return nullptr;
        // Match the importer's 4096-byte budget including the NUL terminator.
        std::array<char, 4096> name{};
        size_t length = 0;
        for (;;) {
            if (length == name.size() || tablePosition >= headerSize ||
                fp->read(&name[length], 1) != 1) return nullptr;
            ++tablePosition;
            if (name[length++] == '\0') break;
        }
        if (length == 1) return nullptr;
        char* leaf = name.data();
        for (size_t n = 0; n + 1 < length; ++n) {
            if (name[n] == '/' || name[n] == '\\') leaf = name.data() + n + 1;
        }
        if (*leaf == '\0') return nullptr;
        ArchivedFileInfo info;
        info.m_archiveFilename = archiveName;
        info.m_offset = static_cast<Int>(offset);
        info.m_size = static_cast<Int>(size);
        info.m_filename = leaf;
        info.m_filename.toLower();
        if (leaf != name.data()) *leaf = '\0';
        else name[0] = '\0';
        archive->addFile(AsciiString(name.data()), &info);
    }
    archive->attachFile(fp.release());
    return archive.release();
}

void StdBIGFileSystem::closeArchiveFile(const Char *filename) {
	// Need to close the specified big file
	ArchiveFileMap::iterator it =  m_archiveFileMap.find(filename);
	if (it == m_archiveFileMap.end()) {
		return;
	}

	if (stricmp(filename, MUSIC_BIG) == 0) {
		// Stop the current audio
		TheAudio->stopAudio(AudioAffect_Music);

		// No need to turn off other audio, as the lookups will just fail.
	}
	DEBUG_ASSERTCRASH(stricmp(filename, MUSIC_BIG) == 0, ("Attempting to close Archive file '%s', need to add code to handle its shutdown correctly.", filename));

	// may need to do some other processing here first.

	delete (it->second);
	m_archiveFileMap.erase(it);
}

void StdBIGFileSystem::closeAllArchiveFiles() {
}

void StdBIGFileSystem::closeAllFiles() {
}

Bool StdBIGFileSystem::loadBigFilesFromDirectory(AsciiString dir, AsciiString fileMask, Bool overwrite) {

	FilenameList filenameList;
	TheLocalFileSystem->getFileListInDirectory(dir, "", fileMask, filenameList, TRUE);

	fprintf(stderr, "[gxbig] scanning '%s' for '%s': %u candidate(s)\n",
		dir.isEmpty() ? "." : dir.str(), fileMask.str(), (unsigned)filenameList.size());

	Bool actuallyAdded = FALSE;
	unsigned int ignoredInactiveModArchives = 0;
	FilenameListIter it = filenameList.begin();
	while (it != filenameList.end()) {
#if RTS_ZEROHOUR
		// The Android Mod Manager isolates all mods beneath the retail root's
		// Mods/ directory. A recursive base scan must never import an inactive
		// mod (nor preload the active one ahead of -mod handling).
		if (!overwrite && isStandaloneModArchiveBelowRoot(dir, *it)) {
			++ignoredInactiveModArchives;
			++it;
			continue;
		}
		// TheSuperHackers @bugfix bobtista 18/11/2025 Skip duplicate INIZH.big in Data\INI to prevent CRC mismatches.
		// English, Chinese, and Korean SKUs shipped with two INIZH.big files (one in Run directory, one in Run\Data\INI).
		// The DeleteFile cleanup doesn't work on EA App/Origin installs because the folder is not writable, so we skip loading it instead.
		if (it->endsWithNoCase("Data\\INI\\INIZH.big") || it->endsWithNoCase("Data/INI/INIZH.big")) {
			it++;
			continue;
		}
#endif

		ArchiveFile *archiveFile = openArchiveFile((*it).str());

		// GeneralsX @diag Android port 06/09/2026 Which archives were actually
		// mounted is the first thing worth knowing about a "half my textures are
		// magenta" report, and until now the log never said. DEBUG_LOG below is
		// compiled out of release builds, which is exactly the build testers run.
		fprintf(stderr, "[gxbig] %s: %s\n",
			archiveFile != nullptr ? "loaded" : "FAILED TO OPEN", (*it).str());

		if (archiveFile != nullptr) {
			DEBUG_LOG(("StdBIGFileSystem::loadBigFilesFromDirectory - loading %s into the directory tree.", (*it).str()));
			loadIntoDirectoryTree(archiveFile, overwrite);
			m_archiveFileMap[(*it)] = archiveFile;
			DEBUG_LOG(("StdBIGFileSystem::loadBigFilesFromDirectory - %s inserted into the archive file map.", (*it).str()));
			actuallyAdded = TRUE;
		}

		it++;
	}
	if (ignoredInactiveModArchives != 0)
		fprintf(stderr, "[gxbig] excluded %u inactive Mods/ BIG(s) from base scan '%s'\n",
			ignoredInactiveModArchives, dir.str());

	return actuallyAdded;
}
