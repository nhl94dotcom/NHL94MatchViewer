"""Does a "coasting" bonus make Elo ratings better? (2026-10-30; the user's own ratings give the winner a bonus for
coasting.) The user's databases outside the repository (%USERPROFILE%\\NHL94_League_Data), aggregates only.

Coasting, the user's rule: the final unbroken stretch of the game in which the eventual winner's chance of winning
is 90% or more (a 1-goal lead never counts), as a share of the third period's length: more than 100% if it starts in
an earlier period (40% of the way into the second: 160%; all of the second and third: 200%), at least 10% for any win
by 2 or more goals (a 1-goal win gets none, so overtime gets none). A version capped at 100% is run beside it.
The rating update for that game is K x (1 + bonus) x (result - expected).

The chance of winning at each 10 seconds comes either from the league's own table (lead and time, as in
league_flow_study.winprob) or from a model with the two players' ratings in it: each team scores Poisson goals for the
rest of regulation, the rates tilted so that at the start the model gives the Elo expectation, overtime a coin flip.

Each version's K is tuned; all are scored the same way: log loss of the pre-game expectation on decided games between
players with 30+ games, in date order.
python analysis/league_elo_coasting.py"""
import math
import sys
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from league_flow_study import FILES, load, result  # noqa: E402

STEP = 10


def poisson(lam, k):
    return math.exp(-lam) * lam ** k / math.factorial(k)


@lru_cache(maxsize=None)
def lead_win(lead, lam_lead, lam_trail):
    """P(the side ahead by `lead` wins) with Poisson goals still to come for each side; a tie is a coin flip."""
    pa = [poisson(lam_lead, k) for k in range(25)]
    pb = [poisson(lam_trail, k) for k in range(25)]
    win = tie = 0.0
    for i, x in enumerate(pa):
        for j, y in enumerate(pb):
            d = lead + i - j
            if d > 0:
                win += x * y
            elif d == 0:
                tie += x * y
    return win + 0.5 * tie


@lru_cache(maxsize=None)
def tilt_for(p, rate):
    """The share s of the game's scoring rate the home side gets so that at the start it wins with chance p."""
    lo, hi = 0.02, 0.98
    for _ in range(40):
        s = (lo + hi) / 2
        q = lead_win(0, round(2 * rate * 900 * s, 3), round(2 * rate * 900 * (1 - s), 3))
        lo, hi = (s, hi) if q < p else (lo, s)
    return (lo + hi) / 2


def table(games):
    cells = defaultdict(lambda: [0.0, 0])
    for g in games:
        res = result(g)
        for t in range(0, 900, STEP):
            lead = sum((1 if h else -1) for tt, h in g["goals"] if tt < t)
            if lead:
                c = cells[(min(abs(lead), 6), t)]
                c[0] += res if lead > 0 else 1 - res
                c[1] += 1
    return lambda L, t: (cells[(min(L, 6), t)][0] / cells[(min(L, 6), t)][1]) if cells[(min(L, 6), t)][1] >= 30 else 1.0


def coasting(g, chance):
    """The winner's coasting share (0 if none): chance(lead_for_winner, t, game) gives the winner's chance."""
    if g["hs"] == g["as"] or any(t >= 900 for t, _ in g["goals"]):
        return 0.0
    home_won = g["hs"] > g["as"]
    start = None
    for t in range(0, 900, STEP):
        lead = sum((1 if h else -1) for tt, h in g["goals"] if tt < t) * (1 if home_won else -1)
        ok = lead >= 2 and chance(lead, t, g) >= 0.9
        if ok and start is None:
            start = t
        elif not ok:
            start = None
    share = 0.0 if start is None else (900 - start) / 300
    return max(0.1, share) if abs(g["hs"] - g["as"]) >= 2 else share


def run(games, k, bonus):
    R = defaultdict(lambda: 1500.0)
    seen = Counter()
    ll = n = 0
    for g in games:
        rh, ra = R[g["hp"]], R[g["ap"]]
        p = 1 / (1 + 10 ** (-(rh - ra) / 400))
        s = result(g)
        if seen[g["hp"]] >= 30 and seen[g["ap"]] >= 30 and s != 0.5:
            ll -= math.log(p if s == 1 else 1 - p)
            n += 1
        delta = k * (1 + bonus(g, p)) * (s - p)
        R[g["hp"]] += delta
        R[g["ap"]] -= delta
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    return ll / n, n


def main():
    for name, label in FILES:
        games = [g for g in load(name) if g["goals"] is not None
                 and g["hs"] - g["as"] == sum(1 if h else -1 for _, h in g["goals"])]
        rate = sum(sum(1 for t, _ in g["goals"] if t < 900) for g in games) / len(games) / 900 / 2
        tab = table(games)
        league = {id(g): coasting(g, lambda L, t, g: tab(L, t)) for g in games}
        # with ratings: a first plain pass gives each game's pre-game expectation
        R = defaultdict(lambda: 1500.0)
        pre = {}
        for g in games:
            p = 1 / (1 + 10 ** (-(R[g["hp"]] - R[g["ap"]]) / 400))
            pre[id(g)] = p
            R[g["hp"]] += 16 * (result(g) - p)
            R[g["ap"]] -= 16 * (result(g) - p)

        def rated(L, t, g):
            p = pre[id(g)]
            s = tilt_for(round(p if g["hs"] > g["as"] else 1 - p, 2), rate)
            left = 2 * rate * (900 - t)
            return lead_win(L, round(left * s, 2), round(left * (1 - s), 2))
        withr = {id(g): coasting(g, rated) for g in games}
        shares = [v for v in league.values() if v]
        print(f"\n{label}: {len(games)} games; the winner coasted in {100 * len(shares) / len(games):.0f}% of them "
              f"(league table), a mean bonus of {sum(shares) / max(1, len(shares)):.2f} when they did; with the ratings "
              f"in the line {100 * sum(1 for v in withr.values() if v) / len(games):.0f}%")
        versions = {"plain Elo": lambda g, p: 0.0,
                    "coasting bonus (league table)": lambda g, p: league[id(g)],
                    "coasting bonus, capped at 100%": lambda g, p: min(1.0, league[id(g)]),
                    "coasting bonus (with the ratings)": lambda g, p: withr[id(g)],
                    "goal-margin bonus (for comparison)": lambda g, p: min(1.0, max(0, abs(g["hs"] - g["as"]) - 1) / 4)}
        for vname, b in versions.items():
            best = min((run(games, k, b) + (k,) for k in (4, 5, 6, 7, 8, 10, 12, 14, 16, 20, 24, 28)), key=lambda x: x[0])
            print(f"  {vname:36}: log loss {best[0]:.4f} at K {best[2]} ({best[1]} games)")


if __name__ == "__main__":
    main()
