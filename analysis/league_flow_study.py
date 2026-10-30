"""Game flow, skill and luck in the leagues' own results (2026-10-30). The user's databases outside the repository
(%USERPROFILE%\\NHL94_League_Data), simulated games left out, aggregates only (no player names printed).
- elo: a rating for every person, game by game in date order (win 1, tie 0.5), tuned on the next games' outcomes;
  each game keeps both players' ratings from before it, for the studies below.
- winprob: the leading team's chance to win by lead and seconds played (regulation, 5-minute periods), against a model
  in which both teams keep scoring at the league's rate (and overtime is a coin flip), and against the same with the
  two players' ratings; when each lead reaches 90%.
- momentum: does the team that just scored score the next goal more often than its share of the game's goals says?
  And how soon do goals follow a goal?
- scoreeffects: the leading team's share of shots and goals in the third period, by lead, against what the ratings
  predict.
- luckskill: how much of a team's season and of a player's shooting carries over (split-half correlations).
- era: goals, shots, shooting %, one-timers, breakaways, checks, passes and penalties a game by year.
- timing: goals by second of the period (the last seconds, the first minute).
python analysis/league_flow_study.py [part ...]   (default: all)"""
import ast
import csv
import math
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path.home() / "NHL94_League_Data"
FILES = (("All_Games_GENS.csv", "GENESIS"), ("All_Games_SNES.csv", "SNES"))


def num(v):
    try:
        return float(v)
    except ValueError:
        return None


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
            for k in ("Shots", "OneTimerGoals", "OneTimerTries", "BreakGoals", "BreakTries", "Checks", "PassComps",
                      "PassTries", "PIM", "ShotsP1", "ShotsP2", "ShotsP3", "GoalsP1", "GoalsP2", "GoalsP3"):
                g["h" + k], g["a" + k] = num(r["Home" + k]), num(r["Away" + k])
            goals = []
            try:
                for col, home in (("HomeGoals", True), ("AwayGoals", False)):
                    for e in ast.literal_eval(r[col]) if r[col] else []:
                        goals.append(((int(e[0]) - 1) * 300 + int(e[1]), home))
            except (ValueError, SyntaxError, IndexError, TypeError):
                goals = None
            g["goals"] = sorted(goals) if goals is not None else None
            games.append(g)
    games.sort(key=lambda g: tuple(int(x) for x in g["date"].replace("-", " ").replace(":", " ").split() if x.isdigit())
               if g["date"] else ())
    return games


def result(g):
    return 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5


def elo(games, label, k=24, scale=400.0):
    """Ratings in date order; each game gets 'eh' / 'ea' (before it) and 'p' (the predicted home result)."""
    R = defaultdict(lambda: 1500.0)
    seen = Counter()
    ll = n = 0
    for g in games:
        rh, ra = R[g["hp"]], R[g["ap"]]
        p = 1 / (1 + 10 ** (-(rh - ra) / scale))
        g["eh"], g["ea"], g["p"] = rh, ra, p
        s = result(g)
        if seen[g["hp"]] >= 30 and seen[g["ap"]] >= 30 and s != 0.5:
            ll -= math.log(p if s == 1 else 1 - p)
            n += 1
        R[g["hp"]] += k * (s - p)
        R[g["ap"]] -= k * (s - p)
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    return ll / max(1, n), n, R, seen


def tune_elo(games, label):
    best = min(((elo(games, label, k)[0], k) for k in (12, 16, 24, 32, 40)))
    ll, n, R, seen = elo(games, label, best[1])
    base = -math.log(0.5)
    regular = sorted((v for p, v in R.items() if seen[p] >= 100), reverse=True)
    print(f"\n{label} ratings: K {best[1]} predicts the next game with log loss {ll:.3f} (a coin flip {base:.3f}) over "
          f"{n} games between players with 30+ games; {len(regular)} players with 100+ games, their spread (sd) "
          f"{(sum((x - sum(regular) / len(regular)) ** 2 for x in regular) / len(regular)) ** 0.5:.0f} points: "
          f"a one-sd edge wins {100 / (1 + 10 ** (-(sum((x - sum(regular) / len(regular)) ** 2 for x in regular) / len(regular)) ** 0.5 / 400)):.0f}%")


def skellam_win(lead, rate_left, ot=0.5):
    """P(the leader wins) when each team scores Poisson(rate_left) more: diff > -lead, a tie decided by a coin flip."""
    lam = rate_left
    pk = lambda j: math.exp(-lam) * lam ** j / math.factorial(j) if j < 60 else 0.0
    probs = [pk(j) for j in range(40)]
    win = tie = 0.0
    for i, pi in enumerate(probs):          # goals by the trailing team
        for j, pj in enumerate(probs):      # goals by the leader
            d = lead + j - i
            if d > 0:
                win += pi * pj
            elif d == 0:
                tie += pi * pj
    return win + ot * tie


def winprob(games, label):
    # every game whose goal list adds up to its score, overtime ones included (the lead counts regulation goals only)
    reg = [g for g in games if g["goals"] is not None and g["hs"] - g["as"] == sum(1 if h else -1 for _, h in g["goals"])]
    rate = sum(sum(1 for t, _ in g["goals"] if t < 900) for g in reg) / len(reg) / 900 / 2   # goals a second, each team
    checkpoints = (60, 150, 300, 450, 600, 750, 840, 870)
    cell = defaultdict(lambda: [0.0, 0])        # (lead, t) -> [wins, games]
    cell_r = defaultdict(lambda: [0.0, 0.0, 0])  # (lead, t) -> [wins, predicted wins from ratings + model, games]
    first90 = {}
    curve = defaultdict(lambda: [0.0, 0])
    for g in reg:
        res = result(g)
        for t in range(10, 900, 10):
            lead = sum((1 if h else -1) for tt, h in g["goals"] if tt < t)
            if lead == 0:
                continue
            L = min(abs(lead), 5)
            won = res if lead > 0 else 1 - res
            curve[(L, t)][0] += won
            curve[(L, t)][1] += 1
            if t in checkpoints:
                cell[(L, t)][0] += won
                cell[(L, t)][1] += 1
    print(f"\n{label}: win % of the team leading by L after t seconds of regulation ({len(reg)} games); "
          f"model: both keep scoring {rate * 900 * 2:.2f} goals a game between them, overtime a coin flip")
    print("  lead | " + " | ".join(f"{t:>4}s" for t in checkpoints))
    for L in range(1, 5):
        row = []
        for t in checkpoints:
            w, n = cell[(L, t)]
            m = skellam_win(L, rate * (900 - t))
            row.append(f"{100 * w / n:4.0f} ({100 * m:3.0f})" if n >= 50 else "   -      ")
        print(f"   {L}   | " + " | ".join(row))
    print("  (in brackets: the model)")
    for L in range(2, 6):
        sm = [(t, curve[(L, t)][0] / curve[(L, t)][1]) for t in range(10, 900, 10) if curve[(L, t)][1] >= 200]
        t90 = next((t for i, (t, p) in enumerate(sm) if all(q >= 0.9 for _, q in sm[i:])), None)
        print(f"  a {L}-goal lead stays at 90% or more from {t90} s on" if t90 is not None else f"  a {L}-goal lead: never")
    # the same with the players' ratings: how much of a lead's value is that the leader tends to be the better player
    by_gap = defaultdict(lambda: [0.0, 0])
    for g in reg:
        if "eh" not in g:
            continue
        lead = sum((1 if h else -1) for tt, h in g["goals"] if tt < 600)
        if abs(lead) == 1:
            res = result(g)
            won = res if lead > 0 else 1 - res
            pre = g["p"] if lead > 0 else 1 - g["p"]
            band = "leader rated 100+ better" if pre >= 0.64 else "within 100" if pre > 0.36 else "leader rated 100+ worse"
            by_gap[band][0] += won
            by_gap[band][1] += 1
    print("  a 1-goal lead after two periods (600 s), by the two players' ratings before the game: " +
          "; ".join(f"{k}: {100 * v[0] / v[1]:.0f}% ({v[1]} games)" for k, v in by_gap.items()))


def momentum(games, label):
    rep = exp = n_pairs = 0.0
    gap_after = Counter()
    for g in games:
        seq = g["goals"]
        if not seq or len(seq) < 2:
            continue
        a = sum(1 for _, h in seq if h)
        b = len(seq) - a
        N = len(seq)
        pairs = N - 1
        # under random order of the same goals, the expected number of consecutive same-team pairs
        exp += pairs * (a * (a - 1) + b * (b - 1)) / (N * (N - 1))
        rep += sum(1 for (t1, h1), (t2, h2) in zip(seq, seq[1:]) if h1 == h2)
        n_pairs += pairs
        for (t1, h1), (t2, h2) in zip(seq, seq[1:]):
            if t2 // 300 == t1 // 300:
                gap_after[("same team" if h1 == h2 else "other team", min((t2 - t1) // 15 * 15, 150))] += 1
    print(f"\n{label} momentum: the next goal by the team that scored the last one {100 * rep / n_pairs:.1f}% of the "
          f"time; {100 * exp / n_pairs:.1f}% expected from each game's goal split in random order "
          f"({int(n_pairs)} goal pairs)")
    print("  time to the next goal in the same period (seconds, by who scores it): " + ", ".join(
        f"{s}-{s + 14}: same {gap_after[('same team', s)]} / other {gap_after[('other team', s)]}" for s in range(0, 150, 15)))


def scoreeffects(games, label):
    rows = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0])
    for g in games:
        if g["goals"] is None or "eh" not in g or g["hShotsP3"] is None:
            continue
        lead = sum((1 if h else -1) for t, h in g["goals"] if t < 600)
        L = min(abs(lead), 3)
        if L == 0:
            continue
        home_leads = lead > 0
        p12 = (g["hShotsP1"] + g["hShotsP2"], g["aShotsP1"] + g["aShotsP2"])
        p3 = (g["hShotsP3"], g["aShotsP3"])
        gp3 = (sum(1 for t, h in g["goals"] if 600 <= t < 900 and h), sum(1 for t, h in g["goals"] if 600 <= t < 900 and not h))
        me, them = (0, 1) if home_leads else (1, 0)
        pre = g["p"] if home_leads else 1 - g["p"]
        r = rows[L]
        r[0] += p12[me]; r[1] += p12[me] + p12[them]
        r[2] += p3[me]; r[3] += p3[me] + p3[them]
        r[4] += gp3[me] / max(1, gp3[0] + gp3[1]) if gp3[0] + gp3[1] else 0.5
        r[5] += 1
        r.append(pre)
    # the benchmark: the period-3 shot share of a side with the same pre-game rating edge when tied after two periods
    tied = defaultdict(lambda: [0.0, 0.0])
    for g in games:
        if g["goals"] is None or "eh" not in g or g["hShotsP3"] is None:
            continue
        if sum((1 if h else -1) for t, h in g["goals"] if t < 600) == 0:
            for pre, mine in ((g["p"], g["hShotsP3"]), (1 - g["p"], g["aShotsP3"])):
                b = tied[min(9, int(pre * 10))]
                b[0] += mine
                b[1] += g["hShotsP3"] + g["aShotsP3"]

    def bench(pre):
        b = tied[min(9, int(pre * 10))]
        return b[0] / max(1, b[1])
    print(f"\n{label} score effects: the team leading after two periods, against a side with the same rating edge in "
          f"games tied after two")
    for L in (1, 2, 3):
        r = rows[L]
        exp = sum(bench(x) for x in r[6:]) / max(1, len(r[6:]))
        print(f"  lead {L}{'+' if L == 3 else ''}: shot share periods 1-2 {100 * r[0] / r[1]:.1f}%, period 3 "
              f"{100 * r[2] / r[3]:.1f}% against {100 * exp:.1f}% for the same rating edge when tied ({r[5]} games)")


def luckskill(games, label):
    """Split each player's games in a league season into odd and even games: how well do the halves agree?"""
    halves = defaultdict(lambda: [[0.0, 0.0, 0.0, 0.0, 0], [0.0, 0.0, 0.0, 0.0, 0]])  # (league, player) -> [w, gf, ga, sf..]
    count = Counter()
    for g in games:
        for me, home in ((g["hp"], True), (g["ap"], False)):
            key = (g["league"], me)
            h = halves[key][count[key] % 2]
            count[key] += 1
            res = result(g) if home else 1 - result(g)
            gf, ga = (g["hs"], g["as"]) if home else (g["as"], g["hs"])
            sf, sa = (g["hShots"], g["aShots"]) if home else (g["aShots"], g["hShots"])
            if sf is None or sa is None:
                continue
            h[0] += res; h[1] += gf; h[2] += ga; h[3] += sf; h[4] += 1
            h.append(sa)

    def corr(xs, ys):
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        c = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        return c / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    pairs = [(a, b) for a, b in halves.values() if a[4] >= 10 and b[4] >= 10]
    stat = {"win %": lambda h: h[0] / h[4], "goal difference a game": lambda h: (h[1] - h[2]) / h[4],
            "shots for a game": lambda h: h[3] / h[4], "shooting % (goals / shots)": lambda h: h[1] / max(1, h[3]),
            "save % (1 - goals against / shots against)": lambda h: 1 - h[2] / max(1, sum(h[5:]))}
    print(f"\n{label} skill and luck: a player's odd and even games in a league season ({len(pairs)} player-seasons "
          f"with 10+ games in each half); correlation between the halves (1 = all skill, 0 = all luck)")
    for name, f in stat.items():
        print(f"  {name:42}: {corr([f(a) for a, b in pairs], [f(b) for a, b in pairs]):.2f}")


def era(games, label):
    Y = defaultdict(lambda: defaultdict(float))
    for g in games:
        y = Y[g["date"][:4]]
        y["games"] += 1
        y["goals"] += g["hs"] + g["as"]
        for k in ("Shots", "OneTimerGoals", "OneTimerTries", "BreakGoals", "BreakTries", "Checks", "PassComps", "PassTries", "PIM"):
            y[k] += (g["h" + k] or 0) + (g["a" + k] or 0)
    print(f"\n{label} by year: goals, shots, shooting %, one-timer tries / goals, breakaways / goals, checks, pass %, PIM (a game)")
    for yr, v in sorted(Y.items()):
        n = v["games"]
        print(f"  {yr} ({int(n):5}): {v['goals'] / n:4.1f} {v['Shots'] / n:5.1f} {100 * v['goals'] / v['Shots']:4.1f}%  "
              f"OT {v['OneTimerTries'] / n:4.1f} / {v['OneTimerGoals'] / n:3.1f}  BA {v['BreakTries'] / n:3.1f} / "
              f"{v['BreakGoals'] / n:3.1f}  checks {v['Checks'] / n:4.1f}  pass {100 * v['PassComps'] / max(1, v['PassTries']):4.1f}%  "
              f"PIM {v['PIM'] / n:4.1f}")


def timing(games, label):
    by = Counter()
    n = 0
    for g in games:
        if g["goals"] is None or any(t >= 900 for t, _ in g["goals"]):
            continue
        n += 1
        for t, _ in g["goals"]:
            by[t % 300] += 1
    per_sec = sum(by.values()) / 300
    blocks = [(0, 10), (10, 20), (20, 30), (30, 60), (60, 150), (150, 240), (240, 270), (270, 290), (290, 295), (295, 300)]
    print(f"\n{label} goals by second of the period (regulation, {n} games), as a share of the average second:")
    print("  " + ", ".join(f"{a}-{b - 1}s {sum(by[s] for s in range(a, b)) / (b - a) / per_sec:.2f}" for a, b in blocks))


def main():
    parts = sys.argv[1:] or ["elo", "winprob", "momentum", "scoreeffects", "luckskill", "era", "timing"]
    for name, label in FILES:
        games = load(name)
        tune_elo(games, label)
        for p in parts:
            if p != "elo":
                globals()[p](games, label)


if __name__ == "__main__":
    main()
