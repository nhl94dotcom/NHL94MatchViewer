"""The period length option and overtime length, played (Genesis, 2026-11-09, for NOSE4Web 438dec8: a fourth period
length with its own regular-season overtime; McMarkis's 99MinOT_Menu made general). One emulator per process.

menu ROM OUT [4way]: power-on to Game Setup (with EA's 4-Way Play adaptor for 4way: OptionLimits4Way), DOWN to the
  period length line (line 4: Optperlen $D050), then RIGHT 6 times; after each press Optperlen and a screenshot.
game ROM OUT: power-on, START into a regular-season game. Then for each case (play mode OptPlayMode $D048 and
  Optperlen set in RAM in the first period; ResetClock reads both at each period start): the third period's clock
  set to 2 s at 0-0, played (START through the intermission) into overtime; the overtime clock read at its first
  faceoff, and the clock shown at several values (screenshots: the rink's clock is gameclock $C468 printed each
  frame). Then, regular season on the fourth length: a home goal at 1:40 left (97:20 in), its ScoreSum entry; and,
  from the overtime start again, the clock run out at 0-0: what follows (gsp $C466, screenshots).

python gen_ot_check.py menu|game ROM OUT [4way]"""
import struct
import sys
from pathlib import Path

import harness as H
import lowload
from emu import Emu

PLAYMODE, PERLEN, FOURWAY, GSP, CLOCK, SCREEN = 0xD048, 0xD050, 0xD046, 0xC466, 0xC468, 0xFFF7
HMGOALS, AWGOALS = 0xC6DA, 0xCA3E
TEAMS = (0xC6F7, 0xCA5B)          # team ids: an intermission highlight of another game has its own
OURS = []


def to_setup(e, out):
    """Power-on to Game Setup: the intro, START at the title, START at the title screen (the menu's first line)."""
    e.run(900)
    e.run(4, hold=["START"])
    e.run(120)
    e.run(4, hold=["START"])
    e.run(320)
    e.screenshot(out / "setup.png")


def press(e, b, n=1):
    for _ in range(n):
        e.run(4, hold=[b])
        e.run(26)


def menu(rom, out, fourway):
    e = Emu(rom, fourway=fourway)
    to_setup(e, out)
    press(e, "DOWN", 4)
    print("FourWayPlay", e.w(FOURWAY), "play mode", e.w(PLAYMODE), flush=True)
    seen = [e.w(PERLEN)]
    e.screenshot(out / f"perlen_{len(seen)}_{seen[-1]}.png")
    for _ in range(6):
        before = e.w(PERLEN)
        for _ in range(5):                       # a lost press is pressed again
            press(e, "RIGHT")
            if e.w(PERLEN) != before:
                break
        seen.append(e.w(PERLEN))
        e.screenshot(out / f"perlen_{len(seen)}_{seen[-1]}.png")
    print("Optperlen after each RIGHT:", seen, flush=True)


def ours(e):
    return not OURS or tuple(e.b(a) for a in TEAMS) == OURS[0]


def into_play(e):
    for _ in range(80):
        if e.b(SCREEN) == 0 and ours(e):
            c = e.w(CLOCK)
            e.run(60)
            if e.b(SCREEN) == 0 and e.w(CLOCK) != c and ours(e):
                return True
        e.run(4, hold=["START"])
        e.run(60)
    return False


def to_overtime(e, base, mode, perlen, out, tag):
    """From the base state: mode and length set, period 3 at 0:02, 0-0; played into overtime. Returns the clock at
    the overtime's first frame of play (None if it never came)."""
    e.unserialize(base)
    e.setw(PLAYMODE, mode)
    e.setw(PERLEN, perlen)
    e.setw(GSP, 2)
    e.setw(CLOCK, 2)
    e.setw(HMGOALS, 0)
    e.setw(AWGOALS, 0)
    top, run, last, still = None, 0, None, 0
    for f in range(40000):
        hold = ["START"] if still >= 150 and f % 150 == 0 else []     # screens that wait for a press
        e.run(1, hold=hold)
        c = e.w(CLOCK)
        still = still + 1 if c == last else 0
        live = e.w(GSP) == 3 and ours(e) and (e.w(HMGOALS), e.w(AWGOALS)) == (0, 0)
        if not live:
            top = None
        if live and e.b(SCREEN) == 0:
            top = c if top is None else max(top, c)
            run = run + 1 if last is not None and c <= last and top - c >= 1 else 0
            if top - c >= 3:
                break
        last = c
    else:
        return e.w(GSP), None
    e.screenshot(out / f"{tag}_ot_start.png")
    return e.w(GSP), top


def game(rom, out):
    e = Emu(rom)
    to_setup(e, out)
    if not into_play(e):
        print("never reached play")
        return
    print("in play: period", e.w(GSP), "clock", e.w(CLOCK), "mode", e.w(PLAYMODE), "length", e.w(PERLEN), flush=True)
    e.screenshot(out / "first_play.png")
    OURS.append(tuple(e.b(a) for a in TEAMS))
    base = e.serialize()
    for mode, mname in ((0, "regular season"), (2, "new playoffs")):
        for perlen in (0, 3):
            gsp, clock = to_overtime(e, base, mode, perlen, out, f"m{mode}_p{perlen}")
            print(f"{mname}, period length {perlen}: gsp {gsp}, overtime clock {clock}"
                  + (f" ({clock // 60}:{clock % 60:02d})" if clock else ""), flush=True)
            lowload.breathe()
    # the clock shown long into a 99:00 overtime
    gsp, clock = to_overtime(e, base, 0, 3, out, "long")
    ot = e.serialize()
    for v in (5940, 5999 - 59, 3600, 1199, 600, 61, 59):
        e.unserialize(ot)
        e.setw(CLOCK, v)
        e.run(30)
        e.screenshot(out / f"clock_{v}.png")
    # a home goal at 1:40 left (97:20 in): ScoreSum's entry, then the game's end
    e.unserialize(ot)
    e.setw(CLOCK, 100)
    s0 = e.w(HMGOALS), e.w(AWGOALS)
    scored = None
    for y, vy in ((250, 3000), (-250, -3000)):
        e.unserialize(ot)
        e.setw(CLOCK, 100)
        for f in range(90):
            for g in (5, 11):                         # both goalies aside
                e.setw(H.rec(g), 120)
                e.setw(H.rec(g) + 0x14, 0)
            if f == 0:
                e.setw(H.PUCK, 0)
                e.setw(H.PUCK + 0x14, y)
                e.setw(H.PUCK + 0x18, 0)
                e.setw(H.PUCK + 0x28, 0)
                e.setw(H.PUCK + 0x2A, vy & 0xFFFF)
                e.setb(H.PUCK + 0x60, 0xFF)
            e.run(1)
            if (e.w(HMGOALS), e.w(AWGOALS)) != s0:
                scored = (e.w(HMGOALS), e.w(AWGOALS), e.w(CLOCK))
                break
        if scored:
            break
    print("goal late in the 99:00 overtime:", scored, flush=True)
    if scored:
        e.run(2)
        ss = bytes(e.b(0xC472 + i) for i in range(0x60))
        print("ScoreSum bytes:", ss.hex(), flush=True)
        for k in range(40):
            e.run(4, hold=["START"] if k > 3 else [])
            e.run(90)
            e.screenshot(out / f"after_goal_{k:02d}.png")
            if e.b(SCREEN) == 0 and k > 6:
                break
        print("after the goal: gsp", e.w(GSP), flush=True)
    # a 99:00 overtime run out at 0-0
    e.unserialize(ot)
    e.setw(CLOCK, 3)
    for k in range(50):
        e.run(4, hold=["START"] if k > 3 else [])
        e.run(90)
        e.screenshot(out / f"tie_{k:02d}.png")
        if k % 5 == 0:
            print(f"tie step {k} (ours {ours(e)}): gsp {e.w(GSP)}, clock {e.w(CLOCK)}, screen {e.b(SCREEN)}, score {e.w(HMGOALS)}-{e.w(AWGOALS)}",
                  flush=True)


def main():
    what, rom, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    if what == "menu":
        menu(rom, out, len(sys.argv) > 4)
    else:
        game(rom, out)


if __name__ == "__main__":
    main()
