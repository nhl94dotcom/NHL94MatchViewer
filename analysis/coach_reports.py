"""A detailed report per coach, per system, for coaches with 100+ games (2026-11-04, the user). They name real people, so they go only to %USERPROFILE%\\NHL94_League_Data\\coach_guides\\reports, never the
repository; the user shares a report only with that coach's agreement. Run coach_rating.py, coach_rating.py groups, coach_history.py and league_ratings.py first.

Classic comes first in every report, as the league's most important. Then the Rating and its trend (with a chart from the history), league families, opponents by level, how concentrated the opponents are
and every league played, with its strength. The notes and the comments in each section are fixed rules that state what the numbers show, never why a coach played as they did.
python analysis/coach_reports.py NAME [NAME ...]     only those coaches, to check
python analysis/coach_reports.py                     everyone"""
import csv
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
    """Fixed rules. Each states what the numbers show, never why a coach played as they did."""
    n = []
    gap = me["rating"] - me["career"]
    if abs(gap) >= 3:
        n.append(f"**Recent form {'lifts' if gap > 0 else 'lowers'} the Rating.** Recent games count more, and the Rating is {abs(gap):.1f} points {'above' if gap > 0 else 'below'} the Career number, where every game counts the same.")
    if me["last_year"] and abs(me["last_year"][1] - me["rating"]) >= 5:
        y_, v = me["last_year"]
        n.append(f"**The latest year doesn't match the Rating.** Their {y_} results alone rate {v:.1f}, against a Rating of {me['rating']:.1f}. The Rating moves slowly, so it may still be catching up.")
    if me["win_rank"] - me["rank"] >= 15:
        n.append(f"**Tough opponents help this Rating.** They rank {me['rank']} of {me['of']} by Rating but {me['win_rank']} by win %, because beating strong coaches counts for more than beating weak ones.")
    elif me["rank"] - me["win_rank"] >= 15:
        n.append(f"**Easier opponents hold this Rating down.** They rank {me['win_rank']} by win % but {me['rank']} of {me['of']} by Rating, because beating weaker coaches counts for less.")
    if me["classic_games"] == 0:
        n.append("**No Classic games on this system.**")
    elif me["classic_weight"] < 10:
        n.append(f"**Little of this Rating comes from Classic:** only {me['classic_weight']:.0f}% of its weight.")
    if me["big_family"]:
        fam, wt, wins, losses, opp = me["big_family"]
        n.append(f"**A lot rests on one kind of league.** `{fam}` holds {wt:.0f}% of the weight, at {rec(wins, losses)} ({share(wins, losses)}) against opponents averaging {opp:.1f}. All their recent opponents average {me['recent_opp']:.1f}.")
    if me["non_classic_weight"] >= 50:
        n.append(f"**The Rating can't separate coach from roster outside Classic.** It allows for team strength only in Classic. {me['non_classic_weight']:.0f}% of the weight comes from other leagues, where a strong roster counts as the coach's own strength.")
    if me["top5"] >= 50:
        n.append(f"**A small group of opponents matters a lot.** The five opponents who count most hold {me['top5']:.0f}% of the Rating's weight.")
    if me["days_away"] >= 365:
        n.append(f"**They haven't played lately.** Their last game was {me['last']}, so their games now count for less and the Rating is less certain.")
    if me["range"] >= 8:
        n.append(f"**The Rating is uncertain.** Its range is {me['range']:.1f} points wide.")
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
    # an average team: the team terms' mean, weighted by use, as in the team guides
    team_use = Counter()
    for i, g in enumerate(games):
        if D.cols[i, 2] != D.home:
            team_use[g["ht"]] += 1
            team_use[g["at"]] += 1
    team_mean = sum(beta_all[D.teams[t]] * c for t, c in team_use.items()) / max(1, sum(team_use.values()))
    ratings, classic = G.table(label), G.table(label, "_classic")
    order = sorted((p for p in regulars if p in ratings), key=lambda p: -float(ratings[p]["win_chance_vs_average"]))
    classic_big = sorted((p for p, r in classic.items() if int(r["games"]) >= MIN_GAMES), key=lambda p: -float(classic[p]["win_chance_vs_average"]))
    wins_all = {p: sum((won[i] if s > 0 else 1 - won[i]) for i, s in per[p] if decided[i]) / max(1, sum(1 for i, s in per[p] if decided[i])) for p in regulars}
    win_order = sorted(regulars, key=lambda p: -wins_all[p])
    phase = {}
    csv.field_size_limit(10 ** 9)
    with open(C.DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            phase[(row["DateTime"], row["League"], row["HomePlayer"].strip().lower(), row["AwayPlayer"].strip().lower(), row["HomeScore"], row["AwayScore"])] = row["RegOrPlay"]
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
        play = np.array([phase.get(games[i]["key"]) == "P" for i in ids])
        r = ratings[p]
        c = classic.get(p)
        opp = [games[i]["ap"] if s > 0 else games[i]["hp"] for i, s in me]
        weights = fade[ids]
        total = float(weights.sum())
        rating, career = float(r["win_chance_vs_average"]), float(r["career"])
        rank = order.index(p) + 1
        recent = days[ids] >= now - RECENT
        is_classic = np.array([games[i]["classic"] for i in ids])
        fam_of = np.array([LR.family(games[i]["league"]) for i in ids])
        lg_of = np.array([games[i]["league"] for i in ids])
        team_of = np.array([(games[i]["ht"] if s_ > 0 else games[i]["at"]) or "" for i, s_ in me])
        opp_now = np.array([now_val[o] for o in opp])
        opp_career = np.array([career_val[o] for o in opp])
        years = np.array([date.fromordinal(int(days[i])).year for i in ids])

        def tally(mask):
            return int((wins * ok)[mask].sum()), int(((1 - wins) * ok)[mask].sum()), int((~ok & mask).sum())

        def rp_cells(mask):
            """Regular season, its win %, playoffs, its win %."""
            a_, b_ = tally(mask & ~play), tally(mask & play)
            return [rec(*a_) if sum(a_) else "—", share(a_[0], a_[1]), rec(*b_) if sum(b_) else "—", share(b_[0], b_[1])]

        RP = "Regular season | Win % | Playoffs | Win %"
        RP_LINE = "--- | --- | --- | ---"
        name = p
        out = [f"# {p}: {title}", ""]
        out += [f"| Rating | Rank | Career | {RP} | Last played |", f"| --- | --- | --- | {RP_LINE} | --- |",
                f"| {rating:.1f}% (range {r['low']}-{r['high']}) | {rank} of {len(order)} | {career:.1f}% | " + " | ".join(rp_cells(np.ones(len(ids), dtype=bool))) + f" | {r['last_played']} |", ""]
        all_w, all_l, _ = tally(np.ones(len(ids), dtype=bool))
        all_pct = 100 * all_w / max(1, all_w + all_l)
        # Classic
        out += ["## Classic", ""]
        classic_weight = 100 * float(weights[is_classic].sum()) / total
        if is_classic.any():
            rank_c = f"{classic_big.index(p) + 1} of {len(classic_big)}" if p in classic_big else "under 100 games"
            cw, cl_, _ = tally(is_classic)
            rw, rl, _ = tally(is_classic & recent)
            ew, el, _ = tally(is_classic & ~recent)
            opp_c = float(opp_career[is_classic].mean())
            text = [f"In Classic, {name} has won {share(cw, cl_)} of their games, against {all_pct:.1f}% across all leagues, and their Classic opponents have averaged {opp_c:.1f}."]
            if c:
                text.append(f"Their Classic rating of {c['win_chance_vs_average']}% ranks {rank_c}." if p in classic_big else f"Their Classic rating is {c['win_chance_vs_average']}%, unranked because they have under 100 Classic games.")
            if rw + rl >= 30 and ew + el >= 30:
                now_pct, then_pct = 100 * rw / (rw + rl), 100 * ew / (ew + el)
                text.append(f"Over the last 3 years they've won {now_pct:.1f}%, " + ("about the same as" if abs(now_pct - then_pct) < 3 else "up from" if now_pct > then_pct else "down from") + f" {then_pct:.1f}% earlier.")
            pw, pl, _ = tally(is_classic & play)
            sw, sl, _ = tally(is_classic & ~play)
            if pw + pl >= 15 and sw + sl:
                text.append(f"In Classic playoffs they're {rec(pw, pl)} ({share(pw, pl)}), against {share(sw, sl)} in the regular season.")
            elif pw + pl:
                text.append(f"They've played only {pw + pl} Classic playoff games, too few to read much into.")
            out += [" ".join(text), ""]
            out += [f"| Classic rating | Rank | {RP} | Last 3 years | Opponents | Share of Rating's weight |", f"| --- | --- | {RP_LINE} | --- | --- | --- |",
                    (f"| {c['win_chance_vs_average']}% (range {c['low']}-{c['high']}) | {rank_c} | " if c else "| — | — | ") + " | ".join(rp_cells(is_classic)) + f" | {rec(rw, rl) + ' (' + share(rw, rl) + ')' if rw + rl else '—'} | {opp_c:.1f} | {classic_weight:.0f}% |", ""]
            team_rows = []
            for tm in sorted(set(team_of[is_classic])):
                m = is_classic & (team_of == tm)
                tw, tl, tt = tally(m)
                if tw + tl + tt < MIN_TEAM or not tw + tl:
                    continue
                pred = 0.0
                for k in np.nonzero(m & ok)[0]:
                    i, s_ = me[k]
                    own = beta_all[D.teams[tm]] - team_mean if tm in D.teams and D.cols[i, 2] != D.home else 0.0
                    pred += 1 / (1 + math.exp(-((every[i] * s_ - own) * scale)))
                team_rows.append((100 * tw / (tw + tl) - 100 * pred / (tw + tl), tm, tw, tl, tt, 100 * pred / (tw + tl), m))
            team_rows.sort(key=lambda x: -x[0])
            if team_rows:
                out += [f"**Teams with {MIN_TEAM}+ games**", ""]
                if len(team_rows) >= 2:
                    hi_, lo_ = team_rows[0], team_rows[-1]
                    out += [f"Compared with what you'd expect from {name} on an average team, their best results are with {hi_[1]} ({hi_[0]:+.1f} over {hi_[2] + hi_[3]} decided games) and their weakest with {lo_[1]} ({lo_[0]:+.1f} over {lo_[2] + lo_[3]})." + (" This partly reflects how strong those teams are, and with so few games much of it could be chance." if min(hi_[2] + hi_[3], lo_[2] + lo_[3]) < 100 else " This partly reflects how strong those teams are."), ""]
                out += [f"| Team | {RP} | Win %, all | Predicted with an average team | Above |", f"| --- | {RP_LINE} | --- | --- | --- |"]
                out += [f"| {tm} | " + " | ".join(rp_cells(m)) + f" | {100 * tw / (tw + tl):.1f}% | {pr:.1f}% | {d:+.1f} |" for d, tm, tw, tl, tt, pr, m in team_rows] + [""]
            out += ["**Classic leagues**", ""]
            lg_rows = []
            for lg in set(lg_of[is_classic]):
                m = lg_of == lg
                lw, ll, _ = tally(m)
                lg_rows.append((league_info.get(lg, {}).get("start", 0), lg, lw, ll, m))
            lg_rows.sort(key=lambda x: -x[0])
            full = [x for x in lg_rows if x[2] + x[3] >= 20]
            if len(full) >= 2:
                top = max(full, key=lambda x: x[2] / (x[2] + x[3]))
                low = min(full, key=lambda x: x[2] / (x[2] + x[3]))
                top_s, low_s = league_info.get(top[1], {}).get("scale_rating"), league_info.get(low[1], {}).get("scale_rating")
                out += [f"Their best full Classic season was `{top[1]}`, at {share(top[2], top[3])} in a league of strength {LR.fmt(top_s)}. Their weakest was `{low[1]}`, at {share(low[2], low[3])} in a league of strength {LR.fmt(low_s)}.", ""]
            out += [f"| League | First game | Team | {RP} | League strength, at the start | League strength, one scale |", f"| --- | --- | --- | {RP_LINE} | --- | --- |"]
            for st, lg, lw, ll, m in lg_rows:
                inf = league_info.get(lg, {})
                tm = Counter(team_of[m]).most_common(2)
                out.append(f"| `{lg}` | {date.fromordinal(inf['start']).isoformat() if inf else '—'} | {'/'.join(t for t, _ in tm)} | " + " | ".join(rp_cells(m)) + f" | {LR.fmt(inf.get('start_rating'))} | {LR.fmt(inf.get('scale_rating'))} |")
            out.append("")
        else:
            out += [f"{name} hasn't played any Classic games on this system.", ""]
        # Trend
        offsets = (every[ids] * side - beta_all[D.people[p]]) * scale + zero_all * scale
        strengths = []
        rows_y = []
        for yr in sorted(set(years)):
            m = years == yr
            dm = m & ok
            sv = "—"
            if dm.sum() >= MIN_YEAR:
                val = G.pct(G.year_strength(offsets[dm], wins[dm], career_log[p]))
                sv = f"{val:.1f}"
                strengths.append((int(yr), val))
            rows_y.append(f"| {yr} | {int(m.sum())} | " + " | ".join(rp_cells(m)) + f" | {opp_career[m].mean():.1f} | {sv} |")
        last_year = strengths[-1] if strengths else None
        out += ["## Rating over time", ""]
        text = []
        if len(strengths) >= 2:
            first_, last_ = strengths[0], strengths[-1]
            move = last_[1] - first_[1]
            best_y = max(strengths, key=lambda x: x[1])
            text.append(f"Their yearly strength has gone from {first_[1]:.1f} in {first_[0]} to {last_[1]:.1f} in {last_[0]}, " + ("a clear rise" if move >= 5 else "a clear fall" if move <= -5 else "about level overall") + f", with a high of {best_y[1]:.1f} in {best_y[0]}.")
            jumps = [(strengths[k + 1][1] - strengths[k][1], strengths[k + 1][0]) for k in range(len(strengths) - 1)]
            big = max(jumps, key=lambda x: abs(x[0]))
            if abs(big[0]) >= 7:
                text.append(f"The biggest change between years with results was {big[0]:+.1f} points, in {big[1]}.")
            text.append(f"Win % alone can mislead here, because the strength of opponents changes from year to year.")
        elif strengths:
            text.append(f"They have only one year with enough games to rate: {strengths[0][1]:.1f} in {strengths[0][0]}.")
        if text:
            out += [" ".join(text), ""]
        made = chart(folder / f"{safe(p)}.svg",
                     {"all": [(d, G.pct(hist_all[str(d)][p][0])) for d in month_days if p in hist_all[str(d)] and hist_all[str(d)][p][1] > 0],
                      "classic": [(d, G.pct(hist_cl[str(d)][p][0])) for d in month_days_c if p in hist_cl[str(d)] and hist_cl[str(d)][p][1] > 0]}, "Rating", "Classic rating")
        if made:
            out += [f"![Rating over time]({safe(p)}.svg)", ""]
        out += [f"| Year | Games | {RP} | Opponents | Strength |", f"| --- | --- | {RP_LINE} | --- | --- |"] + rows_y + [""]
        # Families
        out += ["## League families", ""]
        big_family = None
        recent_opp = float(opp_now[recent].mean()) if recent.any() else 0.0
        commentary_done = False
        for per_mask, head in ((recent, "Last 3 years"), (~recent, "Earlier")):
            fams_here = sorted(set(fam_of[per_mask]), key=lambda f: -weights[per_mask & (fam_of == f)].sum())
            if not fams_here:
                continue
            if not commentary_done:
                sized = [f for f in fams_here if (per_mask & (fam_of == f)).sum() >= 30]
                if sized:
                    cell = lambda f: tally(per_mask & (fam_of == f))
                    pct_ = lambda f: cell(f)[0] / max(1, cell(f)[0] + cell(f)[1])
                    heavy = fams_here[0]
                    line = f"The largest share of the Rating's weight comes from {'Classic' if heavy == 'Classic' else '`' + heavy + '`'} ({100 * weights[per_mask & (fam_of == heavy)].sum() / total:.0f}%)."
                    if len(sized) >= 2:
                        hi_f, lo_f = max(sized, key=pct_), min(sized, key=pct_)
                        opp_of = lambda f: opp_now[per_mask & (fam_of == f)].mean()
                        line += f" {'Over the last 3 years' if head == 'Last 3 years' else 'Earlier on'}, they've done best in {'Classic' if hi_f == 'Classic' else '`' + hi_f + '`'} ({100 * pct_(hi_f):.1f}%, opponents {opp_of(hi_f):.1f}) and least well in {'Classic' if lo_f == 'Classic' else '`' + lo_f + '`'} ({100 * pct_(lo_f):.1f}%, opponents {opp_of(lo_f):.1f})."
                        line += " Win rates usually fall as opponents get stronger, so compare the two columns together."
                    out += [line, ""]
                    commentary_done = True
            out += [f"**{head}**", "", f"| League family | Games | {RP} | Opponents | Share of Rating's weight |", f"| --- | --- | {RP_LINE} | --- | --- |"]
            small = np.zeros(len(ids), dtype=bool)
            count_small = 0
            for f in fams_here:
                m = per_mask & (fam_of == f)
                if m.sum() < MIN_FAMILY:
                    small |= m
                    count_small += 1
                    continue
                wt = 100 * weights[m].sum() / total
                out.append(f"| {'**Classic**' if f == 'Classic' else '`' + f + '`'} | {int(m.sum())} | " + " | ".join(rp_cells(m)) + f" | {opp_now[m].mean():.1f} | {wt:.1f}% |")
                if head == "Last 3 years" and f != "Classic" and wt >= 25 and not big_family:
                    fw, fl, _ = tally(m)
                    big_family = (f, wt, fw, fl, float(opp_now[m].mean()))
            if small.any():
                out.append(f"| Other families ({count_small}) | {int(small.sum())} | " + " | ".join(rp_cells(small)) + f" | {opp_now[small].mean():.1f} | {100 * weights[small].sum() / total:.1f}% |")
            out.append("")
        # Opponents
        tier_rows = []
        for lab, lo, hi in TIERS:
            m = (opp_now >= lo) & (opp_now < hi)
            ra, rb, _ = tally(m & recent)
            ea, eb, _ = tally(m & ~recent)
            tier_rows.append((lab, ra, rb, ea, eb, 100 * weights[m & recent].sum() / total))
        out += ["## Opponents by level", ""]
        text = []
        solid = [t for t in tier_rows if t[1] + t[2] >= 30]
        if solid:
            even = next((t for t in solid if t[1] / (t[1] + t[2]) >= 0.5), None)
            if even:
                text.append(f"Over the last 3 years, the toughest opponents they've had a winning record against are those rated {even[0]} ({share(even[1], even[2])}).")
            else:
                text.append("Over the last 3 years, they haven't had a winning record against any level with 30+ games.")
            moved = [(100 * t[1] / (t[1] + t[2]) - 100 * t[3] / (t[3] + t[4]), t[0]) for t in solid if t[3] + t[4] >= 30]
            if moved:
                ups = sum(1 for d, _ in moved if d >= 3)
                downs = sum(1 for d, _ in moved if d <= -3)
                if ups == len(moved):
                    text.append("They've improved against every level compared with earlier years.")
                elif downs == len(moved):
                    text.append("They've done worse against every level compared with earlier years.")
                else:
                    best_d = max(moved)
                    text.append(f"Compared with earlier years, the biggest change is {best_d[0]:+.1f} points against opponents rated {best_d[1]}." if abs(best_d[0]) >= 3 else "Their results by level are about the same as in earlier years.")
        if text:
            out += [" ".join(text), ""]
        out += ["| Opponent's Rating now | Last 3 years | Win % | Earlier | Win % | Share of weight, last 3 years |", "| --- | --- | --- | --- | --- | --- |"]
        out += [f"| {lab} | {rec(ra, rb)} | {share(ra, rb)} | {rec(ea, eb)} | {share(ea, eb)} | {wt:.1f}% |" for lab, ra, rb, ea, eb, wt in tier_rows]
        opp_w = Counter()
        for o, wt in zip(opp, weights):
            opp_w[o] += wt
        top5 = 100 * sum(v for _, v in opp_w.most_common(5)) / total
        top10 = 100 * sum(v for _, v in opp_w.most_common(10)) / total
        out += ["", f"They've faced {len(opp_w)} different opponents. The five who count most hold {top5:.0f}% of the Rating's weight, and the ten who count most hold {top10:.0f}%.", ""]
        # Leagues
        out += ["## How tough their leagues were", ""]
        known = [league_info[lg] for lg in set(lg_of) if lg in league_info and not league_info[lg]["small"]]
        if known:
            size = lambda inf: int((lg_of == inf["league"]).sum())
            common = [LR.on_all_leagues(x) for x in known]
            mean_s = float(np.average([x["scale_rating"] for x in common], weights=[size(x) for x in common]))
            cl = [x for x in known if x["classic"]]
            ot = [x for x in known if not x["classic"]]
            part = []
            if ot:
                part.append(f"{np.average([x['scale_rating'] for x in common if not x['classic']], weights=[size(x) for x in common if not x['classic']]):.1f} outside Classic")
            if cl:
                part.append(f"{np.average([x['scale_rating'] for x in common if x['classic']], weights=[size(x) for x in common if x['classic']]):.1f} in Classic")
            tough = max(common, key=lambda x: x["scale_rating"])
            out += [f"A league strength of 50 means its coaches are about as good as an average coach. By games played, {name}'s leagues average {mean_s:.1f}: {' and '.join(part)}. These use all-leagues ratings so they can be compared, so the Classic numbers differ from those in the Classic section. Their toughest was `{tough['league']}`, at {tough['scale_rating']:.1f}.", ""]
        out += ["**Every league, newest first**", "", f"| League | First game | Team | {RP} | League strength, one scale |", f"| --- | --- | --- | {RP_LINE} | --- |"]
        for lg in sorted(set(lg_of), key=lambda x: league_info.get(x, {}).get("start", 0), reverse=True):
            m = lg_of == lg
            inf = league_info.get(lg, {})
            tm = Counter(team_of[m]).most_common(1)[0][0] or "—"
            out.append(f"| {'**Classic:** ' if lg.lower().startswith(C.CLASSIC) else ''}`{lg}` | {date.fromordinal(inf['start']).isoformat() if inf else '—'} | {tm} | " + " | ".join(rp_cells(m)) + f" | {LR.fmt(inf.get('scale_rating'))} |")
        out.append("")
        info = {"rating": rating, "career": career, "last_year": last_year, "rank": rank, "of": len(order), "win_rank": win_order.index(p) + 1, "classic_games": int(is_classic.sum()), "classic_weight": classic_weight,
                "big_family": big_family, "non_classic_weight": 100 - classic_weight, "top5": top5, "recent_opp": recent_opp, "days_away": now - date.fromisoformat(r["last_played"]).toordinal(), "last": r["last_played"],
                "range": float(r["high"]) - float(r["low"])}
        said = notes(info)
        if said:
            at_classic = out.index("## Classic")
            out[at_classic:at_classic] = ["**What to know about this Rating**", ""] + [f"- {x}" for x in said] + [""]
        out += ["## How to read this", "",
                "- **Rating:** the chance of beating an average coach (the mean of coaches with 100+ games), with neutral teams and no home-ice edge, from all leagues except a few outliers. Recent games count more: a game's weight halves every 1.5 years.",
                "- **Career:** the same, with every game counting equally.",
                "- **Classic rating:** the same as Rating, from Classic games alone, with team strength taken out. It comes from a separate calculation, so it can't be compared directly with Rating.",
                "- **Regular season and Playoffs:** the record in each, as the league's records mark them. Other columns count both.",
                "- **Predicted with an average team:** the win % you'd expect in those same games if the coach had used an average team in place of this one, from the coach's strength, the opposing coach and team, and home ice. An average team is the average of the teams people actually use. **Above** is the actual win % minus that. It shows the team's own strength as well as this coach's fit with it, and with few games it's mostly chance.",
                "- **Strength in a year:** one number from that year's wins and losses, given the opponents, teams and home ice, pulled lightly toward the coach's career strength.",
                "- **Opponents:** how good the opposing coaches are, where 50 is an average coach. In Classic and the year table it's their career strength; in league families and by level it's their Rating now.",
                "- **Share of Rating's weight:** how much those games count toward the Rating, given that recent games count more.",
                "- **League strength:** how often the league's coaches would beat an average coach, so higher is tougher. \"At the start\" uses ratings as of its first game; \"one scale\" uses career strengths, so it's fair across years. See `docs/LEAGUE_RATINGS.md`.",
                "", "The comments in this report are written by fixed rules from the numbers beside them. They show how a coach has done, not why, or how they'd do in another league. Gaps of 10 or 15 points over a few dozen games can easily be luck.", ""]
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
