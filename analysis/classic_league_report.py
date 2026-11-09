"""A whole league's season, every coach in it (2026-11-09, the user: a ready-made analysis of each division at the
season's end, with at least one complimentary thing about every coach). Names real people, so the reports go only to
%USERPROFILE%\\NHL94_League_Data\\season_reports, never the repository; the script prints nothing but the paths.

python analysis/classic_league_report.py Classic_Fall2026            every league whose name starts so (both systems)
python analysis/classic_league_report.py Classic_Fall2026_GENS-A ...  the leagues named
    --coaches   also each coach's own report (classic_season_report.py) beside it

Per league, from the league database (as classic_season_report.py: every regular-season game the league counts, a
double upload too, simulated games left out; 2 points a win, none for a loss):
- standings with expected wins from the pre-season Classic ratings (coach_history), and the groups when the schedule
  has them (coaches meeting 4+ times), with each group's record against the other;
- every coach's rates per game side by side, the league leaders, skaters' and goalies' leaders;
- head to head; notable games (biggest wins, the most goals, comebacks, upsets by pre-season odds); streaks;
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


def result(g):
    a, b = g["us"]["Score"], g["them"]["Score"]
    return "W" if a > b else "L" if a < b else "T"


def wl(t):
    return f"{t['W']}-{t['L']}" + (f"-{t['T']}" if t["T"] else "")


def build(league):
    system, games = S.load(league)
    if not games:
        raise SystemExit(f"no games in {league}")
    per = defaultdict(list)
    for r in games:
        for g in S.sides(r):
            per[g["coach"]].append(g)
    for c in per:
        per[c].sort(key=lambda g: g["when"])
    first = date.fromisoformat(min(r["DateTime"] for r in games)[:10])
    rat, rat_day = S.ratings(system, first)
    known = [rat[c.lower()] for c in per if c.lower() in rat] or [0.0]
    mean_known = sum(known) / len(known)
    R = lambda c: rat.get(c.lower(), mean_known)
    teams = {c: Counter(g["team"] for g in gs).most_common(1)[0][0] for c, gs in per.items()}

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
    n = len(tab)
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

    def rank_of(k, c, hb):
        v = vals[k][c]
        return 1 + sum(1 for o in tab if (vals[k][o] > v if hb else vals[k][o] < v))

    def rankword(r):
        return "best" if r == 1 else f"{ORD(r)}-best"

    L = []
    w = L.append
    gp_all = sorted(((tab[c]["GP"], c) for c in tab), reverse=True)
    w(f"# {league}: the season\n")
    w(f"{len(games)} games from {min(r['DateTime'] for r in games)[:10]} to {max(r['DateTime'] for r in games)[:10]}, "
      f"{n} coaches. Games played: " + ", ".join(f"{c} {g}" for g, c in gp_all) + ". Rates are per game; ranks are out "
      f"of all {n} coaches (1 the best, ties share a rank). Pre-season ratings: coach_history's Classic rating on "
      f"{rat_day}.\n")

    # --- standings
    w("## Standings\n")
    w("| | Coach | Team | GP | W-L | OT W-L | Pts | Pts % | GF/G | GA/G | Diff/G | Exp. W | W - Exp. | Pre-season vs avg |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in order:
        t = tab[c]
        w(f"| {place[c]} | {c} | {teams[c]} | {t['GP']} | {wl(t)} | {t['OTW']}-{t['OTL']} | {t['Pts']} | "
          f"{t['Pts'] / (2 * t['GP']):.3f} | {rate(c, 'F_Score'):.2f} | {rate(c, 'A_Score'):.2f} | "
          f"{rate(c, 'F_Score') - rate(c, 'A_Score'):+.2f} | {t['exp_W']:.1f} | {t['W'] - t['exp_W']:+.1f} | "
          f"{100 * S.sig(R(c) - mean_known):.0f}%{'' if c.lower() in rat else ' (new)'} |")
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
            stack += [o for o, k in meet[x].items() if k >= 4 and o not in grp]
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
    ups = sorted(allg, key=lambda x: S.sig(R(x[1]) - R(x[0]["opp"])))[:3]
    w("- Upsets by pre-season odds: " + "; ".join(
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
            bw = min(wins, key=lambda g: (place[g["opp"]], -(g["us"]["Score"] - g["them"]["Score"])))
            extra.append(f"best win: {int(bw['us']['Score'])}-{int(bw['them']['Score'])} over {bw['opp']} "
                         f"({ORD(place[bw['opp']])} in the standings, {bw['when'][:10]})")
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
        close = [g for g in per[c] if result(g) == "L" and g["them"]["Score"] - g["us"]["Score"] == 1]
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
        p = S.OUT / f"{lg}_league.md"
        p.write_text(build(lg), encoding="utf-8")
        print(p)
        if coaches:
            system, games = S.load(lg)
            for c in sorted({r["HomePlayer"] for r in games} | {r["AwayPlayer"] for r in games}):
                q = S.OUT / f"{lg}_{c}.md"
                q.write_text(S.build(lg, c), encoding="utf-8")
                print(q)


if __name__ == "__main__":
    main()
