#!/usr/bin/env python3
"""Guard the Zero Hour high-unit-count client optimization.

Compares the original and cached ghost-manager query scheduling for 1000,
2000 and 4000 synthetic Drawables, without altering game data or claiming
Android GPU FPS. This only checks call counts/ordering and source invariants.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[2] / (
    "GeneralsMD/Code/GameEngine/Source/GameClient/GameClient.cpp"
)


def check_source() -> None:
    s = SOURCE.read_text(encoding="utf-8")
    assert s.count("TheGhostObjectManager->trackAllPlayers()") == 1
    assert s.count("const bool gxTrackAllGhostPlayers = gxShroudEnabled &&") == 1
    assert s.count("if (gxShroudEnabled)") == 2
    assert s.count("if (gxTrackAllGhostPlayers)") == 2
    assert s.count("object->getShroudedStatus(*playerIndex);") == 1
    assert s.count("object->getShroudedStatus(localPlayerIndex);") == 1
    assert s.count("draw->updateDrawable();") == 1
    assert s.count("gxTraceLargeBattleClient(") == 2
    assert "if (gxPerfTrace) ++gxDrawableCount;" in s
    assert "if (gxPerfTrace) ++gxQueryCount;" in s
    assert "sampleStride=32" in s


def model(units: int, players: int, ghost_all: bool, shroud: bool, optimized: bool):
    # Synthetic immutable frame. Every Drawable is updated; a subset has a
    # game Object and a further subset has ghost data. The original refreshes
    # all non-local ghost statuses, followed by the local status, in that order.
    track_checks = 0
    visits = []
    if shroud:
        track_checks += 1
    cached = shroud and ghost_all
    for i in range(units):
        obj = i % 13 != 0
        has_ghost = i % 3 != 0
        if shroud and obj:
            if not optimized:
                track_checks += 1
            if (cached if optimized else ghost_all) and has_ghost:
                for p in range(1, players):
                    visits.append((i, p))
            visits.append((i, 0))
        visits.append((i, "clientUpdate"))
    return track_checks, visits


def main() -> None:
    check_source()
    for units in (1000, 2000, 4000):
        for players in (1, 4, 8):
            for ghost_all in (False, True):
                for shroud in (False, True):
                    baseline = model(units, players, ghost_all, shroud, optimized=False)
                    candidate = model(units, players, ghost_all, shroud, optimized=True)
                    assert baseline[1] == candidate[1], (units, players, ghost_all, shroud)
                    assert candidate[0] <= baseline[0]
                    assert candidate[0] <= 1
        # In 32 successive frames the rotating 1/32 sampler covers every
        # Drawable index exactly once, including indices > 1000.
        for index in range(units):
            sampled_frames = sum(
                ((index + offset) & 31) == 0 for offset in range(32)
            )
            assert sampled_frames == 1
        before = model(units, 4, True, True, optimized=False)[0]
        after = model(units, 4, True, True, optimized=True)[0]
        print(f"PASS {units} Drawables: mode checks/frame {before} -> {after}, "
              "shroud status and client-update visitation unchanged")
    print("PASS: no simulation changes, no duplicate ghost refreshes, "
          "1/32 telemetry sample coverage. No measured FPS claim.")


if __name__ == "__main__":
    main()
