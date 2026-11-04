/*
**	Command & Conquer Generals Zero Hour(tm)
**	Copyright 2025 TheSuperHackers
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

#include "PreRTS.h"
#include "Common/FrameRateLimit.h"
#include <algorithm>

// GeneralsX @build BenderAI 12/02/2026 Platform-specific high-resolution timing
#ifndef _WIN32
#include <time.h>    // clock_gettime, nanosleep
#include <errno.h>
#endif

// GeneralsX @bugfix Codex 04/11/2026 Keep a scheduled deadline across small
// scheduler oversleeps, but rebase after a missed frame or a limiter change.
// Only render pacing changes: elapsed time remains the actual wall interval.
static Int64 frameRateLimitTick()
{
#ifdef _WIN32
	LARGE_INTEGER tick;
	QueryPerformanceCounter(&tick);
	return tick.QuadPart;
#else
	struct timespec tick;
	clock_gettime(CLOCK_MONOTONIC, &tick);
	return static_cast<Int64>(tick.tv_sec) * 1000000000 + tick.tv_nsec;
#endif
}

FrameRateLimit::FrameRateLimit()
{
#ifdef _WIN32
	LARGE_INTEGER freq;
	QueryPerformanceFrequency(&freq);
	m_freq = freq.QuadPart;
#else
	m_freq = 1000000000; // nanoseconds per second
#endif
	m_start = frameRateLimitTick();
	m_deadline = m_start;
	m_lastMaxFps = 0;
}

Real FrameRateLimit::wait(UnsignedInt maxFps)
{
	PROFILER_SECTION;
	Int64 tick = frameRateLimitTick();

	// Include the preset sentinel itself. Uncapped frames never sleep/spin.
	if (maxFps == 0 || maxFps >= RenderFpsPreset::UncappedFpsValue)
	{
		const Real elapsed = static_cast<Real>(static_cast<double>(tick - m_start) / m_freq);
		m_start = m_deadline = tick;
		m_lastMaxFps = 0;
		return elapsed;
	}

	const Int64 period = std::max<Int64>(1, m_freq / maxFps);
	const Int64 deadline = (m_lastMaxFps == maxFps ? m_deadline : m_start) + period;
#ifdef _WIN32
	const double sleepSeconds = static_cast<double>(deadline - tick) / m_freq - 0.002;
	if (sleepSeconds > 0.0)
		Sleep(static_cast<DWORD>(sleepSeconds * 1000));
#else
	// GeneralsX @performance Codex 04/11/2026 Leave only 0.2 ms to spin on
	// high-resolution POSIX timers. Recompute after an interrupted sleep so a
	// signal cannot turn the rest of a whole frame into a CPU-burning wait.
	const Int64 spinTicks = m_freq / 5000;
	while (deadline - tick > spinTicks)
	{
		const Int64 sleepTicks = deadline - tick - spinTicks;
		struct timespec sleepTime;
		sleepTime.tv_sec = static_cast<time_t>(sleepTicks / m_freq);
		sleepTime.tv_nsec = static_cast<long>((sleepTicks % m_freq) * 1000000000 / m_freq);
		const int result = nanosleep(&sleepTime, nullptr);
		if (result != 0 && errno != EINTR)
			break;
		tick = frameRateLimitTick();
	}
#endif

	while (tick < deadline)
		tick = frameRateLimitTick();

	const Real elapsed = static_cast<Real>(static_cast<double>(tick - m_start) / m_freq);
	m_start = tick;
	// Do not replay missed render deadlines after loading/backgrounding or a
	// slow frame. Small scheduler jitter is corrected by the following wait.
	m_deadline = tick - deadline >= period ? tick : deadline;
	m_lastMaxFps = maxFps;
	return elapsed;
}


const UnsignedInt RenderFpsPreset::s_fpsValues[] = {
#if defined(GENERALS_ONLINE_HIGH_FPS_SERVER)
	60, 65, 70, 72, 75, 80, 85, 90, 100, 110, 120, 144, 240, 480, UncappedFpsValue };
#else
	30, 50, 56, 60, 65, 70, 72, 75, 80, 85, 90, 100, 110, 120, 144, 240, 480, UncappedFpsValue };
#endif

static_assert(LOGICFRAMES_PER_SECOND <= GENERALS_ONLINE_HIGH_FPS_LIMIT, "Min FPS values need to be revisited!");

UnsignedInt RenderFpsPreset::getNextFpsValue(UnsignedInt value)
{
	const Int first = 0;
	const Int last = ARRAY_SIZE(s_fpsValues) - 1;
	for (Int i = first; i < last; ++i)
	{
		if (value >= s_fpsValues[i] && value < s_fpsValues[i + 1])
		{
			return s_fpsValues[i + 1];
		}
	}
	return s_fpsValues[last];
}

UnsignedInt RenderFpsPreset::getPrevFpsValue(UnsignedInt value)
{
	const Int first = 0;
	const Int last = ARRAY_SIZE(s_fpsValues) - 1;
	for (Int i = last; i > first; --i)
	{
		if (value <= s_fpsValues[i] && value > s_fpsValues[i - 1])
		{
			return s_fpsValues[i - 1];
		}
	}
	return s_fpsValues[first];
}

UnsignedInt RenderFpsPreset::changeFpsValue(UnsignedInt value, FpsValueChange change)
{
	switch (change)
	{
	default:
	case FpsValueChange_Increase: return getNextFpsValue(value);
	case FpsValueChange_Decrease: return getPrevFpsValue(value);
	}
}


UnsignedInt LogicTimeScaleFpsPreset::getNextFpsValue(UnsignedInt value)
{
	return value + StepFpsValue;
}

UnsignedInt LogicTimeScaleFpsPreset::getPrevFpsValue(UnsignedInt value)
{
	if (value - StepFpsValue < MinFpsValue)
	{
		return MinFpsValue;
	}
	else
	{
		return value - StepFpsValue;
	}
}

UnsignedInt LogicTimeScaleFpsPreset::changeFpsValue(UnsignedInt value, FpsValueChange change)
{
	switch (change)
	{
	default:
	case FpsValueChange_Increase: return getNextFpsValue(value);
	case FpsValueChange_Decrease: return getPrevFpsValue(value);
	}
}
