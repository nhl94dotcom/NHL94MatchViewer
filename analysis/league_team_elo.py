"""Elo adjustments for the Classic teams: how many points a coach's Elo should go up or down for the team used (the user's question). Aggregates only.

The Elo is the league's own method: every game on the system in date order, a start of 1500, K 20, +7 points for the home side in the expected score, and the
winner's gain and the loser's loss both multiplied by (1 + coasting bonus). The bonus is the final unbroken stretch of regulation at a 90%+ chance of winning on lead and
time alone, with no 1-goal lead counting, as a share of the third period: 100% from the P2 buzzer, more from earlier, 10% at least. The chances come from the system's own games.

A team's adjustment is fitted on Classic games between coaches with 30+ earlier games, using each coach's Elo at the start of that league:
    P(home wins) = 1 / (1 + 10^(-(home Elo - away Elo + 7 + home team - away team) / 400))
so a value can be added to a rating as it stands, and a coach's strength can change over time. A tie counts half. A light ridge keeps rarely used teams from running off.
Zero is the average team as used, weighted by appearances. Spreads come from resampling whole leagues. Checked three ways: by predicting each later year's games from earlier
years' adjustments, against one fixed strength per coach, and with the adjustments fed back into the Elo itself.
python analysis/league_team_elo.py     prints the tables and writes reports/classic_team_elo.json (git-ignored; classic_team_guide.py reads it)"""
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
from lowload import breathe, gentle  # noqa: E402

SCALE = 400 / math.log(10)                  # Elo points per unit of the logit
K, HOME, START = 20, 7, 1500.0
MIN_SEEN, MIN_SHOWN = 30, 100
RIDGE_TEAM, RIDGE_PERSON = 2.0, 0.5         # in logit units^-2: a prior of about +/- 280 Elo on a team
DRAWS = 200
SYSTEMS = (("All_Games_GENS.csv", "Genesis"), ("All_Games_SNES.csv", "SNES"))


def run_elo(games, table=None):
    """{(league, person): (rating at the first game of that league, games before it)}, and each game's Classic flag. table: team adjustments for the expected score in Classic games."""
    R = defaultdict(lambda: START)
    seen = defaultdict(int)
    pre = {}
    for g in games:
        for who in (g["hp"], g["ap"]):
            pre.setdefault((g["league"], who), (R[who], seen[who]))
        gap = R[g["hp"]] - R[g["ap"]] + HOME
        if not table:
            g["live"] = gap
        if table and g["classic"]:
            gap += table.get(g["ht"], 0) - table.get(g["at"], 0)
        p = 1 / (1 + 10 ** (-gap / 400))
        s = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
        d = K * (1 + g["coast"]) * (s - p)
        R[g["hp"]] += d
        R[g["ap"]] -= d
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    return pre


def elo_with_tables(games, tables, share):
    """The Elo run with each year's adjustments (fitted on earlier years only), scaled by share, inside the expected score of Classic games, as a league would use them.
    Returns the log loss list over decided Classic games from 2020 between coaches with 30+ earlier games."""
    R = defaultdict(lambda: START)
    seen = defaultdict(int)
    out = []
    for g in games:
        year = date.fromordinal(g["day"]).year
        gap = R[g["hp"]] - R[g["ap"]] + HOME
        table = tables.get(year) if g["classic"] else None
        if table:
            gap += share * (table.get(g["ht"], 0) - table.get(g["at"], 0))
        p = 1 / (1 + 10 ** (-gap / 400))
        s = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
        if table and s != 0.5 and g["ht"] != g["at"] and seen[g["hp"]] >= MIN_SEEN and seen[g["ap"]] >= MIN_SEEN:
            q = min(max(p, 1e-6), 1 - 1e-6)
            out.append(-(s * math.log(q) + (1 - s) * math.log(1 - q)))
        d = K * (1 + g["coast"]) * (s - p)
        R[g["hp"]] += d
        R[g["ap"]] -= d
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    return np.array(out)


def logistic(X, y, offset, ridge, weights=None):
    w = np.ones(len(y)) if weights is None else weights
    beta = np.zeros(X.shape[1])
    for _ in range(40):
        p = 1 / (1 + np.exp(-(offset + X @ beta)))
        g = X.T @ (w * (y - p)) - ridge * beta
        H = (X * (w * p * (1 - p))[:, None]).T @ X + np.diag(ridge)
        step = np.linalg.solve(H, g)
        beta += step
        if np.abs(step).max() < 1e-6:
            break
    return beta


def design(rows, pre, teams, intercept=False):
    at = {t: i for i, t in enumerate(teams)}
    X = np.zeros((len(rows), len(teams) + (1 if intercept else 0)))
    y, offset = np.zeros(len(rows)), np.zeros(len(rows))
    for k, g in enumerate(rows):
        X[k, at[g["ht"]]] += 1
        X[k, at[g["at"]]] -= 1
        if intercept:
            X[k, -1] = 1
        offset[k] = (pre[(g["league"], g["hp"])][0] - pre[(g["league"], g["ap"])][0] + HOME) / SCALE
        y[k] = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
    return X, y, offset


def centred(beta, teams, used):
    weight = np.array([used[t] for t in teams], float)
    v = beta[:len(teams)] * SCALE
    return v - (v * weight).sum() / weight.sum()


def rated(games, pre):
    return [g for g in games if g["classic"] and g["ht"] != g["at"] and pre[(g["league"], g["hp"])][1] >= MIN_SEEN and pre[(g["league"], g["ap"])][1] >= MIN_SEEN]


def fixed_strength(rows, teams, used):
    """One strength per coach over all their Classic seasons, with no Elo: the comparison."""
    people = sorted({g["hp"] for g in rows} | {g["ap"] for g in rows})
    pi = {p: i for i, p in enumerate(people)}
    n = len(people)
    X = np.zeros((len(rows), n + len(teams) + 1))
    at = {t: n + i for i, t in enumerate(teams)}
    y = np.zeros(len(rows))
    for k, g in enumerate(rows):
        X[k, pi[g["hp"]]] += 1
        X[k, pi[g["ap"]]] -= 1
        X[k, at[g["ht"]]] += 1
        X[k, at[g["at"]]] -= 1
        X[k, -1] = 1
        y[k] = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
    ridge = np.full(X.shape[1], RIDGE_TEAM)
    ridge[:n] = RIDGE_PERSON
    ridge[-1] = 1e-6
    beta = logistic(X, y, np.zeros(len(rows)), ridge)
    return centred(beta[n:n + len(teams)], teams, used)


def study(name, label):
    C.PREFIX = None
    games, _ = C.prepare(name)
    pre = run_elo(games)
    classic = [g for g in games if g["classic"] and g["ht"] != g["at"]]
    used = defaultdict(int)
    for g in classic:
        used[g["ht"]] += 1
        used[g["at"]] += 1
    teams = sorted(used)
    rows = rated(games, pre)
    ridge = np.full(len(teams), RIDGE_TEAM)
    X, y, offset = design(rows, pre, teams)
    point = centred(logistic(X, y, offset, ridge), teams, used)
    leagues = sorted({g["league"] for g in rows})
    where = defaultdict(list)
    for i, g in enumerate(rows):
        where[g["league"]].append(i)
    rng = np.random.default_rng(94)
    draws = []
    for _ in range(DRAWS):
        w = np.zeros(len(rows))
        for lg in rng.choice(leagues, len(leagues)):
            w[where[lg]] += 1
        draws.append(centred(logistic(X, y, offset, ridge, w), teams, used))
        breathe()
    se = np.std(draws, axis=0)
    fixed = fixed_strength(classic, teams, used)
    # how much home edge is left over after the +7
    Xh, yh, oh = design(rows, pre, teams, intercept=True)
    extra = logistic(Xh, yh, oh, np.append(ridge, 1e-6))[-1] * SCALE
    # with the adjustments fed back into the Elo
    table = dict(zip(teams, point))
    for _ in range(2):
        pre2 = run_elo(games, table)
        rows2 = rated(games, pre2)
        X2, y2, o2 = design(rows2, pre2, teams)
        table = dict(zip(teams, centred(logistic(X2, y2, o2, ridge), teams, used)))
    fed_total = np.array([table[t] for t in teams])
    # how much the coaches' rating gaps are worth, against the +1 the Elo gives them
    Xw = np.column_stack([X, offset])
    weight = logistic(Xw, y, np.zeros(len(y)), np.append(ridge, 1e-6))[-1]
    # predicting later years
    days = {id(g): g["day"] for g in rows}
    years = sorted({date.fromordinal(g["day"]).year for g in rows})
    loss = {"none": [], "table": [], "live none": [], "live table": []}
    tables = {}
    for yr in (v for v in years if v >= 2020):
        cut = date(yr, 1, 1).toordinal()
        early = [g for g in rows if days[id(g)] < cut]
        late = [g for g in rows if cut <= days[id(g)] < date(yr + 1, 1, 1).toordinal() and g["hs"] != g["as"]]
        if len(early) < 500 or not late:
            continue
        Xe, ye, oe = design(early, pre, teams)
        b = logistic(Xe, ye, oe, ridge)
        tables[yr] = dict(zip(teams, centred(b, teams, used)))
        Xl, yl, ol = design(late, pre, teams)
        live = np.array([g["live"] for g in late]) / SCALE
        for key, z in (("none", ol), ("table", ol + Xl @ b), ("live none", live), ("live table", live + Xl @ b)):
            p = np.clip(1 / (1 + np.exp(-z)), 1e-6, 1 - 1e-6)
            loss[key].extend(-(yl * np.log(p) + (1 - yl) * np.log(1 - p)))
        breathe()
    a, b = np.array(loss["table"]), np.array(loss["none"])
    d = a - b
    la, lb = np.array(loss["live table"]), np.array(loss["live none"])
    ld = la - lb
    base = elo_with_tables(games, tables, 0.0)
    inside = {}
    for share in (0.25, 0.5, 0.75, 1.0):
        run = elo_with_tables(games, tables, share)
        inside[str(share)] = [float(run.mean()), float((run - base).mean()), float((run - base).std() / len(base) ** .5)]
        breathe()
    print(f"  Inside the running Elo, each year's adjustments from earlier years ({len(base)} games): none {base.mean():.4f}; " + "; ".join(f"x {k}: {v[0]:.4f} ({v[1]:+.4f} +- {v[2]:.4f})" for k, v in inside.items()))
    shown = [t for t in teams if used[t] >= MIN_SHOWN]
    idx = [teams.index(t) for t in shown]
    print(f"\n{label}: {len(classic)} Classic games, {len(rows)} with both coaches at 30+ earlier games; home edge left after the +{HOME}: {extra:+.0f} points")
    print(f"  Rating gaps are worth {weight:.2f} of their face value in these games")
    print(f"  Later years predicted ({len(d)} games), ratings at the league's start: no adjustment {b.mean():.4f}, with adjustments {a.mean():.4f}, difference {d.mean():+.4f} +- {d.std() / len(d) ** .5:.4f}")
    print(f"  The same, ratings as they stood at each game: no adjustment {lb.mean():.4f}, with adjustments {la.mean():.4f}, difference {ld.mean():+.4f} +- {ld.std() / len(ld) ** .5:.4f}")
    print(f"  Against one fixed strength per coach: {np.corrcoef(point[idx], fixed[idx])[0, 1]:+.2f}; fed back into the Elo: {np.corrcoef(point[idx], fed_total[idx])[0, 1]:+.2f}, typical change {np.abs(point[idx] - fed_total[idx]).mean():.0f} points")
    print("  Team  Adjustment  +/-  Fixed strength  Fed back  Games")
    for i in sorted(range(len(teams)), key=lambda i: -point[i]):
        t = teams[i]
        print(f"  {t:4} {point[i]:+6.0f}  {se[i]:4.0f}  {fixed[i]:+6.0f}  {fed_total[i]:+6.0f}  {used[t]:5}")
    return {"teams": {t: {"adj": float(point[i]), "se": float(se[i]), "fixed": float(fixed[i]), "fed": float(fed_total[i]), "games": used[t]} for i, t in enumerate(teams)},
            "extra_home": float(extra), "weight": float(weight), "games": len(rows), "test_games": len(d), "none": float(b.mean()), "with": float(a.mean()), "diff": float(d.mean()), "diff_se": float(d.std() / len(d) ** .5),
            "live_none": float(lb.mean()), "live_with": float(la.mean()), "live_diff": float(ld.mean()), "live_diff_se": float(ld.std() / len(ld) ** .5),
            "inside_none": float(base.mean()), "inside_games": len(base), "inside": inside}


def main():
    gentle()
    out = {label: study(name, label) for name, label in SYSTEMS}
    path = Path(__file__).resolve().parents[1] / "reports" / "classic_team_elo.json"
    path.write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main()
