"""What wins NHL '94 games, from the leagues' own results (2026-11-26, the user: "do we actually know why exactly
players win or lose?"). The user's databases outside the repository (%USERPROFILE%\\NHL94_League_Data), simulated games
left out, aggregates only (no player names printed). Each game's stats as the home team minus the away team (or as
the home team's share where a share is fairer: leagues play different period lengths).

- wins: for each stat, how often the winner had more, the winner-minus-loser mean, and its rank correlation with the
  goal difference; then a logistic model of the result on the stats with and without the two players' ratings from
  before the game (league_flow_study.elo): which stats win games beyond being the better player.
- better: games between players with 30+ rated games each, by the pre-game rating gap: what the stronger player does
  differently (win %, goal difference, shot share, shooting % for and against, one-timers, breakaways, passing,
  faceoffs, penalties), and his goal difference split into more shots (at the league's shooting %) and better
  finishing (on the shots taken) and goaltending.
- luck: how often the better player loses, by the gap; how often the team with more shots loses, by the shot margin;
  how much of a game's goal difference the shot difference and the ratings explain.

python analysis/league_what_wins.py [wins|better|luck ...]   (default: all)"""
import ast
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import league_flow_study as LF

DATA = LF.DATA
K = {"GENESIS": 16, "SNES": 24}                     # LEAGUE_RESULTS "Player ratings": tuned on the next games
COLS = ("Shots", "OneTimerGoals", "OneTimerTries", "BreakGoals", "BreakTries", "Checks", "PassComps", "PassTries", "PIM",
        "FaceoffWins", "AttackZoneTime", "PPGoals", "PPTries", "SHGoals")


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def mmss(v):
    """Attack zone time: seconds, or 'm:ss'."""
    if v is None:
        return None
    v = str(v).strip()
    if ":" in v:
        try:
            m, s = v.split(":")[:2]
            return int(m) * 60 + int(s)
        except ValueError:
            return None
    return num(v)


def load(name):
    csv.field_size_limit(10 ** 9)
    games = []
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1":
                continue
            hs, as_ = num(r["HomeScore"]), num(r["AwayScore"])
            if hs is None or as_ is None:
                continue
            g = {"date": r["DateTime"], "league": r["League"], "hp": r["HomePlayer"].strip().lower(),
                 "ap": r["AwayPlayer"].strip().lower(), "hs": hs, "as": as_}
            for k in COLS:
                f = mmss if k == "AttackZoneTime" else num
                g["h" + k], g["a" + k] = f(r["Home" + k]), f(r["Away" + k])
            games.append(g)
    games.sort(key=lambda g: tuple(int(x) for x in g["date"].replace("-", " ").replace(":", " ").split() if x.isdigit())
               if g["date"] else ())
    return games


def share(a, b):
    return a / (a + b) if a is not None and b is not None and a + b > 0 else None


def stats(g):
    """The home team's side of each stat: differences and shares, None where the game doesn't have it."""
    h = lambda k: g["h" + k]  # noqa: E731
    a = lambda k: g["a" + k]  # noqa: E731
    out = {}
    out["shot share"] = share(h("Shots"), a("Shots"))
    out["shots (difference)"] = h("Shots") - a("Shots") if h("Shots") is not None and a("Shots") is not None else None
    out["one-timers tried (difference)"] = h("OneTimerTries") - a("OneTimerTries") if h("OneTimerTries") is not None and a("OneTimerTries") is not None else None
    out["one-timer share of shots (difference)"] = (h("OneTimerTries") / h("Shots") - a("OneTimerTries") / a("Shots")
                                                    if all(x is not None for x in (h("OneTimerTries"), a("OneTimerTries"))) and h("Shots") and a("Shots") else None)
    out["breakaways tried (difference)"] = h("BreakTries") - a("BreakTries") if h("BreakTries") is not None and a("BreakTries") is not None else None
    pc = [h("PassComps"), h("PassTries"), a("PassComps"), a("PassTries")]
    out["passes completed (difference)"] = pc[0] - pc[2] if pc[0] is not None and pc[2] is not None and (pc[0] or pc[2]) else None
    out["pass completion % (difference)"] = (pc[0] / pc[1] - pc[2] / pc[3]) * 100 if all(x for x in pc) else None
    out["attacking zone time share"] = share(h("AttackZoneTime"), a("AttackZoneTime"))
    out["checks (difference)"] = h("Checks") - a("Checks") if h("Checks") is not None and a("Checks") is not None and (h("Checks") or a("Checks")) else None
    out["faceoff share"] = share(h("FaceoffWins"), a("FaceoffWins"))
    out["penalty minutes (difference)"] = h("PIM") - a("PIM") if h("PIM") is not None and a("PIM") is not None else None
    out["power plays (difference)"] = h("PPTries") - a("PPTries") if h("PPTries") is not None and a("PPTries") is not None else None
    return out


PROCESS = ["shot share", "one-timers tried (difference)", "one-timer share of shots (difference)", "breakaways tried (difference)",
           "passes completed (difference)", "pass completion % (difference)", "attacking zone time share", "checks (difference)",
           "faceoff share", "penalty minutes (difference)", "power plays (difference)"]


def spearman(x, y):
    rx, ry = np.argsort(np.argsort(x)), np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def logistic(X, y, lam=1.0, iters=30):
    X = np.column_stack([np.ones(len(y)), X])
    w = np.zeros(X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-X @ w))
        g = X.T @ (y - p) - lam * np.r_[0, w[1:]]
        H = (X * (p * (1 - p))[:, None]).T @ X + lam * np.diag(np.r_[0, np.ones(len(w) - 1)])
        w += np.linalg.solve(H, g)
    p = 1 / (1 + np.exp(-X @ w))
    ll = -np.mean(y * np.log(p + 1e-12) + (1 - y) * np.log(1 - p + 1e-12))
    return w, ll


def rated(games, label):
    LF.elo(games, label, K[label])
    seen = defaultdict(int)
    for g in games:
        g["rated"] = seen[g["hp"]] >= 30 and seen[g["ap"]] >= 30
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1


def wins(games, label):
    dec = [g for g in games if g["hs"] != g["as"]]
    print(f"\n## {label}: what the winner does ({len(dec)} games with a winner; {len(games) - len(dec)} ties left out)")
    print(f"{'stat (winner minus loser, or the winner share)':48s} {'games':>7s} {'winner higher':>14s} {'winner - loser':>16s} {'rank corr. with goal diff':>26s}")
    rows = []
    for k in PROCESS:
        xs, gd, wl = [], [], []
        for g in dec:
            v = stats(g)[k]
            if v is None:
                continue
            hw = g["hs"] > g["as"]
            sh = k.endswith("share")
            w = (v if hw else 1 - v) if sh else (v if hw else -v)
            l = (1 - v if hw else v) if sh else (-v if hw else v)
            wl.append(w - l)
            xs.append(v)
            gd.append(g["hs"] - g["as"])
        if len(xs) < 500:
            print(f"{k:48s} {len(xs):7d}  too few")
            continue
        wl = np.array(wl)
        hi = float(np.mean(wl > 0) + 0.5 * np.mean(wl == 0))
        rows.append((abs(hi - 0.5), k))
        print(f"{k:48s} {len(xs):7d} {100 * hi:13.0f}% {wl.mean():+9.2f} ± {wl.std() / math.sqrt(len(wl)):.2f} {spearman(np.array(xs), np.array(gd)):+26.2f}")
    # the model: games with every stat, players rated
    use = [k for _, k in sorted(rows, reverse=True)]
    G = [g for g in dec if g.get("rated") and all(stats(g)[k] is not None for k in use)]
    if len(G) < 2000:
        use = [k for k in use if sum(stats(g)[k] is not None for g in dec if g.get("rated")) > 0.8 * sum(1 for g in dec if g.get("rated"))]
        G = [g for g in dec if g.get("rated") and all(stats(g)[k] is not None for k in use)]
    X = np.array([[stats(g)[k] for k in use] for g in G], float)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    y = np.array([1.0 if g["hs"] > g["as"] else 0.0 for g in G])
    elo = np.array([math.log(g["p"] / (1 - g["p"])) for g in G])
    _, ll0 = logistic(elo[:, None], y)
    w1, ll1 = logistic(Z, y)
    w2, ll2 = logistic(np.column_stack([Z, elo]), y)
    print(f"\nA model of the result ({len(G)} games, both players with 30+ rated games; log loss, a coin flip 0.693):")
    print(f"  the ratings alone {ll0:.3f}; the stats alone {ll1:.3f}; the stats and the ratings {ll2:.3f}")
    print("  weight of each stat (a standard deviation's worth, in log-odds): alone | with the ratings known")
    for j in np.argsort(-np.abs(w2[1:-1])):
        print(f"    {use[j]:44s} {w1[1 + j]:+.2f} | {w2[1 + j]:+.2f}   (a standard deviation: {sd[j]:.3g})")
    print(f"    {'the ratings (log-odds of the pre-game chance)':44s}   -   | {w2[-1]:+.2f}")


def better(games, label):
    G = [g for g in games if g.get("rated")]
    print(f"\n## {label}: what the better player does differently ({len(G)} games between players with 30+ rated games)")
    bins = [(0, 50), (50, 100), (100, 200), (200, 300), (300, 10 ** 6)]
    hdr = ["games", "wins %", "goal diff", "shot share", "sh% for", "sh% against", "1T tried +", "breaks +", "pass % +", "faceoffs", "PIM +"]
    print(f"{'rating gap':>11s} " + " ".join(f"{h:>11s}" for h in hdr))
    lg = [g for g in G if g["hShots"] and g["aShots"]]
    league_sh = sum(g["hs"] + g["as"] for g in lg) / sum(g["hShots"] + g["aShots"] for g in lg)
    split = []
    for lo, hi in bins:
        rows = []
        for g in G:
            gap = g["eh"] - g["ea"]
            if not lo <= abs(gap) < hi:
                continue
            s = "h" if gap >= 0 else "a"
            o = "a" if s == "h" else "h"
            gf, ga = (g["hs"], g["as"]) if s == "h" else (g["as"], g["hs"])
            rows.append(dict(win=1.0 if gf > ga else 0.0 if gf < ga else 0.5, gd=gf - ga, sf=g[s + "Shots"], sa=g[o + "Shots"], gf=gf, ga=ga,
                             ot=(g[s + "OneTimerTries"] or 0) - (g[o + "OneTimerTries"] or 0) if g[s + "OneTimerTries"] is not None else None,
                             br=(g[s + "BreakTries"] or 0) - (g[o + "BreakTries"] or 0) if g[s + "BreakTries"] is not None else None,
                             pc=(g[s + "PassComps"] / g[s + "PassTries"] - g[o + "PassComps"] / g[o + "PassTries"]) * 100
                             if g[s + "PassTries"] and g[o + "PassTries"] and g[s + "PassComps"] is not None and g[o + "PassComps"] is not None else None,
                             fo=share(g[s + "FaceoffWins"], g[o + "FaceoffWins"]),
                             pim=(g[s + "PIM"] - g[o + "PIM"]) if g[s + "PIM"] is not None and g[o + "PIM"] is not None else None))
        if not rows:
            continue
        m = lambda k: np.mean([r[k] for r in rows if r[k] is not None]) if any(r[k] is not None for r in rows) else float("nan")  # noqa: E731
        sr = [r for r in rows if r["sf"] and r["sa"]]
        sf, sa = sum(r["sf"] for r in sr), sum(r["sa"] for r in sr)
        gfs, gas = sum(r["gf"] for r in sr), sum(r["ga"] for r in sr)
        vals = [len(rows), 100 * m("win"), m("gd"), 100 * sf / (sf + sa), 100 * gfs / sf, 100 * gas / sa, m("ot"), m("br"), m("pc"), 100 * m("fo") if not math.isnan(m("fo")) else float("nan"), m("pim")]
        print(f"{f'{lo}-{hi if hi < 10**6 else chr(43)}':>11s} " + " ".join(f"{v:11.2f}" if isinstance(v, float) else f"{v:11d}" for v in vals))
        n = len(sr)
        vol = (sf - sa) / n * league_sh                       # more shots at the league's shooting %
        fin = (gfs - sf * league_sh) / n                      # his shots scored above the league's rate
        gk = (sa * league_sh - gas) / n                       # the other's shots scored below it (the computer in net)
        split.append((lo, hi, (gfs - gas) / n, vol, fin, gk))
    print(f"\nThe better player's goal difference a game, split (the league's shooting % {100 * league_sh:.1f}):")
    print(f"{'rating gap':>11s} {'goal diff':>10s} {'more shots':>11s} {'his finishing':>14s} {'the other side':>15s}")
    for lo, hi, gd, vol, fin, gk in split:
        print(f"{f'{lo}-{hi if hi < 10**6 else chr(43)}':>11s} {gd:10.2f} {vol:11.2f} {fin:14.2f} {gk:15.2f}")


def luck(games, label):
    G = [g for g in games if g.get("rated") and g["hs"] != g["as"]]
    print(f"\n## {label}: luck in a single game ({len(G)} decided games between rated players)")
    for lo, hi in ((0, 50), (50, 100), (100, 200), (200, 300), (300, 10 ** 6)):
        sel = [g for g in G if lo <= abs(g["eh"] - g["ea"]) < hi]
        if not sel:
            continue
        lost = np.mean([(g["eh"] > g["ea"]) != (g["hs"] > g["as"]) for g in sel])
        exp = np.mean([min(g["p"], 1 - g["p"]) for g in sel])
        print(f"  rating gap {lo}-{hi if hi < 10**6 else '+'}: the better player loses {100 * lost:.0f}% ({len(sel)} games; the ratings expect {100 * exp:.0f}%)")
    S = [g for g in games if g["hs"] != g["as"] and g["hShots"] is not None and g["aShots"] is not None]
    print(f"  the team with more shots loses (decided games with shots, {len(S)}):")
    for lo, hi in ((1, 3), (3, 6), (6, 10), (10, 1000)):
        sel = [g for g in S if lo <= abs(g["hShots"] - g["aShots"]) < hi]
        if sel:
            print(f"    outshot by {lo}-{hi - 1 if hi < 1000 else '+'}: {100 * np.mean([(g['hShots'] > g['aShots']) != (g['hs'] > g['as']) for g in sel]):.0f}% of {len(sel)}")
    A = [g for g in games if g.get("rated") and g["hShots"] is not None and g["aShots"] is not None and g["hShots"] + g["aShots"] > 0]
    gd = np.array([g["hs"] - g["as"] for g in A])
    sd_ = np.array([g["hShots"] - g["aShots"] for g in A])
    el = np.array([g["eh"] - g["ea"] for g in A])
    def r2(*xs):
        X = np.column_stack([np.ones(len(gd)), *xs])
        b = np.linalg.lstsq(X, gd, rcond=None)[0]
        return 1 - np.var(gd - X @ b) / np.var(gd)
    print(f"  a game's goal difference ({len(A)} games between rated players): the share of its spread explained by the "
          f"pre-game ratings {100 * r2(el):.0f}%, by the shot difference {100 * r2(sd_):.0f}%, by both {100 * r2(el, sd_):.0f}%")
    # within the same two players, how much the result varies: pairs with 10+ games together
    P = defaultdict(list)
    for g in games:
        if g["hs"] == g["as"]:
            continue
        a, b = sorted((g["hp"], g["ap"]))
        P[(g["league"], a, b)].append(1.0 if (g["hs"] > g["as"]) == (g["hp"] == a) else 0.0)
    big = [v for v in P.values() if len(v) >= 10]
    if big:
        rates = np.array([np.mean(v) for v in big])
        n = np.array([len(v) for v in big])
        obs = np.var(rates)
        noise = np.mean(rates * (1 - rates) / n)
        print(f"  the same two players in one league, 10+ decided games ({len(big)} pairs): the spread of the first player's win % "
              f"{100 * math.sqrt(obs):.0f} points, of which game-to-game chance alone would give {100 * math.sqrt(noise):.0f}; "
              f"the most one-sided pairs: {100 * np.mean((rates >= 0.8) | (rates <= 0.2)):.0f}% win or lose 80%+ of their games")


def main():
    parts = sys.argv[1:] or ["wins", "better", "luck"]
    for name, label in LF.FILES:
        games = load(name)
        rated(games, label)
        for p in parts:
            globals()[p](games, label)


if __name__ == "__main__":
    main()
