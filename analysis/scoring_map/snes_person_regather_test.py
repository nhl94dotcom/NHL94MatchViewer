"""NOSE4Web's SNES shot fix, second version (2026-11-14: sfssdir put back only for a person's shooter, pflags $1283
bit 3): does a person's wind-up still fire after he loses the puck at his stick and gathers it again?

Pad 1 on its team from the menus (snes_shootout_lock_check.person_start). Each time pad 1's player carries the puck
(puckc $0AD9 = his object x 2, his pflags with the person bit), and no trial ran in the last 2 s (real): A held
HOLD frames (the wind-up: doinput's A press starts ShotMode's swing, the release fires). In a forced trial the puck
is made loose at his stick FORCE_AT frames in (puckc $FFFF: he gathers it straight back through puckstick / puckglue,
which clears the shot flag); in a plain trial nothing is done (a check that A held and released shoots at all). After
the release, LOOK frames: fired (the puck left him with his nopuck $1203 at 16: doshot), held (he still has it),
lost (someone else, or loose with no shot). The shot flag (sflags $15D8 bit 3) is logged as he gathers it back.

python snes_person_regather_test.py ROM OUT [TRIALS]"""
import json
import sys
from pathlib import Path

import lowload
from snes_shootout_lock_check import person_start

PUCKC, PFLAGS, NOPUCK, SFLAGS, SPA = 0x0AD9, 0x1283, 0x1203, 0x15D8, 0x11A3
HOLD, FORCE_AT, LOOK = 14, 4, 40


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    trials = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e, m = person_start(rom, out)
    res = {"forced": {"fired": 0, "held": 0, "lost": 0, "no swing": 0}, "plain": {"fired": 0, "held": 0, "lost": 0, "no swing": 0}}
    flags, last, f, n = [], -10 ** 9, 0, 0
    while n < trials and f < 60 * 60 * 30:
        e.run(1)
        f += 1
        if f % 3600 == 0:
            lowload.breathe()
        pc = s16(m.w(PUCKC))
        if pc < 0 or pc > 22 or not m.w(PFLAGS + pc) & 8 or f - last < 120:
            continue
        k = pc // 2
        kind = "forced" if n % 3 else "plain"          # two forced trials to every plain one
        swung, back_flag, gone = False, None, False
        for i in range(HOLD):
            if kind == "forced" and i == FORCE_AT and s16(m.w(PUCKC)) == 2 * k:
                m.setw(PUCKC, 0xFFFF)                    # loose at his stick: he gathers it back
                gone = True
            e.run(1, hold=["A"])
            f += 1
            swung = swung or 0xED4A <= m.w(SPA + 2 * k) <= 0xF020
            if gone and back_flag is None and s16(m.w(PUCKC)) == 2 * k:
                back_flag = bool(m.w(SFLAGS) & 8)
        result = None
        for i in range(LOOK):
            e.run(1)
            f += 1
            p = s16(m.w(PUCKC))
            if gone and back_flag is None and p == 2 * k:
                back_flag = bool(m.w(SFLAGS) & 8)
            if p < 0 and m.w(NOPUCK + 2 * k) == 16:
                result = "fired"
                break
        if result is None:
            result = "held" if s16(m.w(PUCKC)) == 2 * k else "lost"
        if not swung:
            result = "no swing"
        res[kind][result] += 1
        if kind == "forced":
            flags.append(back_flag)
        last, n = f, n + 1
        print(f"trial {n}: {kind}, {result}" + (f", the flag as he gathered it back: {back_flag}" if kind == "forced" else ""), flush=True)
    res["flag set as he gathered it back (forced trials)"] = {str(v): flags.count(v) for v in set(flags)}
    print(json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
