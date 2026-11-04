"""The team guides: docs/TEAM_GUIDE_GENESIS.md and docs/TEAM_GUIDE_SNES.md, every retail team in the Classic leagues (2026-11-04, the user, to hand out).
Aggregates only; no coach is named. Run coach_rating.py groups and coach_team_levels.py first: the conversion factors and settings come from the former,
the values by level of player from the latter (reports/classic_team_levels.json), and the Elo adjustments from league_team_elo.py (reports/classic_team_elo.json).

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
MIN_FULL, MIN_LEVEL, MIN_ELO, DRAWS = 100, 150, 300, 200
GOOD, ALIKE, WEAK = 1.5, 5.0, 3.0                       # points: strength for Good or Poor; the largest gap for Both alike; the smallest for a Weak call
ERAS = (("2013-2019", 2013, 2019), ("2020-2022", 2020, 2022), ("2023-2026", 2023, 2026))
LENSES = ("coach", "strength", "name")


def nth(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def sign(v, d=1):
    return f"{v:+.{d}f}".replace("-", "−")


def anchor(rank, city_name, abbr):
    """GitHub's link target for a team's heading, "## 1. St. Louis (STL)": lower case, punctuation gone, spaces as hyphens."""
    return re.sub(r"[^a-z0-9 -]", "", f"{rank}. {city_name} ({abbr})".lower()).replace(" ", "-")


def elo_text(e):
    return sign(e["adj"], 0) + ("*" if e["games"] < MIN_ELO else "")


def overall(value):
    """Good, Average or Poor, from the team's strength now."""
    return "Good" if value >= GOOD else "Poor" if value <= -GOOD else "Average"


def best_for(lv):
    """(Best for, Confidence): which level of player gets more from the team, from the three ways of measuring level (see COACH_RATING section 10)."""
    gaps = [lv[k].get("gap") for k in LENSES]
    known = [g for g in gaps if g]
    best, sure = "Unclear", "—"
    state = lambda v: "good" if v and min(v) >= GOOD else None
    if len(known) == len(LENSES) and len({np.sign(g[0]) for g in known}) == 1:
        side = "High-level" if known[0][0] > 0 else "Low-level"
        z = [abs(g[0]) / g[1] if g[1] else 0 for g in known]
        high = state([x[0] for x in (lv["coach"]["levels"].get("0"), lv["name"]["levels"].get("0")) if x])
        low = state([x[0] for x in (lv["coach"]["levels"].get("2"), lv["name"]["levels"].get("2")) if x])
        if sum(x >= 1.5 for x in z) >= 2:
            best, sure = side, "Likely"
        elif sum(x >= 1 for x in z) >= 2:
            best, sure = side, "Leaning"
        elif bool(high) != bool(low) and (side == "High-level") == bool(high) and min(abs(g[0]) for g in known) >= WEAK:
            best, sure = side, "Weak"
    if best == "Unclear" and len(known) == len(LENSES) and max(abs(g[0]) for g in known) <= ALIKE:
        best = "Both alike"
    few = sum(1 for k, level in (("coach", "0"), ("coach", "2"), ("name", "0"), ("name", "2")) if lv[k]["levels"].get(level, [0, 0, 0])[2] < MIN_LEVEL)
    if few >= 2:
        sure = "Few games" if sure == "—" else f"{sure}, few games"
    return best, sure


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


def build(name, label, tab, at, romfile, outfile, levels, elo, conv, settings, readings):
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
    rank_elo = sorted(full, key=lambda t: -elo[t]["adj"])
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
           "**Jump to a team:** " + " · ".join(f"[{city[t]}](#{anchor(i, city[t], t)})" for i, t in enumerate(full, 1)) + "\n",
           "## How to read this guide\n",
           "**The basics**\n",
           "- **Points:** strength values are points of win chance above or below 50, against the average team as used in these leagues, with even coaches and no home edge. +5 means about a 55% chance.\n",
           "- **± (spread):** about how far a value could be off by chance, from resampling whole leagues or, in the Record table, from the number of games. A value within one spread of zero can't be told from zero.\n",
           "- **Results show what happened, not why.** Players choose or are given teams, and rarely used teams rest on few coaches.\n",
           "- **± understates the uncertainty for rarely used teams.** Their values are pulled toward average, and ± is measured around the pulled value. A team with few games or few coaches is less certain than its ± suggests.\n",
           "**Why the numbers for a team can disagree**\n",
           "Two teams can have similar strengths but different Elo adjustments, or a team can have a good record and a poor strength. Usually that's not an error. Where the numbers agree, the method doesn't matter. Where they differ, the team is less certain. "
           "Use strength to judge how good a team is, and the Elo adjustment inside an Elo rating.\n",
           "- **Each number uses a different yardstick for the coach.** Every team value is what's left after taking out who was coaching. Strength uses one fitted strength for each coach. The Elo adjustment uses each coach's Elo at the start of that league. A different yardstick leaves a different remainder, even with the same record.\n",
           "- **Elo can run high or low for a while.** If a coach's Elo is well above how they then play, the team they're using looks worse than it is. If it's well below, the team looks better. A fitted strength reflects the coach's whole Classic career, so it's less affected by this.\n",
           "- **Favorites tend to fall short of what Elo predicts.** A rating gap in Classic games is only worth about 0.6 of its face value. A team usually used by Elo favorites can therefore look a little worse on the Elo adjustment than on strength, and a team usually used by underdogs a little better. In simulated seasons this effect was usually small and varied a lot.\n",
           "- **Rarely used teams rest on a few seasons.** One or two unusual seasons, or one coach, can move their numbers a lot, and more on the Elo adjustment than on strength.\n",
           "- **Each number counts different results.** Strength counts how early wins were safe as well as who won. The Elo adjustment's fit counts only who won, and it leaves out games where a coach has under 30 earlier games.\n",
           "- **Strength now and strength over all years cover different games.** A team can look better or worse lately because of who has used it recently, or because the leagues have changed, so a gap between the two doesn't prove the team itself changed. Rosters in these leagues stay the same.\n",
           "- **A record alone doesn't say how good a team is.** Better coaches may have used it, or worse ones. A strong team can have a modest record if weaker coaches tend to use it, and a weak team can have a good record if stronger coaches do. That's what the Expected column is for.\n",
           "- **Most differences between levels don't repeat well** when half the leagues are compared with the other half, so treat them as ideas to test. In simulated seasons where every team played the same at every level, gaps of up to about 6 points still appeared by chance. "
           + ("The overall team order is sturdier.\n" if tab == "GENESIS" else "On the SNES, the team order itself depends more on the method than on the Genesis, so read small gaps as ties.\n"),
           "**The \"All teams\" table**\n",
           "- **#:** the team's rank by strength now.\n",
           "- **Team:** the team and its abbreviation. Click a name to go to its entry.\n",
           "- **Overall:** from strength now. Good is +1.5 or better, Poor is −1.5 or worse, and Average is in between.\n",
           "- **Best for:** which level of player gets more from this team than from their other teams. High-level or Low-level means one does, Both alike means no gap of over 5 points, and Unclear means the measures disagree or there are too few games. "
           "A team can be Poor overall and still best for one level: that level just loses less with it.\n",
           "- **Confidence:** how sure the Best for call is. Likely: all three measures of level agree on direction, and the gap is at least 1.5 spreads in two. Leaning: the same, at 1 spread. Weak: they agree on direction, "
           "the gap is at least 3 points each way, and the team is good for only that level. \"Few games\" means at least two values rest on under 150 appearances. A dash means no call to rate.\n",
           f"- **Strength now:** how much the team adds, in points, with recent games counting more. A game's weight halves every {hl:g} years, so a game from 3 years ago counts {'a quarter' if hl == 1.5 else 'half' if hl == 3 else f'{0.5 ** (3 / hl):.2f} times'} as much as one played today. It's the better guide to how a team has done lately.\n",
           "- **Strength, all years:** the same, with every game counting equally. It rests on more games, so it's steadier.\n",
           "- **Elo adjustment:** points to add to a coach's Elo for using this team, against the average team in use. It's fitted on the league Elo: every game in order, a 1500 start, K 20, +7 for home and each team's own adjustment in the expected score, and the winner's gain and loser's loss raised by the coasting bonus. Rarely used teams are pulled toward zero, by the amount that best predicted later years. A * marks under 300 games, so treat it as rough. "
           + ("Tested on later years, using these inside the running Elo predicts clearly better than leaving them out.\n" if tab == "GENESIS" else
              "Tested on later years, using these inside the running Elo predicts about the same as leaving them out, so they describe past results more than they improve ratings.\n"),
           "- **Record:** all wins and losses with this team, plus ties when there are any.\n",
           "- **Win %:** wins as a share of wins and losses, without ties or any adjustment for who was coaching.\n",
           "- **Expected:** the win % that the team's coaches, home ice and the other team predict if this team were the average team in use. A record above expected is what the team itself added.\n",
           "**The \"By level of player\" table** (all years; each value says how much better that level does with this team than with its other teams, after taking out who was using it)\n",
           "- **High level** and **Low level:** the value for each level. A * marks under 150 appearances.\n",
           "- **High minus low:** the gap between the two. Positive means the team does more for high-level players.\n",
           "- **By coach (row):** level is each coach's career strength. High and low are the top and bottom groups, with about a third of the appearances each.\n",
           "- **By league strength (row):** level is the strength of the league's coaches, cut the same way.\n",
           "- **Top league against others (row):** high is each season's top league, the one with the most As, and low is the same season's other leagues.\n",
           "**The \"Record\" table** (one row for each kind of game: all games, regular season, playoffs, home, away, three eras, each coach level, and top league or other leagues)\n",
           "- **Record**, **Win %** and **Expected:** as in the \"All teams\" table.\n",
           "- **Against expected:** win % minus expected, in points, with its spread. Positive means the team did better than its coaches and opponents predict.\n",
           "**The \"Per game\" table** (averages over the team's games)\n",
           "- **Stat** and **Value:** what's measured, explained below, and the team's figure. Percentages are over all its games, not an average of each game's.\n",
           "- **Rank:** its place among the teams in this guide. 1st is best: the fewest for goals against, shots against and penalty minutes, and the most for checks.\n",
           "- **Goals for** and **Goals against:** goals scored and allowed.\n",
           "- **Shots for** and **Shots against:** shots on goal taken and allowed.\n",
           "- **Shooting %:** goals for as a share of shots for.\n",
           "- **Save %:** the share of shots against that didn't score.\n",
           "- **Power play %:** power play goals as a share of power plays.\n",
           "- **Penalty kill %:** the share of the other team's power plays that didn't score.\n",
           "- **One-timer goals** and **Breakaway goals:** goals of each kind, as the game counts them.\n",
           "- **Checks:** checks thrown, as the game counts them.\n",
           "- **Penalty minutes:** the team's penalty minutes.\n",
           "- **Faceoffs won %:** the team's share of faceoffs.\n",
           "- **Attack zone time, seconds:** time spent in the attacking zone.\n",
           "- **Pass completion %:** completed passes as a share of passes tried, as the game counts them. The game only credits a pass caught by the intended receiver.\n",
           "**The \"Ratings\" table** (from the ROM; the number in parentheses is the rank among all 26 NHL teams, with 1st the highest, so the heaviest for Weight)\n",
           "- **Overall**, **Weight**, **Speed**, **Agility**, **Shot Power**, **Shot Accuracy** and **Checking:** the mean roster rating of the team's top 12 skaters by overall. "
           + ("Hot and cold values change them a little in play.\n" if tab == "GENESIS" else "The SNES hot / cold bug maxes about 46% of ratings each game, but never Weight, so ratings other than Weight count for less than they look.\n"),
           "- **Goalie Agility:** the roster Agility of the team's higher-rated goalie. "
           + ("On the Genesis it sets the goalie's reach.\n" if tab == "GENESIS" else "On the SNES every goalie covers the same net, so it matters less than on the Genesis.\n"),
           "- **Hidden bonus (line under the table):** what the ROM adds to some of the team's ratings at home and takes away on the road.\n",
           "**The \"Leading skaters\" table** (the team's top 6 by points; all figures are per team game, whether or not the skater played in it)\n",
           "- **Player** and **Pos:** the skater, as a forward (F) or defenceman (D).\n",
           ("- **Goals**, **Assists**, **Points** and **Checks:** the skater's figures per team game.\n" if tab == "GENESIS" else "- **Goals**, **Assists** and **Points:** the skater's figures per team game.\n"),
           "- **Overall**, **Weight**, **Speed**, **Shot Power** and **Shot Acc:** the skater's roster ratings from the ROM.\n",
           "**The \"Goalies\" table** (the team's two goalies who faced the most shots)\n",
           "- **Goalie:** the goalie.\n",
           "- **Shots faced:** all shots the goalie faced in these games.\n",
           "- **Save %:** the share of those shots the goalie stopped.\n",
           "- **Agility** and **Puck Control:** the goalie's roster ratings from the ROM.\n",
           "\n## All teams\n",
           ("![Genesis Classic teams on a line by Elo adjustment](img/elo_teams_genesis.svg)\n" if tab == "GENESIS" else
            "![SNES Classic teams on a line by Elo adjustment, zoomed in](img/elo_teams_snes_zoom.svg)\n\n![SNES Classic teams on the same scale as the Genesis guide](img/elo_teams_snes.svg)\n"),
           "| # | Team | Overall | Best for | Confidence | Strength now | Strength, all years | Elo adjustment | Record | Win % | Expected |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, t in enumerate(full, 1):
        a = rec[t]["all"]
        best, sure = best_for(levels[t])
        out.append(f"| {i} | [{city[t]} ({t})](#{anchor(i, city[t], t)}) | {overall(now_v[t][0])} | {best} | {sure} | {sign(now_v[t][0])} | {sign(all_v[t][0])} | {elo_text(elo[t])} | {a.w:,}-{a.l:,}" + (f"-{a.t}" if a.t else "") + f" | {100 * a.w / a.n():.1f}% | {100 * a.exp / a.n():.1f}% |")
    rest = sorted((t for t in S if t not in full), key=lambda t: -S[t]["sides"])
    if rest:
        out.append("\nToo few games for a full entry: " + "; ".join(f"{city[t]} ({t}) {rec[t]['all'].w}-{rec[t]['all'].l}" + (f"-{rec[t]['all'].t}" if rec[t]['all'].t else "") for t in rest) + ".")
    for i, t in enumerate(full, 1):
        s, a, lv, u = S[t], rec[t]["all"], levels[t], used[t]
        out.append(f"\n## {i}. {city[t]} ({t})\n")
        best, sure = best_for(lv)
        out.append(f"**Overall: {overall(now_v[t][0])}. Best for: {best}" + ("" if sure == "—" else f" ({sure.lower()})") + f".** Strength {sign(now_v[t][0])} ± {now_v[t][1]:.1f} now ({nth(rank_now.index(t) + 1)} of {len(full)}), {sign(all_v[t][0])} ± {all_v[t][1]:.1f} over all years ({nth(rank_all.index(t) + 1)}).\n")
        e = elo[t]
        out.append(f"**Elo adjustment:** {elo_text(e)} ± {e['se']:.0f} points ({nth(rank_elo.index(t) + 1)} of {len(full)}). Against an even coach on the average team, on neutral ice, that's a {100 / (1 + 10 ** (-e['adj'] / 400)):.0f}% win chance. With one fixed strength per coach instead of Elo, it's {sign(e['fixed'], 0)}.\n")
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
        out.append("\n**Per game**\n\n| Stat | Value | Rank | | Stat | Value | Rank |\n| --- | --- | --- | --- | --- | --- | --- |")
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
        # only Genesis rows give each player's checks throughout; most SNES rows have no such field, and that slot holds penalty minutes
        genesis = tab == "GENESIS"
        out.append("\n**Leading skaters** (per team game)\n\n| Player | Pos | Goals | Assists | Points |" + (" Checks |" if genesis else "") + " Overall | Weight | Speed | Shot Power | Shot Acc |\n| --- | --- | --- | --- | --- |" + (" --- |" if genesis else "") + " --- | --- | --- | --- | --- |")
        for nm, q in top:
            p = roster.get(nm.lower())
            rate = f"{p['ovr']} | {p['a'][0]} | {p['a'][2]} | {p['a'][5]} | {p['a'][9]}" if p else " | | | | "
            out.append(f"| {nm} | {q[5]} | {q[0] / s['sides']:.2f} | {q[1] / s['sides']:.2f} | {q[2] / s['sides']:.2f} |" + (f" {q[4] / s['sides']:.2f} |" if genesis else "") + f" {rate} |")
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
    readings.append(f"\n**{system_name} Classic**\n\n| Team | High coaches | Low coaches | Top league | Other leagues | Overall | Best for | Confidence |\n| --- | --- | --- | --- | --- | --- | --- | --- |")
    for t in full:
        lv = levels[t]
        best, sure = best_for(lv)
        readings.append(f"| {t} | {bare(lv['coach']['levels'].get('0'))} | {bare(lv['coach']['levels'].get('2'))} | {bare(lv['name']['levels'].get('0'))} | {bare(lv['name']['levels'].get('2'))} | {overall(now_v[t][0])} | {best} | {sure} |")
    print(f"{label}: {len(full)} full entries, {len(rest)} short; {outfile}", flush=True)


def main():
    gentle()
    text = (C.DATA / "coach_rating_groups.md").read_text(encoding="utf-8")
    conv = [float(x) for x in re.findall(r"Conversion factor ([\d.]+)", text)]
    fits = re.findall(r"Final fit: coast, half-life ([\d.]+), ridge ([\d.]+)", text)
    levels = json.loads((ROOT / "reports" / "classic_team_levels.json").read_text(encoding="utf-8"))
    elo = json.loads((ROOT / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    readings = []
    for name, label, tab, at, romfile, outfile in SYSTEMS:
        build(name, label, tab, at, romfile, outfile, levels[label], elo[label]["teams"], conv[at], (float(fits[at][0]), float(fits[at][1])), readings)
    (ROOT / "reports" / "classic_team_readings.md").write_text("\n".join(readings) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
