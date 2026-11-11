"""Work RAM from $FFE000 up through the screens a game doesn't visit (2026-11-11, for NOSE4Web's $FFF080): the playoff
tree (New Playoffs), a shootout (Play Mode 4) with a few attempts, and in a regular game the pause menu's Edit Lines and
Team Roster (paged), player cards and stats; and, with --fights, a stretch of play with every fighting rating at 14
(fights on a fighting build). Every 2 frames work RAM from $FFE000 is compared with Game Setup's and each byte that ever
differs is marked. Printed: the changed ranges from $FFE000 and whether $FFF080-$FFF081 is among them.

python gen_ram_tour_check.py ROM [--fights]"""
import sys

import numpy as np

import gen_ot_check as G
import lowload
from emu import Emu

PLAYMODE, SCREEN, BASE, SZ = 0xD048, 0xFFF7, 0xB04A, 0x80


def main():
    rom = sys.argv[1]
    fights = "--fights" in sys.argv
    lowload.gentle()
    from pathlib import Path
    import tempfile
    out = Path(tempfile.gettempdir()) / "ram_tour"
    out.mkdir(exist_ok=True)
    e = Emu(rom)
    G.to_setup(e, out)
    setup = e.serialize()
    ram = lambda: np.frombuffer(bytes(e.ram[:0x10000]), np.uint8)
    base = ram().copy()
    touched = np.zeros(0x10000, bool)

    def run(n, hold=()):
        nonlocal touched
        for _ in range(n // 2):
            if fights:
                for k in range(12):
                    e.setb(BASE + SZ * k + 0x74, 14)
            e.run(2, hold=list(hold))
            touched |= ram() != base

    def press(b, w=40):
        run(4, [b])
        run(w)
    # the playoff tree
    e.unserialize(setup)
    e.setw(PLAYMODE, 2)
    for _ in range(4):
        press("START", 200)
    for b in ("DOWN", "DOWN", "UP", "START"):
        press(b, 120)
    # a shootout
    e.unserialize(setup)
    e.setw(PLAYMODE, 4)
    for _ in range(4):
        press("START", 300)
    for _ in range(4):
        run(90, ["UP"])
        press("C", 300)
    # a regular game: play, then the pause menu's screens
    e.unserialize(setup)
    G.into_play(e)
    run(1800 if not fights else 6000)
    for item in range(1, 9):
        press("START", 90)
        for _ in range(item):
            press("DOWN", 20)
        press("C", 200)
        for b in ("RIGHT", "RIGHT", "DOWN", "C", "B", "B", "B", "START"):
            press(b, 90)
        for _ in range(4):
            if e.b(SCREEN) == 0:
                break
            press("START", 120)
    run(600)
    addrs = sorted({i ^ 1 for i in np.nonzero(touched)[0] if (i ^ 1) >= 0xE000})
    rs = []
    for a in addrs:
        if rs and a == rs[-1][1] + 1:
            rs[-1][1] = a
        else:
            rs.append([a, a])
    print(f"{Path(rom).name}{' (fights)' if fights else ''}: changed from $FFE000: "
          + (" ".join(f"${0xFF0000 + lo:06X}-${0xFF0000 + hi:06X}" for lo, hi in rs) or "none")
          + f"; $FFF080/1 changed: {0xF080 in addrs or 0xF081 in addrs}")


if __name__ == "__main__":
    main()
