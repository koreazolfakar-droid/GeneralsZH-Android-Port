#pragma once
// GeneralsX @bugfix Codex 07/10/2026 Bound a complete lobby/signaling message, including all fragments.
#include <cstddef>
#include <cstring>
#include <vector>
constexpr size_t GX_MAX_ONLINE_MESSAGE_BYTES = 1024 * 1024;
inline bool GXAppendOnlineFragment(std::vector<char>& buffer, const char* data, size_t size)
{
    if (buffer.size() > GX_MAX_ONLINE_MESSAGE_BYTES ||
        size > GX_MAX_ONLINE_MESSAGE_BYTES - buffer.size() || (!data && size)) return false;
    try {
        const size_t start = buffer.size();
        buffer.resize(start + size);
        if (size) std::memcpy(buffer.data() + start, data, size);
        return true;
    } catch (...) {
        return false;
    }
}
