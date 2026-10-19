"""Runaway speed on the SNES (2026-10-19; the Genesis one is GENESIS_MECHANICS 3.4). NHL94SNES updateplayers multiplies
a skater's velocity each step by a friction byte, .21 ($FD, $FA, $F7 ... by timestep) normally and .22 ($FF, $FF, $FE ...)
while pflags bit 0 is set, so that flag is the Genesis pfdoff. asspassrec sets it on the receiver of a pass; it is cleared
when his wait ends (asspassrec .6), when his stick touches the puck (puckstick, any player), in assnearest and in
resetplstuff (faceoffs). FallDown never sets it. For every recorded sample: skaters with the flag on, how long it stays
on, how fast they go, and whether a person had them.
python analysis/snes_runaway_study.py [capture folders]"""
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402

XVEL, YVEL, PFLAGS, POSITION = 0x0EC3, 0x0EE3, 0x1283, 0x0F43


def sw(v):
    return v - 0x10000 if v >= 0x8000 else v


def main():
    folders = [Path(a) for a in sys.argv[1:]]
    speeds = Counter()
    runs = []
    for folder in folders:
        try:
            cap = Capture(folder)
        except Exception as e:  # noqa: BLE001
            print("skip", folder, e)
            continue
        on = {}
        for i in range(cap.count):
            for k in range(12):
                if sw(cap.word(i, POSITION + 2 * k)) < 0:
                    on.pop(k, None)
                    continue
                fl = cap.word(i, PFLAGS + 2 * k)
                vx, vy = sw(cap.word(i, XVEL + 2 * k)), sw(cap.word(i, YVEL + 2 * k))
                sp = math.hypot(vx, vy)
                if fl & 1:
                    r = on.setdefault(k, [folder.name, k, cap.ms(i), cap.ms(i), 0, False])
                    r[3], r[4] = cap.ms(i), max(r[4], sp)
                    r[5] = r[5] or bool(fl & 0x0008)
                    speeds[int(sp // 2000) * 2000] += 1
                elif k in on:
                    runs.append(on.pop(k))
        runs.extend(on.values())
    print(len(runs), "stretches with the flag on")
    long_ = [r for r in runs if r[3] - r[2] > 2000]
    print("on for more than 2 s:", len(long_))
    for person in (True, False):
        d = sorted(r[3] - r[2] for r in runs if r[5] == person)
        if d:
            print("person" if person else "computer", len(d), "stretches; ms on: median", d[len(d) // 2], "90%", d[int(len(d) * 0.9)], "max", d[-1])
    for r in long_:
        print("long:", r)
    for r in sorted(runs, key=lambda r: -r[4])[:15]:
        print(f"{r[0]} obj {r[1]} {r[2] / 1000:7.1f}-{r[3] / 1000:7.1f} s  top {r[4]:6.0f}  person {r[5]}")
    print("speeds while on (samples):", sorted(speeds.items()))


if __name__ == "__main__":
    main()
