"""What separates the winner from the loser in the recorded people's games (2026-11-14; the user's goal for the
analyses: the stats that show why someone won or lost).

Every finished game recorded from its start with a person on both sides (season summaries: humans both true, no bot
side, fromStart), Genesis and SNES apart. Each team stat of the summary (tools/season.py: numbers, and the numbers
inside lists and dicts as STAT.i / STAT.key) taken as this team minus the other; the stats that are the score itself
or follow from it are left out (OUTCOME, and the goal parts of lists: DROP), and the mirrored ones (the other team's
own number: attA, xG against ...). Per stat, over the games with a winner:
  winner higher   the share of games the winner's value was higher (ties half)
  mean diff       the winner's value minus the loser's, mean, with its standard error
  rank corr.      Spearman correlation of the stat's difference with the goal difference, over every game
Sorted by how far the winner-higher share is from 50%. Then a logistic model of winning on the standardized
differences of the TOP stats with the strongest single associations (ridge-penalized, fitted by Newton's method): which
carry weight when the others are known. Associations, not causes: a team ahead may sit back, a team behind may press.

python analysis/what_wins.py [genesis|snes] [--top=N] [--min-games=N]"""
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
OUTCOME = {"gf", "ga", "ppg", "ppgA", "shg", "breakGoals", "oneTimerGoals", "chkGoal", "gkGiveGoals", "dtw", "assisted",
           "sa", "score", "onGoalie"}
SKIP = {"shotMap", "habits", "pairs", "sides", "puckPos", "entryPos", "possZones",
        "attA", "tapA", "tapMissA", "postsA", "possAttAgainst", "tap"}   # mirrored: the other team's own stat
# list entries that are goals, or the other side's (a mirror of this side's): left out (tools/season.py's layouts)
DROP = {"adv": {1, 3, 5, 6, 7}, "advEv": {1, 3, 5, 6, 7}, "xg": {1, 2, 3}, "hd": {1, 2, 3, 5}, "reb": {1, 2},
        "flip": {1, 2, 3}, "origin": {4, 5, 6, 7}, "oddMan": {2}, "wrap": {1}, "toShot": {1}}


def flatten(prefix, v, out):
    if isinstance(v, bool):
        return
    if isinstance(v, (int, float)):
        out[prefix] = float(v)
    elif isinstance(v, list):
        for i, x in enumerate(v):
            flatten(f"{prefix}.{i}", x, out)
    elif isinstance(v, dict):
        for k, x in v.items():
            flatten(f"{prefix}.{k}", x, out)


def games(system):
    for f in sorted((HOME / "matches").glob("*.summary.json")):
        s = json.loads(f.read_text(encoding="utf-8"))
        if s.get("system", "genesis") != system or s.get("bot") or not all(s.get("humans", [False, False])):
            continue
        if not s.get("finished") or not s.get("fromStart"):
            continue
        yield f.name.replace(".summary.json", ""), s


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    if rx.std() == 0 or ry.std() == 0:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def logistic(X, y, lam=1.0, iters=50):
    w = np.zeros(X.shape[1] + 1)
    A = np.hstack([np.ones((len(X), 1)), X])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-A @ w))
        g = A.T @ (p - y) + lam * np.r_[0, w[1:]]
        H = A.T @ (A * (p * (1 - p))[:, None]) + lam * np.diag(np.r_[0, np.ones(len(w) - 1)])
        w -= np.linalg.solve(H, g)
    return w


def main():
    system = next((a for a in sys.argv[1:] if a in ("genesis", "snes")), "genesis")
    top = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--top=")), 6))
    min_games = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--min-games=")), 15))
    rows = []
    for name, s in games(system):
        feats = []
        for t in (0, 1):
            out = {}
            for k, v in s["teams"][t].items():
                if k in OUTCOME or k in SKIP:
                    continue
                flatten(k, v, out)
            # decision ratios (2026-11-14): quality against quantity, and what checks and entries pay
            tm = s["teams"][t]

            def ratio(a, b):
                return a / b if b else None
            xg0 = (tm.get("xg") or [None])[0]
            for key, val in (("ratio xG per attempt", ratio(xg0, tm.get("att", 0)) if xg0 is not None else None),
                             ("ratio one-timers per attempt", ratio(tm.get("oneTimerTried", 0), tm.get("att", 0))),
                             ("ratio entries leading to an attempt", ratio((tm.get("entries") or [0] * 5)[4],
                                                                           (tm.get("entries") or [0])[0])),
                             ("ratio passes completed (person)", ratio((tm.get("humanPasses") or [0, 0])[1],
                                                                        (tm.get("humanPasses") or [0])[0])),
                             ("ratio passes completed (all)", ratio(tm.get("passMade", 0), tm.get("passTried", 0))),
                             ("ratio checks that paid off", ratio(tm.get("chkGain", 0), tm.get("checks", 0))),
                             ("ratio giveaways per attempt", ratio(tm.get("give", 0), tm.get("att", 0)))):
                if val is not None:
                    out[key] = val
            for k, idx in DROP.items():
                for i in idx:
                    out.pop(f"{k}.{i}", None)
            feats.append(out)
        gd = s["teams"][0]["gf"] - s["teams"][1]["gf"]
        diffs = {k: feats[0][k] - feats[1][k] for k in feats[0] if k in feats[1]}
        rows.append((name, gd, diffs))
    print(f"{system}: {len(rows)} games with a person on both sides, recorded from the start and finished; "
          f"{sum(1 for _, gd, _ in rows if gd)} with a winner\n")
    keys = sorted({k for _, _, d in rows for k in d})
    table = []
    for k in keys:
        xs = [(gd, d[k]) for _, gd, d in rows if k in d]
        if len(xs) < min_games:
            continue
        w = [(dk if gd > 0 else -dk) for gd, dk in xs if gd]          # the winner's value minus the loser's
        if len(w) < min_games or np.std(w) == 0:
            continue
        w = np.array(w)
        higher = (np.sum(w > 0) + 0.5 * np.sum(w == 0)) / len(w)
        se = w.std(ddof=1) / math.sqrt(len(w))
        rho = spearman(np.array([gd for gd, _ in xs], float), np.array([dk for _, dk in xs], float))
        table.append((k, len(w), higher, w.mean(), se, rho))
    table.sort(key=lambda r: -abs(r[2] - 0.5))
    print("| stat (team minus opponent) | games | winner higher | winner - loser (mean +- SE) | rank corr. with goal diff |")
    print("|---|---|---|---|---|")
    for k, n, hi, m, se, rho in table[:40]:
        print(f"| {k} | {n} | {100 * hi:.0f}% | {m:+.2f} +- {se:.2f} | {rho:+.2f} |")
    # the logistic model on the strongest single stats (one per family: the first of each stat's name before '.')
    chosen, seen = [], set()
    for k, *_ in table:
        fam = k.split(".")[0]
        if fam in seen:
            continue
        seen.add(fam)
        chosen.append(k)
        if len(chosen) >= top:
            break
    data = [(gd, [d.get(k) for k in chosen]) for _, gd, d in rows if gd and all(k in d for k in chosen)]
    if len(data) >= 2 * len(chosen) + 5:
        X = np.array([v for _, v in data], float)
        y = np.array([1.0 if gd > 0 else 0.0 for gd, _ in data])
        # symmetric: each game both ways (team 0's view and team 1's), so the intercept stays near 0
        X = np.vstack([X, -X])
        y = np.r_[y, 1 - y]
        mu, sd = X.mean(axis=0), X.std(axis=0)
        sd[sd == 0] = 1
        wts = logistic((X - mu) / sd, y)
        p = 1 / (1 + np.exp(-(np.hstack([np.ones((len(X), 1)), (X - mu) / sd]) @ wts)))
        acc = np.mean((p > 0.5) == (y > 0.5))
        print(f"\nLogistic model of winning on the standardized differences ({len(data)} games, each both ways; "
              f"right on {100 * acc:.0f}% of them, in sample):")
        for k, wt in sorted(zip(chosen, wts[1:]), key=lambda z: -abs(z[1])):
            print(f"  {k}: {wt:+.2f} per standard deviation")


if __name__ == "__main__":
    main()
