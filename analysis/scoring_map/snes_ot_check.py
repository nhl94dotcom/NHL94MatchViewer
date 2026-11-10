"""SNES overtime length by play mode and period length, played (2026-11-09, for NOSE4Web 5560584: the fourth period
length with a 99:00 regular-season overtime; gen_ot_check.py is the Genesis one). In live play
(snes_assist_stick_test.Game: retail, or the SA-1 build at 60 frames a second), for each case the play mode
(OptPlayMode $34BC: 0 regular season, else playoffs) and period length (Optperlen $34C2) set in RAM (ResetClock reads
both at each period start; on the SA-1 build in BW-RAM), the third period's clock set to 2 s at 0-0 (goals by period
cleared too), and play run into overtime (START tapped when the clock has stood still 5 s). In overtime (period 3,
the ROM's team ids, 0-0, the clock run 3 s): the clock it started from, and the frames each of 20 clock seconds took
(24 at the game's 2.5 game seconds a real second, 60 frames a second on both). Then, regular season on the fourth
length, the overtime clock set to 3 s at 0-0: what follows (period, clock, every 5 s).

python snes_ot_check.py ROM [ROM ...]"""
import sys

import lowload
from snes_assist_stick_test import Game

PLAYMODE, PERLEN, GSP, CLOCK, STILL = 0x34BC, 0x34C2, 0x1630, 0x1632, 0x15D6
GOALS, GOALS_P, TEAMS = 0x178E, 0x177E, (0x1C98, 0x1C9A)


def to_overtime(G, base, mode, perlen):
    e = G.e
    e.unserialize(base)
    teams = tuple(G.w(a) for a in TEAMS)
    G.setw(PLAYMODE, mode)
    G.setw(PERLEN, perlen)
    G.setw(GSP, 2)
    G.setw(CLOCK, 2)
    for a in (GOALS, GOALS + 2) + tuple(GOALS_P + 2 * i for i in range(8)):
        G.setw(a, 0)
    top, last, still = None, None, 0
    for f in range(60000):
        G.run(1, hold=["START"] if still >= 300 and f % 60 < 4 else [])
        c = G.w(CLOCK)
        still = still + 1 if c == last else 0
        last = c
        live = G.w(GSP) == 3 and tuple(G.w(a) for a in TEAMS) == teams and (G.w(GOALS), G.w(GOALS + 2)) == (0, 0)
        if not live:
            top = None
            continue
        top = c if top is None else max(top, c)
        if top - c >= 3:
            break
    else:
        return None, None, None
    # the frames each clock second takes
    ticks, n, c0 = [], 0, G.w(CLOCK)
    while len(ticks) < 20 and n < 5000:
        G.run(1)
        n += 1
        c = G.w(CLOCK)
        if c != c0:
            ticks.append(n)
            n, c0 = 0, c
    return top, ticks[1:], e.serialize()


def main():
    for rom in sys.argv[1:]:
        G = Game(rom)
        base = G.g.bases[0]
        print("==", rom.split("/")[-1], flush=True)
        ot_state = None
        for mode, mname in ((0, "regular season"), (2, "playoffs")):
            for perlen in (0, 3):
                top, ticks, st = to_overtime(G, base, mode, perlen)
                print(f"  {mname}, period length {perlen}: overtime clock {top}"
                      + (f" ({top // 60}:{top % 60:02d}); frames a clock second {sorted(set(ticks))}" if top else ""),
                      flush=True)
                if mode == 0 and perlen == 3:
                    ot_state = st
                lowload.breathe()
        if ot_state:
            G.e.unserialize(ot_state)
            G.setw(CLOCK, 3)
            last, still = None, 0
            for f in range(60 * 60):
                G.run(1, hold=["START"] if still >= 300 and f % 60 < 4 else [])
                c = G.w(CLOCK)
                still = still + 1 if c == last else 0
                last = c
                if f % 300 == 0:
                    print(f"  tie run-out, {f // 60} s: period {G.w(GSP)}, clock {c}, goals {G.w(GOALS)}-{G.w(GOALS + 2)}",
                          flush=True)


if __name__ == "__main__":
    main()
