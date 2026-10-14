// GeneralsX @performance Codex 14/10/2026 Last queued static terrain bytes.
// Producer-thread only. A version is committed after GL has captured its data;
// it represents FIFO submission, not a claim that the GPU has finished reading.
#pragma once
#include <algorithm>
#include <cstddef>
#include <cstring>
#include <new>
#include <vector>

class GxBufferSnapshot
{
	std::vector<unsigned char> bytes;
	size_t validEnd = 0;
	bool refused = false;
	static size_t &used() { static size_t n = 0; return n; }
public:
	static constexpr size_t maxBufferBytes = 512u << 10;
	static constexpr size_t budgetBytes = 32u << 20;
	GxBufferSnapshot() = default;
	GxBufferSnapshot(const GxBufferSnapshot &) = delete;
	GxBufferSnapshot &operator=(const GxBufferSnapshot &) = delete;
	~GxBufferSnapshot() { used() -= bytes.size(); }
	static size_t memoryBytes() { return used(); }
	bool ready(size_t size) const { return size != 0 && bytes.size() == size; }
	bool rememberFull(const unsigned char *data, size_t size, size_t initialized)
	{
		if (refused || size == 0 || size > maxBufferBytes) return false;
		if (!ready(size)) {
			if (size > budgetBytes - used()) return false;
			try {
				std::vector<unsigned char> fresh(data, data + size);
				used() -= bytes.size();
				bytes.swap(fresh);
				used() += bytes.size();
			} catch (const std::bad_alloc &) {
				refused = true; // retain ordinary uploads; do not retry allocation every frame
				return false;
			}
		} else {
			std::memcpy(bytes.data(), data, size);
		}
		validEnd = std::min(initialized, size);
		return true;
	}
	// Trim only bytes known initialized in GL. Unwritten zero-filled CPU shadow
	// bytes must still be uploaded even when their value compares equal.
	void trim(const unsigned char *data, size_t &begin, size_t &end) const
	{
		const size_t knownEnd = std::min(end, validEnd);
		while (begin + 64 <= knownEnd && std::memcmp(data + begin, bytes.data() + begin, 64) == 0) begin += 64;
		while (begin < knownEnd && data[begin] == bytes[begin]) ++begin;
		if (end <= validEnd) {
			while (end >= begin + 64 && std::memcmp(data + end - 64, bytes.data() + end - 64, 64) == 0) end -= 64;
			while (end > begin && data[end - 1] == bytes[end - 1]) --end;
		}
	}
	void rememberRange(const unsigned char *data, size_t begin, size_t end)
	{
		std::memcpy(bytes.data() + begin, data + begin, end - begin);
		if (begin <= validEnd) validEnd = std::max(validEnd, end);
	}
};
