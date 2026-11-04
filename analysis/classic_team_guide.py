"""The team guides: docs/TEAM_GUIDE_GENESIS.md and docs/TEAM_GUIDE_SNES.md, every retail team in the Classic leagues (2026-11-04, the user, to hand out).
Aggregates only; no coach is named. Run coach_rating.py groups and coach_team_levels.py first: the conversion factors and settings come from the former,
the values by level of player from the latter (reports/classic_team_levels.json).

For each team: strength now (recent games count more, as in the coach table) and over all years, both from the rating's equation with spreads from
resampling whole leagues; how it does by level of player; its record against what its coaches, home ice and the other team predict, by era and level; team
stats a game with ranks; the ROM's ratings with ranks; its leading players. Also writes reports/classic_team_readings.md, the tables for COACH_RATING section 10.
python analysis/classic_team_guide.py"""
import ast
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scoring_map"))
import coach_rating as C  # noqa: E402
import coach_team_levels as CTL  # noqa: E402
import league_team_study as L  # noqa: E402
from league_home_study import RETAIL_HOME_AWAY  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

ROOT = HERE.parent
SYSTEMS = (("All_Games_GENS.csv", "Genesis", "GENESIS", 0, "9438f5dd_a738ea1c.bin", "TEAM_GUIDE_GENESIS.md"),
           ("All_Games_SNES.csv", "SNES", "SNES", 1, "cd85e387.smc", "TEAM_GUIDE_SNES.md"))
MIN_FULL, MIN_LEVEL, DRAWS = 100, 150, 200
ERAS = (("2013-2019", 2013, 2019), ("2020-2022", 2020, 2022), ("2023-2026", 2023, 2026))
LENSES = ("coach", "strength", "name")


def nth(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def sign(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def reading(lv):
    """The plain reading of a team from its level values (see COACH_RATING section 10)."""
    H, Lo, T, R = (lv["coach"]["levels"].get("0"), lv["coach"]["levels"].get("2"), lv["name"]["levels"].get("0"), lv["name"]["levels"].get("2"))
    vals = [x[0] for x in (H, Lo, T, R) if x]
    high = [x[0] for x in (H, T) if x]
    low = [x[0] for x in (Lo, R) if x]
    state = lambda v: "good" if v and min(v) >= 1.5 else "poor" if v and max(v) <= -1.5 else None
    sh, sl = state(high), state(low)
    if sh and sh == sl:
        text = f"{sh.capitalize()} at both levels"
    elif vals and min(vals) >= 1:
        text = "Slightly good at both levels"
    elif vals and max(vals) <= -1:
        text = "Slightly poor at both levels"
    elif vals and max(abs(v) for v in vals) <= 3:
        text = "About average at both levels"
    elif sh or sl:
        parts = [f"{sh} for high-level players" if sh else None, f"{sl} for low-level players" if sl else None]
        text = "; ".join(p for p in parts if p)
        text = text[0].upper() + text[1:]
    else:
        text = "Unclear"
    gaps = [lv[k].get("gap") for k in LENSES]
    if all(gaps):
        signs = {np.sign(g[0]) for g in gaps}
        if len(signs) == 1:
            side = "high" if signs == {1.0} else "low"
            z = [abs(g[0]) / g[1] if g[1] else 0 for g in gaps]
            if sum(x >= 1.5 for x in z) >= 2:
                text += "; the gap is likely real" if f"ood for {side}-level" in text else f"; likely better for {side}-level players"
            elif sum(x >= 1 for x in z) >= 2:
                text += "; the gap leans that way" if f"ood for {side}-level" in text else f"; leaning toward {side}-level players"
    few = sum(1 for k, level in (("coach", "0"), ("coach", "2"), ("name", "0"), ("name", "2")) if lv[k]["levels"].get(level, [0, 0, 0])[2] < MIN_LEVEL)
    return text + ("; few games" if few >= 2 else "")


def cell(x):
    if not x:
        return "too few"
    return f"{sign(x[0])} ± {x[1]:.1f}" + ("*" if len(x) > 2 and x[2] < MIN_LEVEL else "")


def bare(x, few=True):
    if not x:
        return "none"
    return f"({sign(x[0])})" if few and x[2] < MIN_LEVEL else sign(x[0])


def per(s, key, n):
    return s[key] / n if n else 0


class Tally:
    def __init__(self):
        self.w = self.l = self.t = 0
        self.exp = 0.0

    def add(self, a, b, p):
        if a > b:
            self.w += 1
        elif a < b:
            self.l += 1
        else:
            self.t += 1
            return
        self.exp += p

    def n(self):
        return self.w + self.l

    def row(self, label):
        m = self.n()
        if not m:
            return f"| {label} | no games | | | |"
        rec = f"{self.w:,}-{self.l:,}" + (f"-{self.t}" if self.t else "")
        return f"| {label} | {rec} | {100 * self.w / m:.1f}% | {100 * self.exp / m:.1f}% | {sign(100 * (self.w - self.exp) / m)} ± {50 / m ** 0.5:.1f} |"


def build(name, label, tab, at, romfile, outfile, levels, conv, settings, readings):
    C.PREFIX = "classic"
    games, _ = C.prepare(name)
    D = C.Design(games)
    y = C.values(games)["coast"]
    n = len(games)
    days = np.array([g["day"] for g in games])
    now = days.max()
    hl, ridge = settings
    every = np.ones(n, dtype=bool)
    scale = conv
    w_now = 0.5 ** ((now - days) / (365.25 * hl))
    beta_now = D.fit(every, w_now, y, ridge)[0]
    beta_all = D.fit(every, np.ones(n), y, ridge)[0]
    won = np.array([g["hs"] > g["as"] for g in games], float)
    decided = np.array([g["hs"] != g["as"] for g in games])
    idx = np.nonzero(decided)[0]
    hist_scale = C.scale_for(D.predict(beta_all, idx), won[idx])
    # zero is the average team as used, weighted by appearances, as in the values by level of player
    used_n = Counter()
    for g in games:
        used_n[g["ht"]] += 1
        used_n[g["at"]] += 1
    team_list = sorted(D.teams)
    weights = np.array([used_n[t] for t in team_list], float)
    centre = lambda b: float((np.array([b[D.teams[t]] for t in team_list]) * weights).sum() / weights.sum())
    pts = lambda b, t: 100 / (1 + np.exp(-(b[D.teams[t]] - centre(b)) * scale)) - 50
    zero_all = centre(beta_all)
    leagues = sorted({g["league"] for g in games})
    where = defaultdict(list)
    for i, g in enumerate(games):
        where[g["league"]].append(i)
    rng = np.random.default_rng(94)
    runs_now, runs_all = defaultdict(list), defaultdict(list)
    for _ in range(DRAWS):
        c = np.zeros(n)
        for lg in rng.choice(leagues, len(leagues)):
            c[where[lg]] += 1
        m = c > 0
        b1 = D.fit(m, c * w_now, y, ridge)[0]
        b2 = D.fit(m, c, y, ridge)[0]
        for t in D.teams:
            runs_now[t].append(pts(b1, t))
            runs_all[t].append(pts(b2, t))
        breathe()
    now_v = {t: (float(pts(beta_now, t)), float(np.std(runs_now[t]))) for t in D.teams}
    all_v = {t: (float(pts(beta_all, t)), float(np.std(runs_all[t]))) for t in D.teams}
    # levels of coach and league, as in coach_team_levels
    sides = Counter()
    players, league_n = defaultdict(set), Counter()
    for g in games:
        sides[g["hp"]] += 1
        sides[g["ap"]] += 1
        players[g["league"]] |= {g["hp"], g["ap"]}
        league_n[g["league"]] += 1
    coach_level = CTL.thirds([(p, beta_all[i], sides[p]) for p, i in D.people.items()])
    named = CTL.top_leagues(players)
    # the raw rows: every stat, by team
    csv.field_size_limit(10 ** 9)
    S = defaultdict(lambda: defaultdict(float))
    rec = defaultdict(lambda: defaultdict(Tally))
    used = defaultdict(lambda: {"leagues": set(), "top": set(), "coaches": set(), "last": 0})
    scorers = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0, ""]))
    goalies = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    names = defaultdict(Counter)
    total_leagues = set()
    with open(C.DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1" or not r["League"].lower().startswith(C.CLASSIC):
                continue
            hp, ap = r["HomePlayer"].strip().lower(), r["AwayPlayer"].strip().lower()
            d = C.day(r["DateTime"])
            if not hp or not ap or hp == ap or not d:
                continue
            total_leagues.add(r["League"])
            ht, at_ = r["HomeTeamAbbrev"].strip(), r["AwayTeamAbbrev"].strip()
            hs, as_ = int(float(r["HomeScore"])), int(float(r["AwayScore"]))
            year = int(r["DateTime"].split("-")[0])
            both = ht in D.teams and at_ in D.teams and ht != at_
            x = beta_all[D.people[hp]] - beta_all[D.people[ap]] + beta_all[D.home]
            for side, other, t, o, me, you, a, b, home in (("Home", "Away", ht, at_, hp, ap, hs, as_, True), ("Away", "Home", at_, ht, ap, hp, as_, hs, False)):
                s = S[t]
                names[t][r[side + "Team"].strip()] += 1
                s["sides"] += 1
                s["gf"] += a
                s["ga"] += b
                val = lambda c_, k=side: float(r[k + c_] or 0)
                s["sf"] += val("Shots")
                s["sa"] += val("Shots", other)
                s["ppg"] += val("PPGoals")
                s["ppt"] += val("PPTries")
                s["ppag"] += val("PPGoals", other)
                s["ppat"] += val("PPTries", other)
                s["shg"] += val("SHGoals")
                s["otg"] += val("OneTimerGoals")
                s["ott"] += val("OneTimerTries")
                s["brg"] += val("BreakGoals")
                s["brt"] += val("BreakTries")
                s["chk"] += val("Checks")
                s["pim"] += val("PIM")
                s["fow"] += val("FaceoffWins")
                s["fot"] += float(r["FaceoffTotal"] or 0)
                s["azt"] += val("AttackZoneTime")
                s["pc"] += val("PassComps")
                s["pt"] += val("PassTries")
                u = used[t]
                u["leagues"].add(r["League"])
                u["coaches"].add(me)
                u["last"] = max(u["last"], d)
                if named.get(r["League"]) == 0:
                    u["top"].add(r["League"])
                # expected from the coaches, home ice and the other team, with this team taken as the average team in use
                xx = x if home else -x
                if both:
                    xx += zero_all - beta_all[D.teams[o]]
                p = float(1 / (1 + np.exp(-hist_scale * xx)))
                tally = rec[t]
                tally["all"].add(a, b, p)
                tally["Regular season" if r["RegOrPlay"] == "R" else "Playoffs"].add(a, b, p)
                tally["Home" if home else "Away"].add(a, b, p)
                for lab, y0, y1 in ERAS:
                    if y0 <= year <= y1:
                        tally[lab].add(a, b, p)
                tally[("High", "Mid", "Low")[coach_level[me]] + " coach"].add(a, b, p)
                if named.get(r["League"]) == 0:
                    tally["Top league"].add(a, b, p)
                elif named.get(r["League"]) == 2:
                    tally["Other leagues"].add(a, b, p)
                try:
                    for q in ast.literal_eval(r[side + "Players"]) if r[side + "Players"] else []:
                        row = scorers[t][str(q[1])]
                        row[0] += q[3]
                        row[1] += q[4]
                        row[2] += q[5]
                        row[3] += q[6]
                        row[4] += q[7]
                        row[5] = q[2]
                    for q in ast.literal_eval(r[side + "Goalies"]) if r[side + "Goalies"] else []:
                        goalies[t][str(q[1])][0] += q[2]
                        goalies[t][str(q[1])][1] += q[4]
                except (ValueError, SyntaxError, IndexError, TypeError):
                    pass
    # the ROM
    rom_teams = getattr(L, tab.lower() if tab == "SNES" else "genesis").read_teams(L.rom(romfile))
    rom_t = {t["abbr"]: t for t in rom_teams}
    ratings = L.ratings(rom_teams)
    retail = [t for t in ratings if t not in ("ASE", "ASW")]
    rank_rom = {k: sorted(retail, key=lambda t: -ratings[t][k]) for k in next(iter(ratings.values()))}
    # stats and ranks
    full = [t for t in S if S[t]["sides"] >= MIN_FULL and t in D.teams and t in levels]
    full.sort(key=lambda t: -now_v[t][0])
    rank_now = sorted(full, key=lambda t: -now_v[t][0])
    rank_all = sorted(full, key=lambda t: -all_v[t][0])
    frac = lambda a, b: a / b if b else 0
    STATS = (("Goals for", lambda s: s["gf"] / s["sides"], "{:.2f}", 1), ("Goals against", lambda s: s["ga"] / s["sides"], "{:.2f}", -1),
             ("Shots for", lambda s: s["sf"] / s["sides"], "{:.1f}", 1), ("Shots against", lambda s: s["sa"] / s["sides"], "{:.1f}", -1),
             ("Shooting %", lambda s: 100 * frac(s["gf"], s["sf"]), "{:.1f}", 1), ("Save %", lambda s: 100 * (1 - frac(s["ga"], s["sa"])), "{:.1f}", 1),
             ("Power play %", lambda s: 100 * frac(s["ppg"], s["ppt"]), "{:.1f}", 1), ("Penalty kill %", lambda s: 100 * (1 - frac(s["ppag"], s["ppat"])), "{:.1f}", 1),
             ("One-timer goals", lambda s: s["otg"] / s["sides"], "{:.2f}", 1), ("Breakaway goals", lambda s: s["brg"] / s["sides"], "{:.2f}", 1),
             ("Checks", lambda s: s["chk"] / s["sides"], "{:.1f}", 1), ("Penalty minutes", lambda s: s["pim"] / s["sides"], "{:.1f}", -1),
             ("Faceoffs won %", lambda s: 100 * frac(s["fow"], s["fot"]), "{:.1f}", 1), ("Attack zone time, seconds", lambda s: s["azt"] / s["sides"], "{:.0f}", 1),
             ("Pass completion %", lambda s: 100 * frac(s["pc"], s["pt"]), "{:.1f}", 1))
    stat_rank = {lab: sorted(full, key=lambda t: -d * f(S[t])) for lab, f, _, d in STATS}
    city = {t: names[t].most_common(1)[0][0] for t in names}
    last = C.date.fromordinal(int(now)).isoformat()
    system_name = "Genesis" if tab == "GENESIS" else "SNES"
    out = [f"# {system_name} Classic team guide\n",
           f"Every retail team in the {system_name} Classic leagues (names starting `Classic_Spring`, `Classic_Summer` or `Classic_Fall`): {n:,} games in {len(total_leagues)} leagues, through {last}. "
           "No coach is named. The method is in [COACH_RATING.md](COACH_RATING.md).\n",
           "## How to read this guide\n",
           "- **Strength** is points of win chance above or below 50 against the average team as used in these leagues, with even coaches and no home edge, with who was coaching taken out. "
           "\"Now\" counts recent games more; \"all years\" counts every game the same. ± is one spread, from resampling whole leagues.\n",
           "- **Expected** is what the team's coaches, home ice and the other team predict if this team were the average team in use. A record above expected is what the team itself added.\n",
           "- **By level of player** says how much better that level does with this team than with its other teams, using all years. Level is measured three ways: each coach's career strength (high and low are about a third of appearances each), "
           "each league's coach strength, and each season's top league (the one with the most As) against its others. A * marks under 150 appearances.\n",
           "- **Readings** go by rule, from the coach and top-league rows. Good or poor means +1.5 or better, or −1.5 or worse, in both rows for that level. \"Slightly\" means +1 or −1 in all of them, and \"about average\" means all within 3. "
           "\"Likely\" and \"leaning\" need the gap to point the same way all three ways, at 1.5 or 1 spreads in two of them.\n",
           "- **Most differences between levels don't repeat well** when half the leagues are compared with the other half, so treat them as ideas to test. "
           + ("The overall team order is sturdier.\n" if tab == "GENESIS" else "On the SNES, the team order itself depends more on the method than on the Genesis, so read small gaps as ties.\n"),
           "- **Ranks** run 1st = best (for goals against, shots against and penalty minutes, 1st is fewest; for checks, the most). They compare the teams in this guide.\n",
           "- **Ratings** are the ROM's, as rosters: the top 12 skaters' mean and the higher-rated goalie. "
           + ("Hot and cold values change them a little in play.\n" if tab == "GENESIS" else "The SNES hot / cold bug maxes about 46% of ratings each game, but never Weight, so ratings other than Weight count for less than they look.\n"),
           "- **Results show what happened, not why.** Players choose or are given teams, and rarely used teams rest on few coaches.\n",
           "\n## All teams\n",
           "| # | Team | Now | All years | Record | Win % | Expected | Reading |\n| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, t in enumerate(full, 1):
        a = rec[t]["all"]
        out.append(f"| {i} | {city[t]} ({t}) | {sign(now_v[t][0])} | {sign(all_v[t][0])} | {a.w:,}-{a.l:,}" + (f"-{a.t}" if a.t else "") + f" | {100 * a.w / a.n():.1f}% | {100 * a.exp / a.n():.1f}% | {reading(levels[t])} |")
    rest = sorted((t for t in S if t not in full), key=lambda t: -S[t]["sides"])
    if rest:
        out.append("\nToo few games for a full entry: " + "; ".join(f"{city[t]} ({t}) {rec[t]['all'].w}-{rec[t]['all'].l}" + (f"-{rec[t]['all'].t}" if rec[t]['all'].t else "") for t in rest) + ".")
    for i, t in enumerate(full, 1):
        s, a, lv, u = S[t], rec[t]["all"], levels[t], used[t]
        out.append(f"\n## {i}. {city[t]} ({t})\n")
        out.append(f"**{reading(lv)}.** Strength {sign(now_v[t][0])} ± {now_v[t][1]:.1f} now ({nth(rank_now.index(t) + 1)} of {len(full)}), {sign(all_v[t][0])} ± {all_v[t][1]:.1f} over all years ({nth(rank_all.index(t) + 1)}).\n")
        out.append(f"Used in {len(u['leagues'])} of {len(total_leagues)} leagues ({len(u['top'])} of them a season's top league), by {len(u['coaches'])} coaches, {int(s['sides']):,} games, most recently {C.date.fromordinal(u['last']).isoformat()}.\n")
        out.append("**By level of player**\n\n| | High level | Low level | High minus low |\n| --- | --- | --- | --- |")
        for lab, key in (("By coach", "coach"), ("By league strength", "strength"), ("Top league against others", "name")):
            lvl = lv[key]["levels"]
            gap = lv[key].get("gap")
            out.append(f"| {lab} | {cell(lvl.get('0'))} | {cell(lvl.get('2'))} | {cell(gap)} |")
        out.append("\n**Record**\n\n| | Record | Win % | Expected | Against expected |\n| --- | --- | --- | --- | --- |")
        out.append(a.row("All games"))
        for lab in ("Regular season", "Playoffs", "Home", "Away", *[e[0] for e in ERAS], "High coach", "Mid coach", "Low coach", "Top league", "Other leagues"):
            if rec[t][lab].n():
                out.append(rec[t][lab].row(lab))
        out.append("\n**A game**\n\n| Stat | Value | Rank | | Stat | Value | Rank |\n| --- | --- | --- | --- | --- | --- | --- |")
        half = (len(STATS) + 1) // 2
        for j in range(half):
            lab, f, fmt, _ = STATS[j]
            left = f"{lab} | {fmt.format(f(s))} | {nth(stat_rank[lab].index(t) + 1)}"
            if j + half < len(STATS):
                lab2, f2, fmt2, _ = STATS[j + half]
                right = f"{lab2} | {fmt2.format(f2(s))} | {nth(stat_rank[lab2].index(t) + 1)}"
            else:
                right = " | | "
            out.append(f"| {left} | | {right} |")
        if t in ratings:
            order = ("Overall", "Weight", "Speed", "Agility", "Shot Power", "Shot Accuracy", "Checking", "Goalie Agility")
            out.append("\n**Ratings**\n\n| " + " | ".join(order) + " |\n| " + " | ".join("---" for _ in order) + " |")
            out.append("| " + " | ".join(f"{ratings[t][k]:.1f} ({nth(rank_rom[k].index(t) + 1)})" for k in order) + " |")
            ha = RETAIL_HOME_AWAY.get(t)
            if ha:
                out.append(f"\nHidden bonus: +{ha[0]} at home, −{ha[1]} away.")
        roster = {p["name"].lower(): p for p in rom_t[t]["players"]} if t in rom_t else {}
        top = sorted(scorers[t].items(), key=lambda kv: -kv[1][2])[:6]
        out.append("\n**Leading skaters** (per team game)\n\n| Player | Pos | Goals | Assists | Points | Checks | Overall | Weight | Speed | Shot Power | Shot Acc |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for nm, q in top:
            p = roster.get(nm.lower())
            rate = f"{p['ovr']} | {p['a'][0]} | {p['a'][2]} | {p['a'][5]} | {p['a'][9]}" if p else " | | | | "
            out.append(f"| {nm} | {q[5]} | {q[0] / s['sides']:.2f} | {q[1] / s['sides']:.2f} | {q[2] / s['sides']:.2f} | {q[4] / s['sides']:.2f} | {rate} |")
        gl = sorted(goalies[t].items(), key=lambda kv: -kv[1][1])[:2]
        out.append("\n**Goalies**\n\n| Goalie | Shots faced | Save % | Agility | Puck Control |\n| --- | --- | --- | --- | --- |")
        for nm, (ga, sa) in gl:
            p = roster.get(nm.lower())
            out.append(f"| {nm} | {int(sa):,} | {100 * (1 - frac(ga, sa)):.1f} | {p['a'][1] if p else ''} | {p['a'][5] if p else ''} |")
    (ROOT / "docs" / outfile).write_text("\n".join(out) + "\n", encoding="utf-8")
    # the tables for COACH_RATING sections 9 and 10
    readings.append(f"\n**{system_name} Classic, section 9**\n\n| Team | Now | All years | Sides |\n| --- | --- | --- | --- |")
    for t in full:
        readings.append(f"| {t} | {sign(now_v[t][0])} ± {now_v[t][1]:.1f} | {sign(all_v[t][0])} ± {all_v[t][1]:.1f} | {int(S[t]['sides']):,} |")
    readings.append(f"\n**{system_name} Classic**\n\n| Team | High coaches | Low coaches | Top league | Other leagues | Reading |\n| --- | --- | --- | --- | --- | --- |")
    for t in sorted(full, key=lambda t: -all_v[t][0]):
        lv = levels[t]
        readings.append(f"| {t} | {bare(lv['coach']['levels'].get('0'))} | {bare(lv['coach']['levels'].get('2'))} | {bare(lv['name']['levels'].get('0'))} | {bare(lv['name']['levels'].get('2'))} | {reading(lv)} |")
    print(f"{label}: {len(full)} full entries, {len(rest)} short; {outfile}", flush=True)


def main():
    gentle()
    text = (C.DATA / "coach_rating_groups.md").read_text(encoding="utf-8")
    conv = [float(x) for x in re.findall(r"Conversion factor ([\d.]+)", text)]
    fits = re.findall(r"Final fit: coast, half-life ([\d.]+), ridge ([\d.]+)", text)
    levels = json.loads((ROOT / "reports" / "classic_team_levels.json").read_text(encoding="utf-8"))
    readings = []
    for name, label, tab, at, romfile, outfile in SYSTEMS:
        build(name, label, tab, at, romfile, outfile, levels[label], conv[at], (float(fits[at][0]), float(fits[at][1])), readings)
    (ROOT / "reports" / "classic_team_readings.md").write_text("\n".join(readings) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
