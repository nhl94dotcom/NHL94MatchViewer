"""What each skater rating does at both ends, from the Classic leagues' games (2026-11-11, the user: the defencemen's
league value is offence only, and forwards defend too; RATING_VALUES "Defence").

Every regular-season team-game of the Classic leagues (simulated games left out) is a row: that team's goals. Inputs:
its lineup (the 3 forwards and 2 defencemen with the most ice time, their stored ratings averaged by position, from the
league's ROM; the goalie with the most time, his Agility) and the opponent's lineup the same way, home ice, and a
fixed effect for the team's coach (his attack) and for the opponent's coach (his defence), so a rating is measured by
the same coaches using different players. A team's own ratings give each rating's worth in goals FOR, the opponent's
its worth in goals AGAINST (how much a defender's rating cuts the other team's goals); FOR minus AGAINST is the total,
in goal difference a game. One player's step: the position average moves by 1/3 (forwards) or 1/2 (defencemen).

Checked by fitting on the even-numbered leagues (by name) and predicting the odd ones, against the coaches alone.
Prints the tables for RATING_VALUES; names nobody.

python analysis/defence_value.py [genesis|snes]"""
import ast
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
import league_value as L  # noqa: E402
from league_player_study import rom  # noqa: E402
from systems import genesis  # noqa: E402

DATA = Path.home() / "NHL94_League_Data"
NAMES = ["Weight", "Agility", "Speed", "Off. Aware", "Def. Aware", "Shot Power", "Checking", "Stickhandling",
         "Shot Acc", "Pass Acc"]
IDX = [0, 1, 2, 3, 4, 5, 6, 8, 9, 12]
MIN_COACH_GAMES = 40


def rosters(system):
    cfg = L.SYSTEMS[system]
    mod = genesis if system == "genesis" else __import__("systems.snes", fromlist=["snes"])
    teams = mod.read_teams(rom(cfg["rom"]))
    out = {}
    for t in teams:
        for p in t["players"]:
            out[(t["abbr"], p["name"].lower())] = p
    return out


def lineup(players, keepers, team, ros, used=None):
    """(forward average ratings, defence average ratings, goalie Agility) or None. The players with the most ice time;
    the SNES rows have none (the players who dressed: usually 3 forwards and 2 defencemen), so there the ones the team
    used most often in that league (used: (team, name) -> games listed)."""
    F, D = [], []
    order = (lambda p: -p[9]) if players and len(players[0]) >= 10 else (lambda p: -(used or {}).get((team, str(p[1]).lower()), 0))
    for p in sorted(players, key=order):
        r = ros.get((team, str(p[1]).lower()))
        if not r or r["g"]:
            continue
        if p[2] == "D" and len(D) < 2:
            D.append([r["a"][i] for i in IDX])
        elif p[2] != "D" and len(F) < 3:
            F.append([r["a"][i] for i in IDX])
    g = None
    for k in sorted(keepers, key=lambda k: -(k[-1] if len(k) >= 9 else (used or {}).get((team, str(k[1]).lower()), 0))):
        r = ros.get((team, str(k[1]).lower()))
        if r and r["g"]:
            g = r["a"][1]
            break
    if len(F) < 3 or len(D) < 2 or g is None:
        return None
    return np.mean(F, 0), np.mean(D, 0), g


def main():
    system = sys.argv[1] if len(sys.argv) > 1 else "genesis"
    ros = rosters(system)
    name = "All_Games_GENS.csv" if system == "genesis" else "All_Games_SNES.csv"
    csv.field_size_limit(10 ** 9)
    rows, leagues = [], []
    used = defaultdict(Counter)                    # (league) -> (team, name) -> games listed (the SNES rows' order)
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["League"].lower().startswith("classic"):
                for s in ("Home", "Away"):
                    try:
                        for p in ast.literal_eval(r[s + "Players"] or "[]") + ast.literal_eval(r[s + "Goalies"] or "[]"):
                            used[r["League"]][(r[s + "TeamAbbrev"].strip(), str(p[1]).lower())] += 1
                    except (ValueError, SyntaxError):
                        pass
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1" or r["RegOrPlay"] != "R" or not r["League"].lower().startswith("classic"):
                continue
            try:
                side = {s: lineup(ast.literal_eval(r[s + "Players"] or "[]"), ast.literal_eval(r[s + "Goalies"] or "[]"),
                                  r[s + "TeamAbbrev"].strip(), ros, used[r["League"]]) for s in ("Home", "Away")}
            except (ValueError, SyntaxError):
                continue
            if None in side.values():
                continue
            for s, o in (("Home", "Away"), ("Away", "Home")):
                rows.append(dict(gf=float(r[s + "Score"]), own=side[s], opp=side[o], home=s == "Home",
                                 coach=r[s + "Player"].strip().lower(), ocoach=r[o + "Player"].strip().lower()))
                leagues.append(r["League"])
    n = Counter(c for r in rows for c in (r["coach"],))
    coaches = sorted(c for c, k in n.items() if k >= MIN_COACH_GAMES)
    ci = {c: i for i, c in enumerate(coaches)}
    K, R = len(coaches), len(IDX)

    def design(rs):
        X = np.zeros((len(rs), 4 * R + 2 + 2 * (K + 1)), np.float32)
        for j, r in enumerate(rs):
            X[j, 0:R], X[j, R:2 * R], X[j, 2 * R] = r["own"][0], r["own"][1], r["own"][2]
            X[j, 2 * R + 1:3 * R + 1], X[j, 3 * R + 1:4 * R + 1], X[j, 4 * R + 1] = r["opp"][0], r["opp"][1], r["opp"][2]
            X[j, 4 * R + 2 + ci.get(r["coach"], K)] = 1
            X[j, 4 * R + 2 + K + 1 + ci.get(r["ocoach"], K)] = 1
        return X
    X = design(rows)
    home = np.array([[1.0 if r["home"] else 0.0] for r in rows], np.float32)
    X = np.hstack([X, home])
    y = np.array([r["gf"] for r in rows])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    # standard errors from a game-clustered bootstrap would be best; a plain one is a floor: use 200 resamples of games
    rng = np.random.default_rng(1)
    g_ix = np.arange(len(rows)) // 2
    ng = g_ix.max() + 1
    boots = []
    for _ in range(60):
        pick = rng.integers(0, ng, ng)
        ix = np.concatenate([2 * pick, 2 * pick + 1])
        b, *_ = np.linalg.lstsq(X[ix], y[ix], rcond=None)
        boots.append(b[:4 * R + 2])
    se = np.std(np.array(boots), 0)
    print(f"{system}: {len(rows) // 2} Classic regular-season games, {len(rows)} team-games; {K} coaches with "
          f"{MIN_COACH_GAMES}+ team-games (the rest together); goals a team-game {y.mean():.2f}; home ice {beta[-1]:+.3f}")
    print("\nOne player's roster step, goals a game: FOR (his team's), AGAINST (cut from the other team's: + is good), "
          "TOTAL (goal difference); +- one standard error (bootstrap of games)")
    for pos, off, odiv in (("Forwards", 0, 3), ("Defencemen", R, 2)):
        print(f"\n{pos} (one of {odiv})")
        print("| Rating | For | Against (cut) | Total |")
        print("|---|---|---|---|")
        for k in range(R):
            f, fs = beta[off + k] / odiv, se[off + k] / odiv
            a, as_ = -beta[2 * R + 1 + off + k] / odiv, se[2 * R + 1 + off + k] / odiv
            print(f"| {NAMES[k]} | {f:+.3f} +- {fs:.3f} | {a:+.3f} +- {as_:.3f} | {f + a:+.3f} +- {np.hypot(fs, as_):.3f} |")
    print(f"\nGoalie Agility, a step: for {beta[2 * R]:+.3f} +- {se[2 * R]:.3f}, against (cut) {-beta[4 * R + 1]:+.3f} +- "
          f"{se[4 * R + 1]:.3f}")
    # the check: fit on the even-numbered leagues, predict the odd ones; ratings + coaches against coaches alone
    lg = sorted(set(leagues))
    odd = np.array([lg.index(x) % 2 == 1 for x in leagues])
    for label, cols in (("coaches and home ice only", np.r_[4 * R + 2:X.shape[1]]), ("ratings too", np.r_[0:X.shape[1]])):
        b, *_ = np.linalg.lstsq(X[~odd][:, cols], y[~odd], rcond=None)
        p = X[odd][:, cols] @ b
        r2 = 1 - ((y[odd] - p) ** 2).sum() / ((y[odd] - y[odd].mean()) ** 2).sum()
        print(f"held-out leagues, goals a team-game explained, {label}: {r2:.4f}")


if __name__ == "__main__":
    main()
