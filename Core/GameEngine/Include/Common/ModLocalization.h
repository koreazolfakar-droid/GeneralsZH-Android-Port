// GeneralsX @bugfix Codex 05/10/2026 Resolve mod text without changing global asset priority.
#pragma once

#include "Common/ArchiveFile.h"
#include "Common/FileSystem.h"
#include "Common/GlobalData.h"
#include "Common/LocalFileSystem.h"
#include <algorithm>
#include <cctype>
#include <limits>
#include <string>

struct ModLocalizationSource
{
	AsciiString filename;
	AsciiString description;
	FileInstance instance = 0;
	Bool activeMod = FALSE;
	Bool available = FALSE;
	Int priority = 4;
};

inline std::string modLocalizationPath(const AsciiString& path)
{
	std::string result(path.str());
	std::replace(result.begin(), result.end(), '\\', '/');
	return result;
}

// GeneralsX @bugfix Codex 08/10/2026 Ownership is case/separator insensitive;
// preserve the original spelling when opening a loose path on Android.
inline std::string modLocalizationOwnershipPath(const AsciiString& path)
{
	std::string result = modLocalizationPath(path);
	for (char& ch : result)
		ch = (char)std::tolower((unsigned char)ch);
	while (!result.empty() && result.back() == '/')
		result.pop_back();
	return result;
}

inline Bool isActiveModLocalizationArchive(ArchiveFile* archive)
{
	if (archive == nullptr || TheGlobalData == nullptr)
		return FALSE;
	const std::string name = modLocalizationOwnershipPath(archive->getName());
	const std::string big = modLocalizationOwnershipPath(TheGlobalData->m_modBIG);
	if (!big.empty() && name == big)
		return TRUE;
	const std::string directory = modLocalizationOwnershipPath(TheGlobalData->m_modDir);
	return !directory.empty() && name.compare(0, directory.size() + 1, directory + "/") == 0;
}

inline ModLocalizationSource describeModLocalization(const AsciiString& filename, FileInstance instance = 0)
{
	ModLocalizationSource source;
	source.filename = filename;
	source.instance = instance;
	if (TheLocalFileSystem && TheLocalFileSystem->doesFileExist(filename.str()))
	{
		if (instance == 0)
		{
			source.description.format("loose:%s", filename.str());
			source.available = TRUE;
			return source;
		}
		--instance;
	}
	ArchiveFile* archive = TheArchiveFileSystem ? TheArchiveFileSystem->getArchiveFile(filename, instance) : nullptr;
	if (archive != nullptr)
	{
		source.description.format("big:%s!%s", archive->getName().str(), filename.str());
		source.activeMod = isActiveModLocalizationArchive(archive);
		source.available = TRUE;
	}
	else
		source.description = "none";
	return source;
}

inline ModLocalizationSource resolveModLocalization(const AsciiString& defaultFile,
	const AsciiString& language, const char* leaf)
{
	AsciiString candidates[4];
	candidates[0].format("data/%s/%s", language.str(), leaf);
	candidates[1].format("data/english/%s", leaf);
	candidates[2].format("data/%s", leaf);
	candidates[3] = leaf;
	// GeneralsX @bugfix Codex 08/10/2026 Search every instance at each language/layout
	// before trying the next. A translation/base archive cannot mask the active mod.
	for (Int priority = 0; priority < 4; ++priority)
	{
		const AsciiString& candidate = candidates[priority];
		if (TheGlobalData && TheGlobalData->m_modDir.isNotEmpty() && TheLocalFileSystem)
		{
			std::string directory = modLocalizationPath(TheGlobalData->m_modDir);
			if (directory.back() != '/') directory += '/';
			AsciiString loose;
			loose.format("%s%s", directory.c_str(), candidate.str());
			if (TheLocalFileSystem->doesFileExist(loose.str()))
			{
				ModLocalizationSource source = describeModLocalization(loose);
				source.activeMod = TRUE;
				source.priority = priority;
				return source;
			}
		}
		const Int looseOffset = TheLocalFileSystem && TheLocalFileSystem->doesFileExist(candidate.str()) ? 1 : 0;
		// FileInstance is a byte in the engine. Never wrap it when enumerating BIGs.
		for (Int index = 0; TheArchiveFileSystem && index <= (std::numeric_limits<FileInstance>::max)() - looseOffset; ++index)
		{
			ArchiveFile* archive = TheArchiveFileSystem->getArchiveFile(candidate, (FileInstance)index);
			if (archive == nullptr) break;
			if (isActiveModLocalizationArchive(archive))
			{
				ModLocalizationSource source = describeModLocalization(candidate, (FileInstance)(index + looseOffset));
				source.priority = priority;
				return source;
			}
		}
	}
	return describeModLocalization(defaultFile);
}

inline ModLocalizationSource resolveVanillaLocalization(const AsciiString& filename)
{
	// Instance 1 is not necessarily Vanilla: a mod can supply several BIG tables.
	for (Int index = 0; index <= (std::numeric_limits<FileInstance>::max)(); ++index)
	{
		ModLocalizationSource source = describeModLocalization(filename, (FileInstance)index);
		if (!source.available || !source.activeMod)
			return source;
	}
	ModLocalizationSource missing;
	missing.filename = filename;
	missing.description = "none";
	return missing;
}
