"""The game's own SNES shots (xg_calib.py runs) scored again by today's xg_snes model, at a chosen frame step, against
what the game did (2026-11-10, SNES xG for SA-1 games: the SA-1 build's shots at step 1 against the retail game's at
step 2). Per category: shots, goals, the model's expected goals, its log loss, and the same for one rate for all shots
(the baseline). The goalie's spot blurred by GOALIE_SPREAD (as for recorded games) and not (exact: the state is
known). Gentle mode (lowload), one process.

python xg_calib_rescore.py RUN STEP [SAMPLES]   (RUN: a paths.RUNS folder with xg_calib_snes.jsonl; ROM from paths)"""
import json
import math
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

from lowload import breathe, gentle
from paths import RUNS, SNES_ROM

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as xs  # noqa: E402


def score(r, data, step, spread, samples):
    xs.GOALIE_SPREAD = spread
    rng = random.Random(f"{r['tag']}:{r['px']}:{r['py']}:{r['ord']}:{spread}:{step}")
    gx, gy, gvx, gvy, w, agl, spd, aid = r["goalie"]
    d = r["aim"] if r["aim"] is not None and 0 <= r["aim"] <= 8 else 8
    tx, tz = xs.AIM[d]
    G = xs.Goalie(data, gx, gy, gvx, gvy, r["facing"], r["frame"], w, agl, spd, aid)
    return sum(xs.play_out(r["px"], r["py"], tx, r["gl"], tz, max(1.0, r["speed"] / 136), r["sha"],
                           (r["sha"] + 1) / (r["sha"] + 16), G, rng, step=step) == "goal"
               for _ in range(samples)) / samples


def ll(p, y):
    p = min(max(p, 1e-3), 1 - 1e-3)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def main():
    run, step = sys.argv[1], int(sys.argv[2])
    samples = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    gentle()
    data = xs.RomData(SNES_ROM.read_bytes())
    rows = [json.loads(line) for line in open(RUNS / run / "xg_calib_snes.jsonl")]
    shots = [r for r in rows if "goal" in r and "goalie" in r]
    by = defaultdict(list)
    t0 = time.time()
    for i, r in enumerate(shots):
        by[r["cat"]].append((r["goal"], score(r, data, step, xs.GOALIE_SPREAD_DEFAULT, samples),
                             score(r, data, step, 0.0, samples)))
        if i % 25 == 24:
            breathe()
    print(f"{run} at step {step}, {samples} draws a shot ({time.time() - t0:.0f} s), ROM {SNES_ROM.name}")
    print("| category | shots | goals | xG (blurred) | xG (exact) | log loss blurred / exact / one rate |")
    print("|---|---|---|---|---|---|")
    total = []
    for cat in sorted(by) + ["all"]:
        v = total if cat == "all" else by[cat]
        if cat != "all":
            total += v
        n, g = len(v), sum(x[0] for x in v)
        rate = g / n if n else 0
        print(f"| {cat} | {n} | {g} | {sum(x[1] for x in v):.1f} | {sum(x[2] for x in v):.1f} | "
              f"{sum(ll(x[1], x[0]) for x in v) / n:.4f} / {sum(ll(x[2], x[0]) for x in v) / n:.4f} / "
              f"{sum(ll(rate, x[0]) for x in v) / n:.4f} |")


xs.GOALIE_SPREAD_DEFAULT = xs.GOALIE_SPREAD
if __name__ == "__main__":
    main()
