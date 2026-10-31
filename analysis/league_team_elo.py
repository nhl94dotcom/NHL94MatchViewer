"""Elo adjustments for the retail teams (2026-10-30; the user's question: how much should a player's Elo go up or down
for the team he uses?). The Classic games of league_team_study.py, but fitted on the result in Elo's own units:
    P(home wins) = 1 / (1 + 10^(-(home person - away person + home team - away team + home edge) / 400))
(a tie counts half), one strength per person over all their Classic seasons, by maximum likelihood (Newton steps; a
light ridge keeps the rarely used teams from running off). A team's number is the Elo points its user gains from it
against the average team. Checked a second way: each person's Elo at the start of the league season (all his games on
that system, league_flow_study's K) in place of the fitted person strengths, its weight fitted too. Standard errors
from the fit (each game counted once, so a little too narrow). Teams with under MIN_GAMES games are listed apart.
The numbers are centred on the games-weighted average of the teams shown.
python analysis/league_team_elo.py"""
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from league_team_study import games, pre_league_elo, rom  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from systems import genesis, snes  # noqa: E402

SCALE = 400 / math.log(10)                  # Elo points per unit of the logit
MIN_GAMES = 300
RIDGE_TEAM = 2.0                            # in logit units^-2: a prior of about +/- 280 Elo on a team
RIDGE_PERSON = 0.5


def logistic_fit(X, y, ridge):
    beta = np.zeros(X.shape[1])
    for _ in range(50):
        z = X @ beta
        p = 1 / (1 + np.exp(-z))
        g = X.T @ (y - p) - ridge * beta
        H = (X * (p * (1 - p))[:, None]).T @ X + np.diag(ridge)
        step = np.linalg.solve(H, g)
        beta += step
        if np.abs(step).max() < 1e-7:
            break
    cov = np.linalg.inv(H)
    return beta, np.sqrt(np.diag(cov))


def fit(rows, teams, elo=None):
    people = [] if elo else sorted({g[1] for g in rows} | {g[2] for g in rows})
    pi = {p: i for i, p in enumerate(people)}
    off = len(people) + (1 if elo else 0)
    ti = {t: off + i for i, t in enumerate(teams)}
    n = off + len(teams) + 1
    X = np.zeros((len(rows), n))
    y = np.zeros(len(rows))
    for k, g in enumerate(rows):
        if elo:
            X[k, 0] = (elo[(g[0], g[1])][0] - elo[(g[0], g[2])][0]) / SCALE
        else:
            X[k, pi[g[1]]] += 1
            X[k, pi[g[2]]] -= 1
        X[k, ti[g[3]]] += 1
        X[k, ti[g[4]]] -= 1
        X[k, -1] = 1
        y[k] = 1.0 if g[5] > g[6] else 0.0 if g[5] < g[6] else 0.5
    ridge = np.full(n, 1e-6)
    ridge[:len(people)] = RIDGE_PERSON
    ridge[off:off + len(teams)] = RIDGE_TEAM
    beta, se = logistic_fit(X, y, ridge)
    return ({t: beta[ti[t]] * SCALE for t in teams}, {t: se[ti[t]] * SCALE for t in teams}, beta[-1] * SCALE,
            beta[0] if elo else None)


def study(csv_name, label, teams_rom, k_elo):
    retail = {t["abbr"] for t in teams_rom} - {"ASE", "ASW"}
    names = {t["abbr"]: t["name"] for t in teams_rom}
    names["NYI"], names["NYR"] = "NY Islanders", "NY Rangers"
    rows = games(csv_name, retail)
    teams = sorted({g[3] for g in rows} | {g[4] for g in rows})
    used = defaultdict(int)
    for g in rows:
        used[g[3]] += 1
        used[g[4]] += 1
    eff, se, home, _ = fit(rows, teams)
    elo = pre_league_elo(csv_name, k_elo)
    rows_e = [g for g in rows if elo.get((g[0], g[1]), (0, 0))[1] >= 30 and elo.get((g[0], g[2]), (0, 0))[1] >= 30]
    teams_e = sorted({g[3] for g in rows_e} | {g[4] for g in rows_e})
    eff_e, _, _, w_elo = fit(rows_e, teams_e, elo)
    shown = [t for t in teams if used[t] >= MIN_GAMES]
    W = sum(used[t] for t in shown)
    c = sum(eff[t] * used[t] for t in shown) / W
    ce = sum(eff_e.get(t, 0) * used[t] for t in shown) / W
    print(f"\n{label}: {len(rows)} Classic games; home edge {home:+.0f} Elo points; the Elo way's weight on the "
          f"pre-season ratings {w_elo:.2f} ({len(rows_e)} games)")
    print("  Team                Elo adjustment (+/- 1 s.e.)   the Elo way   games")
    for t in sorted(shown, key=lambda t: -eff[t]):
        print(f"  {names[t]:18} {eff[t] - c:+5.0f} (+/- {se[t]:3.0f})          {eff_e.get(t, float('nan')) - ce:+5.0f}"
              f"      {used[t]:5}")
    rare = [t for t in teams if used[t] < MIN_GAMES]
    print("  Too few games: " + ", ".join(f"{names[t]} {eff[t] - c:+.0f} (+/- {se[t]:.0f}, {used[t]})"
                                         for t in sorted(rare, key=lambda t: -used[t])))
    print("  Unused: " + ", ".join(names[t] for t in sorted(retail - set(teams))))
    agree = np.corrcoef([eff[t] for t in shown], [eff_e.get(t, 0) for t in shown])[0, 1]
    print(f"  The two ways agree: correlation {agree:+.2f}")


def main():
    study("All_Games_GENS.csv", "GENESIS", genesis.read_teams(rom("9438f5dd_a738ea1c.bin")), 16)
    study("All_Games_SNES.csv", "SNES", snes.read_teams(rom("cd85e387.smc")), 24)


if __name__ == "__main__":
    main()
