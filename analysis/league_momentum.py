"""Momentum in the league's box scores (2026-11-08, a community member's question: does a team's shooting % early in a
game carry on later? The recorded games' version, by shot order, is momentum_study.py; the box scores have goals and
shots only by period, so here the halves are periods).

The league result databases (%USERPROFILE%/NHL94_League_Data, simulated games left out; regulation only, and a team-game
only if every period's goals are at most its shots). For each system:
- shooting % (goals / shots on goal) in periods 1, 2 and 3;
- the correlation over team-games between one period's shooting % and the next's (periods with 3 or more shots).
  Team and goalie strength that game make it positive on their own, so the test of momentum is a baseline with order
  meaning nothing: each team-game's regulation goals dealt out again at random over its shots (its shots per period
  kept; a multivariate hypergeometric draw), SHUFFLES times. Momentum would put the real correlation above that range.
- teams that shot 50% or better in period 1 (4+ shots): their shooting % in periods 2 and 3, against the baseline's.
Aggregates only (no names).

python analysis/league_momentum.py"""
import csv
import os
from pathlib import Path

import numpy as np

DATA = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "NHL94_League_Data"
SHUFFLES = 300


def load(name):
    rows, bad = [], 0
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1":
                continue
            for side in ("Home", "Away"):
                try:
                    g = [int(r[f"{side}GoalsP{p}"]) for p in (1, 2, 3)]
                    s = [int(r[f"{side}ShotsP{p}"]) for p in (1, 2, 3)]
                except (ValueError, KeyError, TypeError):
                    bad += 1
                    continue
                if any(a > b or a < 0 for a, b in zip(g, s)):
                    bad += 1
                    continue
                rows.append(g + s)
    return np.array(rows), bad


def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])


def measures(G, S):
    """G, S: (n, 3) goals and shots by period. Period shooting %, period-to-period correlations, after a hot P1."""
    pct = G.sum(0) / S.sum(0)
    out = {"pct": pct}
    for i, j in ((0, 1), (1, 2), (0, 2)):
        ok = (S[:, i] >= 3) & (S[:, j] >= 3)
        out[f"r{i + 1}{j + 1}"] = corr(G[ok, i] / S[ok, i], G[ok, j] / S[ok, j])
    hot = (S[:, 0] >= 4) & (G[:, 0] >= 0.5 * S[:, 0])
    out["hot"] = G[hot, 1:].sum() / S[hot, 1:].sum()
    out["hot_n"] = int(hot.sum())
    return out


def deal(G, S, rng):
    """Each team-game's regulation goals dealt out at random over its shots, its shots per period kept."""
    out = np.zeros_like(G)
    left_g, left_s = G.sum(1), S.sum(1)
    for p in range(2):
        out[:, p] = rng.hypergeometric(left_g, left_s - left_g, S[:, p])   # goals, other shots, this period's shots
        left_g = left_g - out[:, p]
        left_s = left_s - S[:, p]
    out[:, 2] = left_g
    return out


def main():
    rng = np.random.default_rng(94)
    for label, name in (("GENESIS", "All_Games_GENS.csv"), ("SNES", "All_Games_SNES.csv")):
        a, bad = load(name)
        G, S = a[:, :3], a[:, 3:]
        real = measures(G, S)
        base = [measures(deal(G, S, rng), S) for _ in range(SHUFFLES)]
        rng_of = lambda k: (np.percentile([b[k] for b in base], 2.5), np.mean([b[k] for b in base]), np.percentile([b[k] for b in base], 97.5))
        print(f"{label}: {len(a)} team-games ({len(a) // 2} games about; {bad} team-games left out: missing or goals over shots)")
        pb = np.array([b["pct"] for b in base])
        for p in range(3):
            print(f"  P{p + 1} shooting % {100 * real['pct'][p]:.1f}%   (goals dealt at random: {100 * pb[:, p].mean():.1f}%, "
                  f"95% {100 * np.percentile(pb[:, p], 2.5):.1f}-{100 * np.percentile(pb[:, p], 97.5):.1f})")
        for k, lab in (("r12", "P1 with P2"), ("r23", "P2 with P3"), ("r13", "P1 with P3")):
            lo, mean, hi = rng_of(k)
            print(f"  correlation, {lab}: {real[k]:+.3f}   (no momentum: {mean:+.3f}, 95% {lo:+.3f} to {hi:+.3f})")
        lo, mean, hi = rng_of("hot")
        print(f"  {real['hot_n']} team-games shooting 50%+ in P1 (4+ shots): P2-P3 shooting % {100 * real['hot']:.1f}%   "
              f"(no momentum: {100 * mean:.1f}%, 95% {100 * lo:.1f}-{100 * hi:.1f})")


if __name__ == "__main__":
    main()
