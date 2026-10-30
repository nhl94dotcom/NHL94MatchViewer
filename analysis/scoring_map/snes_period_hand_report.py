"""Read snes_period_hand_run.py's results: python snes_period_hand_report.py RUN

Goals and valid shots for each condition; for each pair of conditions with the same draws (same net or the goalie's
hand flipped), how many shots came out differently, shot by shot. The catching-hand pairs are compared at mirror
spots and aims (x -> -x, left <-> right), where a goalie who is an exact mirror image would give the same results;
the lane spots (10 off centre, 88-128 out from the goal line at y 268: y 140-180, slapshots aimed at that
side) are shown on their own."""
import json
import sys
from collections import defaultdict

from paths import RUNS

MIRROR_AIM = {0: 0, 1: 7, 2: 6, 3: 5, 4: 4, 5: 3, 6: 2, 7: 1, 8: 8}


def load(run):
    res = json.load(open(RUNS / run / "snes_period_hand.json"))
    by = defaultdict(dict)
    for k, v in res.items():
        if k == "meta":
            continue
        cond, x, y = k.split(",")
        by[cond][(int(x), int(y))] = v
    return by


def totals(spots, kinds=("wrist", "slap")):
    g = n = 0
    for v in spots.values():
        for key, c in v.items():
            if key.split(",")[0] in kinds:
                g += c["g"]
                n += c["n"]
    return g, n


def paired(a, b, mirror=False):
    """Shots valid in both: (both goals, a only, b only, both valid)."""
    both = ao = bo = n = 0
    for (x, y), va in a.items():
        vb = b.get((-x, y) if mirror else (x, y))
        if vb is None:
            continue
        for key, ca in va.items():
            kind, aim = key.split(",")
            cb = vb.get(f"{kind},{MIRROR_AIM[int(aim)] if mirror else aim}")
            if cb is None:
                continue
            for ra, rb in zip(ca["r"], cb["r"]):
                if ra in "01" and rb in "01":
                    n += 1
                    both += ra == rb == "1"
                    ao += ra == "1" and rb == "0"
                    bo += ra == "0" and rb == "1"
    return both, ao, bo, n


def main():
    by = load(sys.argv[1])
    print("Condition: goals / valid shots (wrist, slap)")
    for cond, spots in by.items():
        gw, nw = totals(spots, ("wrist",))
        gs, ns = totals(spots, ("slap",))
        print(f"  {cond:14} {len(spots):3} spots: wrist {gw}/{nw} ({100 * gw / max(1, nw):.2f}%), "
              f"slap {gs}/{ns} ({100 * gs / max(1, ns):.2f}%)")
    print("\nShot by shot (same draws): goals in both / first only / second only, of shots valid in both")
    for a, b, m in (("p1top", "p1top_as_p2", False), ("p2bottom", "p2bottom_as_p1", False),
                    ("p1top", "p1top_hand", True), ("p2bottom", "p2bottom_hand", True)):
        if a in by and b in by:
            both, ao, bo, n = paired(by[a], by[b], m)
            print(f"  {a} v {b}{' (mirror spots and aims)' if m else ''}: {both} / {ao} / {bo} of {n}")
    print("\nThe lane (slapshots 10 off centre, y 140-180: 88-128 out; aimed Left / Up-Left / Down-Left or the mirror):")
    for cond, spots in by.items():
        top = "top" in cond
        for side, x in (("shooter's left", -10 if top else 10), ("shooter's right", 10 if top else -10)):
            aims = (6, 7, 5) if x < 0 else (2, 1, 3)
            g = n = 0
            for y in (140, 160, 180):
                v = spots.get((x, y))
                for a in aims:
                    if v and f"slap,{a}" in v:
                        g += v[f"slap,{a}"]["g"]
                        n += v[f"slap,{a}"]["n"]
            if n:
                print(f"  {cond:14} {side:15} (x {x:+d}, aimed that way): {g}/{n} ({100 * g / n:.0f}%)")


if __name__ == "__main__":
    main()
