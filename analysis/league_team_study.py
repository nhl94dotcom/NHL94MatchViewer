"""Which teams are strongest in the Classic leagues, with the people playing them taken out (2026-10-30). The user's
databases outside the repository (%USERPROFILE%\\NHL94_League_Data), aggregates only (team names, no players).

People pick or are given teams to balance a league (in the Classic drafts the people thought weaker pick first), so
a team's raw record says little. Every Classic game (both teams retail ones, in leagues that play the retail
rosters) is fitted at once, two ways:
- "person": home goals - away goals = the home person's strength - the away person's + the home team's - the away
  team's + home edge, one strength per person over all their Classic seasons, by least squares. A team is judged by
  how the same people do with it against their other teams.
- "elo": the same with each person's strength replaced by his Elo rating (league_flow_study's, over all his games on
  that system, K 16 / 24) at the start of that league season, times one fitted factor; games between people with 30+
  earlier games. The draft can't touch that rating, and it follows people who improve.
(A first version gave each person a strength for each league season. In a season each person plays one team, so that
couldn't tell the person from the team, and it rated teams by who drafted them: the teams the strong people are left
with came out strongest. Dropped.)
The same "person" fit on the result (win 1, tie 1/2, loss 0) gives the win-rate version. The spread comes from
refitting on leagues drawn at random with replacement (bootstrap, 100 draws); the reliability from fitting two random
halves of the leagues apart and comparing (teams with MIN_GAMES+ games in each). Teams with under MIN_GAMES games
aren't shown or used in the rating comparison.

Then the team strengths against the ROM's ratings (the retail Genesis ROM and NHL94_Classic): the starting
goalie's Agility (the higher-rated goalie) and the top 12 skaters' mean Speed, Shot Power, Shot Accuracy, Agility,
Weight, Checking and Overall.
python analysis/league_team_study.py"""
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from systems import genesis, snes  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from league_flow_study import load, result  # noqa: E402

DATA = Path.home() / "NHL94_League_Data"
ROMS = [Path(__file__).resolve().parents[1] / "roms", Path.home() / "Documents" / "NHL94 Viewer" / "roms"]
SKATER = {"Weight": 0, "Agility": 1, "Speed": 2, "Shot Power": 5, "Checking": 6, "Shot Accuracy": 9}
RIDGE = 1.0
DRAWS = 100
MIN_GAMES = 300


def rom(name):
    return next(d / name for d in ROMS if (d / name).exists())


def games(csv_name, retail):
    csv.field_size_limit(10 ** 9)
    rows = []
    with open(DATA / csv_name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1" or "classic" not in r["League"].lower():
                continue
            try:
                hs, as_ = int(r["HomeScore"]), int(r["AwayScore"])
            except ValueError:
                continue
            rows.append((r["League"], r["HomePlayer"].strip().lower(), r["AwayPlayer"].strip().lower(),
                         r["HomeTeamAbbrev"].strip(), r["AwayTeamAbbrev"].strip(), hs, as_))
    share = defaultdict(lambda: [0, 0])
    for g in rows:
        share[g[0]][0] += g[3] in retail and g[4] in retail
        share[g[0]][1] += 1
    keep = {lg for lg, (a, n) in share.items() if a >= 0.95 * n}
    return [g for g in rows if g[0] in keep and g[3] in retail and g[4] in retail and g[3] != g[4]]


def pre_league_elo(csv_name, k):
    """{(league, person): (rating at his first game of that league, games before it)}, over all games in date order."""
    R = defaultdict(lambda: 1500.0)
    seen = defaultdict(int)
    out = {}
    for g in load(csv_name):
        for who in (g["hp"], g["ap"]):
            out.setdefault((g["league"], who), (R[who], seen[who]))
        p = 1 / (1 + 10 ** (-(R[g["hp"]] - R[g["ap"]]) / 400))
        d = k * (result(g) - p)
        R[g["hp"]] += d
        R[g["ap"]] -= d
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    return out


def fit(rows, teams, y_of, elo=None):
    """Team strengths (mean 0) and the home edge; people as fixed strengths, or (elo given) by their pre-league Elo."""
    people = [] if elo else sorted({g[1] for g in rows} | {g[2] for g in rows})
    pi = {p: i for i, p in enumerate(people)}
    off = len(people) + (1 if elo else 0)
    ti = {t: off + i for i, t in enumerate(teams)}
    n = off + len(teams) + 1
    X = np.zeros((len(rows), n))
    y = np.zeros(len(rows))
    for k, g in enumerate(rows):
        if elo:
            X[k, 0] = (elo[(g[0], g[1])][0] - elo[(g[0], g[2])][0]) / 100
        else:
            X[k, pi[g[1]]] += 1
            X[k, pi[g[2]]] -= 1
        X[k, ti[g[3]]] += 1
        X[k, ti[g[4]]] -= 1
        X[k, -1] = 1                                  # home edge
        y[k] = y_of(g)
    A = X.T @ X
    d = np.arange(n - 1)
    A[d, d] += 1e-6                                   # people and teams: only differences are fixed
    beta = np.linalg.solve(A, X.T @ y)
    t = beta[off:-1]
    return t - t.mean(), beta[-1]


def ratings(teams_rom):
    out = {}
    for t in teams_rom:
        goalies = sorted((p for p in t["players"] if p["g"]), key=lambda p: -p["ovr"])
        skaters = sorted((p for p in t["players"] if not p["g"]), key=lambda p: -p["ovr"])[:12]
        r = {k: float(np.mean([p["a"][i] for p in skaters])) for k, i in SKATER.items()}
        r["Overall"] = float(np.mean([p["ovr"] for p in skaters]))
        r["Goalie Agility"] = goalies[0]["a"][1] if goalies else float("nan")
        out[t["abbr"]] = r
    return out


def study(csv_name, label, teams_rom, k_elo):
    retail = {t["abbr"] for t in teams_rom} - {"ASE", "ASW"}
    rows = games(csv_name, retail)
    elo = pre_league_elo(csv_name, k_elo)
    rows_elo = [g for g in rows if elo.get((g[0], g[1]), (0, 0))[1] >= 30 and elo.get((g[0], g[2]), (0, 0))[1] >= 30]
    teams_elo = sorted({g[3] for g in rows_elo} | {g[4] for g in rows_elo})
    teams = sorted({g[3] for g in rows} | {g[4] for g in rows})
    gd = lambda g: g[5] - g[6]
    res = lambda g: 1.0 if g[5] > g[6] else 0.0 if g[5] < g[6] else 0.5
    t_gd, home_gd = fit(rows, teams, gd)
    t_w, home_w = fit(rows, teams, res)
    t_e, _ = fit(rows_elo, teams_elo, gd, elo)
    t_e = dict(zip(teams_elo, t_e))
    leagues = sorted({g[0] for g in rows})
    by_league = defaultdict(list)
    for g in rows:
        by_league[g[0]].append(g)
    rnd = random.Random(94)
    boot = []
    for _ in range(DRAWS):
        sample = [g for lg in (rnd.choice(leagues) for _ in leagues) for g in by_league[lg]]
        present = sorted({g[3] for g in sample} | {g[4] for g in sample})
        tb, _ = fit(sample, present, gd)
        boot.append({t: v for t, v in zip(present, tb)})
    raw = defaultdict(lambda: [0.0, 0])
    games_n = defaultdict(int)
    for g in rows:
        raw[g[3]][0] += res(g)
        raw[g[4]][0] += 1 - res(g)
        raw[g[3]][1] += 1
        raw[g[4]][1] += 1
    print(f"\n{label}: {len(rows)} Classic games in {len(leagues)} leagues; home edge {home_gd:+.2f} goals, "
          f"{100 * (home_w - 0.5):+.1f} points of win rate")
    print(f"  Team: strength in goals a game against an average team (90% range), the same as win-rate points, "
          f"by pre-season Elo instead ({len(rows_elo)} games), raw win %, games")
    order = sorted(range(len(teams)), key=lambda i: -t_gd[i])
    for i in order:
        t = teams[i]
        if raw[t][1] < MIN_GAMES:
            continue
        vals = sorted(b[t] for b in boot if t in b)
        lo, hi = vals[int(0.05 * len(vals))], vals[int(0.95 * len(vals)) - 1]
        print(f"  {t:4} {t_gd[i]:+.2f} ({lo:+.2f} to {hi:+.2f})  {100 * t_w[i]:+5.1f}  elo {t_e.get(t, float('nan')):+.2f}  "
              f"raw {100 * raw[t][0] / raw[t][1]:4.1f}%  {raw[t][1]:5}")
    rt = ratings(teams_rom)
    print("  Correlation of the team strength (goals) with the ROM's ratings, over the teams (games-weighted):")
    halves = []
    for _ in range(20):
        lg = leagues[:]
        rnd.shuffle(lg)
        a, b = set(lg[::2]), set(lg[1::2])
        ra, rb = [g for g in rows if g[0] in a], [g for g in rows if g[0] in b]
        ta = sorted({g[3] for g in ra} | {g[4] for g in ra})
        tb = sorted({g[3] for g in rb} | {g[4] for g in rb})
        ea, _ = fit(ra, ta, gd)
        eb, _ = fit(rb, tb, gd)
        da, db = dict(zip(ta, ea)), dict(zip(tb, eb))
        na, nb = defaultdict(int), defaultdict(int)
        for g in ra:
            na[g[3]] += 1
            na[g[4]] += 1
        for g in rb:
            nb[g[3]] += 1
            nb[g[4]] += 1
        common = [t for t in teams if na[t] >= MIN_GAMES and nb[t] >= MIN_GAMES]
        if len(common) >= 6:
            halves.append(np.corrcoef([da[t] for t in common], [db[t] for t in common])[0, 1])
    common = [t for t in teams if raw[t][1] >= MIN_GAMES and t in t_e]
    print(f"  The two ways agree (teams with {MIN_GAMES}+ games): correlation "
          f"{np.corrcoef([t_gd[teams.index(t)] for t in common], [t_e[t] for t in common])[0, 1]:+.2f}")
    print(f"  Reliability: two halves of the leagues fitted apart agree with correlation {np.mean(halves):+.2f} "
          f"(mean of {len(halves)} splits)")
    teams = [t for t in teams if raw[t][1] >= MIN_GAMES]
    t_gd = [dict(zip(sorted({g[3] for g in rows} | {g[4] for g in rows}), t_gd))[t] for t in teams]
    w = np.array([raw[t][1] for t in teams], float)
    print("  (person / elo)")
    for k in list(SKATER) + ["Overall", "Goalie Agility"]:
        x = np.array([rt[t][k] for t in teams])
        cs = []
        for y in (np.array(t_gd), np.array([t_e.get(t, 0.0) for t in teams])):
            xm, ym = np.average(x, weights=w), np.average(y, weights=w)
            cs.append(np.average((x - xm) * (y - ym), weights=w) / np.sqrt(np.average((x - xm) ** 2, weights=w) *
                                                                         np.average((y - ym) ** 2, weights=w)))
        print(f"    {k:15} {cs[0]:+.2f} / {cs[1]:+.2f}")
    X = np.array([[rt[t]["Shot Power"], rt[t]["Speed"], rt[t]["Goalie Agility"], 1.0] for t in teams])
    sw = np.sqrt(w / w.mean())
    beta, *_ = np.linalg.lstsq(X * sw[:, None], np.array(t_gd) * sw, rcond=None)
    pred = X @ beta
    r2 = 1 - np.average((np.array(t_gd) - pred) ** 2, weights=w) / np.average(
        (np.array(t_gd) - np.average(t_gd, weights=w)) ** 2, weights=w)
    print(f"  Fitted together: goals a game = {beta[0]:+.2f} x mean Shot Power {beta[1]:+.2f} x mean Speed "
          f"{beta[2]:+.2f} x goalie Agility + const; R^2 {r2:.2f}")


def main():
    study("All_Games_GENS.csv", "GENESIS", genesis.read_teams(rom("9438f5dd_a738ea1c.bin")), 16)
    study("All_Games_SNES.csv", "SNES", snes.read_teams(rom("cd85e387.smc")), 24)


if __name__ == "__main__":
    main()
