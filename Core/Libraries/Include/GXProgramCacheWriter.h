/*
** Command & Conquer Generals Zero Hour(tm)
** Copyright 2025 Electronic Arts Inc.
** SPDX-License-Identifier: GPL-3.0-or-later
*/
#pragma once

// Shader program *disk* cache writer. GL object access and glGetProgramBinary
// remain on the owning render context; only filesystem I/O moves to this worker.
// One low-priority thread, bounded byte queue and atomic rename. Nothing is read
// or written to game logic, CRC, models, or texture state.
#include <atomic>
#include <condition_variable>
#include <cstdio>
#include <cstdint>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>
#if defined(__ANDROID__)
#include <sys/resource.h>
#include <unistd.h>
#endif

class GXProgramCacheWriter
{
public:
    GXProgramCacheWriter() = default;
    GXProgramCacheWriter(const GXProgramCacheWriter&) = delete;
    GXProgramCacheWriter& operator=(const GXProgramCacheWriter&) = delete;

    ~GXProgramCacheWriter()
    {
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            m_stopping = true;
        }
        m_ready.notify_one();
        if (m_thread.joinable())
            m_thread.join();
    }

    // Returns false if unavailable/full. Caller may use original sync writer;
    // never drop the binary or impact the shader that is already linked.
    bool enqueue(const std::string& path, uint32_t format, std::vector<uint8_t>&& bytes)
    {
        if (path.empty() || bytes.empty())
            return false;
        const size_t length = bytes.size();
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_stopping || length > kMaxPendingBytes || m_pendingBytes > kMaxPendingBytes - length)
            return false;
        if (!m_thread.joinable()) {
            try {
                m_thread = std::thread([this] { run(); });
            } catch (...) {
                return false;
            }
        }
        m_queue.push_back(Job{path, format, std::move(bytes)});
        m_pendingBytes += length;
        m_ready.notify_one();
        return true;
    }

    unsigned takeCompleted() { return m_completed.exchange(0, std::memory_order_relaxed); }

private:
    static constexpr size_t kMaxPendingBytes = 24u << 20;
    struct Job {
        std::string path;
        uint32_t format;
        std::vector<uint8_t> bytes;
    };

    static bool writeOne(const Job& job)
    {
        const std::string temp = job.path + ".tmp";
        FILE *file = fopen(temp.c_str(), "wb");
        if (!file)
            return false;
        const uint32_t header[3] = {0x42505847u, job.format, static_cast<uint32_t>(job.bytes.size())};
        const bool ok = fwrite(header, sizeof(header), 1, file) == 1
            && fwrite(job.bytes.data(), 1, job.bytes.size(), file) == job.bytes.size()
            && fflush(file) == 0;
        const bool closed = fclose(file) == 0;
        if (ok && closed && rename(temp.c_str(), job.path.c_str()) == 0)
            return true;
        remove(temp.c_str());
        return false;
    }

    void run()
    {
#if defined(__ANDROID__)
        // Do not compete with the game/render threads while streaming new views.
        setpriority(PRIO_PROCESS, static_cast<id_t>(gettid()), 10);
#endif
        for (;;) {
            Job job;
            {
                std::unique_lock<std::mutex> lock(m_mutex);
                m_ready.wait(lock, [this] { return m_stopping || !m_queue.empty(); });
                if (m_queue.empty() && m_stopping)
                    break;
                job = std::move(m_queue.front());
                m_queue.pop_front();
            }
            const bool saved = writeOne(job);
            {
                std::lock_guard<std::mutex> lock(m_mutex);
                m_pendingBytes -= job.bytes.size();
            }
            if (saved)
                m_completed.fetch_add(1, std::memory_order_relaxed);
        }
    }

    std::mutex m_mutex;
    std::condition_variable m_ready;
    std::deque<Job> m_queue;
    std::thread m_thread;
    size_t m_pendingBytes = 0;
    bool m_stopping = false;
    std::atomic<unsigned> m_completed{0};
};
