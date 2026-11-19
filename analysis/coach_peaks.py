"""The strongest coaches at each year's end, and each coach's peak, by four measures (2026-11-19, the user: the greatest
NHL '94 players of all time, Genesis and SNES). From the league result databases outside the repository
(%USERPROFILE%\\NHL94_League_Data). Names real people, so the tables go only to that folder (coach_peaks/); the console
gets counts only.

- **Year's end:** the published Rating (coach_rating.py's final fit: all leagues, recent games counting more, team
  terms in the Classic leagues) as it stood on 31 December, from the games played by then (coach_history.Fit), as a win
  chance against an average coach (one with 100+ games). Listed: coaches with 100+ games by then and 20+ in that year.
  2026 is to the last game in the data.
- **1. Peak Rating:** the highest of that Rating at the first of any month, with the same two conditions (20+ games in the
  year before that day).
- **2. Best year and prime:** a strength from one calendar year's games alone, given the opponents, teams and home ice,
  pulled toward the coach's career strength (coach_guide.year_strength; years with MIN_YEAR+ decided games). Prime: the
  best three calendar years in a row, the mean of the three, weighted by games.
- **3. Against the field:** at each month, how far a coach's Rating stood above the active field's mean (coaches
  meeting the conditions), in the field's standard deviations: the peak of that; and years finishing first.
- **4. Peak Elo:** the league's own Elo (league_team_elo: K 20, home +7, the coasting multiplier, the Classic team
  table in the leagues that use it, from reports/classic_team_elo.json), held: the best 30-game stretch's median
  rating after each game, from the coach's 50th game on; and the single highest.
- **All four:** a coach's rank on each measure among those ranked on all, and the mean of the four.

python analysis/coach_peaks.py"""
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scoring_map"))
import coach_guide as CG  # noqa: E402
import coach_history as H  # noqa: E402
import coach_rating as C  # noqa: E402
import league_team_elo as LE  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

OUT = C.DATA / "coach_peaks"
SYSTEMS = (("All_Games_GENS.csv", "GENESIS", "Genesis", 0), ("All_Games_SNES.csv", "SNES", "SNES", 1))
MIN_CAREER, MIN_RECENT, TOP, LIST = 100, 20, 10, 25
ELO_WINDOW, ELO_FROM = 30, 50
FIRST_YEAR = 2013


def pct(v):
    return 100 / (1 + math.exp(-v))


def ratings_over_time(fit, days_wanted):
    """{day: {coach: (log odds, games by then, games in the 365 days before)}}."""
    out = {}
    who = np.concatenate([fit.home_i, fit.away_i])
    when = np.concatenate([fit.days, fit.days])
    for i, day in enumerate(days_wanted):
        vals = fit.as_of(day)
        recent = np.bincount(who[(when < day) & (when >= day - 365)], minlength=len(fit.names))
        out[day] = {p: (v, n, int(recent[fit.names.index(p)])) for p, (v, n) in vals.items()}
        if i % 40 == 39:
            breathe()
    return out


def year_strengths(name, at, ridge, scale):
    """{coach: {year: (strength log odds, decided games)}} as in the coach guides."""
    C.PREFIX = None
    games, _ = C.prepare(name)
    D = C.Design(games)
    y = C.values(games)["coast"]
    n = len(games)
    beta = D.fit(np.ones(n, dtype=bool), np.ones(n), y, ridge)[0]
    days = np.array([g["day"] for g in games])
    won = np.array([1.0 if g["hs"] > g["as"] else 0.0 for g in games])
    decided = np.array([g["hs"] != g["as"] for g in games])
    every = D.predict(beta, np.arange(n))
    per = defaultdict(list)
    for i, g in enumerate(games):
        per[g["hp"]].append((i, 1.0))
        per[g["ap"]].append((i, -1.0))
    regulars = [p for p, v in per.items() if len(v) >= CG.MIN_GAMES]
    zero = float(np.mean([beta[D.people[p]] for p in regulars]))
    out = {}
    for p, me in per.items():
        if len(me) < CG.MIN_GAMES:
            continue
        ids = np.array([i for i, _ in me])
        side = np.array([s for _, s in me])
        wins = np.array([won[i] if s > 0 else (1 - won[i]) for i, s in me])
        dm_all = decided[ids]
        start = (beta[D.people[p]] - zero) * scale
        offsets = (every[ids] * side) * scale - beta[D.people[p]] * scale + zero * scale
        years = np.array([date.fromordinal(int(days[i])).year for i in ids])
        out[p] = {}
        for yr in sorted(set(years)):
            dm = (years == yr) & dm_all
            if dm.sum() >= CG.MIN_YEAR:
                out[p][int(yr)] = (CG.year_strength(offsets[dm], wins[dm], start), int(dm.sum()))
    return out


def elo_paths(name, label):
    """{coach: [rating after each game]} by the league's Elo."""
    games = LE.load_games(name)
    try:
        table = {t: v["adj"] for t, v in json.loads((HERE.parent / "reports" / "classic_team_elo.json").read_text())[label]["teams"].items()}
    except (OSError, KeyError):
        table = {}
    R = defaultdict(lambda: LE.START)
    path = defaultdict(list)
    for g in games:
        gap = R[g["hp"]] - R[g["ap"]] + LE.HOME
        if table and g["wide"]:
            gap += table.get(g["ht"], 0) - table.get(g["at"], 0)
        p = 1 / (1 + 10 ** (-gap / 400))
        s = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
        d = LE.K * (1 + g["coast"]) * (s - p)
        R[g["hp"]] += d
        R[g["ap"]] -= d
        path[g["hp"]].append((R[g["hp"]], g["day"]))
        path[g["ap"]].append((R[g["ap"]], g["day"]))
    return path, bool(table)


def build(name, label, title, at, sets):
    fit = H.Fit(name, "all", at, sets)
    last = int(fit.days.max())
    years = list(range(FIRST_YEAR, date.fromordinal(last).year + 1))
    ends = [min(date(y + 1, 1, 1).toordinal(), last + 1) for y in years]
    lo = date.fromordinal(int(fit.days.min()))
    months = [date(y, m, 1).toordinal() for y in range(lo.year, date.fromordinal(last).year + 1) for m in range(1, 13)
              if lo < date(y, m, 1) and date(y, m, 1).toordinal() <= last + 1] + [last + 1]
    at_end = ratings_over_time(fit, ends)
    at_month = ratings_over_time(fit, sorted(set(months)))
    # each game's coaches and result, for the year records
    rec = defaultdict(lambda: [0, 0, 0])
    for g in fit.games:
        yr = date.fromordinal(g["day"]).year
        for p, mine, theirs in ((g["hp"], g["hs"], g["as"]), (g["ap"], g["as"], g["hs"])):
            r = rec[(p, yr)]
            r[0 if mine > theirs else 1 if mine < theirs else 2] += 1

    def ok(v):
        return v[1] >= MIN_CAREER and v[2] >= MIN_RECENT

    lines = [f"# {title}: the strongest coaches by year, and each coach's peak", "",
             f"Private: names real people. From {lo.isoformat()} to {date.fromordinal(last).isoformat()} "
             f"({len(fit.games):,} games). Ratings are win chances against an average coach (one with {MIN_CAREER}+ games), "
             "neutral teams and no home edge; how each measure is made is at the top of analysis/coach_peaks.py.", ""]
    # ---- year's end
    firsts = defaultdict(list)
    top10s = defaultdict(int)
    lines += ["## The top ten at each year's end", ""]
    for yr, day in zip(years, ends):
        vals = sorted(((v[0], p, v) for p, v in at_end[day].items() if ok(v)), reverse=True)
        when = "to date" if day == last + 1 else "31 December"
        lines += [f"### {yr} ({when}; {len(vals)} coaches qualified)", "", "| Rank | Coach | Rating | Games, career | Year's record |",
                  "| --- | --- | --- | --- | --- |"]
        for rank, (v, p, full) in enumerate(vals[:TOP], 1):
            w, l, t = rec[(p, yr)]
            lines.append(f"| {rank} | {p} | {pct(v):.1f}% | {full[1]:,} | {w}-{l}" + (f"-{t}" if t else "") + " |")
            top10s[p] += 1
            if rank == 1:
                firsts[p].append(yr)
        lines.append("")
    # ---- peaks
    peak_rating, peak_z = {}, {}
    for day, vals in at_month.items():
        field = [v[0] for v in vals.values() if ok(v)]
        if len(field) < 10:
            continue
        mu, sd = float(np.mean(field)), float(np.std(field))
        for p, v in vals.items():
            if not ok(v):
                continue
            if v[0] > peak_rating.get(p, (-9,))[0]:
                peak_rating[p] = (v[0], day)
            z = (v[0] - mu) / sd
            if z > peak_z.get(p, (-9,))[0]:
                peak_z[p] = (z, day, len(field))
    ys = year_strengths(name, at, sets["all"][0][at][1], sets["all"][1][at])
    best_year, prime = {}, {}
    for p, by in ys.items():
        if by:
            yr, (v, n) = max(by.items(), key=lambda kv: kv[1][0])
            best_year[p] = (v, yr, n)
        for yr in by:
            if yr + 1 in by and yr + 2 in by:
                trio = [by[yr], by[yr + 1], by[yr + 2]]
                v = sum(s * n for s, n in trio) / sum(n for _, n in trio)
                if v > prime.get(p, (-9,))[0]:
                    prime[p] = (v, yr, sum(n for _, n in trio))
    paths, had_table = elo_paths(name, title)
    peak_elo = {}
    for p, path in paths.items():
        if len(path) < ELO_FROM + ELO_WINDOW:
            continue
        r = np.array([x for x, _ in path])
        best = None
        for i in range(ELO_FROM, len(r) - ELO_WINDOW + 1):
            m = float(np.median(r[i:i + ELO_WINDOW]))
            if best is None or m > best[0]:
                best = (m, path[i][1], path[i + ELO_WINDOW - 1][1])
        top_i = int(np.argmax(r[ELO_FROM:])) + ELO_FROM
        peak_elo[p] = (best[0], best[1], best[2], float(r[top_i]), path[top_i][1])

    def d(day):
        return date.fromordinal(int(day)).strftime("%b %Y")

    lines += ["## Years finishing first, and years in the top ten", "", "| Coach | First | Top ten |", "| --- | --- | --- |"]
    for p in sorted(top10s, key=lambda p: (-len(firsts.get(p, [])), -top10s[p], p))[:LIST]:
        lines.append(f"| {p} | {len(firsts.get(p, []))}" + (f" ({', '.join(map(str, firsts[p]))})" if firsts.get(p) else "") + f" | {top10s[p]} |")
    lines += ["", "## 1. Peak Rating (the highest at the first of a month)", "", "| Rank | Coach | Peak | When |", "| --- | --- | --- | --- |"]
    for i, (p, (v, day)) in enumerate(sorted(peak_rating.items(), key=lambda kv: -kv[1][0])[:LIST], 1):
        lines.append(f"| {i} | {p} | {pct(v):.1f}% | {d(day)} |")
    lines += ["", f"## 2. Best single year, and the best three years in a row ({CG.MIN_YEAR}+ decided games a year)", "",
              "| Rank | Coach | Best year | Year | Games | | Rank | Coach | Prime | Years | Games |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    by_year = sorted(best_year.items(), key=lambda kv: -kv[1][0])[:LIST]
    by_prime = sorted(prime.items(), key=lambda kv: -kv[1][0])[:LIST]
    for i in range(LIST):
        a = by_year[i] if i < len(by_year) else None
        b = by_prime[i] if i < len(by_prime) else None
        left = f"{i + 1} | {a[0]} | {pct(a[1][0]):.1f}% | {a[1][1]} | {a[1][2]}" if a else " | | | |"
        right = f"{i + 1} | {b[0]} | {pct(b[1][0]):.1f}% | {b[1][1]}-{b[1][1] + 2} | {b[1][2]}" if b else " | | | |"
        lines.append(f"| {left} | | {right} |")
    lines += ["", "## 3. Against the field (the peak height above the active coaches' mean, in their standard deviations)", "",
              "| Rank | Coach | Above the field | When | Coaches active |", "| --- | --- | --- | --- | --- |"]
    for i, (p, (z, day, nf)) in enumerate(sorted(peak_z.items(), key=lambda kv: -kv[1][0])[:LIST], 1):
        lines.append(f"| {i} | {p} | {z:+.2f} | {d(day)} | {nf} |")
    lines += ["", f"## 4. Peak Elo (the league's own; held: the best {ELO_WINDOW}-game stretch's median, from game {ELO_FROM})"
              + ("" if had_table else " [no team table found: plain Elo]"), "",
              "| Rank | Coach | Held | From | To | Highest | When |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for i, (p, (m, a, b, hi, hd)) in enumerate(sorted(peak_elo.items(), key=lambda kv: -kv[1][0])[:LIST], 1):
        lines.append(f"| {i} | {p} | {m:.0f} | {d(a)} | {d(b)} | {hi:.0f} | {d(hd)} |")
    # ---- all four
    measures = [{p: v[0] for p, v in peak_rating.items()}, {p: v[0] for p, v in prime.items()},
                {p: v[0] for p, v in peak_z.items()}, {p: v[0] for p, v in peak_elo.items()}]
    both = set.intersection(*(set(m) for m in measures))
    ranks = []
    for m in measures:
        order = sorted(both, key=lambda p: -m[p])
        ranks.append({p: i + 1 for i, p in enumerate(order)})
    mean_rank = {p: sum(r[p] for r in ranks) / 4 for p in both}
    lines += ["", f"## All four together ({len(both)} coaches ranked on every measure)", "",
              "| Rank | Coach | Mean rank | Peak Rating | Prime | Field | Peak Elo | Years first | Years top ten |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, p in enumerate(sorted(both, key=lambda p: mean_rank[p])[:LIST], 1):
        lines.append(f"| {i} | {p} | {mean_rank[p]:.1f} | {ranks[0][p]} | {ranks[1][p]} | {ranks[2][p]} | {ranks[3][p]} | "
                     f"{len(firsts.get(p, []))} | {top10s.get(p, 0)} |")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"PEAKS_{label}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{title}: {len(fit.games):,} games to {date.fromordinal(last)}; {len(years)} year-end tables; peaks for "
          f"{len(peak_rating)} / {len(prime)} / {len(peak_z)} / {len(peak_elo)} coaches; {len(both)} on all four; team table "
          f"{'used' if had_table else 'missing'}", flush=True)


def main():
    gentle()
    sets = H.settings()
    for name, label, title, at in SYSTEMS:
        build(name, label, title, at, sets)
        breathe()


if __name__ == "__main__":
    main()
