#!/usr/bin/env python3
"""Source regression checks for the selective GeneralsX Android upstream v1.4.2 port.

This is NOT a substitute for compiling 30/60 Hz engines or for device acceptance.
Runs offline, does not install or publish anything, and never touches OTA.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def count(path: str, text: str, expected: int = 1) -> None:
    actual = read(path).count(text)
    assert actual == expected, f"{path}: expected {expected} occurrence(s) of {text!r}; got {actual}"


def main() -> None:
    gles = "Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp"
    common = "Core/GameEngine/Include/Common/GameCommon.h"
    draw = "Core/GameEngineDevice/Source/W3DDevice/GameClient/Drawable/Draw/"
    count(gles, 'vec4(aUV%d.xy, 1.0, 0.0)')
    count(gles, 'vec4(aUV%d.xy, 0.0, 1.0)', 0)
    count(common, 'const Real LOGICFRAMES_PER_BASEFRAME_REAL =')
    for path, vel, accel, speed in (
        ("W3DTankDraw.cpp", 1, 0, 0),
        ("W3DTankTruckDraw.cpp", 1, 1, 1),
        ("W3DTruckDraw.cpp", 0, 1, 1),
    ):
        file = draw + path
        count(file, 'velMag = (Real)sqrt( velMag ) * LOGICFRAMES_PER_BASEFRAME_REAL;', vel)
        count(file, 'velMag = (Real)sqrt( velMag );', 0)
        count(file, 'accel.length()*LOGICFRAMES_PER_BASEFRAME_REAL*LOGICFRAMES_PER_BASEFRAME_REAL>ACCEL_THRESHOLD;', accel)
        count(file, 'speed *= LOGICFRAMES_PER_BASEFRAME_REAL;', speed)
    for game in ("Generals", "GeneralsMD"):
        menu = f"{game}/Code/GameEngine/Source/GameClient/GUI/GUICallbacks/Menus/QuitMenu.cpp"
        count(menu, 'fps /= GENERALS_ONLINE_HIGH_FPS_FRAME_MULTIPLIER;')
        powers = f"{game}/Code/GameEngine/Source/GameLogic/Object/SpecialPower/SpecialPowerModule.cpp"
        count(powers, 'xfer->getXferMode() == XFER_LOAD && m_availableOnFrame == 0xFFFFFFFF')
    basepowers = "Generals/Code/GameEngine/Source/GameLogic/Object/SpecialPower/SpecialPowerModule.cpp"
    count(basepowers, 'm_availableOnFrame = 0xFFFFFFFF;', 0)
    count(basepowers, 'm_availableOnFrame = 0;', 2)  # constructor and old-save normalization
    missile = "Generals/Code/GameEngine/Source/GameLogic/Object/Update/MissileLauncherBuildingUpdate.cpp"
    count(missile, 'if (m_specialPowerModule == nullptr)')
    for game, expected in (("Generals", 4), ("GeneralsMD", 6)):
        path = f"{game}/Code/GameEngineDevice/Source/W3DDevice/GameClient/W3dWaypointBuffer.cpp"
        count(path, 'if (m_waypointNodeRobj) {', expected)
        count(path, 'm_waypointNodeRobj->Set_Position(', expected)
    sdl = "GeneralsMD/Code/GameEngineDevice/Source/SDL3GameEngine.cpp"
    count(sdl, 'static void gxRequestSurfaceFrameRate(SDL_Window *window)')
    count(sdl, 'gxRequestSurfaceFrameRate(m_SDLWindow);')
    count(sdl, 'typedef int32_t (*SetFrameRateFn)')
    count("Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp", '[GX-TERRAIN] shader=')
    print("PASS: upstream #58/#62/#65/#69 engine fixes are present exactly once.")
    print("NOTE: native compilation, APK/device tests, and physical TEOD FPS are not covered.")


if __name__ == "__main__":
    main()
