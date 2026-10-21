// GeneralsX @feature Codex 14/10/2026 Bounded preRTT attribution, no per-event logging.
// Main engine thread only. Nested phases overlap; wall minus thread CPU includes
// scheduling and waits, not a GPU-duration measurement.
#pragma once
#include "GXFrameTimeStats.h"
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>

namespace GXPreRTT {
enum Phase { Views, Particles, Terrain, Region, Callbacks, Drawable, Hierarchy,
             ParticleSystems, Emission, ParticleSteps, Smudge, Bridges, PhaseCount };
inline double wallUs() {
    return std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now().time_since_epoch()).count();
}
inline double (*&cpuClockReader())() { static double (*reader)()=nullptr; return reader; }
inline double cpuUs() { const auto reader=cpuClockReader(); return reader?reader():-1; }
struct Totals { double wall=0,cpu=0; uint64_t calls=0,cpuSamples=0; };
struct Module { int key=0; bool used=false; Totals time; };
struct State {
    bool active=false, reportReady=false, hasMode=false, load=false;
    unsigned lastLogicFrame=0;
    double window=0, rootWall=0,rootCpu=0,queueWait=0;
    uint64_t frames=0,cpuFrames=0,scanned=0,matched=0,drawn=0,hidden=0,viewUpdates=0;
    uint64_t particleTicks=0,systems=0,particleSteps=0,poseBones=0,poseChildren=0,fullMapRefreshes=0,bridgeRebuilds=0,bridgeEmptyAvoided=0;
    std::array<Totals,PhaseCount> phases{};
    std::array<Module,64> modules{};
    Totals moduleOverflow;
    GXFrameTimeStats<2048> pre;
    void resetWindow(double now) {
        for(auto&m:modules) m.time=Totals();
        moduleOverflow=Totals(); phases={}; pre.reset();
        window=now; rootWall=rootCpu=queueWait=0;
        frames=cpuFrames=scanned=matched=drawn=hidden=viewUpdates=0;
        particleTicks=systems=particleSteps=poseBones=poseChildren=fullMapRefreshes=bridgeRebuilds=bridgeEmptyAvoided=0;
        reportReady=false;
    }
    Module *module(int key) {
        const size_t start=uint32_t(key)%modules.size();
        for(size_t i=0;i<modules.size();++i) {
            Module &m=modules[(start+i)%modules.size()];
            if(!m.used) { m.used=true; m.key=key; return &m; }
            if(m.key==key) return &m;
        }
        return nullptr;
    }
};
inline State &state() { static State s; return s; }
inline bool active() { return state().active; }
struct Scope {
    bool enabled;
    Phase phase;
    double wall=0,cpu=-1;
    Scope(Phase p,bool measureCpu=false):enabled(active()),phase(p) {
        if(enabled) { wall=wallUs(); if(measureCpu) cpu=cpuUs(); }
    }
    ~Scope() {
        if(!enabled) return;
        Totals &t=state().phases[phase];
        t.wall+=wallUs()-wall; ++t.calls;
        if(cpu>=0) { const double end=cpuUs(); if(end>=cpu) { t.cpu+=end-cpu; ++t.cpuSamples; } }
    }
};
struct ModuleScope {
    bool enabled;
    double start=0;
    Totals *time=nullptr;
    explicit ModuleScope(int key):enabled(active()) {
        if(enabled) {
            Module *m=state().module(key);
            time=m?&m->time:&state().moduleOverflow; start=wallUs();
        }
    }
    ~ModuleScope() { if(enabled) { time->wall+=wallUs()-start; ++time->calls; } }
};
struct Frame {
    bool enabled, finished=false;
    double wall=0,cpu=-1,wait=0;
    Frame(bool on,double producerWait,bool loadScreen=false,unsigned logicFrame=0,double (*reader)()=nullptr):enabled(on&&!active()),wait(producerWait) {
        if(!enabled) return;
        State &s=state(); cpuClockReader()=reader; wall=wallUs(); cpu=cpuUs();
        if(s.hasMode && (s.load!=loadScreen || logicFrame<s.lastLogicFrame)) s.resetWindow(wall);
        if(s.window==0) s.window=wall;
        s.hasMode=true; s.load=loadScreen; s.lastLogicFrame=logicFrame;
        s.active=true;
    }
    void finish(double producerWait) {
        if(!enabled||finished) return;
        finished=true;
        State &s=state(); s.active=false;
        const double end=wallUs(), duration=end-wall, cpuEnd=cpuUs();
        s.rootWall+=duration; ++s.frames; s.pre.add(duration/1000,0);
        if(cpu>=0&&cpuEnd>=cpu) { s.rootCpu+=cpuEnd-cpu; ++s.cpuFrames; }
        if(producerWait>=wait) s.queueWait+=producerWait-wait;
        s.reportReady=end-s.window>=2000000;
    }
    ~Frame() { finish(wait); }
};
template<class Name> inline void report(Name name,unsigned logicFrame,bool loadScreen) {
    State &s=state(); if(!s.reportReady||s.active||!s.frames) return;
    const double now=wallUs(), n=double(s.frames);
    const auto ms=[&](Phase p){return s.phases[p].wall/n/1000;};
    const auto cpu=[&](Phase p){const Totals&t=s.phases[p];return !t.calls?0.0:(t.cpuSamples==t.calls?t.cpu/n/1000:-1.0);};
    const double scan=s.phases[Region].wall-s.phases[Callbacks].wall;
    double modules=s.moduleOverflow.wall;
    for(const auto&m:s.modules) modules+=m.time.wall;
    const double prep=s.phases[Drawable].wall-modules;
    const double viewOther=s.phases[Views].wall-s.phases[Terrain].wall-s.phases[Region].wall;
    fprintf(stderr,"[GX-PERF-PRERTT] t=%.0fus windowMs=%.3f logicFrame=%u loadScreen=%d frames=%llu dropped=%zu preP50/P95/P99=%.3f/%.3f/%.3f wall=%.3f threadCpu=%.3f producerWait=%.3f viewsWall/Cpu=%.3f/%.3f particlesWall/Cpu=%.3f/%.3f terrainWall/Cpu=%.3f/%.3f regionWall=%.3f scanWall=%.3f callbacksWall=%.3f scanned/matched/drawable/hidden=%.1f/%.1f/%.1f/%.1f fullMapRefreshAttempts=%.1f viewUpdates=%.1f viewsOtherWall=%.3f drawableWall/prep/moduleWall=%.3f/%.3f/%.3f (ms/frame; nested phases overlap; wall-CPU includes descheduling; GPU unavailable here)\n",
        now,(now-s.window)/1000,logicFrame,int(loadScreen),(unsigned long long)s.frames,s.pre.dropped,
        s.pre.percentile(.50),s.pre.percentile(.95),s.pre.percentile(.99),s.rootWall/n/1000,
        s.cpuFrames==s.frames?s.rootCpu/n/1000:-1.0,s.queueWait/n/1000,ms(Views),cpu(Views),ms(Particles),cpu(Particles),ms(Terrain),cpu(Terrain),
        ms(Region),scan>0?scan/n/1000:0,ms(Callbacks),s.scanned/n,s.matched/n,s.drawn/n,s.hidden/n,s.fullMapRefreshes/n,s.viewUpdates/n,viewOther>0?viewOther/n/1000:0,ms(Drawable),prep>0?prep/n/1000:0,modules/n/1000);
    fprintf(stderr,"[GX-PERF-PRERTT-WORK] hierarchy=%.3fms calls=%.1f bones=%.1f children=%.1f particleTicks=%.1f systems=%.1f particleSteps=%.1f systemWall=%.3f emitWall=%.3f stepWall=%.3f smudgeWall=%.3f bridgeWall=%.3f bridgeCalls/rebuilds/emptyAvoided=%.1f/%.1f/%.1f (per frame; inclusive wall costs)\n",
        ms(Hierarchy),s.phases[Hierarchy].calls/n,s.poseBones/n,s.poseChildren/n,s.particleTicks/n,s.systems/n,s.particleSteps/n,
        ms(ParticleSystems),ms(Emission),ms(ParticleSteps),ms(Smudge),ms(Bridges),s.phases[Bridges].calls/n,s.bridgeRebuilds/n,s.bridgeEmptyAvoided/n);
    std::array<bool,64> printed{};
    for(size_t row=0;row<8;++row) {
        size_t best=s.modules.size(); double cost=-1;
        for(size_t i=0;i<s.modules.size();++i) if(s.modules[i].used&&s.modules[i].time.calls&&!printed[i]&&s.modules[i].time.wall>cost) {best=i;cost=s.modules[i].time.wall;}
        if(best==s.modules.size()) break;
        printed[best]=true; const Module&m=s.modules[best];
        name(m.key,m.time.wall/n/1000,double(m.time.calls)/n);
    }
    if(s.moduleOverflow.calls) fprintf(stderr,"[GX-PERF-DRAWMODULE] type=<overflow> wallMs=%.3f calls=%.1f per frame\n",s.moduleOverflow.wall/n/1000,s.moduleOverflow.calls/n);
    // Retain stable type slots; only counters reset. No per-frame allocation/name lookup.
    s.resetWindow(wallUs());
}
}
