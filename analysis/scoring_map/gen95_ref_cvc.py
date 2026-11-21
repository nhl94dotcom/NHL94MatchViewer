"""Penalties by type in NHL '95 computer games, any NHL '95 ROM (2026-11-19, for NOSE4Web's referee strictness option on
NHL '95: checkagr's mulu.w multiplier, word $8997A, 26 / 17 / 13 / 9 / 6; goalie interference's cmp.w threshold, word
$7C4D8, 2 / 4 / 5 / 8 / 12). gen_ref_cvc.py at NHL '95's addresses.

Each game: power-on to Game Setup (gen95_fight_check.to_setup), 5-minute periods, penalties On Except Off-sides, line
changes off, START into play (as gen95_3on3_check), the seed $FFCC6A from the game's number, the computer on both
sides (cont1team / cont2team cleared and the person flag taken off every second), three periods. The penalty summary
(PenSumLength $C196, PenSum $C198: 4 bytes each, time, team | rule, roster index) is read every second.
Baselines: the original as NOSE4Web's editor opens it (no options on), so the only differences are the two words.

python gen95_ref_cvc.py ROM GAMES OUT.jsonl [FIRST]   |   report OUT.jsonl ...  (gen_ref_cvc's report)"""
import json
import sys
from pathlib import Path

import gen95_fight_check as F
import gen_ref_cvc as R
import lowload
from emu import Emu

GSP, CLOCK, GMODE, SEED = 0xC020, 0xC022, 0xBEF0, 0xCC6A
PENS = 0xC196
SCORE = (0xC294, 0xC5FA)
BASE, SZ = 0xAC62, 0x80


def game(rom, n):
    e = Emu(rom)
    F.to_setup(e)
    e.setb(F.ROW + 3, 0)                       # 5-minute periods
    e.setb(F.ROW + 6, 2)                       # penalties: On, Except Off-sides
    e.setb(F.ROW + 7, 1)                       # line changes off
    e.run(6, hold=["START"]); e.run(300); e.run(6, hold=["START"]); e.run(60); e.run(1800)
    for _ in range(6):
        e.run(6, hold=["START"]); e.run(300)
    e.setl(SEED, (0x2545F491 * (n + 1)) & 0xFFFFFFFF or 1)
    pens, seen = [], 0
    frame, still, last = 0, 0, None
    while e.w(GSP) < 3 and frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(0xBF4C, 0)
            e.setw(0xBF4E, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            ln = e.w(PENS)
            if 0 < ln <= 240:
                while seen + 4 <= ln:
                    t, code = e.w(PENS + 2 + seen), e.b(PENS + 4 + seen)
                    pens.append(dict(period=t >> 14, secs=t & 0x3FFF, team=1 if code & 0x80 else 0,
                                     rule=R.RULES.get(code & 0x7F, hex(code & 0x7F))))
                    seen += 4
            if frame % 3600 == 0:
                lowload.breathe()
        e.run(1, hold=["START"] if still >= 8 and frame % 60 < 2 else [])
        frame += 1
    return {"game": n, "rom": Path(rom).name, "frames": frame, "penalties": pens,
            "goals": [e.w(SCORE[0]), e.w(SCORE[1])], "reached": e.w(GSP)}


def main():
    if sys.argv[1] == "report":
        R.report(sys.argv[2:])
        return
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    first = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    lowload.gentle()
    for n in range(first, first + games):
        r = game(rom, n)
        with open(out, "a") as fo:
            fo.write(json.dumps(r) + "\n")
        print(n, len(r["penalties"]), r["goals"], r["frames"], flush=True)


if __name__ == "__main__":
    main()
