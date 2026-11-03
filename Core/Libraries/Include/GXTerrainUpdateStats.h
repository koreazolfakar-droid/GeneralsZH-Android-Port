// GeneralsX @feature Astra 03/11/2026 Main-thread terrain invalidation attribution.
// Reported with the existing two-second GX_PERF terrain window, never per frame.
#pragma once
#include "GXTrace.h"
#include <cstdint>
#include <cstdio>

namespace GXTerrainUpdates {
enum Reason { Initialization, StaticLightingOrHeight, TimeOfDay, ResourceRestore,
              DrawSize, InvalidHeightCell, ReasonCount, Unspecified = ReasonCount };
struct Counters {
    uint64_t requests[ReasonCount]{};
    uint64_t fullCompleted=0, initialCompleted=0, cameraFullCompleted=0;
    uint64_t sizeRejected=0, overrideRejected=0, partialUpdates=0;
    uint64_t regeneratedQuads=0, uploads=0, uploadedBytes=0;
};
inline Counters &state() { static Counters c; return c; }
inline Reason &context() { static Reason r=Unspecified; return r; }
struct ReasonScope {
    Reason previous;
    explicit ReasonScope(Reason reason):previous(context()) { context()=reason; }
    ~ReasonScope() { context()=previous; }
};
inline void request(Reason fallback) {
    if (GXTrace::isPerfEnabled()) ++state().requests[context()==Unspecified?fallback:context()];
}
inline void report(double nowUs) {
    const Counters &c=state(); uint64_t total=0;
    for (unsigned i=0;i<ReasonCount;++i) total+=c.requests[i];
    std::fprintf(stderr,"[GX-PERF-TERRAIN-REBUILD] t=%.0fus fullRequests=%llu reasons(init/staticLightingOrHeight/timeOfDay/resources/drawSize/invalidHeight)=%llu/%llu/%llu/%llu/%llu/%llu fullCompleted=%llu initialCompleted=%llu cameraFullCompleted=%llu unchangedSizeRejected=%llu overrideRebuildsAvoided=%llu partialUpdates=%llu regeneratedQuads=%llu vbUploads=%llu uploadedBytes=%llu (interval totals; VB bytes submitted, GPU transfer counters remain separate)\n",
        nowUs,(unsigned long long)total,
        (unsigned long long)c.requests[Initialization],(unsigned long long)c.requests[StaticLightingOrHeight],
        (unsigned long long)c.requests[TimeOfDay],(unsigned long long)c.requests[ResourceRestore],
        (unsigned long long)c.requests[DrawSize],(unsigned long long)c.requests[InvalidHeightCell],
        (unsigned long long)c.fullCompleted,(unsigned long long)c.initialCompleted,(unsigned long long)c.cameraFullCompleted,
        (unsigned long long)c.sizeRejected,(unsigned long long)c.overrideRejected,(unsigned long long)c.partialUpdates,
        (unsigned long long)c.regeneratedQuads,(unsigned long long)c.uploads,(unsigned long long)c.uploadedBytes);
    state()=Counters();
}
}
