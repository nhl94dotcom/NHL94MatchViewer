"""Skater ratings against what players did in the leagues' own results (2026-10-30). The Classic leagues play the
retail rosters, so each player's ratings come from the ROM (Genesis nhl94.bin, SNES NHL94_Classic); his games come from
the user's databases (%USERPROFILE%\\NHL94_League_Data, outside the repository; player lines: Genesis goals, assists,
points, shots, checks, penalty minutes, ice time; SNES goals, assists, points, shots, penalty minutes; penalty lists
by player). Aggregates only.
1. Penalties by roster Aggression: the Genesis working Aggression wraps at 16 (GENESIS_MECHANICS 8.2: rating 4 plays
   like 1, 3 and 6 the most penalised); on the SNES a "cold" rating plays maxed (SNES_MECHANICS 2.2, 8.1).
2. Which ratings go with scoring: within each team and position (forwards, defencemen), each player's goals, points,
   shots a game and shooting % against his ratings (the team's other players at that position as the baseline, so the
   team, its opponents and the people playing it cancel), a least-squares fit on all ratings at once.
3. Genesis checks a game against Weight and Checking, the same way (the weight bug: a person's light checker knocks
   heavier men down, a heavy one rarely: GENESIS_MECHANICS 7.2).
python analysis/league_player_study.py"""
import ast
import csv
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from systems import genesis, snes  # noqa: E402

DATA = Path.home() / "NHL94_League_Data"
ROMS = [Path(__file__).resolve().parents[1] / "roms", Path.home() / "Documents" / "NHL94 Viewer" / "roms"]
NAMES = ["Weight", "Agility", "Speed", "Off. Aware", "Def. Aware", "Shot Power", "Checking", "Handed", "Stick Hand",
         "Shot Acc", "Endurance", "Shoot bias", "Pass Acc", "Aggression"]
USE = [0, 1, 2, 3, 5, 6, 8, 9, 12]           # ratings in the fit (Def. Awareness, Endurance etc. left out)
MIN_GAMES = 150


def rom(name):
    return next(d / name for d in ROMS if (d / name).exists())


def collect(csv_name, ratings, genesis_lines):
    P = defaultdict(lambda: defaultdict(float))
    csv.field_size_limit(10 ** 9)
    with open(DATA / csv_name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1" or "classic" not in r["League"].lower():
                continue
            for side in ("Home", "Away"):
                team = r[side + "TeamAbbrev"].strip()
                try:
                    lines = ast.literal_eval(r[side + "Players"]) if r[side + "Players"] else []
                    pens = ast.literal_eval(r[side + "Penalties"]) if r[side + "Penalties"] else []
                except (ValueError, SyntaxError):
                    continue
                for p in lines:
                    name = str(p[1]).lower()
                    if name not in ratings:
                        continue
                    if genesis_lines and (len(p) < 10 or p[9] < 600):   # regulars: 10+ minutes of ice time
                        continue
                    s = P[(team, name)]
                    s["games"] += 1
                    s["pos"] = 1.0 if p[2] == "D" else 0.0
                    s["goals"] += p[3]
                    s["points"] += p[5]
                    s["shots"] += p[6]
                    if genesis_lines:
                        s["checks"] += p[7]
                for q in pens:
                    name = str(q[4]).lower()
                    if (team, name) in P:
                        P[(team, name)]["penalties"] += 1
    return {k: v for k, v in P.items() if v["games"] >= MIN_GAMES}


def aggression(P, ratings, label, genesis_lines):
    by = defaultdict(lambda: [0.0, 0.0, 0.0, 0])
    for (team, name), s in P.items():
        a = ratings[name][13]
        b = by[a]
        b[0] += s["penalties"]
        b[1] += s["games"]
        b[2] += s.get("checks", 0)
        b[3] += 1
    print(f"\n{label}: penalties by roster Aggression ({len(P)} player-teams with {MIN_GAMES}+ games)")
    base = None
    for a in sorted(by):
        pen, g, chk, n = by[a]
        per = 100 * pen / g
        base = base or per
        extra = f", {100 * pen / chk:.2f} per 100 checks" if genesis_lines and chk else ""
        print(f"  Aggression {a}: {n:3} players, {per:.2f} penalties per 100 games ({per / base:.2f}x rating "
              f"{min(by)}){extra}")


def fit(P, ratings, label, stats):
    print(f"\n{label}: within team and position, per rating step (all ratings fitted together; +/- 2 s.e.)")
    for pos, pname in ((0.0, "forwards"), (1.0, "defencemen")):
        rows = [(k, s) for k, s in P.items() if s["pos"] == pos]
        groups = defaultdict(list)
        for k, s in rows:
            groups[k[0]].append((k, s))
        for stat, f in stats:
            X, y, w = [], [], []
            for team, members in groups.items():
                if len(members) < 3:
                    continue
                xs = np.array([[ratings[k[1]][i] for i in USE] for k, _ in members], float)
                ys = np.array([f(s) for _, s in members], float)
                ws = np.array([s["games"] for _, s in members], float)
                xs -= np.average(xs, axis=0, weights=ws)
                ys -= np.average(ys, weights=ws)
                X.append(xs)
                y.append(ys)
                w.append(ws)
            if not X:
                continue
            X, y, w = np.vstack(X), np.concatenate(y), np.concatenate(w)
            sw = np.sqrt(w / w.mean())
            beta, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
            res = (y - X @ beta) * sw
            dof = max(1, len(y) - len(USE))
            cov = np.linalg.pinv((X * sw[:, None]).T @ (X * sw[:, None])) * (res @ res / dof)
            se = np.sqrt(np.diag(cov))
            parts = [f"{NAMES[USE[i]]} {beta[i]:+.3f}" + ("*" if abs(beta[i]) > 2 * se[i] else "")
                     for i in range(len(USE))]
            print(f"  {pname:10} {stat:13} ({len(y)} players): " + ", ".join(parts))
    print("  (* = more than two standard errors from zero)")


def main():
    for csv_name, label, teams, gl in (("All_Games_GENS.csv", "GENESIS", genesis.read_teams(rom("9438f5dd_a738ea1c.bin")), True),
                                       ("All_Games_SNES.csv", "SNES", snes.read_teams(rom("cd85e387.smc")), False)):
        ratings = {p["name"].lower(): p["a"] for t in teams for p in t["players"] if not p["g"]}
        P = collect(csv_name, ratings, gl)
        aggression(P, ratings, label, gl)
        stats = [("goals/game", lambda s: s["goals"] / s["games"]), ("points/game", lambda s: s["points"] / s["games"]),
                 ("shots/game", lambda s: s["shots"] / s["games"]),
                 ("shooting %", lambda s: 100 * s["goals"] / s["shots"] if s["shots"] else 0)]
        if gl:
            stats.append(("checks/game", lambda s: s["checks"] / s["games"]))
        fit(P, ratings, label, stats)


if __name__ == "__main__":
    main()
