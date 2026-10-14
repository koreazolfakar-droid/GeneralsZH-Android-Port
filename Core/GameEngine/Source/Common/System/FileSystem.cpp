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

//----------------------------------------------------------------------------
//
//                       Westwood Studios Pacific.
//
//                       Confidential Information
//                Copyright(C) 2001 - All Rights Reserved
//
//----------------------------------------------------------------------------
//
// Project:   WSYS Library
//
// Module:    IO
//
// File name: IO_FileSystem.cpp
//
// Created:   4/23/01
//
//----------------------------------------------------------------------------

//----------------------------------------------------------------------------
//         Includes
//----------------------------------------------------------------------------

#include "PreRTS.h"
#include "Common/file.h"
#include "Common/FileSystem.h"

#include "Common/ArchiveFileSystem.h"
#include "Common/ArchiveFile.h"
#include "Common/GameAudio.h"
#include "Common/LocalFileSystem.h"
#include "Common/PerfTimer.h"
#include "GXTrace.h"
#include "GXResourceStats.h"

#include "Lib/PathUtil.h"
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <string>


DECLARE_PERF_TIMER(FileSystem)

//----------------------------------------------------------------------------
//         Externals
//----------------------------------------------------------------------------



//----------------------------------------------------------------------------
//         Defines
//----------------------------------------------------------------------------



//----------------------------------------------------------------------------
//         Private Types
//----------------------------------------------------------------------------



//----------------------------------------------------------------------------
//         Private Data
//----------------------------------------------------------------------------



//----------------------------------------------------------------------------
//         Public Data
//----------------------------------------------------------------------------

//===============================
// TheFileSystem
//===============================
/**
  *	This is the FileSystem's singleton class. All file access
	* should be through TheFileSystem, unless code needs to use an explicit
	* File or FileSystem derivative.
	*
	* Using TheFileSystem->open and File exclusively for file access, particularly
	* in library or modular code, allows applications to transparently implement
	* file access as they see fit. This is particularly important for code that
	* needs to be shared between applications, such as games and tools.
	*/
//===============================

FileSystem	*TheFileSystem = nullptr;

//----------------------------------------------------------------------------
//         Private Prototypes
//----------------------------------------------------------------------------

//----------------------------------------------------------------------------
//         Private Functions
//----------------------------------------------------------------------------


//----------------------------------------------------------------------------
//         Public Functions
//----------------------------------------------------------------------------

// Mod scripts override retail loose AI scripts. The Mod Manager's virtual
// BIG replacement order and all other asset paths remain unchanged.
static bool gxIsAIOverrideScriptPath(const char* filename)
{
	if (filename == nullptr)
		return false;
	// Fast reject: don't allocate/normalize a path for every W3D/texture read.
	const char* base = filename;
	for (const char* p = filename; *p != '\0'; ++p)
		if (*p == '/' || *p == '\\')
			base = p + 1;
	const auto equalsNoCase = [](const char* a, const char* b) {
		while (*a && *b) {
			if (std::tolower(static_cast<unsigned char>(*a)) != std::tolower(static_cast<unsigned char>(*b)))
				return false;
			++a;
			++b;
		}
		return *a == *b;
	};
	if (!equalsNoCase(base, "SkirmishScripts.scb") &&
		!equalsNoCase(base, "MultiplayerScripts.scb") &&
		!equalsNoCase(base, "Scripts.ini"))
		return false;
	std::string path(filename);
	std::transform(path.begin(), path.end(), path.begin(),
		[](unsigned char c) { return c == '\\' ? '/' : static_cast<char>(std::tolower(c)); });
	return path == "data/scripts/skirmishscripts.scb"
		|| path == "data/scripts/multiplayerscripts.scb"
		|| path == "data/scripts/scripts.ini"
		|| path == "data/ini/scripts.ini";
}

static FileInstance gxAIOverrideArchiveCount(const char* filename)
{
	return gxIsAIOverrideScriptPath(filename) && TheArchiveFileSystem != nullptr
		? TheArchiveFileSystem->getFileCount(filename) : 0;
}

// GeneralsX @feature Codex 10/10/2026 Opt-in, filtered asset provenance without release-log flooding.
// GX_ASSET_TRACE or gx_asset_trace.txt in the game root: '*' (or empty marker)
// traces every read; otherwise a case/slash-insensitive virtual-path substring.
static bool gxShouldTraceAsset(const char* filename)
{
	static const std::string filter = []() {
		std::string value;
		const char* env = getenv("GX_ASSET_TRACE");
		if (env != nullptr && env[0] != '\0')
			value = env;
		else if (FILE* marker = fopen("gx_asset_trace.txt", "r"))
		{
			char line[512] = {};
			if (fgets(line, sizeof(line), marker) != nullptr)
				value = line;
			fclose(marker);
			const size_t end = value.find_last_not_of(" \t\r\n");
			value = end == std::string::npos ? "*" : value.substr(0, end + 1);
		}
		std::transform(value.begin(), value.end(), value.begin(),
			[](unsigned char c) { return c == '\\' ? '/' : static_cast<char>(std::tolower(c)); });
		return value;
	}();
	if (filter.empty())
		return false;
	if (filter == "*")
		return true;
	std::string path(filename);
	std::transform(path.begin(), path.end(), path.begin(),
		[](unsigned char c) { return c == '\\' ? '/' : static_cast<char>(std::tolower(c)); });
	return path.find(filter) != std::string::npos;
}

// GeneralsX @feature Codex 10/10/2026 W3D/texture loaders can stop at an existence probe without opening a file.
static Bool gxTraceAssetProbe(const char* filename, FileInstance instance, Bool exists)
{
	if (gxShouldTraceAsset(filename))
	{
		const Bool loose = TheLocalFileSystem != nullptr && TheLocalFileSystem->doesFileExist(filename);
		const FileInstance scriptCopies = gxAIOverrideArchiveCount(filename);
		ArchiveFile* archive = scriptCopies > 0
			? (instance < scriptCopies ? TheArchiveFileSystem->getArchiveFile(filename, instance) : nullptr)
			: (TheArchiveFileSystem != nullptr && (!loose || instance != 0)
				? TheArchiveFileSystem->getArchiveFile(filename, loose ? instance - 1 : instance) : nullptr);
		const Bool selectedLoose = scriptCopies > 0 ? (loose && instance == scriptCopies) : (loose && instance == 0);
		fprintf(stderr, "[gxasset] probe=%s instance=%u source=%s result=%s\n", filename,
			(unsigned)instance, archive != nullptr ? archive->getName().str() : (selectedLoose ? "<loose>" : "<none>"),
			exists ? "FOUND" : "UNRESOLVED");
	}
	return exists;
}


//============================================================================
// FileSystem::FileSystem
//============================================================================

FileSystem::FileSystem()
{

}

//============================================================================
// FileSystem::~FileSystem
//============================================================================

FileSystem::~FileSystem()
{

}

//============================================================================
// FileSystem::init
//============================================================================

void		FileSystem::init()
{
	TheLocalFileSystem->init();
	TheArchiveFileSystem->init();
}

//============================================================================
// FileSystem::update
//============================================================================

void		FileSystem::update()
{
	USE_PERF_TIMER(FileSystem)
	TheLocalFileSystem->update();
	TheArchiveFileSystem->update();
}

//============================================================================
// FileSystem::reset
//============================================================================

void		FileSystem::reset()
{
	USE_PERF_TIMER(FileSystem)
	TheLocalFileSystem->reset();
	TheArchiveFileSystem->reset();
}

//============================================================================
// FileSystem::open
//============================================================================

File*		FileSystem::openFile( const Char *filename, Int access, size_t bufferSize, FileInstance instance )
{
	// GeneralsX @feature Codex 14/10/2026 Includes failed read-only lookups;
	// no changes to local/mod/BIG resolution or archive precedence.
	GXResourceStats::Scope gxResourceScope(GXTrace::isPerfEnabled() && !(access & File::WRITE),GXResourceStats::Lookup);
	USE_PERF_TIMER(FileSystem)
	File *file = nullptr;
	const Bool traceAsset = (access & File::WRITE) == 0 && gxShouldTraceAsset(filename);
	const FileInstance requestedInstance = instance;
	ArchiveFile* sourceArchive = nullptr;
	const FileInstance scriptCopies = (access & File::WRITE) == 0 ? gxAIOverrideArchiveCount(filename) : 0;
	if (scriptCopies > 0 && instance < scriptCopies)
	{
		// Use the already-reconciled BIG tree, keeping standalone mod priority.
		sourceArchive = TheArchiveFileSystem->getArchiveFile(filename, instance);
		file = TheArchiveFileSystem->openFile(filename, 0, instance);
		fprintf(stderr, "[GX-AI-SCRIPT] path=%s instance=%u source=%s result=%s\n", filename,
			(unsigned)requestedInstance, sourceArchive != nullptr ? sourceArchive->getName().str() : "<none>",
			file != nullptr ? "OPEN" : "READ_FAILED");
		if (traceAsset)
			fprintf(stderr, "[gxasset] path=%s instance=%u source=%s result=%s\n", filename,
				(unsigned)requestedInstance, sourceArchive != nullptr ? sourceArchive->getName().str() : "<none>",
				file != nullptr ? "OPEN" : "READ_FAILED");
		return file;
	}
	if (scriptCopies > 0)
		instance -= scriptCopies;

	if ( TheLocalFileSystem != nullptr )
	{
		if (instance != 0)
		{
			if (TheLocalFileSystem->doesFileExist(filename))
			{
				--instance;
			}
		}
		else
		{
			file = TheLocalFileSystem->openFile( filename, access, bufferSize );

#if ENABLE_FILESYSTEM_EXISTENCE_CACHE
			if (file != nullptr && (file->getAccess() & File::CREATE))
			{
				FastCriticalSectionClass::LockClass lock(m_fileExistMutex);
				FileExistMap::iterator it = m_fileExist.find(FileExistMap::key_type::temporary(filename));
				if (it != m_fileExist.end())
				{
					++it->second.instanceExists;
					if (it->second.instanceDoesNotExist != ~FileInstance(0))
						++it->second.instanceDoesNotExist;
				}
				else
				{
					m_fileExist[filename];
				}
			}
#endif
		}
	}

	if ( (TheArchiveFileSystem != nullptr) && (file == nullptr) && scriptCopies == 0 )
	{
		if (traceAsset)
			sourceArchive = TheArchiveFileSystem->getArchiveFile(filename, instance);
		// TheSuperHackers @todo Pass 'access' here?
		file = TheArchiveFileSystem->openFile( filename, 0, instance );
	}
	if (gxIsAIOverrideScriptPath(filename) && (access & File::WRITE) == 0)
		fprintf(stderr, "[GX-AI-SCRIPT] path=%s instance=%u source=%s result=%s\n", filename,
			(unsigned)requestedInstance,
			sourceArchive != nullptr ? sourceArchive->getName().str() : (file != nullptr ? "<loose>" : "<none>"),
			file != nullptr ? "OPEN" : "UNRESOLVED");
	if (traceAsset)
	{
		fprintf(stderr, "[gxasset] path=%s instance=%u source=%s result=%s\n", filename,
			(unsigned)requestedInstance,
			sourceArchive != nullptr ? sourceArchive->getName().str() : (file != nullptr ? "<loose>" : "<none>"),
			file != nullptr ? "OPEN" : (sourceArchive != nullptr ? "READ_FAILED" : "UNRESOLVED"));
	}

	return file;
}

//============================================================================
// FileSystem::doesFileExist
//============================================================================

Bool FileSystem::doesFileExist(const Char *filename, FileInstance instance) const
{
	USE_PERF_TIMER(FileSystem)
	const FileInstance requestedInstance = instance;

#if ENABLE_FILESYSTEM_EXISTENCE_CACHE
	{
		FastCriticalSectionClass::LockClass lock(m_fileExistMutex);
		FileExistMap::const_iterator it = m_fileExist.find(FileExistMap::key_type::temporary(filename));
		if (it != m_fileExist.end())
		{
			// Must test instanceDoesNotExist first!
			if (instance >= it->second.instanceDoesNotExist)
				return gxTraceAssetProbe(filename, requestedInstance, FALSE);
			if (instance <= it->second.instanceExists)
				return gxTraceAssetProbe(filename, requestedInstance, TRUE);
		}
	}
#endif

	const FileInstance scriptCopies = gxAIOverrideArchiveCount(filename);
	if (scriptCopies > 0 && instance < scriptCopies)
	{
#if ENABLE_FILESYSTEM_EXISTENCE_CACHE
		{
			FastCriticalSectionClass::LockClass lock(m_fileExistMutex);
			FileExistMap::mapped_type& value = m_fileExist[filename];
			value.instanceExists = max(value.instanceExists, requestedInstance);
		}
#endif
		return gxTraceAssetProbe(filename, requestedInstance, TRUE);
	}
	if (scriptCopies > 0)
		instance -= scriptCopies;

	if (TheLocalFileSystem->doesFileExist(filename))
	{
		if (instance == 0)
		{
#if ENABLE_FILESYSTEM_EXISTENCE_CACHE
			{
				FastCriticalSectionClass::LockClass lock(m_fileExistMutex);
				FileExistMap::mapped_type& value = m_fileExist[filename];
				value.instanceExists = max(value.instanceExists, requestedInstance);
			}
#endif
			return gxTraceAssetProbe(filename, requestedInstance, TRUE);
		}

		--instance;
	}

	if (scriptCopies == 0 && TheArchiveFileSystem->doesFileExist(filename, instance))
	{
#if ENABLE_FILESYSTEM_EXISTENCE_CACHE
		{
			FastCriticalSectionClass::LockClass lock(m_fileExistMutex);
			FileExistMap::mapped_type& value = m_fileExist[filename];
			value.instanceExists = max(value.instanceExists, requestedInstance);
		}
#endif
		return gxTraceAssetProbe(filename, requestedInstance, TRUE);
	}

#if ENABLE_FILESYSTEM_EXISTENCE_CACHE
	{
		FastCriticalSectionClass::LockClass lock(m_fileExistMutex);
		FileExistMap::mapped_type& value = m_fileExist[filename];
		value.instanceDoesNotExist = min(value.instanceDoesNotExist, requestedInstance);
	}
#endif
	return gxTraceAssetProbe(filename, requestedInstance, FALSE);
}

//============================================================================
// FileSystem::getFileListInDirectory
//============================================================================
void FileSystem::getFileListInDirectory(const AsciiString& directory, const AsciiString& searchName, FilenameList &filenameList, Bool searchSubdirectories) const
{
	USE_PERF_TIMER(FileSystem)
	TheLocalFileSystem->getFileListInDirectory(AsciiString::TheEmptyString, directory, searchName, filenameList, searchSubdirectories);
	TheArchiveFileSystem->getFileListInDirectory(AsciiString::TheEmptyString, directory, searchName, filenameList, searchSubdirectories);
}

//============================================================================
// FileSystem::getFileInfo
//============================================================================
Bool FileSystem::getFileInfo(const AsciiString& filename, FileInfo *fileInfo, FileInstance instance) const
{
	USE_PERF_TIMER(FileSystem)

	// TheSuperHackers @todo Add file info cache?

	if (fileInfo == nullptr) {
		return FALSE;
	}
	memset(fileInfo, 0, sizeof(*fileInfo));

	// Keep metadata FileInstance ordering consistent with openFile().
	const FileInstance scriptCopies = gxAIOverrideArchiveCount(filename.str());
	if (scriptCopies > 0 && instance < scriptCopies)
		return TheArchiveFileSystem->getFileInfo(filename, fileInfo, instance);
	if (scriptCopies > 0)
		instance -= scriptCopies;

	if (TheLocalFileSystem->getFileInfo(filename, fileInfo)) {
		if (instance == 0) {
			return TRUE;
		}

		--instance;
	}

	if (scriptCopies == 0 && TheArchiveFileSystem->getFileInfo(filename, fileInfo, instance)) {
		return TRUE;
	}

	return FALSE;
}

//============================================================================
// FileSystem::createDirectory
//============================================================================
Bool FileSystem::createDirectory(AsciiString directory)
{
	USE_PERF_TIMER(FileSystem)
	if (TheLocalFileSystem != nullptr) {
		return TheLocalFileSystem->createDirectory(directory);
	}
	return FALSE;
}

//============================================================================
// FileSystem::normalizePath
//============================================================================
AsciiString FileSystem::normalizePath(const AsciiString& path)
{
	return TheLocalFileSystem->normalizePath(path);
}

//============================================================================
// FileSystem::isPathInDirectory
//============================================================================
Bool FileSystem::isPathInDirectory(const AsciiString& testPath, const AsciiString& basePath)
{
	AsciiString testPathNormalized = TheFileSystem->normalizePath(testPath);
	AsciiString basePathNormalized = TheFileSystem->normalizePath(basePath);

	if (basePathNormalized.isEmpty())
	{
		DEBUG_CRASH(("Unable to normalize base directory path '%s'.", basePath.str()));
		return false;
	}
	else if (testPathNormalized.isEmpty())
	{
		DEBUG_CRASH(("Unable to normalize file path '%s'.", testPath.str()));
		return false;
	}

#ifdef _WIN32
	const char* pathSep = "\\";
#else
	const char* pathSep = "/";
#endif

	if (!basePathNormalized.endsWith(pathSep))
	{
		basePathNormalized.concat(pathSep);
	}

#ifdef _WIN32
	if (!testPathNormalized.startsWithNoCase(basePathNormalized))
#else
	if (!testPathNormalized.startsWith(basePathNormalized))
#endif
	{
		return false;
	}

	return true;
}

//============================================================================
// FileSystem::removeExtension - Ascii handling variant
//============================================================================
bool FileSystem::removeExtension(AsciiString& path)
{
	if (const Char* ext = getExtension(path.str()))
	{
		path.truncateTo(ext - path.str());
		return true;
	}

	return false;
}

//============================================================================
// FileSystem::removeExtension - Unicode handling variant
//============================================================================
bool FileSystem::removeExtension(UnicodeString& path)
{
	if (const WideChar* ext = getExtension(path.str()))
	{
		path.truncateTo(ext - path.str());
		return true;
	}

	return false;
}
