"""A "count stick deflections" option, tested in the game (Genesis, 2026-11-08, for NOSE4Web; the user approved). The
Genesis doesn't count a shot that comes off the goalie's stick: puckstick .stdef ($151CE) plays the sound, calls
a2touchpuck (which clears sf2shot) and deflects, never reaching ChkShotStat. A test copy of the retail ROM
(count_deflections_rom.py builds it: the hook replaces .stdef's `bsr a2touchpuck / bra deflect` at $151D6) counts the
shot there when the toucher is a goalie, the clock runs, no highlight, and sf2shot stands (cleared, so once), through
ChkShotStat's own .addShot (team, power play, period, shooter and goalie-against counts) without its crowd boost.

Shots from live play, the same on both ROMs: the home centre at a spot with the puck, everyone else parked, C held
3-12 frames with one of nine aims, then 150 frames; at the top net (bot_live states, period 1) and the bottom (the
same moments with the period set to 2 and every skater's attacking end flipped is not the game's, so the bottom uses
paths.STATE_BOTTOM, period 2). Per shot: Home's shots on goal and goals after, on each ROM; and whether the frames
after the release stay the same (every skater's and the puck's position) on both.

python count_deflections_test.py TEST_ROM [ORIGINAL_ROM] [shots per end]"""
import random
import sys
from collections import Counter

from blind_ring_test import park, SHOOTER
from bot import rec, PUCKC, pad
from bot_scenario import live_state
from emu import Emu
from paths import STATE_BOTTOM

SHOTS, SCORE = 0xC6CE, 0xC6DA
AIMS = [None, 0, 1, 2, 3, 4, 5, 6, 7]


def shoot(e, base, rnd, bottom):
    x = rnd.choice((-60, -30, 0, 30, 60))
    y = rnd.choice((110, 140, 170, 200)) * (-1 if bottom else 1)
    aim, hold = rnd.choice(AIMS), rnd.choice((3, 6, 9, 12))
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, rnd.getrandbits(32))
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
        e.run(1)
    s0, g0 = e.w(SHOTS), e.w(SCORE)
    for f in range(80):
        park(e)
        e.run(1, hold=(["C"] if f < hold else []) + (pad(aim) if aim is not None else []))
        if e.w(PUCKC) >= 0x8000:
            break
    else:
        return None
    path = []
    for f in range(150):
        park(e)
        e.run(1)
        path.append(tuple(e.w(rec(k) + o) for k in (*range(12), 14) for o in (0, 0x14)))
    return dict(shots=e.w(SHOTS) - s0, goals=e.w(SCORE) - g0, path=path)


def main():
    test = sys.argv[1]
    orig = sys.argv[2] if len(sys.argv) > 2 else None
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    results = {}
    for name, rom in (("original", orig), ("test", test)):
        e = Emu(rom)
        bases = {"top": [live_state(e, j) for j in range(4)], "bottom": [open(STATE_BOTTOM, "rb").read()]}
        results[name] = {end: [shoot(e, b[i % len(b)], random.Random(f"{end}{i}"), end == "bottom") for i in range(n)]
                         for end, b in bases.items()}
    for end in ("top", "bottom"):
        o, t = results["original"][end], results["test"][end]
        pairs = [(a, b) for a, b in zip(o, t) if a and b]
        c = Counter()
        for a, b in pairs:
            d = b["shots"] - a["shots"]
            same = next((f for f in range(len(a["path"])) if a["path"][f] != b["path"][f]), None)
            c[(d, a["goals"], b["goals"], "same play" if same is None else f"differs from frame {same}")] += 1
        print(f"\n{end} net: {len(pairs)} shots; shots on goal original {sum(a['shots'] for a, _ in pairs)}, "
              f"test {sum(b['shots'] for _, b in pairs)}; goals {sum(a['goals'] for a, _ in pairs)} / {sum(b['goals'] for _, b in pairs)}")
        for (d, ga, gb, same), k in sorted(c.items(), key=lambda t: -t[1]):
            print(f"   {k:4}  shots +{d}, goals {ga} / {gb}, {same}")


if __name__ == "__main__":
    main()
