"""A league's playoffs, series by series (2026-11-10, the user: write-ups for season playoffs; any league). Names real
people, so the reports go only to %USERPROFILE%\\NHL94_League_Data\\season_reports, never the repository; the script
prints nothing but the paths.

The format comes from the games (the user: formats vary, usually knockout series, sometimes a preliminary round; a
series can go unplayed or half-played): every playoff game (RegOrPlay P; simulated games count for series results, not
for player numbers) between two coaches is one series, in date order. In each round a series needs the most wins
anyone reached in that round (first to 4 in most leagues; 2 or 3 in some). A series no one finished goes to the coach
who played on. A series with a coach who had already lost one is a second-chance series (double elimination, third
place): it is listed, not part of the bracket. The bracket's rounds count back from the final (the series whose
winner played no more); more than one such series: the final isn't in the data (or the league ran separate
brackets), and the report says so instead of naming a champion. A coach whose bracket starts a round later had a
bye. Seeds: the regular season's standings (points percentage, then goal difference). Series odds: each coach's
rating at the start of the playoffs (coach_history: Classic or all-leagues), one game's chance turned into the chance
of winning the series.

python analysis/classic_playoff_report.py LEAGUE|PREFIX ...   (an exact league name is that league alone)"""
import ast
import csv
import math
import sys
from collections import Counter, defaultdict
from datetime import date
from math import comb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import classic_season_report as S  # noqa: E402

ORD = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def load_playoffs(league):
    system = S.system_of(league)
    with open(S.DATA / f"All_Games_{system}.csv", newline="", encoding="utf-8", errors="replace") as fh:
        rows = [r for r in csv.DictReader(fh) if r["League"] == league and r["RegOrPlay"] == "P"]
    for r in rows:
        r["DateTime"] = S.padded(r["DateTime"])
    rows.sort(key=lambda r: (r["DateTime"], int(r["MatchID"])))
    return system, rows


def series_odds(p, need):
    """The chance of reaching `need` wins first, each game won with chance p."""
    return sum(comb(need - 1 + k, k) * p ** need * (1 - p) ** k for k in range(need))


def bracket(rows):
    """The series, their winners, rounds and the final (see the docstring)."""
    series = {}
    for r in rows:
        h, a = r["HomePlayer"], r["AwayPlayer"]
        s = series.setdefault(tuple(sorted((h, a))), dict(teams=tuple(sorted((h, a))), games=[], wins=Counter()))
        hs, as_ = S.num(r["HomeScore"]), S.num(r["AwayScore"])
        s["games"].append(r)
        if hs != as_:
            s["wins"][h if hs > as_ else a] += 1
    ss = sorted(series.values(), key=lambda s: (s["games"][0]["DateTime"], s["games"][0]["MatchID"]))
    for i, s in enumerate(ss):
        s["i"] = i
    later = lambda c, i: [t for t in ss[i + 1:] if c in t["teams"]]
    lost = set()
    for s in ss:
        s["second"] = any(c in lost for c in s["teams"])   # a coach who had already lost a series
        top = s["wins"].most_common(2)
        s["lead"] = top
        on = [c for c in s["teams"] if later(c, s["i"])]
        s["went_on"] = on
        s["winner"] = None
        if top:
            # decided once someone has more wins than anyone else and the series is over (checked per round below)
            s["winner"] = top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else None
        if len(on) == 1 and not s["second"]:
            s["winner"] = on[0]                             # whoever the league sent on
        loser = [c for c in s["teams"] if c != s["winner"]] if s["winner"] else []
        lost.update(loser)
    main = [s for s in ss if not s["second"]]
    nxt = {}
    for s in main:
        w = s["winner"]
        nxt[s["i"]] = next((t["i"] for t in main if t["i"] > s["i"] and w in t["teams"]), None) if w else None
    depth = {}

    def d(i):
        if i not in depth:
            depth[i] = 0 if nxt[i] is None else 1 + d(nxt[i])
        return depth[i]
    deepest = max((d(s["i"]) for s in main), default=0)
    for s in main:
        s["round"] = deepest - d(s["i"]) + 1
        s["from_end"] = d(s["i"])
    rounds = defaultdict(list)
    for s in main:
        rounds[s["round"]].append(s)
    for rd, group in rounds.items():
        need = max((max(s["wins"].values(), default=0) for s in group), default=0)
        for s in group:
            s["need"] = need
            top = s["lead"]
            s["finished"] = bool(top) and top[0][1] >= need and (len(top) == 1 or top[0][1] > top[1][1])
    for s in ss:
        if s["second"]:
            s["need"], s["finished"] = max(s["wins"].values(), default=0), True
            s["round"] = None
    roots = [s for s in main if s["from_end"] == 0]
    return ss, main, rounds, roots


def round_name(from_end, n_rounds, n_series):
    return {0: "Final", 1: "Semifinals", 2: "Quarterfinals"}.get(from_end, "First round" if n_series > 1 else
                                                                    "Preliminary round")


def build(league):
    system, rows = load_playoffs(league)
    if not rows:
        raise SystemExit(f"no playoff games in {league}")
    ss, main, rounds, roots = bracket(rows)
    # the regular season: seeds and the coaches' teams
    _, reg = S.load(league)
    lv = S.LEVELS.get(league, {})
    tab = defaultdict(Counter)
    for r in reg:
        for g in S.sides(r):
            t = tab[g["coach"]]
            t["GP"] += 1
            t["W"] += g["us"]["Score"] > g["them"]["Score"]
            t["T"] += g["us"]["Score"] == g["them"]["Score"]
            t["GD"] += g["us"]["Score"] - g["them"]["Score"]
    pct = lambda c: (2 * tab[c]["W"] + tab[c]["T"]) / (2 * tab[c]["GP"]) if tab[c]["GP"] else 0
    order = sorted(tab, key=lambda c: (-pct(c), -tab[c]["GD"] / max(1, tab[c]["GP"])))
    # coaches renamed per level in a two-level league ("GR812NV (CHI)"): match the playoff names to them
    base = defaultdict(list)
    for c in order:
        base[S.base_name(c)].append(c)
    seed = {}
    for c in {c for s in ss for c in s["teams"]}:
        cands = base.get(c, [])
        if cands:
            seed[c] = order.index(cands[0]) + 1
    first = date.fromisoformat(rows[0]["DateTime"][:10])
    rat, rat_day = S.ratings(system, first, league)
    known = [v for v in rat.values()]
    R = lambda c: rat.get(S.base_name(c).lower(), sum(known) / len(known))
    new = lambda c: S.newcomer(system, first, c, league)
    team = defaultdict(Counter)
    for r in rows:
        for side in ("Home", "Away"):
            team[r[side + "Player"]][r[side + "TeamAbbrev"]] += 1
    team = {c: k.most_common(1)[0][0] for c, k in team.items()}

    def res(s):
        if not s["games"]:
            return ""
        w = s["winner"]
        if w is None:
            return "not decided in the data (" + ", ".join(f"{c} {s['wins'][c]}" for c in s["teams"]) + ")"
        l_ = [c for c in s["teams"] if c != w][0]
        txt = f"{w} beat {l_} {s['wins'][w]}-{s['wins'][l_]}"
        # the series' shape: the winner's deepest hole, and a lead the loser let go
        ww = lw = 0
        hole = lead = (0, 0)
        for r in s["games"]:
            hs, as_ = S.num(r["HomeScore"]), S.num(r["AwayScore"])
            if hs == as_:
                continue
            win = r["HomePlayer"] if hs > as_ else r["AwayPlayer"]
            ww, lw = ww + (win == w), lw + (win != w)
            if lw - ww > hole[1] - hole[0]:
                hole = (ww, lw)
            if lw - ww >= 2 and lw > lead[1]:
                lead = (ww, lw)
        if hole[1] - hole[0] >= 2 or (hole[1] == s["need"] - 1 and hole[1] > hole[0]):
            txt += f", from {hole[0]}-{hole[1]} down"
        if not s["finished"]:
            txt += f" (not finished: {w} went on)"
        return txt

    def game_line(r, w):
        h, a = r["HomePlayer"], r["AwayPlayer"]
        hs, as_ = int(S.num(r["HomeScore"])), int(S.num(r["AwayScore"]))
        ot = any(S.num(r[k]) for k in ("HomeGoalsOT", "AwayGoalsOT", "HomeShotsOT", "AwayShotsOT"))
        sim = r["sim"] not in ("0", "")
        return (f"{r['DateTime'][:10]} {a} {as_} at {h} {hs}" + (" OT" if ot else "") + (" (simulated)" if sim else ""))

    L = []
    w = L.append
    champ = roots[0]["winner"] if len(roots) == 1 else None
    w(f"# {league}: the playoffs\n")
    w(f"{len(rows)} playoff games from {rows[0]['DateTime'][:10]} to {rows[-1]['DateTime'][:10]}, {len(ss)} series, "
      f"{len({c for s in ss for c in s['teams']})} coaches. Seeds: the regular season's standings (points "
      f"percentage, then goal difference). Series odds: each coach's {'Classic' if S.is_classic(league) else 'all-leagues'} "
      f"rating on {rat_day} (coach_history), one game's chance made a series chance.\n")

    # --- brief
    w("## The playoffs in brief\n")
    brief = []
    if champ:
        f = roots[0]
        l_ = [c for c in f["teams"] if c != champ][0]
        path = [s for s in main if champ in s["teams"]]
        brief.append(f"**{champ}** ({team.get(champ, '')}, seeded {ORD(seed[champ]) if champ in seed else '?'}) won the "
                     f"playoffs, beating {l_} {f['wins'][champ]}-{f['wins'][l_]} in the final; "
                     f"{sum(s['wins'][champ] for s in path)}-{sum(sum(v for c, v in s['wins'].items() if c != champ) for s in path)} "
                     f"in games over {len(path)} series.")
    elif len(roots) > 1:
        tops = [s for s in roots if s["winner"]]
        brief.append("The data has no single final: the last series were " + "; ".join(res(s) for s in roots) + ". "
                     + ("Separate brackets, or a final not played." if len(tops) > 1 else ""))
    sweeps = [s for s in main if s["finished"] and len(s["lead"]) == 1 and s["need"] > 1]
    long_ = [s for s in main if s["finished"] and len(s["games"]) == 2 * s["need"] - 1 and s["need"] > 1]
    upsets = []
    for s in main:
        if s["winner"] and all(c in seed for c in s["teams"]):
            l_ = [c for c in s["teams"] if c != s["winner"]][0]
            if seed[s["winner"]] > seed[l_]:
                upsets.append((s, l_))
    if upsets:
        brief.append(f"{len(upsets)} lower seed{'s' if len(upsets) > 1 else ''} won a series: " + "; ".join(
            f"{s['winner']} ({ORD(seed[s['winner']])}) over {l_} ({ORD(seed[l_])})" for s, l_ in upsets) + ".")
    if sweeps or long_:
        brief.append(f"{len(sweeps)} sweep{'s' if len(sweeps) != 1 else ''}, {len(long_)} series to the last game.")
    # coaches placed above a playoff coach who didn't play in the playoffs (2026-11-10: SNES B's best regular season,
    # 26-5, sat out): the seeds are regular-season places, not a league's own seeding
    in_po = {c for s in ss for c in s["teams"]}
    lowest = max((seed[c] for c in in_po if c in seed), default=0)
    absent = [c for c in order[:lowest] if S.base_name(c) not in in_po]
    if absent:
        brief.append("Not in the playoffs though placed above a coach who was: " + ", ".join(
            f"{c} ({ORD(order.index(c) + 1)}, {tab[c]['W']}-{tab[c]['GP'] - tab[c]['W'] - tab[c]['T']} in "
            f"{tab[c]['GP']} games)" for c in absent) + "; the seeds here are regular-season places.")
    unf = [s for s in main if not s["finished"]]
    if unf:
        brief.append("Not finished in the data: " + "; ".join(res(s) for s in unf) + ".")
    sec = [s for s in ss if s["second"]]
    if sec:
        brief.append("Second-chance series (a coach who had already lost one): " + "; ".join(res(s) for s in sec) + ".")
    w(" ".join(brief) + "\n")

    # --- the bracket
    w("## The series\n")
    n_rounds = max(rounds) if rounds else 0
    for rd in sorted(rounds):
        group = rounds[rd]
        name = round_name(group[0]["from_end"], n_rounds, len(group))
        if group[0]["from_end"] == 0 and len(roots) > 1:
            name = "The last round (no final in the data)"
        w(f"### {name}\n")
        for s in group:
            a, b = s["teams"]
            odds = ""
            if not new(a) and not new(b):
                p = S.sig(R(a) - R(b))
                pa = series_odds(p, max(1, s["need"]))
                odds = f"; before the series {a} {100 * pa:.0f}%, {b} {100 - 100 * pa:.0f}%"
            seeds = ", ".join(f"{c} {ORD(seed[c])} seed ({team.get(c, '')})" for c in s["teams"] if c in seed)
            w(f"- **{res(s)}** ({seeds}{odds}).")
            for r in s["games"]:
                w(f"  - {game_line(r, s['winner'])}")
        byes = sorted({c for s in rounds.get(rd + 1, []) for c in s["teams"]} -
                      {c for s in rounds[rd] for c in s["teams"]} - {s["winner"] for s in rounds[rd]})
        if byes and rd + 1 in rounds:
            w(f"\nInto the next round without a series here: {', '.join(f'{c} ({ORD(seed[c])} seed)' if c in seed else c for c in byes)}.")
        w("")
    if sec:
        w("### Second-chance series\n")
        for s in sec:
            w(f"- **{res(s)}**.")
            for r in s["games"]:
                w(f"  - {game_line(r, s['winner'])}")
        w("")

    # --- players, goalies, teams (simulated games left out)
    real = [r for r in rows if r["sim"] in ("0", "")]
    pl, gk, tm = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
    big, shut, ots, comebacks = [], [], 0, []
    for r in real:
        hs, as_ = S.num(r["HomeScore"]), S.num(r["AwayScore"])
        ots += any(S.num(r[k]) for k in ("HomeGoalsOT", "AwayGoalsOT", "HomeShotsOT", "AwayShotsOT"))
        for me, op in (("Home", "Away"), ("Away", "Home")):
            c = r[me + "Player"]
            us, them = S.num(r[me + "Score"]), S.num(r[op + "Score"])
            t = tm[c]
            t["GP"] += 1
            t["GF"] += us
            t["GA"] += them
            t["SF"] += S.num(r[me + "Shots"])
            t["SA"] += S.num(r[op + "Shots"])
            t["PPG"] += S.num(r[me + "PPGoals"])
            t["PPT"] += S.num(r[me + "PPTries"])
            for p in ast.literal_eval(r[me + "Players"] or "[]"):
                line = S.player_line(p)
                k = (p[1], c)
                pl[k]["GP"] += 1
                for f in ("G", "A", "P"):
                    pl[k][f] += line[f]
            for q in ast.literal_eval(r[me + "Goalies"] or "[]"):
                k = (q[1], c)
                gk[k]["GP"] += 1
                gk[k]["GA"] += q[2]
                gk[k]["SV"] += q[3]
                gk[k]["SA"] += q[4]
                if them == 0:
                    shut.append((q[1], c, r[op + "Player"], int(us), r["DateTime"][:10]))
            for p in ast.literal_eval(r[me + "Players"] or "[]"):
                if p[3] >= 3:
                    big.append((p[3], p[5], p[1], c, r[op + "Player"], int(us), int(them), r["DateTime"][:10]))
            a2 = S.num(r[me + "GoalsP1"]) + S.num(r[me + "GoalsP2"])
            b2 = S.num(r[op + "GoalsP1"]) + S.num(r[op + "GoalsP2"])
            if a2 < b2 and us > them:
                comebacks.append((int(b2 - a2), c, r[op + "Player"], int(us), int(them), r["DateTime"][:10]))
    w("## Playoff leaders\n")
    w("Simulated games left out.\n")
    w("| Player | Coach | GP | G | A | Pts |")
    w("|---|---|---|---|---|---|")
    for (nm, c), v in sorted(pl.items(), key=lambda kv: (-kv[1]["P"], -kv[1]["G"]))[:12]:
        w(f"| {nm} | {c} | {v['GP']} | {v['G']} | {v['A']} | {v['P']} |")
    w("")
    w("| Goalie | Coach | GP | Shots | Saves | Save % | GA/G |")
    w("|---|---|---|---|---|---|---|")
    for (nm, c), v in sorted(gk.items(), key=lambda kv: -kv[1]["SV"] / max(1, kv[1]["SA"])):
        if v["GP"] >= 3:
            w(f"| {nm} | {c} | {v['GP']} | {v['SA']} | {v['SV']} | {S.pct(v['SV'], v['SA'])} | {v['GA'] / v['GP']:.2f} |")
    w("")
    w("## Teams in the playoffs\n")
    w("| Coach | Team | Seed | GP | GF/G | GA/G | Shots for / against a game | PP % |")
    w("|---|---|---|---|---|---|---|---|")
    for c, t in sorted(tm.items(), key=lambda kv: seed.get(kv[0], 99)):
        w(f"| {c} | {team.get(c, '')} | {seed.get(c, '-')} | {t['GP']} | {t['GF'] / t['GP']:.2f} | {t['GA'] / t['GP']:.2f} | "
          f"{t['SF'] / t['GP']:.1f} / {t['SA'] / t['GP']:.1f} | {S.pct(t['PPG'], t['PPT'])} |")
    w("")
    w("## Notable games\n")
    if big:
        w("- Biggest single games: " + "; ".join(f"{nm} ({c}) {g} goals, {p} points against {o} ({u}-{t}, {d})"
                                                  for g, p, nm, c, o, u, t, d in sorted(big, reverse=True)[:4]) + ".")
    if comebacks:
        w("- Comebacks from behind after two periods: " + "; ".join(f"{c} over {o} {u}-{t}, down {k} ({d})"
                                                                    for k, c, o, u, t, d in sorted(comebacks, reverse=True)[:4]) + ".")
    if shut:
        w(f"- Shutouts ({len(shut)}): " + "; ".join(f"{g} ({c}) {u}-0 against {o} ({d})" for g, c, o, u, d in shut) + ".")
    w(f"- Overtime games: {ots} of {len(real)}.")
    blow = sorted(real, key=lambda r: -abs(S.num(r["HomeScore"]) - S.num(r["AwayScore"])))[:3]
    w("- Biggest wins: " + "; ".join(game_line(r, None) for r in blow) + ".\n")
    return "\n".join(L) + "\n"


def main():
    every = set()                                  # every league with playoff games (some have no regular season)
    for system in ("GENS", "SNES"):
        with open(S.DATA / f"All_Games_{system}.csv", newline="", encoding="utf-8", errors="replace") as fh:
            every |= {r["League"] for r in csv.DictReader(fh) if r["RegOrPlay"] == "P"}
    every = sorted(every)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    names = []
    for a in args:
        names += [a] if a in every else [lg for lg in every if lg.startswith(a)]
    S.OUT.mkdir(parents=True, exist_ok=True)
    for lg in names:
        try:
            text = build(lg)
        except SystemExit as e:
            print(f"{lg}: {e}")
            continue
        p = S.OUT / f"{lg}_playoffs.md"
        p.write_text(text, encoding="utf-8")
        print(p)


if __name__ == "__main__":
    main()
