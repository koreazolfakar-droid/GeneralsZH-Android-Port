#pragma once

// Split a logical, half-open terrain cell interval into at most two physical
// intervals in the scrolling ring buffer. The ring has `extent` cells; the
// duplicated last map vertex is a boundary, not an additional terrain cell.
struct GXTerrainWrappedRange {
    int lo[2];
    int hi[2];
    int count;
};

inline GXTerrainWrappedRange GXTerrainSplitWrappedRange(int lo, int hi, int origin, int extent)
{
    GXTerrainWrappedRange result = {{0, 0}, {0, 0}, 0};
    if (extent <= 0) return result;
    if (lo < 0) lo = 0;
    if (hi > extent) hi = extent;
    if (lo >= hi) return result;

    int normalizedOrigin = origin % extent;
    if (normalizedOrigin < 0) normalizedOrigin += extent;
    const int first = (lo + normalizedOrigin) % extent;
    const int length = hi - lo;
    const int firstLength = length < extent - first ? length : extent - first;
    result.lo[0] = first;
    result.hi[0] = first + firstLength;
    result.count = 1;
    if (firstLength < length) {
        result.lo[1] = 0;
        result.hi[1] = length - firstLength;
        result.count = 2;
    }
    return result;
}
