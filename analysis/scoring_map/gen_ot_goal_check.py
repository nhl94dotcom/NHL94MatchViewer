"""Overtime until a goal (2026-11-11, for NOSE4Web e86d31a: nhl94_overtime_until_goal.bin, PeriodOver's move.w #4,(gsp).w
at $1725C made NOPs). From a game in play: the play mode set (0 regular season, 2 playoffs), overtime (gsp 3) with 3
seconds left and the score tied 1-1; played (START through screens that wait) until either play runs again with the
clock reset (another overtime) or the game is over (gsp 4, or the menus). Printed for each mode: what came after.

python gen_ot_goal_check.py ROM"""
import sys
from pathlib import Path
import tempfile

import gen_ot_check as G
import lowload
from emu import Emu

PLAYMODE, GSP, CLOCK, SCREEN, HM, AW = 0xD048, 0xC466, 0xC468, 0xFFF7, 0xC6DA, 0xCA3E


def main():
    rom = sys.argv[1]
    lowload.gentle()
    out = Path(tempfile.gettempdir()) / "ot_goal"
    out.mkdir(exist_ok=True)
    e = Emu(rom)
    G.to_setup(e, out)
    if not G.into_play(e):
        print("never reached play")
        return
    G.OURS.append(tuple(e.b(a) for a in G.TEAMS))       # our teams (an intermission highlight shows another game's)
    base = e.serialize()
    for mode, name in ((0, "regular season"), (2, "playoffs")):
        e.unserialize(base)
        e.setw(PLAYMODE, mode)
        e.setw(GSP, 3)
        e.setw(CLOCK, 3)
        e.setw(HM, 1)
        e.setw(AW, 1)
        what, last, still = None, None, 0
        for f in range(60 * 60 * 6):
            e.run(1, hold=["START"] if still >= 150 and f % 150 == 0 else [])
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if e.w(GSP) >= 4:
                what = f"game over (gsp {e.w(GSP)})"
                break
            if e.b(SCREEN) not in (0, 0x80, 100) and e.w(GSP) == 0:
                what = "back to the menus"
                break
            if e.b(SCREEN) == 0 and e.w(GSP) == 3 and c > 60 and G.ours(e):
                c0 = c
                e.run(120)
                if e.w(CLOCK) < c0:
                    what = f"another overtime: gsp 3, clock {c0} and running, score {e.w(HM)}-{e.w(AW)}"
                    break
        e.screenshot(out / f"{Path(rom).stem}_{mode}.png")
        print(f"{Path(rom).name}, {name}, overtime ending 1-1: {what or 'nothing decided within the frames'}", flush=True)


if __name__ == "__main__":
    main()
