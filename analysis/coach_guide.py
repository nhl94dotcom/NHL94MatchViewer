"""The coach guides: a page per coach with 100+ games, from the league databases (2026-11-04, the user). They name real people, so they go only to %USERPROFILE%\\NHL94_League_Data\\coach_guides, never into
the repository; the user decides whose page is shared, for coaches who agree. Run coach_rating.py and coach_rating.py groups first: ratings come from their private tables.

For each coach: ratings and their spread; level of competition; year by year (record, opponents, a strength from that year's games); best and worst Classic teams against what the coach, the
opponents and home ice predict with an average team.
Year strength: one number per year, from who won, given the opponents, teams and home ice over all years, pulled lightly toward the coach's strength over all years.
python analysis/coach_guide.py"""
import csv
import math
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scoring_map"))
import coach_rating as C  # noqa: E402
from coach_team_levels import top_leagues  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

OUT = C.DATA / "coach_guides"
SYSTEMS = (("All_Games_GENS.csv", "GENESIS", "Genesis", 0), ("All_Games_SNES.csv", "SNES", "SNES", 1))
MIN_GAMES, MIN_YEAR, MIN_TEAM, RECENT_DAYS = 100, 20, 15, 730
PRIOR = 1.0             # the pull on a year's strength: this spread, in log odds, around the coach's strength over all years


def pct(x):
    return 100 / (1 + math.exp(-x))


def table(label, tail=""):
    with open(C.DATA / f"coach_ratings_{label}{tail}.csv", encoding="utf-8", newline="") as fh:
        return {r["coach"]: r for r in csv.DictReader(fh)}


def year_strength(offsets, won, start):
    """The strength (log odds) that best fits these games, with the pull: offsets are everything else in each game, from this coach's side."""
    t = start
    for _ in range(25):
        p = 1 / (1 + np.exp(-(t + offsets)))
        grad = (won - p).sum() - (t - start) / PRIOR ** 2
        hess = (p * (1 - p)).sum() + 1 / PRIOR ** 2
        step = grad / hess
        t += step
        if abs(step) < 1e-6:
            break
    return float(t)


def record(wins, losses, ties):
    return f"{wins}-{losses}" + (f"-{ties}" if ties else "")


def build(name, label, title, at, ridge, scale):
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
    regulars = [p for p, v in per.items() if len(v) >= MIN_GAMES]
    zero = float(np.mean([beta[D.people[p]] for p in regulars]))
    # log odds against an average regular; opponents' strengths are on the same zero
    strength = {p: (beta[D.people[p]] - zero) * scale for p in per}
    ratings, classic = table(label), table(label, "_classic")
    levels = top_leagues({g["league"] for g in games if g["classic"]})
    now = int(days.max())
    check = []
    order = sorted(regulars, key=lambda p: -float(ratings[p]["win_chance_vs_average"]) if p in ratings else 0)
    out = [f"# {title} coach guide", "",
           f"Private: this names real people. {len(order)} coaches with {MIN_GAMES}+ games, through {date.fromordinal(now).isoformat()}. Share a page only with the coach's agreement.", "",
           "## How to read this guide", "",
           "- **Rating:** the win chance against an average coach (one with 100+ games), with neutral teams and no home edge, recent games counting more. The range is one standard error each way.",
           "- **Career:** the same with every game counting equally.",
           "- **Classic rating:** the same as Rating, fitted on Classic leagues alone.",
           "- **Rank:** among coaches with 100+ games, by Rating.",
           "- **Opponents:** the mean career strength of the people faced, on the same scale: 50 is an average coach. Higher means tougher competition.",
           "- **Top league share:** the share of Classic games played in the top league of that season, where the league name shows one.",
           f"- **Year by year:** Strength is one number from that year's wins and losses, given the opponents, teams and home ice, and pulled lightly toward the coach's career strength, so a year with few games moves less. Years with under {MIN_YEAR} games show no strength.",
           f"- **Best and worst Classic teams:** teams with {MIN_TEAM}+ games. Predicted is the win % the coach's strength, the opponent's coach and team, and home ice predict with an average team, and Above is the win % minus that. It shows the team's own strength as well as this coach's fit with it, and with few games it's mostly chance.", "",
           "Strength here uses one number per coach over all years, with the year-by-year table showing the change. It says how a coach has done, not how they would do in another league.", "",
           "**Coaches:** " + " · ".join(f"[{p}](#{i + 1}-{re.sub(r'[^a-z0-9 _-]', '', p.lower()).replace(' ', '-')})" for i, p in enumerate(order)), ""]
    for rank, p in enumerate(order, 1):
        me = per[p]
        ids = np.array([i for i, _ in me])
        side = np.array([s for _, s in me])
        wins = np.array([won[i] if s > 0 else (1 - won[i]) for i, s in me])
        decided_mine = decided[ids]
        opp = [games[i]["ap"] if s > 0 else games[i]["hp"] for i, s in me]
        opp_val = np.array([pct(strength[o]) for o in opp])
        recent = days[ids] >= now - RECENT_DAYS
        r = ratings.get(p, {})
        c = classic.get(p)
        out += [f"## {rank}. {p}", ""]
        w, l = int((wins * decided_mine).sum()), int(((1 - wins) * decided_mine).sum())
        lines = [f"- **Rating:** {r.get('win_chance_vs_average', '—')}% (range {r.get('low', '—')}-{r.get('high', '—')}), rank {rank} of {len(order)}", f"- **Career:** {r.get('career', '—')}%"]
        if c:
            lines.append(f"- **Classic rating:** {c['win_chance_vs_average']}% (range {c['low']}-{c['high']}) over {c['games']} Classic games")
        lines.append(f"- **Record:** {record(w, l, int((~decided_mine).sum()))}, {100 * w / max(1, w + l):.1f}% over {len(ids)} games, last on {r.get('last_played', '—')}")
        text = f"- **Opponents:** {opp_val.mean():.1f}" + (f", and {opp_val[recent].mean():.1f} in the last two years" if recent.any() else "")
        lines.append(text)
        tops = [levels.get(games[i]["league"]) for i, _ in me if games[i]["classic"]]
        named = [t for t in tops if t in (0, 2)]
        if named:
            lines.append(f"- **Top league share:** {100 * sum(t == 0 for t in named) / len(named):.0f}% of {len(named)} Classic games with a level in the league name")
        out += lines + [""]
        start = strength[p]
        # everything else in each game, from this coach's side
        offsets = (every[ids] * side) * scale - (beta[D.people[p]] * scale) + 0.0
        # the strength term carries the shared zero, so add it back for a value on the average-coach scale
        offsets = offsets + zero * scale
        years = np.array([date.fromordinal(int(days[i])).year for i in ids])
        out += ["| Year | Games | Record | Win % | Opponents | Strength |", "| --- | --- | --- | --- | --- | --- |"]
        for yr in sorted(set(years)):
            m = years == yr
            dm = m & decided_mine
            yw, yl = int(wins[dm].sum()), int((1 - wins[dm]).sum())
            s = "—"
            if dm.sum() >= MIN_YEAR:
                value = pct(year_strength(offsets[dm], wins[dm], start))
                s = f"{value:.1f}"
                check.append((value - float(r.get("career", value)), int(dm.sum())))
            out.append(f"| {yr} | {int(m.sum())} | {record(yw, yl, int(m.sum() - dm.sum()))} | {100 * yw / max(1, yw + yl):.1f} | {opp_val[m].mean():.1f} | {s} |")
        out.append("")
        by_team = defaultdict(lambda: [0, 0, 0, 0.0])
        for (i, s), win, ok in zip(me, wins, decided_mine):
            g = games[i]
            if not g["classic"]:
                continue
            team = g["ht"] if s > 0 else g["at"]
            t = by_team[team]
            if not ok:
                t[2] += 1
                continue
            t[0 if win else 1] += 1
            own = beta[D.teams[team]] if team in D.teams and D.cols[i, 2] != D.home else 0.0
            t[3] += 1 / (1 + math.exp(-((every[i] * s - own) * scale)))
        rows = []
        for team, (tw, tl, tt, pred) in by_team.items():
            if tw + tl + tt >= MIN_TEAM and tw + tl:
                rows.append((100 * tw / (tw + tl) - 100 * pred / (tw + tl), team, tw, tl, tt, 100 * pred / (tw + tl)))
        rows.sort(reverse=True)
        if rows:
            show = rows if len(rows) <= 6 else rows[:3] + rows[-3:]
            out += ["| Classic team | Record | Win % | Predicted | Above |", "| --- | --- | --- | --- | --- |"]
            for diff, team, tw, tl, tt, pred in show:
                out.append(f"| {team} | {record(tw, tl, tt)} | {100 * tw / (tw + tl):.1f} | {pred:.1f} | {diff:+.1f} |")
            out.append("")
        breathe()
    OUT.mkdir(exist_ok=True)
    path = OUT / f"COACH_GUIDE_{label}.md"
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"{title}: {len(order)} coaches, scale {scale:.3f}, zero {zero:+.3f}; year strength minus career, by games: {np.average([c[0] for c in check], weights=[c[1] for c in check]):+.1f}; written to the private folder", flush=True)


def main():
    gentle()
    text = (C.DATA / "coach_rating_test.md").read_text(encoding="utf-8")
    fits = re.findall(r"Final fit: coast, half-life ([\d.]+), ridge ([\d.]+)", text)
    conv = [float(x) for x in re.findall(r"Conversion factor ([\d.]+)", text)]
    for name, label, title, at in SYSTEMS:
        build(name, label, title, at, float(fits[at][1]), conv[at])


if __name__ == "__main__":
    main()
