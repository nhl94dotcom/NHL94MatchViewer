"""A whole league's season, every coach in it (2026-11-09, the user: a ready-made analysis of each division at the
season's end, with at least one complimentary thing about every coach). Names real people, so the reports go only to
%USERPROFILE%\\NHL94_League_Data\\season_reports, never the repository; the script prints nothing but the paths.

python analysis/classic_league_report.py Classic_Fall2026            every league whose name starts so (both systems)
python analysis/classic_league_report.py Classic_Fall2026_GENS-A ...  the leagues named
    --coaches   also each coach's own report (classic_season_report.py) beside it
Coaches with fewer than a quarter of the league's most games (or under 5) are left out of the tables, the rankings
and the coach reports; their games still count for their opponents.

Per league, from the league database (as classic_season_report.py: every regular-season game the league counts, a
double upload too, simulated games left out; 2 points a win, none for a loss):
- standings with expected wins from the pre-season Classic ratings (coach_history), and the groups when the schedule
  has them (coaches meeting 4+ times), with each group's record against the other;
- every coach's rates per game side by side, the league leaders, skaters' and goalies' leaders;
- head to head; notable games (biggest wins, the most goals, comebacks, upsets by pre-season odds); streaks;
- "The season in brief" (the title race, the favourite, the biggest surprise and shortfall, the leaders) and "League
  numbers" (both teams together, beside the season's other leagues on the system, from one read of the database);
- "A good word for every coach": for each coach the season numbers where they rank best in the league (top quarter,
  ties sharing a rank), as plain compliments; when a coach is near the top in nothing, their best moments instead
  (their best win, longest winning streak, best ten-game stretch, top scorer, a goalie's best game). Every one is a
  number from the season, never an opinion."""
import math
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classic_season_report as S  # noqa: E402

ORD = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def leagues_for(prefix):
    import csv
    out = set()
    for sysn in ("GENS", "SNES"):
        p = S.DATA / f"All_Games_{sysn}.csv"
        with open(p, newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                if r["League"].startswith(prefix) and r["RegOrPlay"] == "R" and r["sim"] in ("0", ""):
                    out.add(r["League"])
    return sorted(out)


_NUMBERS = {}


def add_row(a, r):
    """One game into the "League numbers" totals."""
    hs, aw = S.num(r["HomeScore"]), S.num(r["AwayScore"])
    a["GP"] += 1
    a["goals"] += hs + aw
    a["shots"] += S.num(r["HomeShots"]) + S.num(r["AwayShots"])
    a["ppg"] += S.num(r["HomePPGoals"]) + S.num(r["AwayPPGoals"])
    a["ppt"] += S.num(r["HomePPTries"]) + S.num(r["AwayPPTries"])
    a["pim"] += S.num(r["HomePIM"]) + S.num(r["AwayPIM"])
    a["chk"] += S.num(r["HomeChecks"]) + S.num(r["AwayChecks"])
    a["homeW"] += hs > aw
    a["decided"] += hs != aw
    a["ot"] += any(S.num(r[k]) for k in ("HomeGoalsOT", "AwayGoalsOT", "HomeShotsOT", "AwayShotsOT"))
    a["one"] += abs(hs - aw) == 1
    a["blow"] += abs(hs - aw) >= 3
    h2 = S.num(r["HomeGoalsP1"]) + S.num(r["HomeGoalsP2"])
    a2 = S.num(r["AwayGoalsP1"]) + S.num(r["AwayGoalsP2"])
    a["behind2"] += h2 != a2
    a["cameback"] += (h2 < a2 and hs > aw) or (a2 < h2 and aw > hs)


def league_numbers(league, rows=None):
    """Every league of the season on this system (Classic_Fall2026_GENS-A -> Classic_Fall2026_GENS), aggregated in one
    read of the database and kept: per league its games and the totals the "League numbers" table shows. Returns
    (this league's totals, {each other league: totals}). rows: one level of a two-level league, its games (those with
    one of its teams) as "this league", against the season's other leagues."""
    import csv
    head, tail = league.rsplit("_", 1)
    prefix = head + "_" + tail.split("-")[0]
    if prefix not in _NUMBERS:
        system = "GENS" if "GENS" in league else "SNES"
        agg = defaultdict(Counter)
        with open(S.DATA / f"All_Games_{system}.csv", newline="", encoding="utf-8", errors="replace") as fh:
            for r in csv.DictReader(fh):
                if not r["League"].startswith(prefix) or r["RegOrPlay"] != "R" or r["sim"] not in ("0", ""):
                    continue
                add_row(agg[r["League"]], r)
        _NUMBERS[prefix] = agg
    agg = _NUMBERS[prefix]
    others = {k: v for k, v in agg.items() if k != league}
    if rows is not None:
        mine = Counter()
        for r in rows:
            add_row(mine, r)
        return mine, others
    return agg.get(league, Counter()), others


def numbers_table(mine, others):
    rows = [("Goals a game (both teams)", lambda a: a["goals"] / max(1, a["GP"]), "{:.2f}"),
            ("Shots on goal a game (both teams)", lambda a: a["shots"] / max(1, a["GP"]), "{:.1f}"),
            ("Shooting %", lambda a: 100 * a["goals"] / max(1, a["shots"]), "{:.1f}"),
            ("Power plays a game", lambda a: a["ppt"] / max(1, a["GP"]), "{:.1f}"),
            ("Power play %", lambda a: 100 * a["ppg"] / max(1, a["ppt"]), "{:.1f}"),
            ("Penalty minutes a game", lambda a: a["pim"] / max(1, a["GP"]), "{:.1f}"),
            ("Body checks a game", lambda a: a["chk"] / max(1, a["GP"]), "{:.1f}"),
            ("Home team won %", lambda a: 100 * a["homeW"] / max(1, a["decided"]), "{:.1f}"),
            ("Games to overtime %", lambda a: 100 * a["ot"] / max(1, a["GP"]), "{:.1f}"),
            ("One-goal games %", lambda a: 100 * a["one"] / max(1, a["GP"]), "{:.1f}"),
            ("Won by 3 or more %", lambda a: 100 * a["blow"] / max(1, a["GP"]), "{:.1f}"),
            ("Comebacks from behind after two %", lambda a: 100 * a["cameback"] / max(1, a["behind2"]), "{:.1f}")]
    tot = Counter()
    for v in others.values():
        tot.update(v)
    out = ([f"| | This league | The season's other leagues ({len(others)}) |", "|---|---|---|"] if others else
           ["| | This league |", "|---|---|"])
    for lab, f, fmt in rows:
        out.append(f"| {lab} | {fmt.format(f(mine))} |" + (f" {fmt.format(f(tot))} |" if others else ""))
    return out


def season_brief(order, tab, place, teams, R, per, vals, pl, gk, groups, streaks, mine_num, other_num,
                 new=lambda c: False):
    """'The season in brief': the league's story from the numbers in the report below it (2026-11-10, the user)."""
    pts = lambda c: tab[c]["Pts"] / (2 * tab[c]["GP"])
    first, second, last = order[0], order[1], order[-1]
    out = ["## The season in brief\n"]
    gap = pts(first) - pts(second)
    t1, t2 = tab[first], tab[second]
    if gap >= 0.08:
        s = f"{first} ({teams[first]}) ran away with the league, {t1['W']}-{t1['L']} ({pts(first):.3f})."
    elif gap > 0:
        s = (f"{first} ({teams[first]}) won the league, {t1['W']}-{t1['L']} ({pts(first):.3f}), holding off {second} "
             f"({t2['W']}-{t2['L']}, {pts(second):.3f}).")
    else:
        s = (f"{first} ({teams[first]}) and {second} finished level at {pts(first):.3f}; {first} took first on goal "
             f"difference ({t1['W']}-{t1['L']}).")
    # the favourite among the coaches whose ratings rest on games: a newcomer's starting rating says nothing
    # (review 2026-11-10: SNES-D's four newcomers all sat above its three rated coaches)
    rated = [c for c in order if not new(c)]
    fav = max(rated, key=R) if rated else None
    news = len(order) - len(rated)
    note = (f" ({news} of the {len(order)} {'was' if news == 1 else 'were'} new to Classic, with no rating to go on)"
            if news else "")
    if fav is None:
        s += " Nobody had a Classic rating before the season, so there was no favourite."
    elif fav == first:
        s += f" {first} also had the best pre-season rating{note}, so the favourite delivered."
    elif new(first):
        s += f" {first} was new to Classic; the pre-season favourite, {fav}, finished {ORD(place[fav])}{note}."
    else:
        pre = sorted(rated, key=lambda c: -R(c)).index(first) + 1
        s += f" The pre-season favourite, {fav}, finished {ORD(place[fav])}; {first} went in rated {ORD(pre)}{note}."
    h = Counter(result(g) for g in per[first] if g["opp"] == second)
    if sum(h.values()):
        s += f" Between the top two, {first} went {h['W']}-{h['L']} against {second}."
    out.append(s + "\n")
    if groups:
        gl = sorted(groups, key=lambda g: min(place[c] for c in g))
        cross = Counter(result(g) for c in gl[0] for g in per[c] if g["opp"] in gl[1])
        out.append(f"The league played in groups; the group with {first} went {cross['W']}-{cross['L']} against the "
                   f"other.\n")
    # surprises against the ratings only for rated coaches (a newcomer's expected wins come from the starting rating)
    pool = rated or order
    over = max(pool, key=lambda c: tab[c]["W"] - tab[c]["exp_W"])
    under = min(pool, key=lambda c: tab[c]["W"] - tab[c]["exp_W"])
    sp = []
    if rated and tab[over]["W"] - tab[over]["exp_W"] >= 2:
        sp.append(f"the season's biggest surprise was {over}, {ORD(place[over])} with {tab[over]['W']} win{'' if tab[over]['W'] == 1 else 's'} against "
                  f"{tab[over]['exp_W']:.1f} expected from the pre-season ratings")
    short = bool(rated) and tab[under]["W"] - tab[under]["exp_W"] <= -2
    if short:
        sp.append(f"the biggest shortfall was {under}'s, " + ("last" if under == last else ORD(place[under])) +
                  f" with {tab[under]['W']} win{'' if tab[under]['W'] == 1 else 's'} against {tab[under]['exp_W']:.1f} expected")
    if not (under == last and short):
        sp.append(f"{last} finished last, {tab[last]['W']}-{tab[last]['L']}")
    s = "; ".join(sp)
    out.append(s[0].upper() + s[1:] + ".\n")
    gf = max(order, key=lambda c: vals["gf"][c])
    ga = min(order, key=lambda c: vals["ga"][c])
    ln = [f"{gf} had the best attack ({vals['gf'][gf]:.2f} goals a game)",
          f"{ga} the best defence ({vals['ga'][ga]:.2f} against)"]
    if pl:
        (nm, _, c), v = max(pl.items(), key=lambda kv: (kv[1]["P"], kv[1]["G"]))
        ln.append(f"{nm} ({c}) led all skaters with {v['P']} points ({v['G']} goals)")
    if gk:
        gmin = max(1, max(x["GP"] for x in gk.values()) // 3)
        (nm, c), v = max(((k, v) for k, v in gk.items() if v["GP"] >= gmin), key=lambda kv: kv[1]["SV"] / max(1, kv[1]["SA"]))
        ln.append(f"{nm} ({c}) had the best save percentage, {100 * v['SV'] / max(1, v['SA']):.1f}%")
    st = max(order, key=streaks)
    if streaks(st) >= 5:
        ln.append(f"{st} had the longest winning streak, {streaks(st)} games")
    s = "; ".join(ln)
    out.append(s[0].upper() + s[1:] + ".\n")
    if other_num and mine_num["GP"]:
        tot = Counter()
        for v in other_num.values():
            tot.update(v)
        g1, g0 = mine_num["goals"] / mine_num["GP"], tot["goals"] / max(1, tot["GP"])
        comp = ("higher-scoring than the season's other leagues" if g1 - g0 >= 0.5 else
                "lower-scoring than the season's other leagues" if g0 - g1 >= 0.5 else
                "about as high-scoring as the season's other leagues")
        out.append(f"At {g1:.2f} goals a game (both teams) it was {comp} ({g0:.2f}); "
                   f"{100 * mine_num['one'] / mine_num['GP']:.0f}% of games were decided by one goal and "
                   f"{100 * mine_num['ot'] / mine_num['GP']:.0f}% went to overtime.\n")
    return out


def result(g):
    a, b = g["us"]["Score"], g["them"]["Score"]
    return "W" if a > b else "L" if a < b else "T"


def wl(t):
    return f"{t['W']}-{t['L']}" + (f"-{t['T']}" if t["T"] else "")


def build(league, level=None):
    """The league's report; level: one level of a two-level league (S.LEVELS), its coaches alone in the tables."""
    system, games = S.load(league)
    if not games:
        raise SystemExit(f"no games in {league}")
    per = defaultdict(list)
    for r in games:
        for g in S.sides(r):
            per[g["coach"]].append(g)
    for c in per:
        per[c].sort(key=lambda g: g["when"])
    first = S.season_start(league)  # the season's first day on the system: pre-season ratings the same for every league
    rat, rat_day = S.ratings(system, first)
    known = [rat[S.base_name(c).lower()] for c in per if S.base_name(c).lower() in rat] or [0.0]
    mean_known = sum(known) / len(known)
    R = lambda c: rat.get(S.base_name(c).lower(), mean_known)
    teams = {c: S.team_label(gs) for c, gs in per.items()}

    tab = {}
    for c, gs in per.items():
        t = Counter()
        for g in gs:
            us, them = g["us"], g["them"]
            ot = bool(us["GoalsOT"] or them["GoalsOT"] or us["ShotsOT"] or them["ShotsOT"])
            res = result(g)
            t["GP"] += 1
            t[res] += 1
            t["OTW"] += res == "W" and ot
            t["OTL"] += res == "L" and ot
            t["one_goal_W"] += res == "W" and us["Score"] - them["Score"] == 1
            t["one_goal_L"] += res == "L" and them["Score"] - us["Score"] == 1
            a2, b2 = us["GoalsP1"] + us["GoalsP2"], them["GoalsP1"] + them["GoalsP2"]
            t["trailed2"] += a2 < b2
            t["comeback"] += a2 < b2 and res == "W"
            t["led2"] += a2 > b2
            t["held"] += a2 > b2 and res == "W"
            for k in S.STATS:
                t["F_" + k] += us[k]
                t["A_" + k] += them[k]
            t["exp_W"] += S.sig(R(c) - R(g["opp"]))
            t["opp_rating"] += R(g["opp"])
        t["Pts"] = 2 * t["W"] + t["T"]
        tab[c] = t
    # coaches with very few games are left out of the tables and the rankings (the user, 2026-11-09); their games
    # still count in their opponents' records
    gp_league = {c: t["GP"] for c, t in tab.items()}
    omitted = sorted(c for c in tab if tab[c]["GP"] < max(5, max(gp_league.values()) / 4))
    for c in omitted:
        del tab[c]
        del per[c]
    # one level of a two-level league: only its coaches in the tables; games against the other level still count
    lv = S.LEVELS.get(league, {})
    title = S.level_title(league, level) if level else league
    if level:
        for c in [c for c in tab if lv.get(c) != level]:
            del tab[c]
            del per[c]
        games = [r for r in games if lv.get(r["HomePlayer"]) == level or lv.get(r["AwayPlayer"]) == level]
    n = len(tab)
    mine_omitted = [c for c in omitted if not level or lv.get(c) == level]
    order = sorted(tab, key=lambda c: (-tab[c]["Pts"] / (2 * tab[c]["GP"]),
                                       -(tab[c]["F_Score"] - tab[c]["A_Score"]) / tab[c]["GP"]))
    place = {c: i for i, c in enumerate(order, 1)}
    rate = lambda c, k: tab[c][k] / tab[c]["GP"]
    shp = lambda c: 100 * tab[c]["F_Score"] / max(1, tab[c]["F_Shots"])
    svp = lambda c: 100 - 100 * tab[c]["A_Score"] / max(1, tab[c]["A_Shots"])
    ppp = lambda c: 100 * tab[c]["F_PPGoals"] / max(1, tab[c]["F_PPTries"])
    pkp = lambda c: 100 - 100 * tab[c]["A_PPGoals"] / max(1, tab[c]["A_PPTries"])
    fop = lambda c: 100 * tab[c]["F_FaceoffWins"] / max(1, tab[c]["F_FaceoffWins"] + tab[c]["A_FaceoffWins"])
    passp = lambda c: 100 * tab[c]["F_PassComps"] / max(1, tab[c]["F_PassTries"])
    share = lambda c: 100 * tab[c]["F_Shots"] / max(1, tab[c]["F_Shots"] + tab[c]["A_Shots"])

    # (key, label, value, higher is better, format, compliment phrase: "{v}" the value, "{r}" the rank words)
    METRICS = [
        ("pts", "Points %", lambda c: tab[c]["Pts"] / (2 * tab[c]["GP"]), True, "{:.3f}", "the {r} points percentage in the league ({v})"),
        ("gf", "Goals for / game", lambda c: rate(c, "F_Score"), True, "{:.2f}", "the {r} attack: {v} goals a game"),
        ("ga", "Goals against / game", lambda c: rate(c, "A_Score"), False, "{:.2f}", "the {r} defence: {v} goals against a game"),
        ("diff", "Goal difference / game", lambda c: rate(c, "F_Score") - rate(c, "A_Score"), True, "{:+.2f}", "the {r} goal difference ({v} a game)"),
        ("sf", "Shots / game", lambda c: rate(c, "F_Shots"), True, "{:.1f}", "the {q}most shots on goal ({v} a game)"),
        ("sa", "Shots against / game", lambda c: rate(c, "A_Shots"), False, "{:.1f}", "the {q}fewest shots allowed ({v} a game)"),
        ("share", "Shot share %", share, True, "{:.1f}", "the {r} shot share ({v}% of the shots in their games)"),
        ("shp", "Shooting %", shp, True, "{:.1f}", "the {r} shooting percentage ({v}%)"),
        ("svp", "Save %", svp, True, "{:.1f}", "the {r} save percentage ({v}%)"),
        ("ppp", "Power play %", ppp, True, "{:.1f}", "the {r} power play ({v}%)"),
        ("pkp", "Penalty kill %", pkp, True, "{:.1f}", "the {r} penalty kill ({v}%)"),
        ("fop", "Faceoff win %", fop, True, "{:.1f}", "the {r} faceoff record ({v}% won)"),
        ("chk", "Body checks / game", lambda c: rate(c, "F_Checks"), True, "{:.1f}", "the {q}most body checks ({v} a game)"),
        ("pim", "Penalty minutes / game", lambda c: rate(c, "F_PIM"), False, "{:.1f}", "the {q}cleanest team ({v} penalty minutes a game)"),
        ("azt", "Attack zone time / game (s)", lambda c: rate(c, "F_AttackZoneTime"), True, "{:.0f}", "the {q}most time in the attacking zone ({v} s a game)"),
        ("pass", "Pass completion %", passp, True, "{:.1f}", "the {r} passing ({v}% completed)"),
        ("otg", "One-timer goals / game", lambda c: rate(c, "F_OneTimerGoals"), True, "{:.2f}", "the {q}most one-timer goals ({v} a game)"),
        ("brk", "Breakaway goals / game", lambda c: rate(c, "F_BreakGoals"), True, "{:.2f}", "the {q}most breakaway goals ({v} a game)"),
        ("shg", "Short-handed goals", lambda c: tab[c]["F_SHGoals"], True, "{:.0f}", "the {q}most short-handed goals ({v})"),
        ("weo", "Wins above pre-season expectation", lambda c: tab[c]["W"] - tab[c]["exp_W"], True, "{:+.1f}", "the {q}biggest beat of a pre-season rating ({v} wins)"),
        ("ogw", "One-goal games won %", lambda c: tab[c]["one_goal_W"] / max(1, tab[c]["one_goal_W"] + tab[c]["one_goal_L"]), True, "{:.2f}", "the {r} record in one-goal games ({o})"),
    ]
    vals = {k: {c: f(c) for c in tab} for k, _, f, _, _, _ in METRICS}

    is_new = lambda c: S.newcomer(system, first, c)

    def rank_of(k, c, hb):
        v = vals[k][c]
        # wins above expectation: ranked among the coaches whose ratings rest on games
        pool = [o for o in tab if not is_new(o)] if k == "weo" else tab
        return 1 + sum(1 for o in pool if (vals[k][o] > v if hb else vals[k][o] < v))

    def rankword(r):
        return "best" if r == 1 else f"{ORD(r)}-best"

    L = []
    w = L.append
    gp_all = sorted(((tab[c]["GP"], c) for c in tab), reverse=True)
    w(f"# {title}: the season\n")
    if level:
        other = "/".join(sorted(set(lv.values()) - {level}))
        w(f"{league} held two levels in one schedule (an experiment; each level is normally its own league). This is the "
          f"{level} level: its {n} coaches in the tables and ranks, with their games against the {other} level counted "
          f"in every record. The levels are the schedule's groups; the higher one is the group whose coaches with Classic "
          f"games before the season had the higher mean pre-season rating.\n")
    w(f"{len(games)} games from {min(r['DateTime'] for r in games)[:10]} to {max(r['DateTime'] for r in games)[:10]}, "
      f"{n} coaches. Games played: " + ", ".join(f"{c} {g}" for g, c in gp_all) + ". Rates are per game; ranks are out "
      f"of all {n} coaches (1 the best, ties share a rank). Pre-season ratings: coach_history's Classic rating on "
      f"{rat_day}." + (" Left out for playing very few games (their games still count for their opponents): " +
                       ", ".join(f"{c} ({gp_league[c]})" for c in mine_omitted) + "." if mine_omitted else "") + "\n")

    # --- standings
    w("## Standings\n")
    w("| | Coach | Team | GP | W-L | OT W-L | Pts | Pts % | GF/G | GA/G | Diff/G | Exp. W | W - Exp. | Pre-season vs avg |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in order:
        t = tab[c]
        w(f"| {place[c]} | {c} | {teams[c]} | {t['GP']} | {wl(t)} | {t['OTW']}-{t['OTL']} | {t['Pts']} | "
          f"{t['Pts'] / (2 * t['GP']):.3f} | {rate(c, 'F_Score'):.2f} | {rate(c, 'A_Score'):.2f} | "
          f"{rate(c, 'F_Score') - rate(c, 'A_Score'):+.2f} | {t['exp_W']:.1f} | {t['W'] - t['exp_W']:+.1f} | "
          f"{100 * S.sig(R(c) - mean_known):.0f}%{' (new)' if S.newcomer(system, first, c) else ''} |")
    w("\nOrdered by points percentage, then goal difference a game (the league's own tiebreaks may differ).\n")

    # --- groups
    meet = defaultdict(Counter)
    for c, gs in per.items():
        for g in gs:
            meet[c][g["opp"]] += 1
    comp, seen = [], set()
    for c in order:
        if c in seen:
            continue
        stack, grp = [c], set()
        while stack:
            x = stack.pop()
            if x in grp:
                continue
            grp.add(x)
            stack += [o for o, k in meet[x].items() if k >= 4 and o not in grp and o in tab]
        seen |= grp
        comp.append(grp)
    groups = [g for g in comp if len(g) >= 3]
    if len(groups) >= 2 and sum(len(g) for g in groups) == n:
        w("## The groups\n")
        w("The schedule has groups: coaches inside a group met 4 or more times, across groups 2 or fewer.\n")
        gname = {}
        for i, g in enumerate(sorted(groups, key=lambda g: min(place[c] for c in g))):
            for c in g:
                gname[c] = chr(65 + i)
            w(f"**Group {chr(65 + i)}:** " + ", ".join(f"{c} ({place[c]})" for c in sorted(g, key=place.get)) + "\n")
        cross = defaultdict(Counter)
        for c, gs in per.items():
            for g in gs:
                if gname[c] != gname[g["opp"]]:
                    k = (gname[c], gname[g["opp"]])
                    cross[k]["GP"] += 1
                    cross[k][result(g)] += 1
                    cross[k]["GF"] += g["us"]["Score"]
                    cross[k]["GA"] += g["them"]["Score"]
        w("| Group | against | GP | W-L | GF-GA |")
        w("|---|---|---|---|---|")
        for (a, b), v in sorted(cross.items()):
            w(f"| {a} | {b} | {v['GP']} | {wl(v)} | {int(v['GF'])}-{int(v['GA'])} |")
        w("")

    # --- team stats side by side
    w("## Every coach, per game\n")
    show = ["gf", "ga", "sf", "sa", "shp", "svp", "ppp", "pkp", "fop", "chk", "pim", "pass"]
    lab = {k: (l, f, hb) for k, l, _, hb, f, _ in METRICS}
    w("| Coach | " + " | ".join(lab[k][0] for k in show) + " |")
    w("|---|" + "---|" * len(show))
    for c in order:
        w(f"| {c} | " + " | ".join(lab[k][1].format(vals[k][c]) for k in show) + " |")
    w("| *League* | " + " | ".join(lab[k][1].format(sum(vals[k].values()) / n) for k in show) + " |")
    w("")
    w("## League leaders\n")
    w("| | Best | Value | Next |")
    w("|---|---|---|---|")
    for k, l, _, hb, f, _ in METRICS:
        srt = sorted(tab, key=lambda c: vals[k][c], reverse=hb)
        w(f"| {l} | {srt[0]} | {f.format(vals[k][srt[0]])} | " +
          ", ".join(f"{c} {f.format(vals[k][c])}" for c in srt[1:3]) + " |")
    w("")

    # --- players and goalies
    pl = defaultdict(Counter)
    gk = defaultdict(Counter)
    best_goalie_game = {}
    for c, gs in per.items():
        for g in gs:
            for p in g["us"]["Players"]:
                k = (p[1], p[2], c)
                pl[k]["GP"] += 1
                for i, f in enumerate(("G", "A", "P", "SOG", "Chk", "PIM"), 3):
                    pl[k][f] += p[i]
            for q in g["us"]["Goalies"]:
                k = (q[1], c)
                gk[k]["GP"] += 1
                gk[k]["GA"] += q[2]
                gk[k]["SV"] += q[3]
                gk[k]["SA"] += q[4]
                cur = best_goalie_game.get(c)
                if cur is None or (q[3], -q[2]) > (cur[1], -cur[2]):
                    best_goalie_game[c] = (q[1], q[3], q[2], g)
    w("## Skaters\n")
    w("| Player | Pos | Coach | GP | G | A | Pts | Shots | Sh % | Checks |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    top_pl = sorted(pl.items(), key=lambda kv: (-kv[1]["P"], -kv[1]["G"]))
    for (name, pos, c), v in top_pl[:15]:
        w(f"| {name} | {pos} | {c} | {v['GP']} | {v['G']} | {v['A']} | {v['P']} | {v['SOG']} | "
          f"{S.pct(v['G'], v['SOG'])} | {v['Chk']} |")
    w("")
    hitters = sorted(pl.items(), key=lambda kv: -kv[1]["Chk"])[:5]
    w("Most body checks: " + ", ".join(f"{nm} ({c}) {v['Chk']}" for (nm, _, c), v in hitters) + ".\n")
    w("## Goalies\n")
    gmin = max(1, max(v["GP"] for v in gk.values()) // 3)
    w(f"At least {gmin} games.\n")
    w("| Goalie | Coach | GP | Shots | Saves | Save % | GA/G |")
    w("|---|---|---|---|---|---|---|")
    for (name, c), v in sorted(((k, v) for k, v in gk.items() if v["GP"] >= gmin),
                                key=lambda kv: -kv[1]["SV"] / max(1, kv[1]["SA"])):
        w(f"| {name} | {c} | {v['GP']} | {v['SA']} | {v['SV']} | {S.pct(v['SV'], v['SA'])} | {v['GA'] / v['GP']:.2f} |")
    w("")

    # --- head to head
    w("## Head to head\n")
    w("Row coach's record against the column coach (W-L).\n")
    short = {c: c[:10] for c in order}
    w("| | " + " | ".join(short[c] for c in order) + " |")
    w("|---|" + "---|" * n)
    h2h = defaultdict(Counter)
    for c, gs in per.items():
        for g in gs:
            h2h[(c, g["opp"])][result(g)] += 1
    for c in order:
        cells = []
        for o in order:
            v = h2h[(c, o)]
            cells.append("" if c == o else (wl(v) if sum(v.values()) else "-"))
        w(f"| {c} | " + " | ".join(cells) + " |")
    w("")

    # --- notable games and streaks
    allg = [(g, c) for c, gs in per.items() for g in gs if result(g) == "W"]
    w("## Notable games\n")
    big = sorted(allg, key=lambda x: -(x[0]["us"]["Score"] - x[0]["them"]["Score"]))[:3]
    w("- Biggest wins: " + "; ".join(f"{c} {int(g['us']['Score'])}-{int(g['them']['Score'])} over {g['opp']} "
                                     f"({g['when'][:10]})" for g, c in big) + ".")
    most = sorted({r["MatchID"]: r for r in games}.values(),
                  key=lambda r: -(S.num(r["HomeScore"]) + S.num(r["AwayScore"])))[:3]
    w("- The most goals: " + "; ".join(f"{r['HomePlayer']} {int(S.num(r['HomeScore']))}-{int(S.num(r['AwayScore']))} "
                                       f"{r['AwayPlayer']} ({r['DateTime'][:10]})" for r in most) + ".")
    cbs = [(g, c) for g, c in allg if g["us"]["GoalsP1"] + g["us"]["GoalsP2"] < g["them"]["GoalsP1"] + g["them"]["GoalsP2"]]
    cbs.sort(key=lambda x: -((x[0]["them"]["GoalsP1"] + x[0]["them"]["GoalsP2"]) - (x[0]["us"]["GoalsP1"] + x[0]["us"]["GoalsP2"])))
    if cbs:
        w("- Comebacks from behind after two periods: " + "; ".join(
            f"{c} over {g['opp']} {int(g['us']['Score'])}-{int(g['them']['Score'])}, down "
            f"{int(g['them']['GoalsP1'] + g['them']['GoalsP2'] - g['us']['GoalsP1'] - g['us']['GoalsP2'])} ({g['when'][:10]})"
            for g, c in cbs[:4]) + f" ({len(cbs)} in all).")
    # odds only between coaches with ratings from games
    ups = sorted((x for x in allg if not is_new(x[1]) and not is_new(x[0]["opp"])),
                 key=lambda x: S.sig(R(x[1]) - R(x[0]["opp"])))[:3]
    if ups:
        w("- Upsets by pre-season odds (between coaches rated from games): " + "; ".join(
            f"{c} over {g['opp']} {int(g['us']['Score'])}-{int(g['them']['Score'])} ({100 * S.sig(R(c) - R(g['opp'])):.0f}% "
            f"chance, {g['when'][:10]})" for g, c in ups) + ".")

    def streaks(c):
        res = [result(g) for g in per[c]]
        best = cur = 0
        for x in res:
            cur = cur + 1 if x == "W" else 0
            best = max(best, cur)
        return best
    st = sorted(tab, key=lambda c: -streaks(c))
    w("- Longest winning streaks: " + ", ".join(f"{c} {streaks(c)}" for c in st[:4]) + ".\n")

    # --- the good word
    w("## A good word for every coach\n")
    w("Each from the season's own numbers: where the coach ranks best in the league, or, when nowhere near the top,\n"
      "the best of their season.\n")
    for c in order:
        t = tab[c]
        cands = []
        for k, l, _, hb, f, phrase in METRICS:
            r = rank_of(k, c, hb)
            if k == "weo" and is_new(c):  # a newcomer's expectation is the starting rating's: no compliment from it
                continue
            if k == "ogw" and t["one_goal_W"] + t["one_goal_L"] < 4:
                continue
            if k == "shg" and t["F_SHGoals"] == 0:
                continue
            if r <= max(3, n // 4):
                v = f.format(vals[k][c])
                txt = phrase.format(v=v, r=rankword(r), q="" if r == 1 else f"{ORD(r)}-",
                                     o=f"{t['one_goal_W']}-{t['one_goal_L']}")
                if any(vals[k][o] == vals[k][c] for o in tab if o != c):
                    txt += ", tied with " + ", ".join(o for o in tab if o != c and vals[k][o] == vals[k][c])
                cands.append((r, -abs(vals[k][c] - sum(vals[k].values()) / n), k, txt))
        cands.sort()
        picked, used = [], set()
        family = {"gf": "o", "sf": "o", "share": "o", "azt": "o", "shp": "o", "diff": "r", "pts": "r",
                  "ga": "d", "sa": "d", "svp": "d"}
        for r, _, k, txt in cands:
            fam = family.get(k, k)
            if fam in used:
                continue
            used.add(fam)
            picked.append(txt)
            if len(picked) == 3:
                break
        extra = []
        wins = [g for g in per[c] if result(g) == "W"]
        if wins:
            wins = [g for g in wins if g["opp"] in place] or wins
            bw = min(wins, key=lambda g: (place.get(g["opp"], 99), -(g["us"]["Score"] - g["them"]["Score"])))
            extra.append(f"best win: {int(bw['us']['Score'])}-{int(bw['them']['Score'])} over {bw['opp']} " +
                         (f"({ORD(place[bw['opp']])} in the standings, {bw['when'][:10]})" if bw["opp"] in place
                          else f"({bw['when'][:10]})"))
        s = streaks(c)
        if s >= 3:
            extra.append(f"a {s}-game winning streak")
        if t["GP"] >= 12:
            bestrun = max(range(0, t["GP"] - 9), key=lambda i: sum(result(g) == "W" for g in per[c][i:i + 10]))
            part = per[c][bestrun:bestrun + 10]
            wv = sum(result(g) == "W" for g in part)
            if wv >= 6:
                extra.append(f"a {wv}-{sum(result(g) == 'L' for g in part)} run over games {bestrun + 1}-{bestrun + 10}")
        mine_pl = sorted(((k, v) for k, v in pl.items() if k[2] == c), key=lambda kv: (-kv[1]["P"], -kv[1]["G"]))
        if mine_pl:
            (nm, pos, _), v = mine_pl[0]
            lr = 1 + sum(1 for k2, v2 in pl.items() if v2["P"] > v["P"])
            if lr <= 10:
                extra.append(f"{nm}'s {v['P']} points ({v['G']} goals), {ORD(lr)} among the league's skaters")
            elif v["P"]:
                extra.append(f"{nm} leading the team with {v['P']} points ({v['G']} goals)")
        close = [g for g in per[c] if result(g) == "L" and g["them"]["Score"] - g["us"]["Score"] == 1
                 and g["opp"] in place]
        if close:
            cl = min(close, key=lambda g: place[g["opp"]])
            ot = cl["us"]["GoalsOT"] or cl["them"]["GoalsOT"]
            extra.append(f"took {cl['opp']} ({ORD(place[cl['opp']])}) to {'overtime' if ot else 'a one-goal game'}, "
                         f"{int(cl['us']['Score'])}-{int(cl['them']['Score'])} ({cl['when'][:10]})")
        if c in best_goalie_game:
            nm, sv, ga, g = best_goalie_game[c]
            if sv >= 15:
                extra.append(f"{nm}'s {sv} saves against {g['opp']} ({g['when'][:10]})")
        if not picked:
            picked = extra[:3]
        else:
            picked += extra[:1]
        few = f", {t['GP']} games" if t["GP"] < 10 else ""
        w(f"- **{c}** ({ORD(place[c])}, {teams[c]}{few}): " + "; ".join(picked) + ".")
    w("")
    mine_num, other_num = league_numbers(league, games if level else None)
    real_groups = groups if len(groups) >= 2 and sum(len(g) for g in groups) == n else []
    at = 3 if level else 2  # after the title and the header lines
    L[at:at] = (season_brief(order, tab, place, teams, R, per, vals, pl, gk, real_groups, streaks, mine_num, other_num,
                             new=lambda c: S.newcomer(system, first, c))
              + ["## League numbers\n", "Both teams together, every game of the league; beside it the season's other "
                 "leagues on this system, their games pooled.\n"] + numbers_table(mine_num, other_num) + [""])
    return "\n".join(L) + "\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    coaches = "--coaches" in sys.argv
    if not args:
        raise SystemExit(__doc__)
    names = []
    for a in args:
        names += [a] if a.count("_") >= 2 and "-" in a.split("_")[-1] else leagues_for(a)
    S.OUT.mkdir(parents=True, exist_ok=True)
    for lg in names:
        system, games = S.load(lg)
        lv = S.LEVELS.get(lg, {})
        # a two-level league: a report per level, named for the level (Classic_Fall2026_SNES-AB -> _SNES-A, _SNES-B)
        for level in (sorted(set(lv.values())) or [None]):
            p = S.OUT / f"{S.level_title(lg, level) if level else lg}_league.md"
            p.write_text(build(lg, level), encoding="utf-8")
            print(p)
        if coaches:
            gp = Counter([r["HomePlayer"] for r in games] + [r["AwayPlayer"] for r in games])
            for c in sorted(c for c in gp if gp[c] >= max(5, max(gp.values()) / 4)):
                q = S.OUT / f"{S.level_title(lg, lv[c]) if c in lv else lg}_{c}.md"
                q.write_text(S.build(lg, c), encoding="utf-8")
                print(q)


if __name__ == "__main__":
    main()
