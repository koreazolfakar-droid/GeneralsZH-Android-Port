// GeneralsX @feature Codex 03/11/2026 Bounded diagnostic attribution for
// synchronous production work. Never changes or schedules simulation work.
#pragma once

#include <chrono>
#include <cstdio>

enum GXProductionStage
{
	GXPS_BOOKKEEPING,
	GXPS_FLAGS,
	GXPS_AVAILABILITY,
	GXPS_BUILD_TIME,
	GXPS_RESERVE,
	GXPS_CREATE,
	GXPS_EXIT,
	GXPS_AUDIO,
	GXPS_NOTIFY,
	GXPS_CALLBACKS,
	GXPS_UPGRADE_NOTIFY,
	GXPS_UPGRADE_APPLY,
	GXPS_CLEANUP,
	GXPS_COUNT
};

template<class Clock = std::chrono::steady_clock>
class GXProductionProfile
{
public:
	GXProductionProfile(bool enabled, unsigned frame, unsigned id, const char* name) :
		m_enabled(enabled && reportCount() < 64), m_frame(frame), m_id(id), m_name(name),
		m_stage(GXPS_BOOKKEEPING)
	{
		if (!m_enabled)
			return;
		for (unsigned i = 0; i < GXPS_COUNT; ++i) {
			m_us[i] = 0.0;
			m_calls[i] = 0;
		}
		m_calls[m_stage] = 1;
		m_start = m_last = Clock::now();
	}

	void mark(GXProductionStage next)
	{
		if (!m_enabled)
			return;
		const typename Clock::time_point now = Clock::now();
		m_us[m_stage] += std::chrono::duration<double, std::micro>(now - m_last).count();
		m_last = now;
		m_stage = next;
		++m_calls[next];
	}

	~GXProductionProfile()
	{
		if (!m_enabled)
			return;
		const typename Clock::time_point now = Clock::now();
		m_us[m_stage] += std::chrono::duration<double, std::micro>(now - m_last).count();
		const double total = std::chrono::duration<double, std::micro>(now - m_start).count();
		if (total < 5000.0 || reportCount() >= 64)
			return;
		++reportCount();
		fprintf(stderr, "[GX-PERF-PRODUCTION] frame=%u id=%u template=%s wall=%.3fms "
			"bookkeeping=%.3f flags=%.3f availability=%.3f buildTime=%.3f reserve=%.3f "
			"create=%.3f exit=%.3f audio=%.3f notify=%.3f callbacks=%.3f "
			"upgradeNotify=%.3f upgradeApply=%.3f cleanup=%.3f creates=%u exits=%u\n",
			m_frame, m_id, m_name, total / 1000.0,
			m_us[GXPS_BOOKKEEPING] / 1000.0, m_us[GXPS_FLAGS] / 1000.0,
			m_us[GXPS_AVAILABILITY] / 1000.0, m_us[GXPS_BUILD_TIME] / 1000.0,
			m_us[GXPS_RESERVE] / 1000.0, m_us[GXPS_CREATE] / 1000.0,
			m_us[GXPS_EXIT] / 1000.0, m_us[GXPS_AUDIO] / 1000.0,
			m_us[GXPS_NOTIFY] / 1000.0, m_us[GXPS_CALLBACKS] / 1000.0,
			m_us[GXPS_UPGRADE_NOTIFY] / 1000.0, m_us[GXPS_UPGRADE_APPLY] / 1000.0,
			m_us[GXPS_CLEANUP] / 1000.0, m_calls[GXPS_CREATE], m_calls[GXPS_EXIT]);
	}

private:
	GXProductionProfile(const GXProductionProfile&) = delete;
	GXProductionProfile& operator=(const GXProductionProfile&) = delete;
	static unsigned& reportCount() { static unsigned count = 0; return count; }
	bool m_enabled;
	unsigned m_frame, m_id;
	const char* m_name;
	GXProductionStage m_stage;
	typename Clock::time_point m_start, m_last;
	double m_us[GXPS_COUNT];
	unsigned m_calls[GXPS_COUNT];
};
