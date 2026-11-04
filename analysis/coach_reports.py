"""A detailed report per coach, per system, for coaches with 100+ games (2026-11-04, the user). They name real people, so they go only to %USERPROFILE%\\NHL94_League_Data\\coach_guides\\reports, never the
repository; the user shares a report only with that coach's agreement. Run coach_rating.py, coach_rating.py groups, coach_history.py and league_ratings.py first.

Classic comes first in every report, as the league's most important. Then the Rating and its trend (with a chart from the history), league families, opponents by level, how concentrated the opponents are
and every league played, with its strength. The notes are fixed rules that state what the numbers show, never why.
python analysis/coach_reports.py NAME [NAME ...]     only those coaches, to check
python analysis/coach_reports.py                     everyone"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scoring_map"))
import coach_guide as G  # noqa: E402
import coach_history as H  # noqa: E402
import coach_rating as C  # noqa: E402
import league_ratings as LR  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

ROOT = HERE.parent
OUT = C.DATA / "coach_guides" / "reports"
SYSTEMS = (("All_Games_GENS.csv", "GENESIS", "Genesis", 0), ("All_Games_SNES.csv", "SNES", "SNES", 1))
MIN_GAMES, MIN_YEAR, MIN_TEAM, MIN_FAMILY, RECENT = 100, 20, 15, 20, 1096
TIERS = (("85+", 85, 101), ("70-85", 70, 85), ("50-70", 50, 70), ("Under 50", -1, 50))
BLUE, ORANGE, INK, MUTED, GRID, SURFACE = "#2a78d6", "#c2410c", "#0b0b0b", "#52514e", "#dcdcd8", "#fcfcfb"
FONT = "Segoe UI, Helvetica, Arial, sans-serif"


def rec(w, l, t=0):
    return f"{w}-{l}" + (f"-{t}" if t else "")


def share(w, l):
    return f"{100 * w / (w + l):.1f}%" if w + l else "—"


def safe(name):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name)


def chart(path, series, title_all, title_classic):
    """Rating over time, and the Classic rating when there is one. series: {'all': [(day, value)], 'classic': [...]}"""
    points = series["all"] + series["classic"]
    if len(series["all"]) < 2:
        return False
    w, h, left, right, top, bottom = 820, 260, 44, 150, 16, 30
    lo_d, hi_d = min(d for d, _ in points), max(d for d, _ in points)
    lo_v = max(0, 10 * math.floor(min(v for _, v in points) / 10))
    hi_v = min(100, 10 * math.ceil(max(v for _, v in points) / 10))
    x = lambda d: left + (d - lo_d) * (w - left - right) / max(1, hi_d - lo_d)
    y = lambda v: top + (hi_v - v) * (h - top - bottom) / max(1, hi_v - lo_v)
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}" font-size="12">', f'<rect width="{w}" height="{h}" fill="{SURFACE}"/>']
    step = 10 if hi_v - lo_v > 30 else 5
    v = lo_v
    while v <= hi_v:
        s.append(f'<line x1="{left}" x2="{w - right}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{GRID}"/><text x="{left - 6}" y="{y(v) + 4:.1f}" text-anchor="end" fill="{MUTED}">{v}</text>')
        v += step
    y0, y1 = date.fromordinal(lo_d).year, date.fromordinal(hi_d).year
    for yr in range(y0 + 1, y1 + 1):
        d = date(yr, 1, 1).toordinal()
        if yr % (1 if y1 - y0 <= 8 else 2) == 0:
            s.append(f'<line x1="{x(d):.1f}" x2="{x(d):.1f}" y1="{top}" y2="{h - bottom}" stroke="{GRID}"/><text x="{x(d):.1f}" y="{h - bottom + 16}" text-anchor="middle" fill="{MUTED}">{yr}</text>')
    labels = []
    for key, colour, name in (("all", BLUE, title_all), ("classic", ORANGE, title_classic)):
        pts = series[key]
        if len(pts) >= 2:
            s.append(f'<polyline fill="none" stroke="{colour}" stroke-width="2" stroke-linejoin="round" points="' + " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in pts) + '"/>')
            labels.append([y(pts[-1][1]), name, pts[-1][1], colour])
    labels.sort()
    if len(labels) == 2 and labels[1][0] - labels[0][0] < 16:
        labels[1][0] = labels[0][0] + 16
    for ly, name, val, colour in labels:
        s.append(f'<rect x="{w - right + 8}" y="{ly - 5:.1f}" width="10" height="10" rx="2" fill="{colour}"/><text x="{w - right + 22}" y="{ly + 4:.1f}" fill="{INK}">{name} {val:.1f}</text>')
    s.append("</svg>")
    path.write_text("\n".join(s), encoding="utf-8")
    return True


def notes(me):
    """Fixed rules. Each states what the numbers show, never why."""
    n = []
    gap = me["rating"] - me["career"]
    if abs(gap) >= 3:
        n.append(f"**Recent games {'lift' if gap > 0 else 'lower'} the Rating:** it's {abs(gap):.1f} points {'above' if gap > 0 else 'below'} Career.")
    if me["last_year"] and abs(me["last_year"][1] - me["rating"]) >= 5:
        y_, v = me["last_year"]
        n.append(f"**The latest year differs from the Rating:** Strength in {y_} is {v:.1f}, against a Rating of {me['rating']:.1f}.")
    if me["win_rank"] - me["rank"] >= 15:
        n.append(f"**Opponents lift the Rating above the record:** {me['rank']} of {me['of']} by Rating, {me['win_rank']} by win %.")
    elif me["rank"] - me["win_rank"] >= 15:
        n.append(f"**Opponents hold the Rating below the record:** {me['rank']} of {me['of']} by Rating, {me['win_rank']} by win %.")
    if me["classic_games"] == 0:
        n.append("**No Classic games.**")
    elif me["classic_weight"] < 10:
        n.append(f"**Little of the Rating comes from Classic:** {me['classic_weight']:.0f}% of the weight.")
    if me["big_family"]:
        fam, wt, wins, losses, opp = me["big_family"]
        n.append(f"**One family carries a lot of the weight:** `{fam}`, {wt:.0f}%, at {rec(wins, losses)} ({share(wins, losses)}) against opponents averaging {opp:.1f}, where all their recent opponents average {me['recent_opp']:.1f}.")
    if me["non_classic_weight"] >= 50:
        n.append(f"**Teams aren't adjusted outside Classic:** {me['non_classic_weight']:.0f}% of the weight is non-Classic games, where a strong roster counts as the coach's own strength.")
    if me["top5"] >= 50:
        n.append(f"**Few opponents make up much of the Rating:** the five most-weighted hold {me['top5']:.0f}% of it.")
    if me["days_away"] >= 365:
        n.append(f"**Not recent:** last played {me['last']}, so age has reduced their games' weight and the pull toward the middle counts for more.")
    if me["range"] >= 8:
        n.append(f"**Uncertain:** the range is {me['range']:.1f} points wide.")
    return n


def build(name, label, title, at, wanted):
    C.PREFIX = None
    games, _ = C.prepare(name)
    D = C.Design(games)
    y = C.values(games)["coast"]
    n = len(games)
    text = (C.DATA / "coach_rating_test.md").read_text(encoding="utf-8")
    hl, ridge = (float(v) for v in re.findall(r"Final fit: coast, half-life ([\d.]+), ridge ([\d.]+)", text)[at])
    scale = float(re.findall(r"Conversion factor ([\d.]+)", text)[at])
    days = np.array([g["day"] for g in games])
    now = int(days.max())
    fade = 0.5 ** ((now - days) / (365.25 * hl))
    every_game = np.ones(n, dtype=bool)
    beta_now = D.fit(every_game, fade, y, ridge)[0]
    beta_all = D.fit(every_game, np.ones(n), y, ridge)[0]
    won = np.array([1.0 if g["hs"] > g["as"] else 0.0 for g in games])
    decided = np.array([g["hs"] != g["as"] for g in games])
    per = defaultdict(list)
    for i, g in enumerate(games):
        per[g["hp"]].append((i, 1.0))
        per[g["ap"]].append((i, -1.0))
    regulars = [p for p, v in per.items() if len(v) >= MIN_GAMES]
    idx = [D.people[p] for p in regulars]
    zero_now, zero_all = float(beta_now[idx].mean()), float(beta_all[idx].mean())
    now_val = {p: G.pct((beta_now[D.people[p]] - zero_now) * scale) for p in per}
    career_log = {p: float((beta_all[D.people[p]] - zero_all) * scale) for p in per}
    career_val = {p: G.pct(v) for p, v in career_log.items()}
    every = D.predict(beta_all, np.arange(n))
    ratings, classic = G.table(label), G.table(label, "_classic")
    order = sorted((p for p in regulars if p in ratings), key=lambda p: -float(ratings[p]["win_chance_vs_average"]))
    classic_big = sorted((p for p, r in classic.items() if int(r["games"]) >= MIN_GAMES), key=lambda p: -float(classic[p]["win_chance_vs_average"]))
    wins_all = {p: sum((won[i] if s > 0 else 1 - won[i]) for i, s in per[p] if decided[i]) / max(1, sum(1 for i, s in per[p] if decided[i])) for p in regulars}
    win_order = sorted(regulars, key=lambda p: -wins_all[p])
    league_info = {r["league"]: r for r in json.loads((ROOT / "reports" / "league_ratings.json").read_text(encoding="utf-8"))[label]}
    hist_all = json.loads((H.OUT / f"{label}_all.json").read_text(encoding="utf-8"))
    hist_cl = json.loads((H.OUT / f"{label}_classic.json").read_text(encoding="utf-8"))
    month_days = sorted(int(d) for d in hist_all if date.fromordinal(int(d)).day == 1 or int(d) == max(map(int, hist_all)))
    month_days_c = sorted(int(d) for d in hist_cl if date.fromordinal(int(d)).day == 1 or int(d) == max(map(int, hist_cl)))
    folder = OUT / label
    folder.mkdir(parents=True, exist_ok=True)
    people = [p for p in order if not wanted or p.lower() in wanted]
    for p in people:
        me = per[p]
        ids = np.array([i for i, _ in me])
        side = np.array([s for _, s in me])
        wins = np.array([won[i] if s > 0 else 1 - won[i] for i, s in me])
        ok = decided[ids]
        r = ratings[p]
        c = classic.get(p)
        opp = [games[i]["ap"] if s > 0 else games[i]["hp"] for i, s in me]
        weights = fade[ids]
        total = float(weights.sum())
        rating, career = float(r["win_chance_vs_average"]), float(r["career"])
        rank = order.index(p) + 1
        recent = days[ids] >= now - RECENT
        out = [f"# {p}: {title}", ""]
        w, l = int((wins * ok).sum()), int(((1 - wins) * ok).sum())
        out += [f"| Rating | Rank | Career | Record | Last played |", "| --- | --- | --- | --- | --- |",
                f"| {rating:.1f}% (range {r['low']}-{r['high']}) | {rank} of {len(order)} | {career:.1f}% | {rec(w, l, int((~ok).sum()))} ({share(w, l)}) | {r['last_played']} |", ""]
        # Classic
        is_classic = np.array([games[i]["classic"] for i in ids])
        out += ["## Classic", ""]
        cw, cl_, ct = int((wins * ok)[is_classic].sum()), int(((1 - wins) * ok)[is_classic].sum()), int((~ok & is_classic).sum())
        classic_weight = 100 * float(weights[is_classic].sum()) / total
        if is_classic.any():
            cval = [(k, career_val[opp[k]]) for k in np.nonzero(is_classic)[0]]
            rw, rl = int((wins * ok)[is_classic & recent].sum()), int(((1 - wins) * ok)[is_classic & recent].sum())
            rank_c = f"{classic_big.index(p) + 1} of {len(classic_big)}" if p in classic_big else "under 100 games"
            out += ["| Classic rating | Rank | Record | Last 3 years | Opponents | Share of Rating's weight |", "| --- | --- | --- | --- | --- | --- |",
                    (f"| {c['win_chance_vs_average']}% (range {c['low']}-{c['high']}) | {rank_c} | " if c else "| — | — | ") + f"{rec(cw, cl_, ct)} ({share(cw, cl_)}) | {rec(rw, rl) if rw + rl else '—'} ({share(rw, rl)}) | {np.mean([v for _, v in cval]):.1f} | {classic_weight:.0f}% |", ""]
            teams = defaultdict(lambda: [0, 0, 0, 0.0])
            leagues_c = defaultdict(lambda: [0, 0, 0, Counter()])
            for (i, s), win, good in zip(me, wins, ok):
                g = games[i]
                if not g["classic"]:
                    continue
                team = g["ht"] if s > 0 else g["at"]
                t = teams[team]
                lg = leagues_c[g["league"]]
                lg[3][team] += 1
                if not good:
                    t[2] += 1
                    lg[2] += 1
                    continue
                t[0 if win else 1] += 1
                lg[0 if win else 1] += 1
                own = beta_all[D.teams[team]] if team in D.teams and D.cols[i, 2] != D.home else 0.0
                t[3] += 1 / (1 + math.exp(-((every[i] * s - own) * scale)))
            rows = sorted(((100 * tw / (tw + tl) - 100 * pr / (tw + tl), tm, tw, tl, tt, 100 * pr / (tw + tl)) for tm, (tw, tl, tt, pr) in teams.items() if tw + tl + tt >= MIN_TEAM and tw + tl), reverse=True)
            if rows:
                out += [f"**Teams with {MIN_TEAM}+ games**", "", "| Team | Record | Win % | Predicted with an average team | Above |", "| --- | --- | --- | --- | --- |"]
                out += [f"| {tm} | {rec(tw, tl, tt)} | {100 * tw / (tw + tl):.1f}% | {pr:.1f}% | {d:+.1f} |" for d, tm, tw, tl, tt, pr in rows] + [""]
            out += ["**Classic leagues**", "", "| League | First game | Team | Record | Win % | League strength, at the start | League strength, one scale |", "| --- | --- | --- | --- | --- | --- | --- |"]
            for lg in sorted(leagues_c, key=lambda x: league_info.get(x, {}).get("start", 0), reverse=True):
                lw, ll, lt, tm = leagues_c[lg]
                inf = league_info.get(lg, {})
                out.append(f"| `{lg}` | {date.fromordinal(inf['start']).isoformat() if inf else '—'} | {'/'.join(t for t, _ in tm.most_common(2))} | {rec(lw, ll, lt)} | {share(lw, ll)} | {LR.fmt(inf.get('start_rating'))} | {LR.fmt(inf.get('scale_rating'))} |")
            out.append("")
        else:
            out += ["No Classic games on this system.", ""]
        # Trend
        offsets = (every[ids] * side) * scale - (beta_all[D.people[p]] - zero_all) * scale - zero_all * scale + zero_all * scale
        offsets = (every[ids] * side - beta_all[D.people[p]]) * scale + zero_all * scale
        years = np.array([date.fromordinal(int(days[i])).year for i in ids])
        opp_career = np.array([career_val[o] for o in opp])
        out += ["## Rating over time", ""]
        made = chart(folder / f"{safe(p)}.svg",
                     {"all": [(d, G.pct(hist_all[str(d)][p][0])) for d in month_days if p in hist_all[str(d)] and hist_all[str(d)][p][1] > 0],
                      "classic": [(d, G.pct(hist_cl[str(d)][p][0])) for d in month_days_c if p in hist_cl[str(d)] and hist_cl[str(d)][p][1] > 0]}, "Rating", "Classic rating")
        if made:
            out += [f"![Rating over time]({safe(p)}.svg)", ""]
        out += ["| Year | Games | Record | Win % | Opponents | Strength |", "| --- | --- | --- | --- | --- | --- |"]
        last_year = None
        for yr in sorted(set(years)):
            m = years == yr
            dm = m & ok
            yw, yl = int(wins[dm].sum()), int((1 - wins[dm]).sum())
            sv = "—"
            if dm.sum() >= MIN_YEAR:
                val = G.pct(G.year_strength(offsets[dm], wins[dm], career_log[p]))
                sv = f"{val:.1f}"
                last_year = (int(yr), val)
            out.append(f"| {yr} | {int(m.sum())} | {rec(yw, yl, int(m.sum() - dm.sum()))} | {share(yw, yl)} | {opp_career[m].mean():.1f} | {sv} |")
        out.append("")
        # Families
        fams = defaultdict(lambda: {"r": [0, 0, 0, 0.0, 0.0, 0], "o": [0, 0, 0, 0.0, 0.0, 0]})
        for k, (i, s) in enumerate(me):
            g = games[i]
            x = fams[LR.family(g["league"])]["r" if recent[k] else "o"]
            if ok[k]:
                x[0 if wins[k] else 1] += 1
            else:
                x[2] += 1
            x[3] += now_val[opp[k]]
            x[4] += weights[k]
            x[5] += 1
        out += ["## League families", ""]
        big_family = None
        recent_opp = float(np.mean([now_val[o] for o, f in zip(opp, recent) if f])) if recent.any() else 0.0
        for key, head in (("r", "Last 3 years"), ("o", "Earlier")):
            rows = sorted(((f, v[key]) for f, v in fams.items() if v[key][5]), key=lambda kv: -kv[1][4])
            if not rows:
                continue
            out += [f"**{head}**", "", "| League family | Games | Record | Win % | Opponents | Share of Rating's weight |", "| --- | --- | --- | --- | --- | --- |"]
            small = [0, 0, 0, 0.0, 0.0, 0]
            count_small = 0
            for f, x in rows:
                if x[5] < MIN_FAMILY:
                    count_small += 1
                    for j in range(6):
                        small[j] += x[j]
                    continue
                wt = 100 * x[4] / total
                out.append(f"| {'**Classic**' if f == 'Classic' else '`' + f + '`'} | {x[5]} | {rec(x[0], x[1], x[2])} | {share(x[0], x[1])} | {x[3] / x[5]:.1f} | {wt:.1f}% |")
                if key == "r" and f != "Classic" and wt >= 25 and not big_family:
                    big_family = (f, wt, x[0], x[1], x[3] / x[5])
            if small[5]:
                out.append(f"| Other families ({count_small}) | {small[5]} | {rec(small[0], small[1], small[2])} | {share(small[0], small[1])} | {small[3] / small[5]:.1f} | {100 * small[4] / total:.1f}% |")
            out.append("")
        # Opponents
        out += ["## Opponents by level", "", "| Opponent's Rating now | Last 3 years | Win % | Earlier | Win % | Share of weight, last 3 years |", "| --- | --- | --- | --- | --- | --- |"]
        for lab, lo, hi in TIERS:
            a, b, wt = [0, 0], [0, 0], 0.0
            for k in range(len(me)):
                v = now_val[opp[k]]
                if lo <= v < hi and ok[k]:
                    (a if recent[k] else b)[0 if wins[k] else 1] += 1
                if lo <= v < hi and recent[k]:
                    wt += weights[k]
            out.append(f"| {lab} | {rec(*a)} | {share(*a)} | {rec(*b)} | {share(*b)} | {100 * wt / total:.1f}% |")
        opp_w = Counter()
        for o, wt in zip(opp, weights):
            opp_w[o] += wt
        top5 = 100 * sum(v for _, v in opp_w.most_common(5)) / total
        top10 = 100 * sum(v for _, v in opp_w.most_common(10)) / total
        out += ["", f"They've faced {len(opp_w)} different opponents. The five most-weighted hold {top5:.0f}% of the Rating's weight, and the ten most-weighted {top10:.0f}%.", ""]
        # Leagues
        lgs = defaultdict(lambda: [0, 0, 0, Counter(), 0])
        for k, (i, s) in enumerate(me):
            g = games[i]
            x = lgs[g["league"]]
            x[0 if wins[k] and ok[k] else 1 if ok[k] else 2] += 1
            x[3][g["ht"] if s > 0 else g["at"]] += 1
        known = [league_info[lg] for lg in lgs if lg in league_info and not league_info[lg]["small"]]
        out += ["## How tough their leagues were", ""]
        if known:
            weight = np.array([sum(lgs[r["league"]][:3]) for r in known], float)
            mean_s = float(np.average([r["scale_rating"] for r in known], weights=weight))
            cl = [r for r in known if r["classic"]]
            ot = [r for r in known if not r["classic"]]
            part = []
            if ot:
                part.append(f"{np.average([r['scale_rating'] for r in ot], weights=[sum(lgs[r['league']][:3]) for r in ot]):.1f} outside Classic")
            if cl:
                part.append(f"{np.average([r['scale_rating'] for r in cl], weights=[sum(lgs[r['league']][:3]) for r in cl]):.1f} in Classic")
            tough = max(known, key=lambda r: r["scale_rating"])
            out += [f"By games played, their leagues average a one-scale strength of {mean_s:.1f}: {' and '.join(part)}. Classic and other leagues use different ratings, so those two aren't directly comparable. Their toughest was `{tough['league']}` at {tough['scale_rating']:.1f}.", ""]
        out += ["**Every league, newest first**", "", "| League | First game | Team | Record | Win % | League strength, one scale |", "| --- | --- | --- | --- | --- | --- |"]
        for lg in sorted(lgs, key=lambda x: league_info.get(x, {}).get("start", 0), reverse=True):
            lw, ll, lt, tm, _ = lgs[lg]
            inf = league_info.get(lg, {})
            team = tm.most_common(1)[0][0] if tm and tm.most_common(1)[0][0] else "—"
            out.append(f"| {'**Classic:** ' if lg.lower().startswith(C.CLASSIC) else ''}`{lg}` | {date.fromordinal(inf['start']).isoformat() if inf else '—'} | {team} | {rec(lw, ll, lt)} | {share(lw, ll)} | {LR.fmt(inf.get('scale_rating'))} |")
        out.append("")
        info = {"rating": rating, "career": career, "last_year": last_year, "rank": rank, "of": len(order), "win_rank": win_order.index(p) + 1, "classic_games": int(is_classic.sum()), "classic_weight": classic_weight,
                "big_family": big_family, "non_classic_weight": 100 - classic_weight, "top5": top5, "recent_opp": recent_opp, "days_away": now - date.fromisoformat(r["last_played"]).toordinal(), "last": r["last_played"],
                "range": float(r["high"]) - float(r["low"])}
        said = notes(info)
        if said:
            at_classic = out.index("## Classic")
            out[at_classic:at_classic] = ["**Notes**", ""] + [f"- {x}" for x in said] + [""]
        out += ["## How to read this", "",
                "- **Rating:** the win chance against an average coach (the mean of coaches with 100+ games), with neutral teams and no home edge, from all leagues except a few outliers. Recent games count more: a game's weight halves every 1.5 years.",
                "- **Career:** the same, with every game counting equally.",
                "- **Classic rating:** the same as Rating, fitted on Classic games alone with team strength taken out. It comes from a separate fit, so it can't be compared directly with Rating.",
                "- **Predicted with an average team:** the win % the coach's strength, the opponent's coach and team, and home ice predict. **Above** is the actual win % minus that. It shows the team's own strength as well as this coach's fit with it, and with few games it's mostly chance.",
                "- **Strength in a year:** one number from that year's wins and losses, given the opponents, teams and home ice, pulled lightly toward the coach's career strength.",
                "- **Opponents:** in Classic and the year table, their career strength; in league families and by level, their Rating now. 50 is an average coach.",
                "- **League strength:** how often the league's coaches would beat an average coach, so higher is tougher. \"At the start\" uses ratings as of its first game; \"one scale\" uses career strengths, so it's fair across years. See `docs/LEAGUE_RATINGS.md`.",
                "- **Notes:** fixed rules that state what the numbers show, not why.",
                "", "Results show how a coach has done, not why, or how they'd do in another league. Chances of 10 or 15 points on a few dozen games can easily be luck.", ""]
        (folder / f"{safe(p)}.md").write_text("\n".join(out), encoding="utf-8")
        breathe()
    print(f"{title}: {len(people)} reports in the private folder", flush=True)


def main():
    gentle()
    wanted = {a.lower() for a in sys.argv[1:]}
    for name, label, title, at in SYSTEMS:
        build(name, label, title, at, wanted)


if __name__ == "__main__":
    main()
