// GeneralsX @feature Codex 22/10/2026 Engine-interface doubles for the exact production adapter.
#include <cassert>
#include <bitset>
#include <chrono>
#include <cstdio>
#include <limits>
#include <list>
#include <map>
#include <string>
#include <vector>
#include "GameLogic/UniversalTacticalDirector.h"

struct AsciiString : std::string {
 using std::string::string;
 void concat(const AsciiString& value) {append(value);}
};
using Int = int;
using Bool = bool;
using Real = float;
enum { KINDOF_INFANTRY, KINDOF_VEHICLE, KINDOF_AIRCRAFT, KINDOF_STRUCTURE, KINDOF_DOZER,
 KINDOF_HARVESTER, KINDOF_FS_FACTORY, KINDOF_FS_BARRACKS, KINDOF_FS_WARFACTORY,
 KINDOF_FS_AIRFIELD, KINDOF_FS_SUPPLY_CENTER, KINDOF_CASH_GENERATOR, KINDOF_FS_BLACK_MARKET,
 KINDOF_MONEY_HACKER, KINDOF_FS_TECHNOLOGY, KINDOF_FS_ADVANCED_TECH, KINDOF_FS_SUPERWEAPON,
 KINDOF_FS_BASE_DEFENSE, KINDOF_HEAL_PAD, KINDOF_REPAIR_PAD, KINDOF_IMMOBILE };
enum { DIFFICULTY_EASY, DIFFICULTY_NORMAL, DIFFICULTY_HARD };
enum { OBJECT_STATUS_DISGUISED, OBJECT_STATUS_STEALTHED, OBJECT_STATUS_DETECTED, OBJECT_STATUS_UNDER_CONSTRUCTION };
enum { OBJECTSHROUD_CLEAR, OBJECTSHROUD_FOGGED, OBJECTSHROUD_SHROUDED };
enum { ENEMIES, ALLIES };
enum { WEAPON_ANTI_GROUND = 2, WEAPON_ANTI_AIRBORNE_VEHICLE = 1 };
enum { CMD_FROM_AI = 2, ATTACK_NEW_TARGET, ATTACKRESULT_POSSIBLE, ATTACKRESULT_CANNOT_ATTACK };
enum WeaponSlotType { PRIMARY_WEAPON, SECONDARY_WEAPON, TERTIARY_WEAPON, WEAPONSLOT_COUNT };
struct Coord3D { Real x=0,y=0,z=0; void zero() { x=y=z=0; } };
struct WeaponSetFlags { unsigned bits=0; bool operator==(const WeaponSetFlags& b) const {return bits==b.bits;} };
struct WeaponTemplate {
 int anti=WEAPON_ANTI_GROUND; float range=150;
 int getAntiMask() const {return anti;}
 float getUnmodifiedAttackRange() const {return range;}
};
struct WeaponTemplateSet {
 WeaponSetFlags flags;
 const WeaponTemplate* weapons[WEAPONSLOT_COUNT]={};
 unsigned sources[WEAPONSLOT_COUNT]={~0u,~0u,~0u};
 std::bitset<32> preferred[WEAPONSLOT_COUNT];
 const WeaponSetFlags& friend_getWeaponSetFlags() const {return flags;}
 const WeaponTemplate* getNth(WeaponSlotType i) const {return weapons[i];}
 unsigned getNthCommandSourceMask(WeaponSlotType i) const {return sources[i];}
 const std::bitset<32>& getNthPreferredAgainstMask(WeaponSlotType i) const {return preferred[i];}
};
struct ModuleInfo {
 std::vector<AsciiString> modules;
 int getCount() const {return modules.size();}
 AsciiString getNthName(int i) const {return modules.at(i);}
};
struct ThingTemplate {
 std::bitset<32> kinds;
 ModuleInfo modules;
 WeaponTemplateSet weapons;
 mutable int reads=0;
 bool isKindOf(int k) const {++reads;return kinds.test(k);}
 const ModuleInfo& getBehaviorModuleInfo() const {++reads;return modules;}
 const WeaponTemplateSet* findWeaponTemplateSet(const WeaponSetFlags&) const {++reads;return &weapons;}
};
struct TCreateUnitsInfo { AsciiString unitThingName; int minUnits=2,maxUnits=2; };
struct TeamInfo {
 TCreateUnitsInfo m_unitsInfo[16]; int m_numUnitsInfo=1;
 bool m_attackCommonTarget=true;
 int m_productionPriority=10;
 bool m_hasHomeLocation=true;
};
class TeamPrototype {
public:
 TeamInfo info;
 bool eligible=true;
 const TeamInfo* getTemplateInfo() const {return &info;}
 AsciiString getName() const {return "fixture-team";}
};
class Object;
template<class T> struct DLINK_ITERATOR {
 const std::vector<T*>* list; size_t index=0;
 bool done() const {return index==list->size();}
 void advance() {++index;}
 T* cur() {return list->at(index);}
};
class Player {
public:
 using PlayerTeamList=std::list<TeamPrototype*>;
 PlayerTeamList teams;
 struct Money {int amount=5000;int countMoney() const {return amount;}} money;
 int difficulty=DIFFICULTY_HARD; bool skirmish=true; int id=0;
 bool isSkirmishAIPlayer() const {return skirmish;}
 int getPlayerDifficulty() const {return difficulty;}
 int getPlayerIndex() const {return id;}
 int getRelationship(Team* t) const;
 const PlayerTeamList* getPlayerTeams() const {return &teams;}
 Money* getMoney() {return &money;}
};
struct AIUpdateInterface {
 bool priority=false;
 const void* getAttackInfo() {return priority ? this : nullptr;}
};
class Team {
public:
 Player* player=nullptr; TeamPrototype proto; Object* target=nullptr;
 std::vector<Object*> members;
 Player* getControllingPlayer() {return player;}
 TeamPrototype* getPrototype() {return &proto;}
 Object* getTeamTargetObject() {return target;}
 void setTeamTargetObject(Object* p) {target=p;}
 DLINK_ITERATOR<Object> iterate_TeamMemberList() {return {&members,0};}
};
int Player::getRelationship(Team* t) const {return t && t->player!=this ? ENEMIES : ALLIES;}
class Object {
public:
 ThingTemplate* thing=nullptr; Team* team=nullptr; Object* next=nullptr;
 std::bitset<8> status; Coord3D pos;
 bool dead=false,contained=false,able=true,ammo=true,attackable=true;
 int shroud=OBJECTSHROUD_CLEAR;
 AIUpdateInterface ai;
 bool isEffectivelyDead() const {return dead;}
 Object* getContainedBy() {return contained?this:nullptr;}
 Player* getControllingPlayer() {return team->player;}
 Team* getTeam() {return team;}
 bool testStatus(int k) const {return status.test(k);}
 int getShroudedStatus(int) const {return shroud;}
 const ThingTemplate* getTemplate() {return thing;}
 Object* getNextObject() {return next;}
 AIUpdateInterface* getAIUpdateInterface() {return &ai;}
 bool isKindOf(int k) const {return thing->isKindOf(k);}
 bool isAbleToAttack() const {return able;}
 bool isOutOfAmmo() const {return !ammo;}
 const Coord3D* getPosition() const {return &pos;}
 int getAbleToAttackSpecificObject(int,Object* p,int) {return p->attackable?ATTACKRESULT_POSSIBLE:ATTACKRESULT_CANNOT_ATTACK;}
};
struct GameLogic {
 bool skirmish=true,multi=false,replay=false; Object* first=nullptr;
 bool isInSkirmishGame() const {return skirmish;}
 bool isInMultiplayerGame() const {return multi;}
 bool isInReplayGame() const {return replay;}
 Object* getFirstObject() {return first;}
} game;
GameLogic* TheGameLogic=&game;
struct Factory {
 std::map<AsciiString,const ThingTemplate*> templates;
 const ThingTemplate* findTemplate(const AsciiString& s) {auto it=templates.find(s);return it==templates.end()?nullptr:it->second;}
} factory;
Factory* TheThingFactory=&factory;

struct GlobalData {bool m_debugAI=false;} globals;
GlobalData* TheGlobalData=&globals;
struct ScriptEngine {void AppendDebugMessage(const AsciiString&,bool){}} scripts;
ScriptEngine* TheScriptEngine=&scripts;
struct AIData {int m_resourcesPoor=100,m_resourcesWealthy=10000,m_teamPoorMod=2,m_teamWealthyMod=2;};
struct AISystem {AIData data;const AIData* getAiData(){return &data;}} aiSystem;
AISystem* TheAI=&aiSystem;
int randomCalls=0,randomLow=0,randomHigh=0,randomChoice=0;
int GameLogicRandomValue(int lo,int hi){++randomCalls;randomLow=lo;randomHigh=hi;assert(randomChoice>=lo&&randomChoice<=hi);return randomChoice;}
class AIPlayer {
public:
 Player* m_player;
 TeamPrototype* built=nullptr;
 bool m_readyToBuildTeam=true,reinforce=false;
 int m_teamTimer=0,m_teamSeconds=10,reinforcePriority=0;
 explicit AIPlayer(Player* p):m_player(p){}
 // Existing virtual production/factory/prerequisite gate is an interface double.
 bool isAGoodIdeaToBuildTeam(TeamPrototype* p){return p->eligible;}
 bool selectTeamToReinforce(int priority){reinforcePriority=priority;return reinforce;}
 bool isSkirmishAI(){return m_player->isSkirmishAIPlayer();}
 void buildSpecificAITeam(TeamPrototype* p,bool){built=p;}
 bool selectTeamToBuild();
};

// PRODUCTION_ADAPTER

// PRODUCTION_SELECTION

using namespace UniversalTacticalDirector;
struct Scenario {
 Player us,enemy; Team ours,theirs;
 WeaponTemplate ground,aa,longRange;
 ThingTemplate armor,counter,air,antiAir,siege,detector,supply,superweapon,unknown;
 TeamPrototype normalTeam,aaTeam,counterTeam,siegeTeam;
 std::vector<Object> objects;
 Scenario() : objects(8) {
  game=GameLogic(); factory.templates.clear();
  enemy.id=1; ours.player=&us; theirs.player=&enemy;
  aa.anti=WEAPON_ANTI_AIRBORNE_VEHICLE;longRange.range=400;
  armor.kinds.set(KINDOF_VEHICLE);armor.weapons.weapons[0]=&ground;
  counter=armor;counter.weapons.preferred[0].set(KINDOF_VEHICLE);
  air=armor;air.kinds.set(KINDOF_AIRCRAFT);
  antiAir=armor;antiAir.weapons.weapons[0]=&aa;
  siege=armor;siege.weapons.weapons[0]=&longRange;
  detector=armor;detector.modules.modules={"StealthDetectorUpdate"};
  supply.kinds.set(KINDOF_STRUCTURE);supply.kinds.set(KINDOF_IMMOBILE);supply.kinds.set(KINDOF_FS_SUPPLY_CENTER);
  superweapon=supply;superweapon.kinds.set(KINDOF_FS_SUPERWEAPON);
  factory.templates={{"unknown-custom-armor",&armor},{"custom-aa",&antiAir},{"custom-counter",&counter},{"custom-siege",&siege}};
  normalTeam.info.m_unitsInfo[0].unitThingName="unknown-custom-armor";
  aaTeam.info.m_unitsInfo[0].unitThingName="custom-aa";
  counterTeam.info.m_unitsInfo[0].unitThingName="custom-counter";
  siegeTeam.info.m_unitsInfo[0].unitThingName="custom-siege";
  for(auto& o:objects){o.thing=&armor;o.team=&ours;}
  ours.members={&objects[0],&objects[1]};
  link(2);
 }
 void link(size_t n){game.first=n?&objects[0]:nullptr;for(size_t i=0;i<n;++i)objects[i].next=i+1<n?&objects[i+1]:nullptr;}
 TeamPrototype* choose(std::initializer_list<TeamPrototype*> teams,TeamPrototype* fallback){return chooseProduction(&us,Player::PlayerTeamList(teams),fallback);}
};

int main() {
 {
  Scenario s;AIPlayer player(&s.us);
  s.objects[2].team=&s.theirs;s.objects[2].thing=&s.air;s.link(3);
  s.us.teams={&s.normalTeam,&s.aaTeam};randomCalls=0;randomChoice=0;
  assert(player.selectTeamToBuild() && player.built==&s.aaTeam);
  assert(randomCalls==1 && randomLow==0 && randomHigh==1 && !player.m_readyToBuildTeam);
  s.aaTeam.eligible=false;randomCalls=0;
  assert(player.selectTeamToBuild() && player.built==&s.normalTeam && randomHigh==0 && randomCalls==1);
  s.aaTeam.eligible=true;s.aaTeam.info.m_productionPriority=9;
  assert(player.selectTeamToBuild() && player.built==&s.normalTeam && randomHigh==0);
  s.aaTeam.info.m_productionPriority=10;player.reinforce=true;randomCalls=0;player.built=nullptr;
  assert(player.selectTeamToBuild() && !player.built && randomCalls==0 && player.reinforcePriority==10);
  player.reinforce=false;s.normalTeam.eligible=s.aaTeam.eligible=false;
  assert(!player.selectTeamToBuild() && !player.built && randomCalls==0);
  // A destroyed factory/locked tech leaves no eligible team; when the original
  // gate reports recovery, the exact production selector can build again.
  s.aaTeam.eligible=true;assert(player.selectTeamToBuild() && player.built==&s.aaTeam);
  puts("PASS: actual selectTeamToBuild eligibility, priority, reinforcement, recovery and exact RNG call/range");
 }
 {
  Scenario s;
  assert(enabled(&s.us));game.multi=true;assert(!enabled(&s.us));game.multi=false;
  game.skirmish=false;game.replay=true;assert(!enabled(&s.us));
  setReplayMode(true);assert(enabled(&s.us));game.multi=true;assert(!enabled(&s.us));game.multi=false;
  setReplayMode(false);assert(!enabled(&s.us));game.replay=false;game.skirmish=true;
  game.skirmish=false;assert(!enabled(&s.us));game.skirmish=true;
  s.us.difficulty=DIFFICULTY_EASY;assert(!enabled(&s.us));s.us.difficulty=DIFFICULTY_NORMAL;assert(enabled(&s.us));
  s.us.skirmish=false;assert(!enabled(&s.us));
  puts("PASS: offline difficulty/multiplayer/replay/campaign guards");
 }
 {
  Scenario s;
  assert(discover(nullptr).roles==0 && discover(&s.unknown).roles==0);
  assert(discover(&s.antiAir).has(AIR_WEAPON));assert(!discover(&s.antiAir).has(GROUND_WEAPON));
  assert(discover(&s.counter).has(VEHICLE_COUNTER));assert(!discover(&s.armor).has(VEHICLE_COUNTER));
  assert(discover(&s.siege).has(LONG_RANGE));assert(discover(&s.detector).has(DETECTOR));
  s.antiAir.weapons.sources[0]=0;assert(!discover(&s.antiAir).has(AIR_WEAPON));
  s.siege.weapons.flags.bits=1;assert(!discover(&s.siege).has(LONG_RANGE));
  CapabilityCache c;assert(c.get(&s.armor).has(VEHICLE));int reads=s.armor.reads;c.get(&s.armor);assert(s.armor.reads==reads);
  std::vector<ThingTemplate> many(MAX_TEMPLATES+1);for(auto& t:many)c.get(&t);assert(!c.complete);
  puts("PASS: unknown faction, unsupported/conditional weapons, metadata cache bounds");
 }
 {
  Scenario s;
  s.objects[2].team=&s.theirs;s.objects[2].thing=&s.air;s.link(3);
  assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.aaTeam);
  s.objects[2].shroud=OBJECTSHROUD_FOGGED;s.air.reads=0;
  assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.normalTeam);assert(s.air.reads==0);
  s.objects[2].shroud=OBJECTSHROUD_CLEAR;s.objects[2].status.set(OBJECT_STATUS_STEALTHED);
  assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.normalTeam);
  s.objects[2].status.set(OBJECT_STATUS_DETECTED);assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.aaTeam);
  s.objects[2].status.set(OBJECT_STATUS_DISGUISED);assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.normalTeam);
  s.objects[2].status.reset();s.objects[0].thing=&s.antiAir;s.objects[1].thing=&s.antiAir;
  assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.normalTeam);
  // No eligible AA team (e.g. missing factory/tech/money in the original filter).
  assert(s.choose({&s.normalTeam},&s.normalTeam)==&s.normalTeam);
  s.objects[0].dead=s.objects[1].dead=true;
  assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.aaTeam);
  factory.templates.erase("custom-aa");assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.normalTeam);
  puts("PASS: observed aircraft counters, hidden-data exclusion, composition saturation, loss recovery, missing template fallback");
 }
 {
  Scenario s;s.objects[2].team=&s.theirs;s.link(3);
  assert(s.choose({&s.normalTeam,&s.counterTeam},&s.normalTeam)==&s.counterTeam);
  s.us.difficulty=DIFFICULTY_NORMAL;assert(s.choose({&s.normalTeam,&s.counterTeam},&s.normalTeam)==&s.normalTeam);
  s.us.difficulty=DIFFICULTY_HARD;s.objects[2].thing=&s.supply;s.supply.kinds.set(KINDOF_FS_BASE_DEFENSE);
  assert(s.choose({&s.normalTeam,&s.siegeTeam},&s.normalTeam)==&s.siegeTeam);
  s.armor.kinds.set(KINDOF_HARVESTER);assert(s.choose({&s.normalTeam,&s.siegeTeam},&s.normalTeam)==&s.normalTeam);
  puts("PASS: hard vehicle preference, long range against defenses, economy team protection");
 }
 {
  Scenario s;TeamPrototype detection;
  detection.info.m_unitsInfo[0].unitThingName="custom-detector";
  factory.templates["custom-detector"]=&s.detector;
  s.objects[2].team=&s.theirs;s.objects[2].thing=&s.counter;
  s.counter.modules.modules={"StealthUpdate"};s.link(3);
  assert(s.choose({&s.normalTeam,&detection},&s.normalTeam)==&detection);
  s.objects[0].thing=&s.detector;assert(s.choose({&s.normalTeam,&detection},&s.normalTeam)==&s.normalTeam);
  s.objects[0].thing=&s.armor;detection.info.m_numUnitsInfo=MAX_TEAM_TYPES+1;
  assert(s.choose({&s.normalTeam,&detection},&s.normalTeam)==&s.normalTeam);
  detection.info.m_numUnitsInfo=1;detection.info.m_unitsInfo[0].minUnits=-1;
  assert(s.choose({&s.normalTeam,&detection},&s.normalTeam)==&s.normalTeam);
  puts("PASS: observed stealth detector deficit, saturation, malformed team fallback");
 }
 {
  Scenario s;s.objects[2].team=s.objects[3].team=&s.theirs;
  s.objects[2].thing=&s.supply;s.objects[3].thing=&s.superweapon;s.link(4);
  prepareTeamHunt(&s.ours);assert(s.ours.target==&s.objects[3]);
  s.ours.target=nullptr;s.objects[3].shroud=OBJECTSHROUD_FOGGED;
  prepareTeamHunt(&s.ours);assert(s.ours.target==&s.objects[2]);
  s.ours.target=nullptr;s.objects[2].attackable=false;prepareTeamHunt(&s.ours);assert(!s.ours.target);
  s.objects[2].attackable=true;s.objects[0].ai.priority=true;prepareTeamHunt(&s.ours);assert(!s.ours.target);
  s.objects[0].ai.priority=false;s.ours.proto.info.m_attackCommonTarget=false;prepareTeamHunt(&s.ours);assert(!s.ours.target);
  s.ours.proto.info.m_attackCommonTarget=true;s.objects[0].thing=&s.air;prepareTeamHunt(&s.ours);assert(!s.ours.target);
  s.objects[0].thing=&s.armor;s.ours.members.resize(1);prepareTeamHunt(&s.ours);assert(!s.ours.target);
  s.ours.members.push_back(&s.objects[1]);s.objects[2].pos.x=std::numeric_limits<float>::infinity();prepareTeamHunt(&s.ours);assert(!s.ours.target);
  puts("PASS: useful shared objective, minimum force, valid attacks, mod priorities, aircraft and finite distance fallback");
 }
 {
  Scenario s;s.objects.resize(MAX_OBJECTS+1);for(auto& o:s.objects){o.thing=&s.armor;o.team=&s.ours;}s.link(s.objects.size());
  CapabilityCache cache;Situation sit;assert(!observe(&s.us,cache,sit));
  assert(s.choose({&s.normalTeam,&s.aaTeam},&s.normalTeam)==&s.normalTeam);
  const Player::PlayerTeamList candidates={&s.normalTeam,&s.aaTeam};
  for(bool enabledMode:{false,true}) {
   game.multi=!enabledMode;
   const auto start=std::chrono::steady_clock::now();
   for(int i=0;i<2000;++i)assert(chooseProduction(&s.us,candidates,&s.normalTeam)==&s.normalTeam);
   const auto us=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count();
   printf("PASS: synthetic 1024-object budget mean %.2f us (%s; host fixture, not engine/device FPS)\n",us/2000.0,enabledMode?"V1 bounded snapshot":"original-choice bypass");
  }
  game.multi=false;
  printf("PASS: bounded local capability cache size %zu bytes; no director path requests\n",sizeof(CapabilityCache));
 }
 {
  Scenario first;first.objects[2].team=&first.theirs;first.objects[2].thing=&first.air;first.link(3);
  for(int i=0;i<100;++i)assert(first.choose({&first.normalTeam,&first.aaTeam},&first.normalTeam)==&first.aaTeam);
  // The next context has fresh loaded templates; no pointer/cache/history survives.
  Scenario second;assert(second.choose({&second.normalTeam,&second.aaTeam},&second.normalTeam)==&second.normalTeam);
  puts("PASS: repeated deterministic decisions and mod/session reset without persistent state");
 }
}
