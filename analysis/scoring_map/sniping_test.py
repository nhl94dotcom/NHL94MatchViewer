"""NOSE4Web's delayed-penalty sniping fix (bug 13), played in the game (Genesis, 2026-11-08, the user approved running
the patched ROMs). doshot makes every shot within 200 of its aim point exact when the shooter's own goalie is off
(ReadGoaliePulled, then `bmi .perf` at $C422); the fix nops the bmi, so those shots take the normal roll.

Shots in live play (blind_ring_test's setup: the home centre at a spot with the puck, everyone else parked), C tapped
with nothing held, from spots 120-200 from the aim point, each from 30 random seeds, with Home's tmgoalie ($C6F4) as
it is or set to $FF00 (pulled; the goalie himself stays in the net, which the shot code doesn't look at). An exact shot
leaves the same way every time from a spot (the scatter is random): the share of a spot's shots whose puck speeds the
frame after the release equal the most common ones is the share exact.

python sniping_test.py ROM [seeds]"""
import random
import sys
from collections import Counter

from blind_ring_test import park, SHOOTER
from bot import rec, PUCKC
from bot_scenario import live_state
from emu import Emu

SPOTS = [(x, y) for x in (-40, 0, 40) for y in (90, 130, 170)]   # 94-174 from the top net's aim point (0, 264)
HOME_GOALIE = 0xC6F4


def release(e, base, x, y, seed, pulled):
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, seed)
    if pulled:
        e.setw(HOME_GOALIE, 0xFF00)
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(SHOOTER) + 0x62, e.b(rec(SHOOTER) + 0x62) | 8)
    e.setw(0xC320, SHOOTER)
    for _ in range(60):
        e.setw(rec(SHOOTER), x & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x14, y & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        park(e)
        e.setw(PUCKC, SHOOTER)
        if pulled:
            e.setw(HOME_GOALIE, 0xFF00)
        e.run(1)
    e.setl(0xD066, seed)
    for f in range(60):
        park(e)
        e.run(1, hold=["C"] if f < 3 else [])
        if e.w(PUCKC) >= 0x8000:
            return e.sw(rec(14) + 0x28), e.sw(rec(14) + 0x2A), e.sw(rec(14) + 0x2C)
    return None


def main():
    rom = sys.argv[1]
    seeds = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    e = Emu(rom)
    base = live_state(e, 0)
    for pulled in (False, True):
        exact = total = 0
        for x, y in SPOTS:
            vs = [release(e, base, x, y, random.Random(f"{x},{y},{s}").getrandbits(32), pulled) for s in range(seeds)]
            vs = [v for v in vs if v]
            if not vs:
                continue
            exact += Counter(vs).most_common(1)[0][1]
            total += len(vs)
        print(f"{rom.split('/')[-1]}: own goalie {'pulled' if pulled else 'in'}: exact {exact} of {total} ({exact / max(1, total):.0%})")


if __name__ == "__main__":
    main()
