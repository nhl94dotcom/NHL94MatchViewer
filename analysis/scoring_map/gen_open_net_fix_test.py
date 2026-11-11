"""NOSE4Web's open-net one-timer fix (e3de67f, nhl94_open_net_fix.bin), tested in play (2026-11-10).

The fix: shotdiradj's `clr.w d0` at $C5FC becomes `moveq #8,d0`, so when the sightline from the puck through the goalie
misses the net (GENESIS_SHOOTING 4.4) the one-timer is aimed at the middle, mid-height (8, the pulled-goalie aim)
instead of high middle (0). The test: the one-timer harness (ot_harness: the scoring-map test ROM, the passer and the
receiver alone with the goalies, cross-slot passes at the top net), on the test ROM and on it with the build laid
over it (gen_onetimer_assist_test.overlay: every range the build changes against retail). Just before the strike
frame the goalie is either left where he settled ("in position") or put out of the sightline: standing still
wide of the post on the side away from the shooter, or out in front of the net off to the shooter's own side
("out wide", "out front"). At the strike the game's aim is read (passdir $BEDC: 0 high middle, 2 / 6 a post, 8
middle), and the shot is played out from N seeds (goal, saved, post, missed). Also the bytes the build changes
against retail.

python gen_open_net_fix_test.py RETAIL BUILD [N]"""
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

PASSDIR = 0xBEDC


def changed_ranges(a, b):
    out, i = [], 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            out.append((i, b[i:j].hex()))
            i = j
        else:
            i += 1
    return out


def main():
    retail, build = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    a, b = Path(retail).read_bytes(), Path(build).read_bytes()
    print("bytes the build changes against retail:", [(f"${i:X}", h) for i, h in changed_ranges(a, b)])
    import harness
    from ot_harness import OneTimer, PASSER, RECEIVER
    from gen_onetimer_assist_test import overlay
    from paths import ROM
    out = Path(os.environ.get("TEMP", ".")) / ("smap94_" + Path(build).name)
    overlay(build, retail, ROM, out)
    roms = [("test ROM", str(ROM)), (Path(build).name, str(out))]
    # receiver at R, passer across the slot at the same depth: depth from the goal line (264) about 44, 64, 94, 124
    setups = [((x, y), (-x, y)) for y in (220, 200, 170, 140) for x in (30, -30)]
    goalie_cases = ("in position", "out wide", "out front")
    res = defaultdict(Counter)                 # (rom, case, depth) -> outcome counts
    aims = defaultdict(Counter)                # (rom, case) -> passdir counts
    for name, rom in roms:
        harness.Harness.__init__.__defaults__ = (rom,) + harness.Harness.__init__.__defaults__[1:]
        ot = OneTimer("genesis")
        e, s = ot.e, ot.s
        for R, P in setups:
            depth = 264 - R[1]
            ot.setup("top", P, R, 0, random.Random(1))
            pre = None
            for by in (4, 6, 8, 3, 10):
                press, why = ot.pass_to_press("late", by=by)
                if press is None:
                    continue
                pre, why = ot.swing(press, None)
                if pre is not None:
                    break
            if pre is None:
                print(f"  {name}: R {R}: no one-timer ({why})")
                continue
            for case in goalie_cases:
                e.unserialize(pre)
                side = 1 if R[0] > 0 else -1          # the shooter's side of the net
                if case == "out wide":
                    s.put(s.GOALIE, -side * 70, 250)    # wide of the far post, on the goal line
                elif case == "out front":
                    s.put(s.GOALIE, side * 45, 225)     # out toward the shooter's own side, off his line to the net
                start = e.serialize()
                for k in range(n):
                    ot.strike(start, None, 1000 + 7919 * k)
                    aims[(name, case)][e.w(PASSDIR)] += 1
                    res[(name, case, depth)][ot.play_out()] += 1
        print(f"{name}: done")
    print("\nAim at the strike (passdir: 0 high middle, 2 / 6 by a post, 8 middle):")
    for case in goalie_cases:
        print(f"  {case}: " + "; ".join(f"{name} {dict(sorted(aims[(name, case)].items()))}" for name, _ in roms))
    print("\nGoals / shots by depth (units from the goal line):")
    for case in goalie_cases:
        for name, _ in roms:
            row = []
            tot = Counter()
            for R, P in setups[::2]:
                depth = 264 - R[1]
                c = res[(name, case, depth)]
                tot += c
                shots = sum(c.values())
                row.append(f"{depth}: {c['GOAL']}/{shots}" if shots else f"{depth}: -")
            all_ = sum(tot.values())
            print(f"  {case:12s} {name:28s} " + ", ".join(row) + f"; all {tot['GOAL']}/{all_} ({100 * tot['GOAL'] / max(1, all_):.0f}%)"
                  f"  {dict(tot)}")


if __name__ == "__main__":
    main()
