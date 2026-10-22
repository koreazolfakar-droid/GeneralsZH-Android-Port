#!/usr/bin/env python3
"""Host regression for the repeated-work volumetric particle optimization.

Checks real source structure and runs a C++ scalar equivalence fixture. This is
NOT a native Android build or a device FPS/visual acceptance test.
"""
# GeneralsX @performance Codex 23/10/2026 Verify volume layers retain the same bytes.
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'Core/Libraries/Source/WWVegas/WW3D2/pointgr.cpp'


def check_production_source(source):
    start = source.index('void PointGroupClass::RenderVolumeParticle(')
    volume = source[start:]
    loop = volume.index('for ( unsigned int t = 0; t < depth; ++t )')
    before, during = volume[:loop], volume[loop:]
    assert before.count('VectorProcessorClass::CopyIndexed(') == 5, 'expected exactly five compacted input arrays'
    assert 'VectorProcessorClass::CopyIndexed(' not in during, 'compaction was put back inside depth loop'
    assert 'volume_directions[i].Normalize();' in before, 'per-particle direction cache missing'
    assert 'cameraToPointDelta.Normalize();' not in during, 'normalization is repeated per layer'
    assert 'current_loc = source_loc;' in during, 'each layer must start at original coordinates'
    assert 'Update_Arrays(current_loc, current_diffuse, current_size,' in during
    assert 'SortingRendererClass::Insert_Triangles' in during
    assert 'DX8Wrapper::Draw_Triangles' in during
    assert re.search(r'depth\s*>\s*MAX_VOLUME_PARTICLE_DEPTH', before)


HARNESS = r'''
#include <cassert>
#include <cmath>
#include <cstring>
#include <vector>
#include <cstdio>
#include <algorithm>

struct P { float x,y,z; };
struct Q { float r,g,b,a; };
struct Pt { P pos; Q color; float size; unsigned char orientation, frame; };
struct Out { P pos; Q color; float size; unsigned char orientation, frame; };
static int compactions = 0, normalizations = 0;

static P sub(P a,P b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
static P normalize(P a){
    ++normalizations;
    const float length = std::sqrt(a.x*a.x+a.y*a.y+a.z*a.z);
    return length == 0 ? a : P{a.x/length,a.y/length,a.z/length};
}
static std::vector<Pt> compact(const std::vector<Pt>& data,const std::vector<int>& apt){
    ++compactions;
    std::vector<Pt> result; result.reserve(apt.size());
    for(int i:apt)result.push_back(data.at(i));
    return result;
}
static std::vector<std::vector<Out>> render(const std::vector<Pt>& input,
    const std::vector<int>& apt, bool optimized, bool billboard, unsigned depth){
    const P cam{11.0f, 31.0f, -9.0f};
    std::vector<std::vector<Out>> layers;
    std::vector<Pt> once;
    std::vector<P> directions;
    if(optimized){
        once = compact(input,apt);
        if(billboard){
            directions.reserve(once.size());
            for(const auto& p:once)directions.push_back(normalize(sub(cam,p.pos)));
        }
    }
    for(unsigned t=0;t<depth;++t){
        std::vector<Pt> points = optimized ? once : compact(input,apt);
        std::vector<Out> output;
        const float recipDepth = 0.1f / float(depth);
        const float shiftInc = float(t) * points[0].size * recipDepth;
        for(size_t i=0;i<points.size();++i){
            P pos=points[i].pos;
            if(billboard){
                P d=optimized ? directions[i] : normalize(sub(cam,pos));
                d.x*=shiftInc; d.y*=shiftInc; d.z*=shiftInc;
                pos.x+=d.x; pos.y+=d.y; pos.z+=d.z;
                // View transform; both branches run it identically.
                pos = {pos.x*0.5f+4.0f,pos.y*0.75f-8.0f,pos.z*1.25f+2.0f};
            }
            output.push_back({pos,points[i].color,points[i].size,points[i].orientation,points[i].frame});
        }
        layers.push_back(output);
    }
    return layers;
}
int main(){
    for(bool billboard:{false,true}){
        for(bool reordered:{false,true}){
            for(unsigned depth:{2u,3u,8u,16u}){
                for(int n:{1,2,5,32,128}){
                    std::vector<Pt> data;
                    for(int i=0;i<n;++i){
                        Pt p{};
                        p.pos={float(i*i+1)*0.25f,float(i-5),float(i%3)};
                        p.color={float(i%4)*0.25f,float(i%5)*0.2f,0.75f,0.5f};
                        p.size=float((i%10)+1);p.orientation=(unsigned char)(i*23);p.frame=(unsigned char)(i*7);
                        data.push_back(p);
                    }
                    std::vector<int> apt;
                    for(int i=0;i<n;++i)apt.push_back(reordered?n-1-i:i);
                    compactions=normalizations=0;
                    auto original=render(data,apt,false,billboard,depth);
                    const int oldCopies=compactions,oldNorms=normalizations;
                    compactions=normalizations=0;
                    auto candidate=render(data,apt,true,billboard,depth);
                    assert(compactions==1 && oldCopies==(int)depth);
                    assert(normalizations==(billboard?n:0));
                    assert(oldNorms==(billboard?int(n*depth):0));
                    assert(original.size()==candidate.size());
                    for(size_t t=0;t<original.size();++t){
                        assert(original[t].size()==candidate[t].size());
                        for(size_t i=0;i<original[t].size();++i){
                            const Out &a=original[t][i], &b=candidate[t][i];
                            // Compare actual fields, not compiler-dependent struct padding.
                            assert(std::memcmp(&a.pos,&b.pos,sizeof(P))==0);
                            assert(std::memcmp(&a.color,&b.color,sizeof(Q))==0);
                            assert(std::memcmp(&a.size,&b.size,sizeof(float))==0);
                            assert(a.orientation==b.orientation && a.frame==b.frame);
                        }
                    }
                }
            }
        }
    }
    std::puts("PASS: 80 cases with identical per-layer bytes and fewer repeated operations");
}
'''


def main():
    if not SOURCE.exists():
        raise SystemExit('Production source missing; run from the repository checkout')
    check_production_source(SOURCE.read_text())
    compiler = shutil.which('g++') or shutil.which('clang++')
    if compiler is None:
        raise SystemExit('C++ compiler required')
    with tempfile.TemporaryDirectory(prefix='gx-volume-particles-') as folder:
        file = Path(folder) / 'fixture.cpp'
        binary = Path(folder) / 'fixture'
        file.write_text(HARNESS)
        subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-O2', str(file), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print('PASS: renderer source loop and draw path checks')


if __name__ == '__main__':
    main()
