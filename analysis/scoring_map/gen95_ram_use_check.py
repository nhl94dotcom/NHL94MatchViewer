"""NHL '95 (Genesis): which work RAM a game writes (2026-11-16, for NOSE4Web's regular-season shootouts: about $6CE free
bytes and a mark byte; NHL '94's: gen_ram_use_check.py). Power-on to Game Setup (three STARTs, the self-check off), a
Regular Game started with the computer on both teams (cont1team / cont2team 0, the person flags cleared) and played to
its end, the pause menu and an instant replay opened twice on the way, then START through the end screens. Every 4
frames all of work RAM ($FF0000-$FFFFFF) is compared with its copy at Game Setup; every byte that ever differs is
marked (a write that leaves a byte as it was can't be seen, but anything a game uses as a count, flag or address
changes). Saved: the mark map (OUT.npy); printed: the longest unmarked runs from $FFC000 up.

python gen95_ram_use_check.py ROM OUT [PERIOD_SECONDS]   (the clock set to PERIOD_SECONDS at each period's start: a
shorter game, the same code paths)"""
import sys
from pathlib import Path

import numpy as np

from emu import Emu
import lowload

GSP, CLOCK, CONT1, CONT2, GMODE = 0xC020, 0xC022, 0xBF4C, 0xBF4E, 0xBEF0
BASE, SZ = 0xAC62, 0x80


def ram(e):
    return np.frombuffer(bytes(e.ram[:0x10000]), np.uint8).copy()


def runs(mask, lo=0xC000):
    out, start = [], None
    for a in range(lo, 0x10000):
        if not mask[a]:
            start = a if start is None else start
        elif start is not None:
            out.append((start, a - 1)); start = None
    if start is not None:
        out.append((start, 0xFFFF))
    return sorted(out, key=lambda r: r[0] - r[1])


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    per = int(sys.argv[3]) if len(sys.argv) > 3 else None
    lowload.gentle()
    e = Emu(rom)
    e.run(1500)
    for _ in range(3):
        e.run(6, hold=["START"]); e.run(200)
    ref = ram(e)
    used = np.zeros(0x10000, bool)

    def look():
        nonlocal used
        used |= ram(e) != ref

    def press(b, wait=60):
        e.run(6, hold=[b]); look(); e.run(wait); look()

    press("START", 300); press("START", 60)
    for _ in range(30):
        e.run(60); look()
    for _ in range(6):
        press("START", 300)
    f, last_gsp, replays, still, lastc = 0, -1, 0, 0, None
    while f < 60 * 60 * 40:
        if f % 60 == 0:
            e.setw(CONT1, 0); e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
        g = e.w(GSP)
        if g != last_gsp:
            last_gsp = g
            if per and g < 4:
                e.setw(CLOCK, per)
        c = e.w(CLOCK)
        still = still + 1 if c == lastc else 0
        lastc = c
        if replays < 2 and g == replays and c < (per or 600) - 30 and not e.b(GMODE) & 1:
            press("START", 120)                      # the pause menu
            press("DOWN", 30); press("C", 400)       # INSTANT REPLAY
            press("START", 200); press("B", 120); press("START", 120)
            replays += 1
        e.run(4, hold=["START"] if still > 225 and f % 900 < 4 else [])   # 15 s without the clock moving (counted in 4-frame looks)
        f += 4
        look()
        if f % 3600 == 0:
            lowload.breathe()
        if g >= 4 and still > 150:
            break
    for _ in range(8):
        press("START", 300)
    used = used[np.arange(0x10000) ^ 1]          # the core keeps work RAM byte-swapped: address A is index A ^ 1
    np.save(out, used)
    print(f"{Path(rom).name}: played to gsp {e.w(GSP)} in {f} frames; bytes ever changed from $FFC000 up:"
          f" {int(used[0xC000:].sum())} of {0x4000}")
    for a, b in runs(used)[:12]:
        print(f"   never changed: $FF{a:04X}-$FF{b:04X} ({b - a + 1} bytes)")


if __name__ == "__main__":
    main()
