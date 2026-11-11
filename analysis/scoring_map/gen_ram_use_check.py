"""Which work RAM a ROM writes, from $FFC000 up (2026-11-11, for NOSE4Web: is $FFF080-$FFF081 free for the fighting
setting in every game, after chaos's $FFDF00 turned out to be inside smozROM's plus-minus log). Power-on to Game Setup,
Penalties On Except Off-sides and 5-minute periods (and, with --records, User Records on), the computer against itself
(gen_injury_baseline's way) for a whole game, the pause menu and an instant replay opened twice on the way; every 4
frames work RAM from $FFC000 is compared with its first frame at Game Setup and every byte that ever differs is marked
(writes that leave a byte as it was can't be seen this way, but anything that uses a byte for a count, a flag or an
address changes it). Printed: the ranges marked, $FFF000-$FFF0FF in detail, and the longest unmarked runs above
$FFE000.

python gen_ram_use_check.py ROM [--records]"""
import sys

import numpy as np

import gen_ot_check as G
import lowload
from emu import Emu

OPTUSER, OPTPEN, PERLEN, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD054, 0xD056, 0xD050, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ, LO = 0xB04A, 0x80, 0xC000


def ranges(addrs):
    out = []
    for a in sorted(addrs):
        if out and a == out[-1][1] + 1:
            out[-1][1] = a
        else:
            out.append([a, a])
    return out


def main():
    rom = sys.argv[1]
    lowload.gentle()
    e = Emu(rom)
    from pathlib import Path
    import tempfile
    out = Path(tempfile.gettempdir()) / "ram_use_boot"
    out.mkdir(exist_ok=True)
    G.to_setup(e, out)
    ram = lambda: np.frombuffer(bytes(e.ram[:0x10000]), np.uint8)
    base = ram().copy()
    touched = np.zeros(0x10000, bool)

    def look():
        nonlocal touched
        touched |= ram() != base
    e.setw(OPTPEN, 2)
    e.setw(PERLEN, 0)
    if "--records" in sys.argv:
        e.setw(OPTUSER, 0)
        e.setw(0xD04A, 0)
    look()
    if not G.into_play(e):
        print("never reached play")
    frame, still, last, ended, replays = 0, 0, None, None, 0
    while frame < 60 * 60 * 40:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        if replays < 2 and frame in (3000, 12000) and e.b(SCREEN) == 0:     # the pause menu and an instant replay
            replays += 1
            for b, w in (("START", 90), ("DOWN", 30), ("C", 240), ("C", 120), ("START", 60), ("C", 120), ("START", 60),
                         ("B", 120)):
                e.run(4, hold=[b])
                e.run(w)
                look()
            for _ in range(3):
                if e.b(SCREEN) == 0:
                    break
                e.run(4, hold=["START"])
                e.run(120)
        e.run(4, hold=["START"] if still >= 8 and frame % 60 < 4 else [])
        frame += 4
        look()
        if ended is None and e.w(GSP) >= 3:
            ended = frame
        if ended is not None and (e.w(GSP) == 0 or frame - ended > 10 * 60 * 60):
            for _ in range(150):
                e.run(4)
                look()
            break
    # e.ram is the core's copy, words byte-swapped: the byte at address A is at index A ^ 1
    addrs = {i ^ 1 for i in np.nonzero(touched)[0] if (i ^ 1) >= LO}
    rs = ranges(addrs)
    print(f"{Path(rom).name}: game frames {frame}, periods {e.w(GSP)}, score {e.w(0xC6DA)}-{e.w(0xCA3E)}; "
          f"bytes from $FF{LO:04X} that changed: {len(addrs)}")
    print("  $FFF000-$FFF0FF changed:", [f"${0xFF0000 + a:06X}" for a in sorted(x for x in addrs if 0xF000 <= x < 0xF100)] or "none")
    print("  $FFF080/1 changed:", 0xF080 in addrs or 0xF081 in addrs)
    free = []
    a = 0xE000
    for lo, hi in rs + [[0x10000, 0x10000]]:
        if lo > a:
            free.append((a, lo - 1))
        a = max(a, hi + 1)
    free = [f for f in free if f[0] >= 0xE000]
    print("  unchanged runs from $FFE000 (32+ bytes):", [f"${0xFF0000 + lo:06X}-${0xFF0000 + hi:06X}" for lo, hi in free
                                                         if hi - lo >= 31])
    print("  changed ranges from $FFC000:", " ".join(f"{lo:04X}-{hi:04X}" for lo, hi in rs))


if __name__ == "__main__":
    main()
