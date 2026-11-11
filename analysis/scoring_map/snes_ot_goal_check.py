"""SNES overtime until a goal (2026-11-11, for NOSE4Web abba8ad: NHL94_overtime_until_goal.smc and
nhl94snes_SA1_overtime_until_goal.sfc; clockcont_0's regular-season game over `beq` made NOPs, PeriodOver's play-mode
`bne` made `bra`). A game started as snes_60fps_cvc.game does (menus, the computer on both sides, its seed from GAME),
then for each play mode (OptPlayMode $34BC: 0 regular season, 2 playoffs): overtime (period $1630 = 3) with 3 s left
and the score tied 1-1 (the goals word pair $178E and the first period's goals), played on (START when the clock has
stood still 15 s (real), the computer kept on both sides) until the game is over or 60 minutes (real) of frames.
Printed whenever it changes: the period, the score, and each time the clock jumps up (a new period's clock); a
screenshot at each such change and at the end.

python snes_ot_goal_check.py ROM OUT [GAME]"""
import sys
from pathlib import Path

import lowload
import menu_shots as M
from snes_60fps_cvc import CLOCK, CLOCKSTOP, GSP, OPTPEN, SEED, Mem, computer_only

PLAYMODE, GOALS, GOALS_P, TEAMS = 0x34BC, 0x178E, 0x177E, (0x1C98, 0x1C9A)


def start(rom, n, out):
    e = M.emulator(rom)
    m = Mem(e, rom)
    if m.sa1:
        M.play(e, f"w{1800 + 53 * n} START w240", out)
    else:
        M.play(e, f"w{1500 + 53 * n} START w240 START w240 DOWN*3 RIGHT*2 DOWN RIGHT*2 w30", out)
    M.play(e, "START w240 START w200 w2400", out)
    for _ in range(12):
        c = m.w(CLOCK)
        e.run(240)
        if m.w(CLOCK) != c and m.w(CLOCKSTOP) == 0:
            break
        e.run(4, hold=["START"])
        e.run(60)
    m.setw(OPTPEN, 2)
    computer_only(m)
    m.setw(SEED, (0x9E37 * (n + 1)) & 0xFFFF or 1)
    m.setw(SEED + 2, (0x7F4A * (n + 3)) & 0xFFFF or 1)
    return e, m


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e, m = start(rom, n, out)
    teams = tuple(m.w(a) for a in TEAMS)
    base = e.serialize()
    for mode, name in ((0, "regular season"), (2, "playoffs")):
        e.unserialize(base)
        m.setw(PLAYMODE, mode)
        m.setw(GSP, 3)
        m.setw(CLOCK, 3)
        for a in (GOALS, GOALS + 2) + tuple(GOALS_P + 2 * i for i in range(8)):
            m.setw(a, 0)
        m.setw(GOALS, 1)
        m.setw(GOALS + 2, 1)
        m.setw(GOALS_P, 1)
        m.setw(GOALS_P + 2, 1)
        prev, last, still, shots = None, None, 0, 0
        for f in range(0, 60 * 60 * 60, 10):
            e.run(10)
            if f % 300 == 0:
                computer_only(m)
            if f % 3600 == 0:
                lowload.breathe()
            c = m.w(CLOCK)
            still = still + 10 if c == last else 0
            if still >= 900:
                e.run(4, hold=["START"])
                still = 0
            ours = tuple(m.w(a) for a in TEAMS) == teams
            st = (m.w(GSP), m.w(GOALS), m.w(GOALS + 2), ours)
            jump = last is not None and c > last + 5 and ours
            if st != prev or jump:
                print(f"{name} f{f}: period {st[0]} score {st[1]}-{st[2]} clock {c}" + ("" if ours else " (not our game)")
                      + (" <- the clock reset" if jump else ""), flush=True)
                e.screenshot(out / f"{mode}_{shots:02d}_f{f}.png")
                shots += 1
                prev = st
            last = c
            if not ours and f > 600 and st[0] == 0:
                break
        e.screenshot(out / f"{mode}_end.png")
        print(f"{name}: end at frame {f}", flush=True)


if __name__ == "__main__":
    main()
