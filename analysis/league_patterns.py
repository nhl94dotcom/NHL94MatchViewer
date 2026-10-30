"""Game-wide patterns in the leagues' own results (2026-10-30): the user's databases outside the repository
(%USERPROFILE%\\NHL94_League_Data\\All_Games_GENS.csv, All_Games_SNES.csv), simulated games left out; aggregates only.
- conversion rates: shooting %, power play, shorthanded goals, breakaways, one-timers, penalty shots, pass completion;
- scoring by period, overtime and ties;
- the comeback bonus (GENESIS_MECHANICS / SNES_MECHANICS 2.3: +2 Offensive Awareness and Checking, +4 pass / shoot bias
  for a tied or trailing team, by a bug on in the FIRST half of the third period): the trailing team's share of goals
  in each half of the third period against the same halves of the second period, from the goal lists (period, seconds
  into it; 5-minute periods, games with a goal at 300 s or later left out);
- by year: goals and shots a game, shooting %, one-timer and breakaway goals a game.
python analysis/league_patterns.py"""
import ast
import csv
import math
from collections import defaultdict
from pathlib import Path

DATA = Path.home() / "NHL94_League_Data"


def num(v):
    try:
        return float(v)
    except ValueError:
        return None


def goals_of(r):
    out = []
    for col in ("HomeGoals", "AwayGoals"):
        try:
            for e in ast.literal_eval(r[col]) if r[col] else []:
                out.append((int(e[0]), int(e[1]), col == "HomeGoals", str(e[-1])))
        except (ValueError, SyntaxError, IndexError, TypeError):
            return None
    return sorted(out)


def share(a, b):
    n = a + b
    p = a / n if n else 0
    return p, 1.96 * math.sqrt(p * (1 - p) / n) if n else 0


def study(name, label):
    csv.field_size_limit(10 ** 9)
    tot = defaultdict(float)
    per_period = defaultdict(float)
    ot_games = ties = n = 0
    ot_home = ot_decided = 0
    halves = defaultdict(lambda: [0, 0])     # (period, half) -> [goals by the trailing team, by the leading team]
    tied_goals = defaultdict(int)
    year = defaultdict(lambda: defaultdict(float))
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1":
                continue
            hs, as_ = num(r["HomeScore"]), num(r["AwayScore"])
            if hs is None or as_ is None:
                continue
            n += 1
            for side in ("Home", "Away"):
                for k in ("Score", "Shots", "PPGoals", "PPTries", "SHGoals", "BreakGoals", "BreakTries", "OneTimerGoals",
                          "OneTimerTries", "PenShotGoals", "PenShotTries", "PassComps", "PassTries"):
                    v = num(r[side + k])
                    if v is not None:
                        tot[k] += v
                for p in ("P1", "P2", "P3", "OT"):
                    v = num(r[side + "Goals" + p])
                    if v is not None:
                        per_period[p] += v
            y = year[r["DateTime"][:4]]
            y["games"] += 1
            y["goals"] += hs + as_
            for k in ("Shots", "OneTimerGoals", "BreakGoals"):
                y[k] += (num(r["Home" + k]) or 0) + (num(r["Away" + k]) or 0)
            ot = (num(r["HomeShotsOT"]) or 0) + (num(r["AwayShotsOT"]) or 0) + (num(r["HomeGoalsOT"]) or 0) + \
                 (num(r["AwayGoalsOT"]) or 0)
            if ot > 0:
                ot_games += 1
                if hs != as_:
                    ot_decided += 1
                    ot_home += hs > as_
            if hs == as_:
                ties += 1
            g = goals_of(r)
            if not g or any(t >= 300 for _, t, _, _ in g):
                continue
            h = a = 0
            for period, t, home, _ in g:
                if period in (2, 3):
                    half = 0 if t < 150 else 1
                    if h == a:
                        tied_goals[(period, half)] += 1
                    else:
                        trailing_scored = (home and h < a) or (not home and a < h)
                        halves[(period, half)][0 if trailing_scored else 1] += 1
                if home:
                    h += 1
                else:
                    a += 1
    print(f"\n==================== {label}: {n} games")
    print(f"  goals a game {tot['Score'] / n:.2f}, shots {tot['Shots'] / n:.2f}, shooting % {100 * tot['Score'] / tot['Shots']:.1f}")
    print(f"  power play {100 * tot['PPGoals'] / tot['PPTries']:.1f}% ({tot['PPTries'] / n:.2f} a game); "
          f"shorthanded goals {100 * tot['SHGoals'] / tot['PPTries']:.1f} per 100 power plays")
    print(f"  breakaways {100 * tot['BreakGoals'] / tot['BreakTries']:.1f}% ({tot['BreakTries'] / n:.2f} a game); "
          f"one-timers {100 * tot['OneTimerGoals'] / tot['OneTimerTries']:.1f}% ({tot['OneTimerTries'] / n:.2f} a game, "
          f"{100 * tot['OneTimerGoals'] / tot['Score']:.0f}% of goals); penalty shots "
          f"{100 * tot['PenShotGoals'] / max(1, tot['PenShotTries']):.0f}% ({int(tot['PenShotTries'])} in all)")
    print(f"  passes completed {100 * tot['PassComps'] / tot['PassTries']:.1f}%")
    print("  goals by period: " + ", ".join(f"{p} {per_period[p] / n:.2f}" for p in ("P1", "P2", "P3", "OT")) +
          f"; overtime in {100 * ot_games / n:.1f}% of games (home won {100 * ot_home / max(1, ot_decided):.0f}% of "
          f"those decided); ties {100 * ties / n:.1f}%")
    print("  the trailing team's share of goals scored in games not tied at the time (the comeback bonus: third period,"
          " first half):")
    for p in (2, 3):
        for half in (0, 1):
            t, l = halves[(p, half)]
            s, ci = share(t, l)
            print(f"    period {p}, {'first' if half == 0 else 'second'} half: {100 * s:.1f}% (+/- {100 * ci:.1f}) of "
                  f"{t + l} goals; {tied_goals[(p, half)]} goals with the score tied")
    d = (share(*halves[(3, 0)])[0] - share(*halves[(3, 1)])[0]) - (share(*halves[(2, 0)])[0] - share(*halves[(2, 1)])[0])
    print(f"    third-period first half minus second half, less the same in the second period: {100 * d:+.1f} points")
    print("  by year: " + " ".join(f"{k}: {v['goals'] / v['games']:.1f}g {v['Shots'] / v['games']:.1f}s "
                                   f"{100 * v['goals'] / v['Shots']:.0f}% ot{v['OneTimerGoals'] / v['games']:.1f}"
                                   for k, v in sorted(year.items())))


def main():
    study("All_Games_GENS.csv", "GENESIS")
    study("All_Games_SNES.csv", "SNES")


if __name__ == "__main__":
    main()
