"""Testing the league Elo's K and coasting bonus (2026-11-04, the user). Aggregates only.
Every setting runs the league's method (league_team_elo.py) over all its games in order: a 1500 start, +7 for home, the team table (reports/classic_team_elo.json) in the expected score where the league
uses it, and the winner's gain and loser's loss raised by the bonus. Scored by log loss on the next game, decided games from 2020 between coaches with 30+ earlier games, on all games and Classic games, with how much a
rating gap has been worth (1.00 means Elo's expectations were the right size). Bonus versions: the league's (seconds / 600, at least 10%); half that; none; capped at 100%.
The team table was fitted on these years with K 20, which flatters every setting a little and K 20 a little more.
python analysis/league_elo_k.py"""
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
import coach_rating as C  # noqa: E402
import league_team_elo as E  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

KS = (4, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32)
BONUSES = {"league": lambda c: c, "capped at 100%": lambda c: min(c, 1.0), "half size": lambda c: c / 2, "none": lambda c: 0.0}
HOME, START, MIN_SEEN = 7, 1500.0, 30
FIRST = date(2020, 1, 1).toordinal()
SYSTEMS = (("All_Games_GENS.csv", "Genesis"), ("All_Games_SNES.csv", "SNES"))


def run(games, table, k, bonus):
    R = defaultdict(lambda: START)
    seen = defaultdict(int)
    gaps, won, classic = [], [], []
    for g in games:
        gap = R[g["hp"]] - R[g["ap"]] + HOME
        if g["wide"]:
            gap += table.get(g["ht"], 0) - table.get(g["at"], 0)
        p = 1 / (1 + 10 ** (-gap / 400))
        s = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
        if g["day"] >= FIRST and s != 0.5 and seen[g["hp"]] >= MIN_SEEN and seen[g["ap"]] >= MIN_SEEN:
            gaps.append(gap)
            won.append(s)
            classic.append(g["classic"])
        d = k * (1 + bonus(g["coast"])) * (s - p)
        R[g["hp"]] += d
        R[g["ap"]] -= d
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    x = np.array(gaps) * math.log(10) / 400
    return x, np.array(won), np.array(classic), R, seen


def loss(x, y):
    p = np.clip(1 / (1 + np.exp(-x)), 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def main():
    gentle()
    tables = json.loads((Path(__file__).resolve().parents[1] / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    out = {}
    for name, label in SYSTEMS:
        games = E.load_games(name)
        table = {t: v["adj"] for t, v in tables[label]["teams"].items()}
        print(f"\n{label}: {len(games)} games; log loss all / Classic, and what a rating gap is worth")
        res = {}
        for bname, bonus in BONUSES.items():
            for k in KS:
                x, y, c, _, _ = run(games, table, k, bonus)
                res[(bname, k)] = (loss(x, y), loss(x[c], y[c]), C.scale_for(x, y), C.scale_for(x[c], y[c]))
                breathe()
            print(f"  {bname}: " + "; ".join(f"K{k} {res[(bname, k)][0]:.4f}/{res[(bname, k)][1]:.4f}/{res[(bname, k)][2]:.2f}" for k in KS), flush=True)
        current = run(games, table, 20, BONUSES["league"])
        for scope, key in (("all games", 0), ("Classic games", 1)):
            best = min(res, key=lambda r: res[r][key])
            xb, yb, cb, _, _ = run(games, table, best[1], BONUSES[best[0]])
            m = np.ones(len(yb), dtype=bool) if key == 0 else cb
            a = -(yb[m] * np.log(np.clip(1 / (1 + np.exp(-xb[m])), 1e-6, 1)) + (1 - yb[m]) * np.log(np.clip(1 - 1 / (1 + np.exp(-xb[m])), 1e-6, 1)))
            xc, yc, cc = current[:3]
            mc = np.ones(len(yc), dtype=bool) if key == 0 else cc
            b = -(yc[mc] * np.log(np.clip(1 / (1 + np.exp(-xc[mc])), 1e-6, 1)) + (1 - yc[mc]) * np.log(np.clip(1 - 1 / (1 + np.exp(-xc[mc])), 1e-6, 1)))
            d = a - b
            print(f"  best on {scope}: K {best[1]}, bonus {best[0]}: {res[best][key]:.4f}, the league's K 20 {b.mean():.4f}; difference {d.mean():+.4f} +- {d.std() / len(d) ** .5:.4f}; rating gap worth {res[best][2 + key]:.2f}, at K 20 {res[('league', 20)][2 + key]:.2f}")
        out[label] = {f"{a}|{k}": v for (a, k), v in res.items()}
    (Path(__file__).resolve().parents[1] / "reports" / "league_elo_k.json").write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main()
