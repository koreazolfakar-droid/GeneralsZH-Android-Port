#pragma once

// Pure resolution-selection policy shared by SDL3 startup and its host-side tests.
// A bare legacy Options.ini Resolution is ambiguous: it might come from the old
// render-scale slider or an intentional game setting. The current UI explicitly
// marks subsequent user selections as 'custom', so an unmarked legacy value
// cannot silently override the native, high-DPI Android drawable.
#include <cctype>
#include <cerrno>
#include <climits>
#include <cstdlib>
#include <cstring>
#include <string>

namespace MobileResolutionPolicy {

struct Choice {
    int width;
    int height;
    bool explicitCustom;
    const char *reason;
};

inline std::string trim(const std::string &s)
{
    const std::string::size_type first = s.find_first_not_of(" \t\r\n");
    if (first == std::string::npos)
        return std::string();
    const std::string::size_type last = s.find_last_not_of(" \t\r\n");
    return s.substr(first, last - first + 1);
}

inline bool parseOptionLine(const char *line, std::string &key, std::string &value)
{
    if (!line)
        return false;
    const char *eq = std::strchr(line, '=');
    if (!eq)
        return false;
    key = trim(std::string(line, static_cast<size_t>(eq - line)));
    value = trim(eq + 1);
    return !key.empty() && !value.empty() && key[0] != '#' && key[0] != ';';
}

inline bool parseResolution(const char *text, int &width, int &height)
{
    if (!text)
        return false;
    char *end = nullptr;
    errno = 0;
    const long x = std::strtol(text, &end, 10);
    if (errno || end == text || x < 640 || x > 8192)
        return false;
    const char *second = end;
    errno = 0;
    const long y = std::strtol(second, &end, 10);
    if (errno || end == second || y < 360 || y > 8192)
        return false;
    while (*end && std::isspace(static_cast<unsigned char>(*end)))
        ++end;
    if (*end)
        return false;
    width = static_cast<int>(x) & ~1;
    height = static_cast<int>(y);
    return true;
}

inline Choice choose(int nativeWidth, int nativeHeight, const char *policy, const char *saved)
{
    // Caller supplies SDL_GetWindowSizeInPixels(), already checked positive.
    Choice result = {nativeWidth & ~1, nativeHeight, false, "native-default"};
    if (!policy || std::strcmp(policy, "custom") != 0) {
        if (policy && std::strcmp(policy, "native") == 0)
            result.reason = "explicit-native";
        else if (saved && *saved)
            result.reason = "unmarked-legacy-resolution-ignored";
        return result;
    }
    int x = 0, y = 0;
    if (!parseResolution(saved, x, y) || x > result.width || y > result.height) {
        result.reason = "invalid-custom-fallback-native";
        return result;
    }
    result.width = x;
    result.height = y;
    result.explicitCustom = true;
    result.reason = "explicit-custom";
    return result;
}

} // namespace MobileResolutionPolicy
