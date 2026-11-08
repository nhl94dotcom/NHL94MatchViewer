"""Is the shooting-percentage edge going down the screen bigger at the top level? (2026-11-08, a community member's
question: pass shots going down may be easier, and A players may use them more.) Aggregates only.

The league result databases give each team's goals and shots on goal by period. Home attacks up in periods 1 and 3 and
down in period 2; Away the reverse (overtime left out). For each Classic league level (its name gives it), regular
season and playoffs: goals per shot on goal going down and going up, and their ratio, pooled over Home and Away (so
each direction mixes periods and sides). Uncertainty: a bootstrap over games. Both systems.

python analysis/direction_by_level.py"""
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league_ratings as LR  # noqa: E402
from league_elo_levels import rank_of  # noqa: E402

DATA = Path.home() / "NHL94_League_Data"


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def games(path):
    out = defaultdict(list)
    for r in csv.DictReader(open(path, encoding="utf-8", errors="replace")):
        rk = rank_of(LR.level_of(r["League"]))
        if rk is None:
            continue
        level = "A" if rk == 1 else "B" if rk <= 2 else "C" if rk <= 3 else "D and lower"
        v = {}
        for side in ("Home", "Away"):
            for p in (1, 2, 3):
                v[side, p] = (num(r.get(f"{side}GoalsP{p}")), num(r.get(f"{side}ShotsP{p}")))
        if any(g is None or s is None for g, s in v.values()):
            continue
        down = (v["Home", 2], v["Away", 1], v["Away", 3])
        up = (v["Home", 1], v["Home", 3], v["Away", 2])
        g = (sum(a for a, _ in down), sum(b for _, b in down), sum(a for a, _ in up), sum(b for _, b in up))
        if g[1] and g[3]:
            out[level].append(g)
            out["all"].append(g)
    return out


def ratio(rows):
    gd, sd, gu, su = (sum(x[i] for x in rows) for i in range(4))
    return gd / sd, gu / su, (gd / sd) / (gu / su)


def main():
    rnd = random.Random(1)
    for name, sysname in (("All_Games_GENS.csv", "Genesis"), ("All_Games_SNES.csv", "SNES")):
        by = games(DATA / name)
        print(f"\n{sysname} (Classic leagues):")
        for level in ("A", "B", "C", "D and lower", "all"):
            rows = by.get(level)
            if not rows:
                continue
            down, up, r = ratio(rows)
            boot = sorted(ratio([rows[rnd.randrange(len(rows))] for _ in rows])[2] for _ in range(300))
            print(f"  {level:12} {len(rows):6} games: goals per shot on goal going down {down:.1%}, up {up:.1%}; "
                  f"down / up {r:.3f} (95% {boot[7]:.3f}-{boot[292]:.3f})")


if __name__ == "__main__":
    main()
