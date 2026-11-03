#!/usr/bin/env python3
"""Compile and run the repository's actual music-preflight method with fake assets."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'Core/GameEngine/Source/Common/Audio/GameAudio.cpp').read_text()
start = source.index('Bool AudioManager::isMusicAlreadyLoaded() const\n{')
end = source.index('\n//-------------------------------------------------------------------------------------------------\nvoid AudioManager::findAllAudioEventsOfType(', start)
function = source[start:end]
prefix = r'''
#include <cassert>
#include <cstdio>
#include <map>
#include <set>
#include <string>
using Bool = bool;
using UnsignedInt = unsigned int;
#define TRUE true
#define FALSE false
struct AsciiString {
    std::string value;
    AsciiString() = default;
    AsciiString(const char* s): value(s) {}
    const char* str() const { return value.c_str(); }
    bool isEmpty() const { return value.empty(); }
};
const int AT_Music=1, AT_SoundEffect=2;
struct AudioEventInfo { int m_soundType; AsciiString m_audioName; AsciiString path; };
struct AudioEventRTS {
    const AudioEventInfo* info=nullptr;
    void setAudioEventInfo(const AudioEventInfo* value) { info=value; }
    void generateFilename() {}
    AsciiString getFilename() const { return info->path; }
};
struct FakeFileSystem {
    std::set<std::string> existing;
    mutable unsigned probes=0;
    Bool doesFileExist(const char* p) const { ++probes; return existing.count(p) != 0; }
};
FakeFileSystem* TheFileSystem=nullptr;
using AudioEventInfoHash = std::map<std::string, AudioEventInfo*>;
struct AudioManager {
    AudioEventInfoHash m_allAudioEventInfo;
    Bool isMusicAlreadyLoaded() const;
};
'''
suffix = r'''
int main() {
    FakeFileSystem fs;
    TheFileSystem=&fs;
    AudioManager audio;
    AudioEventInfo missing{AT_Music, AsciiString("Game_CHI_01"), AsciiString("Data/Audio/Tracks/CHI_01.mp3")};
    AudioEventInfo present{AT_Music, AsciiString("Game_USA_01"), AsciiString("Data/Audio/Tracks/USA_01.mp3")};
    AudioEventInfo effects{AT_SoundEffect, AsciiString("FX"), AsciiString("Data/Audio/Sounds/FX.wav")};

    assert(!audio.isMusicAlreadyLoaded());
    audio.m_allAudioEventInfo["A_missing"]=&missing;
    assert(!audio.isMusicAlreadyLoaded());

    audio.m_allAudioEventInfo["Z_present"]=&present;
    audio.m_allAudioEventInfo["X_effects"]=&effects;
    fs.existing.insert(present.path.str());
    fs.probes=0;
    assert(audio.isMusicAlreadyLoaded());
    assert(fs.probes==2);

    audio.m_allAudioEventInfo.clear();
    audio.m_allAudioEventInfo["A_present"]=&present;
    audio.m_allAudioEventInfo["Z_missing"]=&missing;
    fs.probes=0;
    assert(audio.isMusicAlreadyLoaded());
    assert(fs.probes==1);

    fs.existing.clear();
    assert(!audio.isMusicAlreadyLoaded());

    audio.m_allAudioEventInfo.clear();
    audio.m_allAudioEventInfo["A_effects"]=&effects;
    assert(!audio.isMusicAlreadyLoaded());
    puts("PASS: music preflight available/missing/reordered/no-music");
}
'''
with tempfile.TemporaryDirectory(prefix='gzh-asset-audio-') as temp:
    path = Path(temp) / 'test_music.cpp'
    exe = Path(temp) / 'test_music'
    path.write_text(prefix + '\n' + function + '\n' + suffix)
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-O2',str(path),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
