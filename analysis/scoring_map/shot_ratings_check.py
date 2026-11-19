"""Shot Power and Shot Accuracy in play (Genesis NHL '94, 2026-11-18, for NOSE4Web's roster-page rewrite):
sniping_test's set-up (live state, the home centre at a spot with the puck, everyone else parked), the shooter's
working rating set every frame.

  acc ROM [SEEDS]   working Shot Accuracy ($6D) 0-30 in steps: C tapped from SPOTS (94-174 from the top net's aim
                    point, within doshot's 200), SEEDS seeds each; the share exact (sniping_test's measure: an exact
                    shot leaves a spot the same way every time, so the share of a spot's shots on its most common
                    velocity) against the code's (ShA + 1) / (ShA + 16)
  power ROM [SEEDS] working Shot Power ($6C): C held through the whole wind-up (WIND frames) and let go, from the slot;
                    the highest passspeed ($BEDE: doshot's speed before x 68) and the puck's speed the frame after
                    the release (sqrt of the three speed words; a puck at 23,000 is about 78 mph)

python shot_ratings_check.py acc|power ROM [SEEDS]"""
import math
import random
import sys
from collections import Counter

from blind_ring_test import park, SHOOTER
from bot import rec, PUCKC
from bot_scenario import live_state
from emu import Emu
from sniping_test import SPOTS

SHP, SHA, PASSSPEED, WIND = 0x6C, 0x6D, 0xBEDE, 90


def shoot(e, base, x, y, seed, rating, value, hold):
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, seed)
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(SHOOTER) + 0x62, e.b(rec(SHOOTER) + 0x62) | 8)
    e.setw(0xC320, SHOOTER)
    for _ in range(60):
        e.setw(rec(SHOOTER), x & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x14, y & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        e.setb(rec(SHOOTER) + rating, value)
        park(e)
        e.setw(PUCKC, SHOOTER)
        e.run(1)
    e.setl(0xD066, seed)
    for f in range(hold + 60):
        park(e)
        e.setb(rec(SHOOTER) + rating, value)
        e.run(1, hold=["C"] if f < hold else [])
        if e.w(PUCKC) >= 0x8000:
            return e.w(PASSSPEED), (e.sw(rec(14) + 0x28), e.sw(rec(14) + 0x2A), e.sw(rec(14) + 0x2C))
    return None


def main():
    mode, rom = sys.argv[1], sys.argv[2]
    seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    e = Emu(rom)
    base = live_state(e, 0)
    if mode == "acc":
        for sha in (0, 5, 10, 15, 20, 25, 30):
            exact = total = 0
            for x, y in SPOTS:
                vs = [shoot(e, base, x, y, random.Random(f"{x},{y},{s}").getrandbits(32), SHA, sha, 3) for s in range(seeds)]
                vs = [v[1] for v in vs if v]
                if vs:
                    exact += Counter(vs).most_common(1)[0][1]
                    total += len(vs)
            print(f"ShA {sha:2d}: exact {exact} of {total} ({exact / max(1, total):.1%}); the code's (ShA + 1) / (ShA + 16) "
                  f"{(sha + 1) / (sha + 16):.1%}", flush=True)
    else:
        for shp in (10, 15, 16, 17, 19, 20, 21, 25, 30):
            best = None
            for s in range(seeds):
                r = shoot(e, base, 0, 120, random.Random(f"p{s}").getrandbits(32), SHP, shp, WIND)
                if r and (best is None or r[0] > best[0] or (r[0] == best[0] and math.hypot(*r[1]) > math.hypot(*best[1]))):
                    best = r
            if best:
                sp = math.hypot(*best[1])
                print(f"ShP {shp:2d}: highest passspeed {best[0]}, puck speed {sp:,.0f} (about {sp * 78 / 23000:.0f} mph)", flush=True)


if __name__ == "__main__":
    main()
