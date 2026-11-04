#!/usr/bin/env python3
"""Compare production object-shroud classification with its pre-fix implementation.
Runs exhaustive visibility combinations and ghost transitions; host only, no FPS claim.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATH = 'GeneralsMD/Code/GameEngine/Source/GameLogic/Object/PartitionManager.cpp'
BASE = '392b2f7b12da16786661ab1c8aa75ee0d736d933'


def extract(source, signature):
    start = source.index(signature)
    end = source.index('\n//-----------------------------------------------------------------------------', start)
    return source[start:end]



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-ref', help='Run the candidate checks against another revision (baseline must fail query bound).')
    args = parser.parse_args()
    signature = 'ObjectShroudStatus PartitionData::getShroudedStatus('
    source = subprocess.check_output(['git', 'show', args.source_ref + ':' + PATH], cwd=ROOT, text=True) if args.source_ref else (ROOT / PATH).read_text()
    current = extract(source, signature)
    legacy = extract(subprocess.check_output(['git', 'show', BASE + ':' + PATH], cwd=ROOT, text=True), signature)
    code = r'''
#include <cassert>
#include <cstdio>
#include <vector>
#include <algorithm>
using Int=int;using Bool=bool;using ObjectShroudStatus=int;using CellShroudStatus=int;
constexpr int MAX_PLAYER_COUNT=8,OBJECTSHROUD_CLEAR=0,OBJECTSHROUD_PARTIAL_CLEAR=1;
constexpr int OBJECTSHROUD_FOGGED=2,OBJECTSHROUD_SHROUDED=3,OBJECTSHROUD_INVALID=4,OBJECTSHROUD_INVALID_BUT_PREVIOUS_VALID=5;
constexpr int CELLSHROUD_CLEAR=0,CELLSHROUD_FOGGED=1,CELLSHROUD_SHROUDED=2;
constexpr int KINDOF_IMMOBILE=1,KINDOF_MINE=2,NEUTRAL=0;
#define DEBUG_ASSERTCRASH(condition,message) assert(condition)
static unsigned queries=0;
struct PartitionCell {int status;int getShroudStatusForPlayer(int) const {++queries;return status;}};
struct CellAndObjectIntersection {PartitionCell cell;PartitionCell*getCell(){return &cell;}};
struct Manager {bool updated=true;bool getUpdatedSinceLastReset(){return updated;}} manager;
static Manager*ThePartitionManager=&manager;
struct Player {int relationship=0;int getRelationship(int){return relationship;}} player;
struct Players {Player*getNthPlayer(int){return &player;}} players;
static Players*ThePlayerList=&players;
struct Object {int kinds=0;int getTeam(){return 0;}bool isKindOf(int k){return kinds&k;}};
struct Ghost {int freed=0,snapped=0;void freeSnapShot(int){++freed;}void snapShot(int){++snapped;}};
struct Data {
 int m_shroudedness[8]{},m_shroudednessPrevious[8]{};bool m_everSeenByPlayer[8]{};
 CellAndObjectIntersection*m_coiArray=nullptr;int m_coiInUseCount=0;Object*m_object=nullptr;Ghost*m_ghostObject=nullptr;
 void invalidateShroudedStatusForPlayer(int p){m_shroudedness[p]=OBJECTSHROUD_INVALID;}
};
struct PartitionData:Data {int getShroudedStatus(int);};
struct LegacyPartitionData:Data {int getShroudedStatus(int);};
'''
    code += legacy.replace('PartitionData::', 'LegacyPartitionData::') + '\n' + current
    code += r'''
int main(){
 unsigned cases=0;
 for(int count=0;count<=7;++count){
  int combinations=1;for(int i=0;i<count;++i)combinations*=3;
  for(int pattern=0;pattern<combinations;++pattern){
   std::vector<CellAndObjectIntersection> cells(count);int v=pattern;
   for(auto&c:cells){c.cell.status=v%3;v/=3;}
   for(int previous=0;previous<4;++previous)for(int flags=0;flags<64;++flags)
    for(int validity:{OBJECTSHROUD_INVALID,OBJECTSHROUD_INVALID_BUT_PREVIOUS_VALID,OBJECTSHROUD_CLEAR}){
     Object object;object.kinds=flags&3;Ghost a,b;player.relationship=(flags>>2)&1;
     PartitionData candidate;LegacyPartitionData baseline;
     candidate.m_coiArray=baseline.m_coiArray=cells.data();candidate.m_coiInUseCount=baseline.m_coiInUseCount=count;
     candidate.m_object=baseline.m_object=(flags&8)?&object:nullptr;
     candidate.m_ghostObject=(flags&16)?&a:nullptr;baseline.m_ghostObject=(flags&16)?&b:nullptr;
     candidate.m_shroudedness[0]=baseline.m_shroudedness[0]=validity;
     candidate.m_shroudednessPrevious[0]=baseline.m_shroudednessPrevious[0]=previous;
     candidate.m_everSeenByPlayer[0]=baseline.m_everSeenByPlayer[0]=(flags&32);
     queries=0;int expected=baseline.getShroudedStatus(0);unsigned before=queries;
     queries=0;assert(candidate.getShroudedStatus(0)==expected);assert(queries<=before);
     assert(candidate.m_shroudednessPrevious[0]==baseline.m_shroudednessPrevious[0]);
     assert(candidate.m_everSeenByPlayer[0]==baseline.m_everSeenByPlayer[0]);
     assert(a.freed==b.freed&&a.snapped==b.snapped);++cases;
    }
  }
 }
 {
  PartitionData candidate;candidate.m_shroudedness[0]=OBJECTSHROUD_CLEAR;
  queries=0;manager.updated=false;
  assert(candidate.getShroudedStatus(0)==OBJECTSHROUD_INVALID&&queries==0);
  manager.updated=true;
 }
 for(int n:{100,500,1376}){
  std::vector<CellAndObjectIntersection> cells(n);for(auto&c:cells)c.cell.status=CELLSHROUD_FOGGED;cells[0].cell.status=CELLSHROUD_CLEAR;
  PartitionData candidate;LegacyPartitionData baseline;
  candidate.m_coiArray=baseline.m_coiArray=cells.data();candidate.m_coiInUseCount=baseline.m_coiInUseCount=n;
  candidate.m_shroudedness[0]=baseline.m_shroudedness[0]=OBJECTSHROUD_INVALID;
  queries=0;assert(baseline.getShroudedStatus(0)==OBJECTSHROUD_PARTIAL_CLEAR);unsigned before=queries;
  queries=0;assert(candidate.getShroudedStatus(0)==OBJECTSHROUD_PARTIAL_CLEAR);
  printf("host mixed-visibility fixture cells=%d queries=%u -> %u\n",n,before,queries);
  assert(queries==2);
 }
 printf("PASS: %u exhaustive production classifications and ghost/ever-seen/previous-state transitions\n",cases);
}
'''
    with tempfile.TemporaryDirectory(prefix='gx-shroud-') as temp:
        cpp = Path(temp) / 'test.cpp'
        exe = Path(temp) / 'test'
        cpp.write_text(code)
        for defines in ([], ['-DDISABLE_INVALID_PREVENTION']):
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
                            *defines, str(cpp), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
