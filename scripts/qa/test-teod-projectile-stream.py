#!/usr/bin/env python3
"""Compile and execute the *production* Weapon::newProjectileFired with strict fake dependencies.

Avoid a copy of the implementation in the fixture: extract its real C++ body.
The test checks missing optional stream templates, neutral owners, and valid
projectile-stream semantics without supplying commercial game/mod assets.
"""
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'GeneralsMD/Code/GameEngine/Source/GameLogic/Object/Weapon.cpp'
text = SOURCE.read_text()
start = text.index('void Weapon::newProjectileFired(')
end = text.index('\n//-------------------------------------------------------------------------------------------------', start)
production_method = text[start:end]
assert 'if (pst == nullptr)' in production_method
assert 'missingStreamWarnings < 8' in production_method

fixture = r'''
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>

using ObjectID = int;
using NameKeyType = int;
#define NAMEKEY(x) (1)
constexpr ObjectID INVALID_ID = -1;
struct Coord3D { float x=0, y=0, z=0; };
struct AsciiString {
    std::string data;
    AsciiString() = default;
    AsciiString(const char* name):data(name){}
    bool isEmpty() const {return data.empty();}
    const char* str() const {return data.c_str();}
};
struct Team {};
struct Player {
    Team* team=nullptr;
    Team* getDefaultTeam() const {return team;}
};
struct ProjectileStreamUpdate {
    int positions=0, projectiles=0, lastSource=-1, lastProjectile=-1, lastVictim=-1;
    void setPosition(const Coord3D*) {++positions;}
    void addProjectile(ObjectID source, ObjectID projectile, ObjectID victim, const Coord3D*) {
        ++projectiles;lastSource=source;lastProjectile=projectile;lastVictim=victim;
    }
};
struct Object {
    ObjectID id=0;
    Player* owner=nullptr;
    ProjectileStreamUpdate* stream=nullptr;
    mutable Coord3D position{};
    ObjectID getID() const {return id;}
    Player* getControllingPlayer() const {return owner;}
    const Coord3D* getPosition() const {return &position;}
    void* findUpdateModule(NameKeyType) const {return stream;}
};
struct ThingTemplate{};
struct WeaponTemplate {
    AsciiString name;
    AsciiString getProjectileStreamName() const {return name;}
};
struct GameLogic {
    Object* registered=nullptr;
    Object* findObjectByID(ObjectID id) {return registered && registered->id == id ? registered : nullptr;}
};
struct ThingFactory {
    ThingTemplate validTemplate;
    Object* nextObject=nullptr;
    int created=0;
    const ThingTemplate* findTemplate(const AsciiString& name) {
        return name.data=="ValidTrail" ? &validTemplate : nullptr;
    }
    Object* newObject(const ThingTemplate* object, Team* owner) {
        if(!object||!owner) throw std::logic_error("Invalid newObject input");
        ++created;
        return nextObject;
    }
};
GameLogic gameLogic;
ThingFactory thingFactory;
GameLogic* TheGameLogic = &gameLogic;
ThingFactory* TheThingFactory = &thingFactory;
struct Weapon {
    WeaponTemplate* m_template=nullptr;
    ObjectID m_projectileStreamID=INVALID_ID;
    void newProjectileFired(const Object*,const Object*,const Object*,const Coord3D*);
};
''' + production_method + r'''
int main() {
    Team team;
    Player owningPlayer{&team};
    ProjectileStreamUpdate streamUpdates;
    Object source{10,&owningPlayer,nullptr,{}};
    Object projectile{20,nullptr,nullptr,{}};
    Object victim{30,nullptr,nullptr,{}};
    Object stream{40,nullptr,&streamUpdates,{}};
    Coord3D target{};
    WeaponTemplate valid{AsciiString("ValidTrail")};
    WeaponTemplate invalid{AsciiString("MissingTeodTrail")};
    WeaponTemplate blank{AsciiString("")};
    Weapon w{};
    thingFactory.nextObject=&stream;

    // Missing template does not call newObject and leaves the actual projectile intact.
    w.m_template=&invalid;
    for(int i=0;i<30;++i) w.newProjectileFired(&source,&projectile,&victim,&target);
    if(thingFactory.created!=0 || w.m_projectileStreamID!=INVALID_ID) return 1;

    // Normal shot with no stream must not create one.
    w.m_template=&blank;w.newProjectileFired(&source,&projectile,&victim,&target);
    if(thingFactory.created!=0) return 2;

    // Neutral/default-team-less shooter must not create a stream.
    w.m_template=&valid;
    Player neutral{};
    source.owner=&neutral;
    w.newProjectileFired(&source,&projectile,&victim,&target);
    if(thingFactory.created!=0) return 3;
    source.owner=nullptr;
    w.newProjectileFired(&source,&projectile,&victim,&target);
    if(thingFactory.created!=0) return 4;
    source.owner=&owningPlayer;

    // Null unexpected inputs fail closed without allocating or touching simulation.
    w.newProjectileFired(nullptr,&projectile,&victim,&target);
    w.newProjectileFired(&source,nullptr,&victim,&target);
    w.newProjectileFired(&source,&projectile,&victim,nullptr);
    w.m_template=nullptr;
    w.newProjectileFired(&source,&projectile,&victim,&target);
    if(thingFactory.created!=0) return 5;

    // Valid stream creates once and registers the same source/target/projectile IDs.
    w.m_template=&valid;
    w.newProjectileFired(&source,&projectile,&victim,&target);
    if(thingFactory.created!=1 || w.m_projectileStreamID!=40) return 6;
    if(streamUpdates.positions!=1 || streamUpdates.projectiles!=1) return 7;
    if(streamUpdates.lastSource!=10 || streamUpdates.lastProjectile!=20 || streamUpdates.lastVictim!=30) return 8;
    gameLogic.registered=&stream;
    w.newProjectileFired(&source,&projectile,nullptr,&target);
    if(thingFactory.created!=1 || streamUpdates.projectiles!=2 || streamUpdates.lastVictim!=INVALID_ID) return 9;

    // Deleted stream is recreated, and valid ownership remains intact.
    gameLogic.registered=nullptr;
    w.newProjectileFired(&source,&projectile,&victim,&target);
    if(thingFactory.created!=2 || streamUpdates.projectiles!=3) return 10;
    std::puts("PASS: production Weapon::newProjectileFired invalid and valid TEOD cases");
}
'''
compiler=shutil.which('g++') or shutil.which('clang++')
if not compiler:
    raise SystemExit('C++ compiler unavailable')
with tempfile.TemporaryDirectory(prefix='gx-weapon-teod-') as temp:
    cpp=pathlib.Path(temp)/'harness.cpp'
    executable=pathlib.Path(temp)/'harness'
    cpp.write_text(fixture)
    subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror',
        '-pedantic','-fsanitize=undefined','-fno-sanitize-recover=undefined',
        str(cpp),'-o',str(executable)],check=True)
    run=subprocess.run([str(executable)],text=True,capture_output=True)
    print(run.stdout)
    assert run.returncode==0,(run.returncode,run.stderr)
    assert run.stderr.count('[GX-WEAPON-STREAM] missing')==8,run.stderr
    print('PASS: missing-stream diagnostics capped at eight messages')
