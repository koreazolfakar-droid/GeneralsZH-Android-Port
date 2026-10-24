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

// GeneralsX @build BenderAI 12/02/2026 Platform-specific high-resolution timing
#ifndef _WIN32
#include <time.h>    // clock_gettime, nanosleep
#include <unistd.h>  // usleep (fallback)
#endif

FrameRateLimit::FrameRateLimit()
{
#ifdef _WIN32
	LARGE_INTEGER freq;
	LARGE_INTEGER start;
	QueryPerformanceFrequency(&freq);
	QueryPerformanceCounter(&start);
	m_freq = freq.QuadPart;
	m_start = start.QuadPart;
	m_deadline = start.QuadPart;
#else
	// Linux: Use CLOCK_MONOTONIC for high-resolution timing.
	struct timespec start;
	clock_gettime(CLOCK_MONOTONIC, &start);
	m_freq = 1000000000; // nanoseconds per second
	const Int64 tickValue = static_cast<Int64>(start.tv_sec) * 1000000000 + start.tv_nsec;
	m_start = tickValue;
	m_deadline = tickValue;
#endif
}

Real FrameRateLimit::wait(UnsignedInt maxFps)
{
	PROFILER_SECTION;

	// GeneralsX @bugfix BenderAI 24/10/2026 Use a fixed frame deadline so late frames do not drift and pile up into visible stutter on Linux/Android.
	if (maxFps == 0 || maxFps > 1000000)
	{
		// Uncapped or invalid: just return elapsed time without limiting.
#ifdef _WIN32
		LARGE_INTEGER tick;
		QueryPerformanceCounter(&tick);
		const Int64 now = tick.QuadPart;
		const double elapsedSeconds = static_cast<double>(now - m_start) / static_cast<double>(m_freq);
		m_start = now;
		m_deadline = now;
		return static_cast<Real>(elapsedSeconds);
#else
		struct timespec tick;
		clock_gettime(CLOCK_MONOTONIC, &tick);
		const Int64 now = static_cast<Int64>(tick.tv_sec) * 1000000000 + tick.tv_nsec;
		const double elapsedSeconds = static_cast<double>(now - m_start) / static_cast<double>(m_freq);
		m_start = now;
		m_deadline = now;
		return static_cast<Real>(elapsedSeconds);
#endif
	}

#ifdef _WIN32
	LARGE_INTEGER tick;
	QueryPerformanceCounter(&tick);
	Int64 now = tick.QuadPart;
	if (m_deadline == 0)
	{
		m_deadline = now;
	}

	const Int64 period = static_cast<Int64>(static_cast<double>(m_freq) / maxFps);
	if (m_deadline <= now)
	{
		m_deadline = now + period;
	}

	const Int64 waitTicks = m_deadline - now;
	if (waitTicks > 0)
	{
		const double sleepSeconds = static_cast<double>(waitTicks) / static_cast<double>(m_freq);
		const DWORD waitMs = static_cast<DWORD>(sleepSeconds * 1000.0);
		if (waitMs > 0)
		{
			Sleep(waitMs);
		}
		while (true)
		{
			QueryPerformanceCounter(&tick);
			now = tick.QuadPart;
			if (now >= m_deadline)
			{
				break;
			}
		}
	}

	const Int64 elapsed = now - m_start;
	m_start = now;
	m_deadline += period;
	return static_cast<Real>(elapsed) / static_cast<Real>(m_freq);
#else
	struct timespec tick;
	clock_gettime(CLOCK_MONOTONIC, &tick);
	Int64 now = static_cast<Int64>(tick.tv_sec) * 1000000000 + tick.tv_nsec;
	if (m_deadline == 0)
	{
		m_deadline = now;
	}

	const Int64 period = static_cast<Int64>(1000000000.0 / maxFps);
	if (m_deadline <= now)
	{
		m_deadline = now + period;
	}

	const Int64 waitNanos = m_deadline - now;
	if (waitNanos > 0)
	{
		struct timespec sleepTime;
		sleepTime.tv_sec = static_cast<time_t>(waitNanos / 1000000000LL);
		sleepTime.tv_nsec = static_cast<long>(waitNanos % 1000000000LL);
		nanosleep(&sleepTime, nullptr);
		clock_gettime(CLOCK_MONOTONIC, &tick);
		now = static_cast<Int64>(tick.tv_sec) * 1000000000 + tick.tv_nsec;
	}

	while (now < m_deadline)
	{
		clock_gettime(CLOCK_MONOTONIC, &tick);
		now = static_cast<Int64>(tick.tv_sec) * 1000000000 + tick.tv_nsec;
	}

	const Int64 elapsed = now - m_start;
	m_start = now;
	m_deadline += period;
	return static_cast<Real>(elapsed) / static_cast<Real>(m_freq);
#endif
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
