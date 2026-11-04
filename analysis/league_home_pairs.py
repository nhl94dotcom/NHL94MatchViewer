"""Home ice with team strength cancelled, in the Classic leagues (2026-11-04). Aggregates only. For each pair of retail teams that met both ways, half the sum of
the two home win rates minus a half is the home edge with the pair's strengths cancelled. A weighted fit of that on the pair's mean bonus points (a game's points:
the home team's home bonus + the away team's away penalty) gives the edge with no bonus and the worth of a point. Also: games with no bonus either side, home / away,
and teams' raw records against their rosters' Overall.
python analysis/league_home_pairs.py"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import league_team_study as L  # noqa: E402
from league_home_study import RETAIL_HOME_AWAY as BONUS  # noqa: E402

CLASSIC = ("classic_spring", "classic_summer", "classic_fall")
SYSTEMS = (("All_Games_GENS.csv", "Genesis", "9438f5dd_a738ea1c.bin", L.genesis), ("All_Games_SNES.csv", "SNES", "cd85e387.smc", L.snes))


def study(name, label, romfile, module):
    csv.field_size_limit(10 ** 9)
    pair, none, raw = defaultdict(lambda: [0.0, 0]), defaultdict(float), defaultdict(lambda: [0.0, 0])
    plain = 0
    with open(L.DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1" or not r["League"].lower().startswith(CLASSIC):
                continue
            h, a = r["HomeTeamAbbrev"].strip(), r["AwayTeamAbbrev"].strip()
            if h not in BONUS or a not in BONUS or h == a:
                continue
            hs, as_ = int(float(r["HomeScore"])), int(float(r["AwayScore"]))
            res = 1.0 if hs > as_ else 0.0 if hs < as_ else 0.5
            pair[(h, a)][0] += res
            pair[(h, a)][1] += 1
            raw[h][0] += res
            raw[h][1] += 1
            raw[a][0] += 1 - res
            raw[a][1] += 1
            if BONUS[h][0] == 0 and BONUS[a][1] == 0:
                plain += 1
                for key, col in (("goals", "Score"), ("shots", "Shots"), ("passes", "PassComps"), ("checks", "Checks"), ("faceoffs", "FaceoffWins")):
                    none[key + "H"] += float(r["Home" + col] or 0)
                    none[key + "A"] += float(r["Away" + col] or 0)
    ys, xs, ws = [], [], []
    for (h, a), (s, n) in pair.items():
        if h < a and (a, h) in pair:
            s2, n2 = pair[(a, h)]
            ys.append((s / n + s2 / n2 - 1) / 2)
            xs.append((BONUS[h][0] + BONUS[a][1] + BONUS[a][0] + BONUS[h][1]) / 2)
            ws.append(1 / (1 / n + 1 / n2))
    X = np.column_stack([np.ones(len(xs)), xs])
    W = np.diag(ws)
    cov = np.linalg.inv(X.T @ W @ X)
    beta = cov @ X.T @ W @ np.array(ys)
    left = np.array(ys) - X @ beta
    s2 = max(float((np.array(ws) * left ** 2).sum() / (len(ys) - 2)), 0.25)
    print(f"{label}: {len(ys)} pairs; home edge with no bonus {100 * beta[0]:+.1f} (+/- {100 * (cov[0, 0] * s2) ** .5:.1f}) points, a bonus point {100 * beta[1]:+.2f} (+/- {100 * (cov[1, 1] * s2) ** .5:.2f})")
    print(f"  no bonus either side: {plain} games; home / away " + ", ".join(f"{k} {none[k + 'H'] / none[k + 'A']:.2f}" for k in ("goals", "shots", "passes", "checks", "faceoffs")))
    rt = L.ratings(module.read_teams(L.rom(romfile)))
    ts = [t for t in raw if t in rt and raw[t][1] >= 300]
    c = np.cov([rt[t]["Overall"] for t in ts], [raw[t][0] / raw[t][1] for t in ts], aweights=[raw[t][1] for t in ts])
    print(f"  raw record against the top 12's Overall, {len(ts)} teams, games-weighted: {c[0, 1] / (c[0, 0] * c[1, 1]) ** .5:+.2f}")


if __name__ == "__main__":
    for system in SYSTEMS:
        study(*system)
