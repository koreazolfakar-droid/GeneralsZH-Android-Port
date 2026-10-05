// GeneralsX @bugfix Codex 05/10/2026 Resolve Android mod text without changing global asset priority.
#pragma once

#include "Common/ArchiveFile.h"
#include "Common/FileSystem.h"
#include "Common/GlobalData.h"
#include "Common/LocalFileSystem.h"
#include <algorithm>
#include <string>

struct ModLocalizationSource
{
	AsciiString filename;
	AsciiString description;
	FileInstance instance = 0;
	Bool activeMod = FALSE;
};

inline std::string modLocalizationPath(const AsciiString& path)
{
	std::string result(path.str());
	std::replace(result.begin(), result.end(), '\\', '/');
	return result;
}

inline Bool isActiveModLocalizationArchive(ArchiveFile* archive)
{
	if (archive == nullptr || TheGlobalData == nullptr)
		return FALSE;
	const std::string name = modLocalizationPath(archive->getName());
	if (TheGlobalData->m_modBIG.isNotEmpty() && name == modLocalizationPath(TheGlobalData->m_modBIG))
		return TRUE;
	if (TheGlobalData->m_modDir.isEmpty())
		return FALSE;
	std::string directory = modLocalizationPath(TheGlobalData->m_modDir);
	if (directory.back() != '/')
		directory += '/';
	return name.compare(0, directory.size(), directory) == 0;
}

inline ModLocalizationSource describeModLocalization(const AsciiString& filename, FileInstance instance = 0)
{
	ModLocalizationSource source;
	source.filename = filename;
	source.instance = instance;
	if (TheLocalFileSystem->doesFileExist(filename.str()))
	{
		if (instance == 0)
		{
			source.description.format("loose:%s", filename.str());
			return source;
		}
		--instance;
	}
	ArchiveFile* archive = TheArchiveFileSystem->getArchiveFile(filename, instance);
	if (archive != nullptr)
	{
		source.description.format("big:%s!%s", archive->getName().str(), filename.str());
		source.activeMod = isActiveModLocalizationArchive(archive);
	}
	else
		source.description = "none";
	return source;
}

inline ModLocalizationSource resolveModLocalization(const AsciiString& defaultFile,
	const AsciiString& language, const char* leaf)
{
	// Prefer the selected language, then the English tables used by most ZH mods.
	// Also accept the development Data/Generals.str and root-level table layouts.
	AsciiString candidates[4];
	candidates[0].format("data/%s/%s", language.str(), leaf);
	candidates[1].format("data/English/%s", leaf);
	candidates[2].format("data/%s", leaf);
	candidates[3] = leaf;
	if (TheGlobalData != nullptr && TheGlobalData->m_modDir.isNotEmpty())
	{
		std::string directory = modLocalizationPath(TheGlobalData->m_modDir);
		if (directory.back() != '/')
			directory += '/';
		for (const AsciiString& candidate : candidates)
		{
			AsciiString loose;
			loose.format("%s%s", directory.c_str(), candidate.str());
			if (TheLocalFileSystem->doesFileExist(loose.str()))
			{
				ModLocalizationSource source = describeModLocalization(loose);
				source.activeMod = TRUE;
				return source;
			}
		}
	}
	for (const AsciiString& candidate : candidates)
	{
		for (FileInstance instance = 0; ; ++instance)
		{
			ArchiveFile* archive = TheArchiveFileSystem->getArchiveFile(candidate, instance);
			if (archive == nullptr)
				break;
			if (isActiveModLocalizationArchive(archive))
			{
				// FileSystem counts a loose base file as instance 0, ahead of BIGs.
				return describeModLocalization(candidate, instance +
					(TheLocalFileSystem->doesFileExist(candidate.str()) ? 1 : 0));
			}
		}
	}
	return describeModLocalization(defaultFile);
}

inline ModLocalizationSource resolveVanillaLocalization(const AsciiString& filename)
{
	// Instance 1 is not necessarily vanilla: a mod can supply several BIG tables.
	for (FileInstance instance = 0; ; ++instance)
	{
		ModLocalizationSource source = describeModLocalization(filename, instance);
		if (!source.activeMod)
			return source;
	}
}
