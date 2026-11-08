"""Penalties and the score in the league's games (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 3: does the game, or the
way people play, call more penalties on the leading or the trailing team? "The game makes a narrative").

The league result databases (%USERPROFILE%/NHL94_League_Data; simulated games left out; games with 5-minute periods,
every event within 300 game seconds of its period's start; regulation only). Each penalty and goal has its period and
its second in the period, so the score at each penalty is rebuilt from the goals before it (a goal in the same second
counts as after). For the penalized team: leading, tied or trailing, and by how much.
- Rates: penalties per 5 game minutes in each state, from the time each team spent in it.
- The same team in the same game, leading against trailing (team quality and style taken out): a stratified rate
  ratio over team-games with time in both (Mantel-Haenszel: sum(a_i t_trail_i / T_i) / sum(b_i t_lead_i / T_i)).
- By period, and the third period's last minute.
Aggregates only (no names).

python analysis/league_penalties.py"""
import ast
import csv
import os
from collections import defaultdict
from pathlib import Path

DATA = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "NHL94_League_Data"
PERIOD = 300


def games(name):
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1":
                continue
            try:
                hg, ag = ast.literal_eval(r["HomeGoals"] or "[]"), ast.literal_eval(r["AwayGoals"] or "[]")
                hp, ap = ast.literal_eval(r["HomePenalties"] or "[]"), ast.literal_eval(r["AwayPenalties"] or "[]")
            except (ValueError, SyntaxError):
                continue
            h, a = r["HomeTeamAbbrev"], r["AwayTeamAbbrev"]
            if h == a:
                continue
            ok = True
            for lst in (hg, ag, hp, ap):
                for e in lst:
                    if not (1 <= e[0] <= 3) or e[1] > PERIOD:
                        if e[0] == 4:
                            continue
                        ok = False
            if not ok:
                continue
            goals = [(g[0], g[1], 0 if g[2] == h else 1 if g[2] == a else None) for g in hg + ag if g[0] <= 3]
            pens = [(p[0], p[1], 0 if p[2] == h else 1 if p[2] == a else None) for p in hp + ap if p[0] <= 3]
            if any(x[2] is None for x in goals + pens):
                continue
            yield sorted(goals), sorted(pens)


def state(d):
    return "leading" if d > 0 else "trailing" if d < 0 else "tied"


def analyse(name):
    rate_t = defaultdict(float)              # (state) -> team-seconds
    rate_n = defaultdict(int)
    by_margin_t, by_margin_n = defaultdict(float), defaultdict(int)
    per_t, per_n = defaultdict(float), defaultdict(int)       # (period, state)
    late_t, late_n = defaultdict(float), defaultdict(int)     # third period's last 60 s
    mh_num = mh_den = 0.0
    n_games = n_pens = 0
    for goals, pens in games(name):
        n_games += 1
        # the timeline: each team's score difference through the game
        marks = [((g[0] - 1) * PERIOD + g[1], g[2]) for g in goals]
        marks.sort()
        t_in = [defaultdict(float), defaultdict(float)]
        pen_in = [defaultdict(int), defaultdict(int)]
        score = [0, 0]
        last = 0
        cuts = marks + [(3 * PERIOD, None)]
        for when, team in cuts:
            for k in (0, 1):
                d = score[k] - score[1 - k]
                # split the span by period for the period tables
                a = last
                while a < when:
                    p = a // PERIOD + 1
                    b = min(when, p * PERIOD)
                    span = b - a
                    st = state(d)
                    t_in[k][st] += span
                    rate_t[st] += span
                    by_margin_t[max(-2, min(2, d))] += span
                    per_t[(p, st)] += span
                    if p == 3:
                        lo = max(a, 3 * PERIOD - 60)
                        if b > lo:
                            late_t[st] += b - lo
                    a = b
            if team is not None:
                score[team] += 1
            last = when
        for p, s, team in pens:
            when = (p - 1) * PERIOD + s
            sc = [sum(1 for w, t in marks if w < when and t == k) for k in (0, 1)]
            d = sc[team] - sc[1 - team]
            st = state(d)
            rate_n[st] += 1
            by_margin_n[max(-2, min(2, d))] += 1
            per_n[(p, st)] += 1
            if p == 3 and s >= PERIOD - 60:
                late_n[st] += 1
            pen_in[team][st] += 1
            n_pens += 1
        for k in (0, 1):
            tl, tt = t_in[k]["leading"], t_in[k]["trailing"]
            if tl > 0 and tt > 0:
                T = tl + tt
                mh_num += pen_in[k]["leading"] * tt / T
                mh_den += pen_in[k]["trailing"] * tl / T
    per5 = lambda n, t: 300 * n / t if t else float("nan")
    print(f"{name}: {n_games:,} games, {n_pens:,} penalties (regulation, 5-minute periods)")
    for st in ("leading", "tied", "trailing"):
        print(f"  {st:9s} {per5(rate_n[st], rate_t[st]):.3f} penalties per 5 game minutes ({rate_n[st]:,} in {rate_t[st] / 60:,.0f} team-minutes)")
    print("  by the penalized team's margin: " + "; ".join(
        f"{('+' if m > 0 else '') + str(m) + ('+' if abs(m) == 2 else '')}: {per5(by_margin_n[m], by_margin_t[m]):.3f}"
        for m in (-2, -1, 0, 1, 2)))
    for p in (1, 2, 3):
        print(f"  period {p}: " + "; ".join(f"{st} {per5(per_n[(p, st)], per_t[(p, st)]):.3f}" for st in ("leading", "tied", "trailing")))
    print("  third period's last minute: " + "; ".join(f"{st} {per5(late_n[st], late_t[st]):.3f}" for st in ("leading", "tied", "trailing")))
    print(f"  the same team in the same game, leading against trailing: rate ratio {mh_num / mh_den:.3f}")
    return dict(rates={st: per5(rate_n[st], rate_t[st]) for st in ("leading", "tied", "trailing")}, mh=mh_num / mh_den)


def main():
    for name in ("All_Games_GENS.csv", "All_Games_SNES.csv"):
        analyse(name)


if __name__ == "__main__":
    main()
