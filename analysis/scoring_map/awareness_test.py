"""NOSE4Web's awareness-slip option (bug 20), played in the game (2026-11-08, the user approved running the patched
ROMs). The computer's wingers and centre on offence (asswingo, asscentero) reload their re-decision timer (temp1) from
aidef (Defensive Awareness) where the other offence jobs use aioff; the option makes it aioff.

From live play with nobody pressing anything (the computer plays both sides' skaters but pad 1's), every frame: each
computer winger or centre whose team has the puck, whose timer jumps up (a reload), noted with his aioff and aidef.
Reloads equal to (or one under: the loud-crowd quickening) only one of the two say which it uses.

python awareness_test.py genesis|snes ROM [frames per moment]"""
import sys
from collections import Counter


def genesis(rom, frames):
    from bot import rec, PUCKC
    from bot_scenario import live_state, LIVE_STATES, CONT_TEAMS
    from emu import Emu
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(LIVE_STATES)]
    out = Counter()
    for base in bases:
        e.unserialize(base)
        e.setw(CONT_TEAMS[0], 0)                       # nobody on a pad: the computer plays every skater
        e.setw(CONT_TEAMS[1], 0)
        for k in range(12):
            e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
        last = [e.b(rec(k) + 0x40) for k in range(12)]
        for f in range(frames):
            e.run(1)
            if e.b(0xFFF7):
                break
            pc = e.w(PUCKC)
            for k in range(12):
                t = e.b(rec(k) + 0x40)
                t = t - 256 if t > 127 else t
                lt = last[k] - 256 if last[k] > 127 else last[k]
                last[k] = e.b(rec(k) + 0x40)
                if e.b(rec(k) + 0x35) not in (3, 4, 5) or pc >= 0x8000 or pc // 6 != k // 6 or t <= lt + 1:
                    continue
                off, de = e.b(rec(k) + 0x6A), e.b(rec(k) + 0x6B)
                out[classify(t, off, de)] += 1
    return out


def classify(t, off, de):
    if off == de:
        return "aioff = aidef"
    a, d = t in (off, off - 1), t in (de, de - 1)
    return "aioff" if a and not d else "aidef" if d and not a else "both" if a else "neither"


def snes(rom, frames):
    from faceoff_fix_test import Snes
    g = Snes(rom)
    out = Counter()
    TEMP1, AIOFF, AIDEF, POS, PUCKC, PLAYERPAD = 0x1003, 0x1323, 0x1343, 0x0F43, 0x0AD9, 0x19D4
    for base in g.bases:
        g.e.unserialize(base)
        for k in range(12):
            g.setw(PLAYERPAD + 2 * k, 0xFFFF)          # every skater the computer's
        sw = lambda a: (lambda v: v - 0x10000 if v >= 0x8000 else v)(g.w(a))
        last = [sw(TEMP1 + 2 * k) for k in range(12)]
        for f in range(frames):
            g.e.lib.retro_run()
            pc = g.w(PUCKC)
            for k in range(12):
                t = sw(TEMP1 + 2 * k)
                lt, last[k] = last[k], t
                if g.w(POS + 2 * k) not in (3, 4, 5) or pc >= 0x8000 or pc // 12 != k // 6 or t <= lt + 1:
                    continue
                out[classify(t, g.w(AIOFF + 2 * k), g.w(AIDEF + 2 * k))] += 1
    return out


def main():
    system, rom = sys.argv[1], sys.argv[2]
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
    out = (genesis if system == "genesis" else snes)(rom, frames)
    print(rom.split("/")[-1], "reloads of computer wingers / centres with their team's puck:", dict(out))


if __name__ == "__main__":
    main()
