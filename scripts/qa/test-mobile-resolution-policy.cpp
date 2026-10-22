// Run: c++ -std=c++17 -Wall -Wextra -Werror -pedantic scripts/qa/test-mobile-resolution-policy.cpp -o /tmp/test-mobile-resolution-policy && /tmp/test-mobile-resolution-policy
#include "../../GeneralsMD/Code/Main/MobileResolutionPolicy.h"
#include <cassert>
#include <string>
using MobileResolutionPolicy::choose;
using MobileResolutionPolicy::parseOptionLine;
using MobileResolutionPolicy::parseResolution;

int main()
{
    int x = 0, y = 0;
    assert(parseResolution(" 1920 1080 \n", x, y) && x == 1920 && y == 1080);
    assert(!parseResolution("1286 594 garbage", x, y));
    assert(!parseResolution("-1 594", x, y));
    assert(!parseResolution("99999999999999999999 720", x, y));
    assert(!parseResolution("0 0", x, y));
    assert(!parseResolution("1920", x, y));
    std::string key, value;
    assert(parseOptionLine("  Resolution = 1286 594\r\n", key, value));
    assert(key == "Resolution" && value == "1286 594");
    assert(parseOptionLine("GXResolutionPolicy = custom", key, value));
    assert(key == "GXResolutionPolicy" && value == "custom");
    assert(!parseOptionLine("# Resolution = 1200 600", key, value));
    assert(!parseOptionLine("no equal sign", key, value));
    auto native = choose(2340, 1080, "native", "1286 594");
    assert(native.width == 2340 && native.height == 1080 && !native.explicitCustom);
    auto migrated = choose(2340, 1080, nullptr, "1286 594");
    assert(migrated.width == 2340 && migrated.height == 1080);
    auto custom = choose(2340, 1080, "custom", "1286 594");
    assert(custom.width == 1286 && custom.height == 594 && custom.explicitCustom);
    auto offscreen = choose(2340, 1080, "custom", "3840 2160");
    assert(offscreen.width == 2340 && offscreen.height == 1080);
    auto bad = choose(2340, 1080, "custom", "abc");
    assert(bad.width == 2340 && bad.height == 1080);
    auto rotated = choose(2400, 1080, "native", "2340 1080");
    assert(rotated.width == 2400 && rotated.height == 1080);
    auto odd = choose(2341, 1080, "custom", "1921 1080");
    assert(odd.width == 1920 && odd.height == 1080);
    return 0;
}
