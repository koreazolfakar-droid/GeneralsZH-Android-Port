// GeneralsX @feature Codex 22/10/2026 Bounded, faction-neutral offline skirmish utilities.
#pragma once

class Player;
class Team;

namespace UniversalTacticalDirector
{
enum
{
	MAX_OBJECTS = 1024,
	MAX_TEMPLATES = 64,
	MAX_TEAMS = 128,
	MAX_TEAM_TYPES = 16,
	MAX_MEMBERS = 32,
	MAX_OBJECTIVES = 32,
	MAX_MODULES = 32
};

enum Role
{
	INFANTRY = 1 << 0, VEHICLE = 1 << 1, AIRCRAFT = 1 << 2,
	GROUND_WEAPON = 1 << 3, AIR_WEAPON = 1 << 4, VEHICLE_COUNTER = 1 << 5,
	LONG_RANGE = 1 << 6, DETECTOR = 1 << 7, HEALER = 1 << 8,
	BUILDER = 1 << 9, HARVESTER = 1 << 10, PRODUCTION = 1 << 11,
	RESOURCE = 1 << 12, TECHNOLOGY = 1 << 13, SUPERWEAPON = 1 << 14,
	STEALTH = 1 << 15, DEFENSE = 1 << 16, STRUCTURE = 1 << 17
};

struct Capabilities
{
	unsigned roles;
	Capabilities() : roles(0) {}
	bool has(unsigned mask) const { return (roles & mask) != 0; }
};

struct Situation
{
	int air, vehicles, defenses, stealth;
	int friendlyAA, friendlyCounters, friendlyRange, friendlyDetectors;
	Situation() : air(0), vehicles(0), defenses(0), stealth(0),
		friendlyAA(0), friendlyCounters(0), friendlyRange(0), friendlyDetectors(0) {}
};

// Integer utilities are deliberately modest: callers retain script priority,
// prerequisites, money, reinforcement rules and the original random draw.
inline int counterNeed(int threats, int counters)
{
	const int need = threats * 2 - counters * 3;
	return need < 0 ? 0 : (need > 24 ? 24 : need);
}

inline int productionUtility(const Capabilities& c, const Situation& s, bool hard)
{
	// Economy/construction/support-only teams keep their script-defined choice.
	if (!c.has(GROUND_WEAPON | AIR_WEAPON) || c.has(BUILDER | HARVESTER | RESOURCE)) return 0;
	int score = c.has(AIR_WEAPON) ? counterNeed(s.air, s.friendlyAA) * 4 : 0;
	if (hard)
	{
		if (c.has(VEHICLE_COUNTER)) score += counterNeed(s.vehicles, s.friendlyCounters) * 3;
		if (c.has(LONG_RANGE)) score += counterNeed(s.defenses, s.friendlyRange) * 3;
		if (c.has(DETECTOR)) score += counterNeed(s.stealth, s.friendlyDetectors) * 4;
	}
	return score;
}

inline int objectiveUtility(const Capabilities& c, int distanceBand, bool hard)
{
	int value = 12;
	if (c.has(RESOURCE)) value += 24;
	if (c.has(PRODUCTION)) value += 32;
	if (c.has(SUPERWEAPON)) value += 48;
	if (hard && c.has(LONG_RANGE | VEHICLE_COUNTER)) value += 16;
	if (hard && c.has(TECHNOLOGY)) value += 16;
	return value * 32 / (32 + distanceBand);
}

// No persistent tactical history: each invocation rebuilds its bounded snapshot.
// Playback mode is session metadata set/reset by Recorder from the existing
// replay build string; older recordings never opt in. Saves retain their format.
void setReplayMode(bool v1);
bool enabled(Player* player);
void prepareTeamHunt(Team* team);
} // namespace UniversalTacticalDirector
