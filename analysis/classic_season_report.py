"""One coach's season in one league, against the rest of that league (2026-11-09, the user: Classic_Fall2026_GENS-A
and _SNES-AB). Names real people, so the report goes only to %USERPROFILE%\\NHL94_League_Data\\season_reports, never
the repository; the script prints nothing but the path.

From the league database (All_Games_GENS.csv / All_Games_SNES.csv): every regular-season game of the league, as the
league counts them (a double upload too); simulated games left out. Points: 2 a win, none for
a loss (overtime included; a tie 1). Rates per game, so coaches with games left compare fairly. Ranks: 1 is the best
(fewest for things against); coaches with very few games (under a quarter of the most, or under 5) are left out of
the table and ranks as in classic_league_report.py, their games still counted for their opponents. Any league (2026-11-10). Pre-season strength: coach_history's rating (Classic for a Classic league, all-leagues for any other) the day before the league's first
game (win chance against coach B = 1 / (1 + exp(-(a - b))); teams and home ice not in it).

"Their season" at the top tells it in words from the same numbers (2026-11-10): the result against the pre-season
ratings, the arc by ten-game stretches and streaks, the best and worst ranks, key games, luck and the leading players.

python analysis/classic_season_report.py LEAGUE COACH"""
import ast
import csv
import json
import math
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

DATA = Path(os.path.expanduser("~")) / "NHL94_League_Data"
OUT = DATA / "season_reports"
STATS = ["Score", "Shots", "PPGoals", "PPTries", "SHGoals", "BreakGoals", "BreakTries", "OneTimerGoals",
         "OneTimerTries", "PenShotGoals", "PenShotTries", "FaceoffWins", "Checks", "PIM", "AttackZoneTime",
         "PassComps", "PassTries", "GoalsP1", "ShotsP1", "GoalsP2", "ShotsP2", "GoalsP3", "ShotsP3", "GoalsOT",
         "ShotsOT"]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


_SYSTEM = {}


def system_of(league):
    """'GENS' or 'SNES': from the name, or, for a league named for neither (Classic_Dynasty_S1, a Genesis league), the
    database that holds it (2026-11-10: it was read from the SNES file and had no games)."""
    if "GENS" in league:
        return "GENS"
    if "SNES" in league:
        return "SNES"
    if league not in _SYSTEM:
        _SYSTEM[league] = "SNES"
        with open(DATA / "All_Games_GENS.csv", newline="", encoding="utf-8", errors="replace") as fh:
            if any(r["League"] == league for r in csv.DictReader(fh)):
                _SYSTEM[league] = "GENS"
    return _SYSTEM[league]


def load(league):
    system = system_of(league)
    path = DATA / f"All_Games_{system}.csv"
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rows = [r for r in csv.DictReader(fh) if r["League"] == league and r["sim"] in ("0", "") and r["RegOrPlay"] == "R"]
    # every uploaded game counts, as the league counts it (a double upload included: the user, 2026-11-09). A row
    # repeating an earlier one (a mistake, or a game entered from another save state with the same outcome) is used
    # like any other game, stats and single-game lists too: not ideal, but better than losing the game (the user,
    # 2026-11-10).
    # DateTime is when a result was uploaded (a batch's games seconds apart), and the games are taken to be uploaded
    # in the order played (the user, 2026-11-10: there is no way of knowing otherwise), so streaks, "in a row" and
    # the last game follow it; MatchID only breaks an exact tie
    # DateTime's month, day and hour aren't zero-padded ("2015-4-27 9:31:00"), so as text 9:31 sorted after 23:20 on
    # the same day (review 2026-11-10): written padded here, so every comparison and [:10] below is right
    for r in rows:
        r["DateTime"] = padded(r["DateTime"])
    rows.sort(key=lambda r: (r["DateTime"], int(r["MatchID"])))
    LEVELS[league] = split_levels(league, system, rows)
    return system, rows


# A league named for two levels (Classic_Fall2026_SNES-AB, _SNES-CD) held both in one schedule: an experiment, each
# level normally its own league (the user, 2026-11-10). Its levels are written up apart: standings, ranks, winners.
LEVELS = {}  # league -> {coach: level letter}; {} for an ordinary league


def level_letters(league):
    m = re.search(r"_(?:GENS|SNES)-([A-Za-z]{2,})$", league)
    letters = m.group(1).upper() if m else ""
    return letters if len(letters) >= 2 and set(letters) != {"A"} else ""  # AA / AAA are one level


def split_levels(league, system, rows):
    """{coach: letter} for a two-level league, and coaches with a team in each level renamed in rows to
    'coach (TEAM)' so each team is its own entry (SNES-CD 2026: one coach ran a team in each level). The levels are the schedule's
    groups: teams meet inside their level at least as often as the commonest pairing (SNES-AB 4, SNES-CD 6), across it
    less. The higher level is the group whose coaches with SNES / Genesis Classic games before the league had the higher
    mean pre-season rating (newcomers' starting rating left out). {} when the schedule doesn't split as the name says."""
    letters = level_letters(league)
    if not letters:
        return {}
    meet = defaultdict(Counter)
    for r in rows:
        h, a = (r["HomePlayer"], r["HomeTeamAbbrev"]), (r["AwayPlayer"], r["AwayTeamAbbrev"])
        meet[h][a] += 1
        meet[a][h] += 1
    common = Counter(k for x in meet for k in meet[x].values()).most_common(1)[0][0]
    comps, seen = [], set()
    for n in sorted(meet):
        if n in seen:
            continue
        stack, comp = [n], set()
        while stack:
            x = stack.pop()
            if x not in comp:
                comp.add(x)
                stack += [o for o, k in meet[x].items() if k >= common and o not in comp]
        seen |= comp
        comps.append(comp)
    if len(comps) != len(letters):
        print(f"note: {league}'s schedule doesn't split into {len(letters)} levels ({len(comps)} groups); one table",
              file=sys.stderr)
        return {}
    first = season_start(league)  # pre-season: before the season's first game on the system
    hist = json.load(open(DATA / "coach_history" / f"{'GENESIS' if system == 'GENS' else 'SNES'}_classic.json",
                          encoding="utf-8"))
    day = max(int(k) for k in hist if int(k) <= first.toordinal())
    rated = {k: v[0] for k, v in hist[str(day)].items() if v[1] > 0}

    def strength(comp):
        v = [rated[c.lower()] for c, _ in comp if c.lower() in rated]
        return sum(v) / len(v) if v else -99

    comps.sort(key=strength, reverse=True)
    level = {node: letters[i] for i, comp in enumerate(comps) for node in comp}
    two = {c for c, _ in level if len({lv for (c2, _), lv in level.items() if c2 == c}) > 1}
    out = {}
    for r in rows:
        for side in ("Home", "Away"):
            c, t = r[side + "Player"], r[side + "TeamAbbrev"]
            name = f"{c} ({t})" if c in two else c
            r[side + "Player"] = name
            out[name] = level[(c, t)]
    return out


def player_line(p):
    """One skater's line from a game's Players list as a dict. Most rows are [number, name, position, G, A, P, shots,
    checks, PIM] with time on ice after (Genesis); older SNES rows have no checks, [number, name, position, G, A, P,
    shots, PIM] (their shots and PIM add up to the team's): Chk is None there (review 2026-11-10)."""
    if len(p) == 8:
        return {"G": p[3], "A": p[4], "P": p[5], "SOG": p[6], "Chk": None, "PIM": p[7]}
    out = {"G": p[3], "A": p[4], "P": p[5], "SOG": p[6], "Chk": p[7], "PIM": p[8] if len(p) > 8 else 0}
    if len(p) > 9:
        out["TOI"] = p[9]
    return out


def base_name(c):
    """A coach's own name, without the '(TEAM)' a two-level league adds."""
    return re.sub(r" \([A-Z]{2,4}\)$", "", c)


def level_title(league, letter):
    """'Classic_Fall2026_SNES-AB' + 'A' -> 'Classic_Fall2026_SNES-A' (the level's own name, for titles and files)."""
    return re.sub(r"-[A-Za-z]{2,}$", "-" + letter, league)


def padded(text):
    """'2015-4-27 9:31:00' -> '2015-04-27 09:31:00' (unparsable text kept as it is)."""
    try:
        d, _, t = text.strip().partition(" ")
        y, m, dd = (int(x) for x in d.split("-"))
        hms = [int(x) for x in t.split(":") if x] + [0, 0, 0]
        return f"{y:04d}-{m:02d}-{dd:02d} {hms[0]:02d}:{hms[1]:02d}:{hms[2]:02d}"
    except ValueError:
        return text


def sides(r):
    """The game from each coach's side: (coach, team, home?, own stats, opponent's stats, opponent, raw row)."""
    out = []
    for me, op in (("Home", "Away"), ("Away", "Home")):
        mine = {k: num(r[me + k]) for k in STATS}
        theirs = {k: num(r[op + k]) for k in STATS}
        mine["Players"], mine["Goalies"], mine["Goals"], mine["Penalties"] = (ast.literal_eval(r[me + k] or "[]")
                                                                            for k in ("Players", "Goalies", "Goals", "Penalties"))
        theirs["Goals"] = ast.literal_eval(r[op + "Goals"] or "[]")
        theirs["Penalties"] = ast.literal_eval(r[op + "Penalties"] or "[]")
        out.append(dict(coach=r[me + "Player"], team=r[me + "TeamAbbrev"], home=me == "Home", us=mine, them=theirs,
                        opp=r[op + "Player"], opp_team=r[op + "TeamAbbrev"], when=r["DateTime"], row=r))
    return out


RATED_GAMES = {}  # (system, day, scope) -> {coach: games behind the rating}; 0 is a newcomer's starting rating
_SEASON_START = {}


def is_classic(league):
    return league.lower().startswith("classic")


def scope(league):
    """The ratings a league is measured by (2026-11-10, the user: these reports for any league): a Classic league by
    coach_history's Classic rating (Classic games only), any other by its all-leagues rating (every league)."""
    return "classic" if is_classic(league) else "all"


def first_league(league):
    """How a newcomer is described: no games before in Classic leagues, or none in any league."""
    return "new to Classic" if is_classic(league) else "in their first league"


def rated_word(league):
    return "Classic games" if is_classic(league) else "league games"


def season_key(league):
    """The season a league belongs to: its name without the level at its end (Classic_Fall2026_GENS-A ->
    Classic_Fall2026_GENS; Blitz_'94_Season_10-B -> Blitz_'94_Season_10; Classic_Fall2020_GENS-B-E ->
    Classic_Fall2020_GENS; Velocity_League_Season_5 is its own)."""
    return re.sub(r"-[A-Za-z]{1,3}\d?(?:-[A-Za-z])?$", "", league)


def season_start(league):
    """The first game day of the league's whole season on its system (the leagues with its season_key). Pre-season
    ratings are taken then, the same for every league of the season: taken on each league's own first day, a league
    starting a day later had the others' first games in its "pre-season" ratings (review 2026-11-10: a coach new on
    October 3 in Genesis F was "the favourite" of Genesis E on October 4)."""
    key, system = season_key(league), system_of(league)
    if (system, key) not in _SEASON_START:
        with open(DATA / f"All_Games_{system}.csv", newline="", encoding="utf-8", errors="replace") as fh:
            days = [padded(r["DateTime"])[:10] for r in csv.DictReader(fh)
                    if season_key(r["League"]) == key and r["RegOrPlay"] == "R" and r["sim"] in ("0", "")]
        _SEASON_START[(system, key)] = date.fromisoformat(min(days))
    return _SEASON_START[(system, key)]


def ratings(system, league_first_day, league="Classic"):
    """{coach: rating} from coach_history on the last day it has on or before league_first_day (the ratings from
    games before that day), and that day: the Classic ratings for a Classic league, the all-leagues ones otherwise."""
    sc = scope(league)
    hist = DATA / "coach_history" / f"{'GENESIS' if system == 'GENS' else 'SNES'}_{sc}.json"
    d = json.load(open(hist, encoding="utf-8"))
    day = max(int(k) for k in d if int(k) <= league_first_day.toordinal())
    RATED_GAMES[(system, league_first_day, sc)] = {k: v[1] for k, v in d[str(day)].items()}
    return {k: v[0] for k, v in d[str(day)].items()}, date.fromordinal(day)


def ratings_after(system, day, league="Classic"):
    """The first ratings coach_history has on or after day (for "looking ahead": the day after a league's last game),
    and that day; the last it has when none is that late (a league still playing)."""
    sc = scope(league)
    hist = DATA / "coach_history" / f"{'GENESIS' if system == 'GENS' else 'SNES'}_{sc}.json"
    d = json.load(open(hist, encoding="utf-8"))
    later = [int(k) for k in d if int(k) >= day.toordinal()]
    k = min(later) if later else max(int(k) for k in d)
    return {c: v[0] for c, v in d[str(k)].items()}, date.fromordinal(k)


def newcomer(system, league_first_day, coach, league="Classic"):
    """True when the coach's pre-season rating is only the starting rating (no games before the league in its
    ratings' leagues), so it says nothing about them: no favourite or pre-season place from it (review 2026-11-10)."""
    key = (system, league_first_day, scope(league))
    if key not in RATED_GAMES:
        ratings(system, league_first_day, league)
    return RATED_GAMES[key].get(base_name(coach).lower(), 0) == 0


def sig(x):
    return 1 / (1 + math.exp(-x))


def pct(a, b, digits=1):
    return f"{100 * a / b:.{digits}f}%" if b else "-"


def fmt_time(s):
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def team_label(gs):
    """The coach's team, or teams when they ran a second one for a real share of their games (SNES-CD 2026: Chicago
    40 and Dallas 34)."""
    n = Counter(g["team"] for g in gs).most_common()
    return "/".join(t for t, k in n if k >= len(gs) / 4) or n[0][0]


def build(league, coach):
    system, games = load(league)
    per = defaultdict(list)
    for r in games:
        for g in sides(r):
            per[g["coach"]].append(g)
    if coach not in per:
        raise SystemExit(f"{coach} has no games in {league}")
    first = season_start(league)  # the season's first day on the system: pre-season ratings the same for every league
    rat, rat_day = ratings(system, first, league)
    known = [rat[base_name(c).lower()] for c in per if base_name(c).lower() in rat]
    mean_known = sum(known) / len(known)
    R = lambda c: rat.get(base_name(c).lower(), mean_known)
    lv = LEVELS.get(league, {})
    my_level = lv.get(coach)
    title = level_title(league, my_level) if my_level else league

    # --- per-coach totals
    tab = {}
    for c, gs in per.items():
        t = Counter()
        for g in gs:
            us, them = g["us"], g["them"]
            ot = bool(us["GoalsOT"] or them["GoalsOT"] or us["ShotsOT"] or them["ShotsOT"])
            win, loss = us["Score"] > them["Score"], us["Score"] < them["Score"]
            t["GP"] += 1
            t["W"] += win
            t["L"] += loss
            t["T"] += not win and not loss
            t["OTW"] += win and ot
            t["OTL"] += loss and ot
            t["one_goal_W"] += win and us["Score"] - them["Score"] == 1
            t["one_goal_L"] += loss and them["Score"] - us["Score"] == 1
            t["blow_W"] += us["Score"] - them["Score"] >= 3
            t["blow_L"] += them["Score"] - us["Score"] >= 3
            for k in STATS:
                t["F_" + k] += us[k]
                t["A_" + k] += them[k]
            t["exp_W"] += sig(R(c) - R(g["opp"]))
            t["opp_rating"] += R(g["opp"])
            t["first_goal"] += 0
        t["Pts"] = 2 * t["W"] + t["T"]
        tab[c] = t
    # as classic_league_report: coaches with very few games are left out of the tables and ranks (their games still
    # count for their opponents), so a coach's report and the league report agree on places (review, 2026-11-10)
    gp_league = {c: t["GP"] for c, t in tab.items()}
    omitted = sorted(c for c in tab if tab[c]["GP"] < max(5, max(gp_league.values()) / 4))
    if coach in omitted:
        raise SystemExit(f"{coach} played too few games in {league} for a report ({gp_league[coach]})")
    for c in omitted:
        del tab[c]
    # a two-level league: the table, ranks and averages are the coach's own level; games against the other level
    # still count in every record (as an omitted coach's do)
    for c in sorted(c for c in tab if my_level and lv.get(c) != my_level):
        del tab[c]
    teams = {c: team_label(gs) for c, gs in per.items()}
    me = tab[coach]

    def rate(c, key):
        t = tab[c]
        return t[key] / t["GP"]

    def rank(value_of, higher_better=True):
        # ties share a rank (review 2026-11-10: tied coaches came in an arbitrary order)
        v = value_of(coach)
        better = sum(1 for c in tab if (value_of(c) > v + 1e-12 if higher_better else value_of(c) < v - 1e-12))
        return better + 1, len(tab)

    def league_avg(value_of):
        return sum(value_of(c) for c in tab) / len(tab)

    L = []
    w = L.append
    gp_all = Counter({c: t["GP"] for c, t in tab.items()})
    w(f"# {coach}'s {title} season\n")
    if my_level:
        w(f"{league} held two levels in one schedule (an experiment; each level is normally its own league). {coach} "
          f"played in the {my_level} level, so the table, ranks and league averages here are the {my_level} level's "
          f"{len(tab)} coaches; games against the other level count in every record.\n")
    fewer = [f"{c} {n}" for c, n in sorted(gp_all.items(), key=lambda x: -x[1]) if n < me['GP']]
    w(f"{len(games)} games in the league ({min(r['DateTime'] for r in games)[:10]} to "
      f"{max(r['DateTime'] for r in games)[:10]}), {len(tab)} coaches{' in the level' if my_level else ''}. "
      f"{coach} played {me['GP']} as {teams[coach]}."
      + (" Fewer games: " + ", ".join(fewer) + "." if fewer else "")
      + (" Left out for playing very few games (their games still count for their opponents): " +
         ", ".join(f"{c} ({gp_league[c]})" for c in omitted) + "." if omitted else "")
      + " Rates are per game, so they compare fairly; ranks are out of all coaches (1 the best).\n")

    # --- standings
    w("## Standings\n")
    w("Points: 2 a win, none for any loss. Expected wins: from each coach's pre-season rating against their opponents' "
      f"(coach_history, {rat_day}; teams and home ice not counted).\n")
    w("| | Coach | Team | GP | W-L | OT W-L | Pts | Pts % | GF/G | GA/G | Diff/G | Exp. W | W - Exp. | Pre-season vs league avg |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    order = sorted(tab, key=lambda c: (-tab[c]["Pts"] / (2 * tab[c]["GP"]), -(tab[c]["F_Score"] - tab[c]["A_Score"]) / tab[c]["GP"]))
    for i, c in enumerate(order, 1):
        t = tab[c]
        name = f"**{c}**" if c == coach else c
        w(f"| {i} | {name} | {teams[c]} | {t['GP']} | {t['W']}-{t['L']}" + (f"-{t['T']}" if t['T'] else "") +
          f" | {t['OTW']}-{t['OTL']} | {t['Pts']} | {t['Pts'] / (2 * t['GP']):.3f} | {t['F_Score'] / t['GP']:.2f} | "
          f"{t['A_Score'] / t['GP']:.2f} | {(t['F_Score'] - t['A_Score']) / t['GP']:+.2f} | {t['exp_W']:.1f} | "
          f"{t['W'] - t['exp_W']:+.1f} | {100 * sig(R(c) - mean_known):.0f}%{'' if base_name(c).lower() in rat else ' (no rating)'} |")
    w("")

    # --- a league of groups (SNES-AB: two groups of 8, 4 games within the group, 2 against some of the other)
    meet = Counter(g["opp"] for g in per[coach])
    group = {coach} | {o for o, n in meet.items() if n >= 4 and o in tab}
    if not my_level and len(group) >= 4 and all(meet[o] <= 2 for o in tab if o not in group):
        w(f"### {coach}'s group\n")
        w(f"The schedule has groups: {coach} played {', '.join(sorted(group - {coach}))} 4 or more times each, and the "
          f"rest of the league ({len(tab) - len(group)} coaches) 2 times or not at all.\n")
        w("| | Coach | Team | GP | W-L | Pts | Pts % | Diff/G | W - Exp. |")
        w("|---|---|---|---|---|---|---|---|---|")
        for i, c in enumerate([c for c in order if c in group], 1):
            t = tab[c]
            w(f"| {i} | {'**' + c + '**' if c == coach else c} | {teams[c]} | {t['GP']} | {t['W']}-{t['L']}" +
              (f"-{t['T']}" if t['T'] else "") + f" | {t['Pts']} | {t['Pts'] / (2 * t['GP']):.3f} | "
              f"{(t['F_Score'] - t['A_Score']) / t['GP']:+.2f} | {t['W'] - t['exp_W']:+.1f} |")
        w("")

    # --- team stats
    def row(label, f_us, f_them=None, higher_better=True, fmt="{:.2f}"):
        v = f_us(coach)
        rk, n = rank(f_us, higher_better)
        line = f"| {label} | {fmt.format(v)} | {fmt.format(league_avg(f_us))} | {rk} of {n} |"
        if f_them:
            v2 = f_them(coach)
            rk2, _ = rank(f_them, not higher_better)
            line += f" {fmt.format(v2)} | {fmt.format(league_avg(f_them))} | {rk2} of {n} |"
        else:
            line += " | | |"
        w(line)

    w("## Team stats per game\n")
    w(f"For: {coach}'s team; against: their opponents. Rank 1 is the most for, and the fewest against.\n")
    w(f"| | {coach} | League | Rank | Against | League | Rank |")
    w("|---|---|---|---|---|---|---|")
    row("Goals", lambda c: rate(c, "F_Score"), lambda c: rate(c, "A_Score"))
    row("Shots on goal", lambda c: rate(c, "F_Shots"), lambda c: rate(c, "A_Shots"))
    row("Shooting %", lambda c: 100 * tab[c]["F_Score"] / max(1, tab[c]["F_Shots"]),
        lambda c: 100 * tab[c]["A_Score"] / max(1, tab[c]["A_Shots"]), fmt="{:.1f}")
    row("Save %", lambda c: 100 - 100 * tab[c]["A_Score"] / max(1, tab[c]["A_Shots"]), None, fmt="{:.1f}")
    row("PDO (shooting % + save %)", lambda c: 100 * tab[c]["F_Score"] / max(1, tab[c]["F_Shots"]) + 100 - 100 * tab[c]["A_Score"] / max(1, tab[c]["A_Shots"]), None, fmt="{:.1f}")
    row("Shot share %", lambda c: 100 * tab[c]["F_Shots"] / max(1, tab[c]["F_Shots"] + tab[c]["A_Shots"]), None, fmt="{:.1f}")
    row("Power-play goals", lambda c: rate(c, "F_PPGoals"), lambda c: rate(c, "A_PPGoals"))
    row("Power plays", lambda c: rate(c, "F_PPTries"), lambda c: rate(c, "A_PPTries"))
    row("Power play %", lambda c: 100 * tab[c]["F_PPGoals"] / max(1, tab[c]["F_PPTries"]),
        lambda c: 100 * tab[c]["A_PPGoals"] / max(1, tab[c]["A_PPTries"]), fmt="{:.1f}")
    row("Short-handed goals", lambda c: rate(c, "F_SHGoals"), lambda c: rate(c, "A_SHGoals"))
    row("Breakaway goals", lambda c: rate(c, "F_BreakGoals"), lambda c: rate(c, "A_BreakGoals"))
    row("Breakaways", lambda c: rate(c, "F_BreakTries"), lambda c: rate(c, "A_BreakTries"))
    row("One-timer goals", lambda c: rate(c, "F_OneTimerGoals"), lambda c: rate(c, "A_OneTimerGoals"))
    row("One-timer tries", lambda c: rate(c, "F_OneTimerTries"), lambda c: rate(c, "A_OneTimerTries"))
    row("Faceoff win %", lambda c: 100 * tab[c]["F_FaceoffWins"] / max(1, tab[c]["F_FaceoffWins"] + tab[c]["A_FaceoffWins"]), None, fmt="{:.1f}")
    row("Body checks", lambda c: rate(c, "F_Checks"), lambda c: rate(c, "A_Checks"))
    row("Penalty minutes", lambda c: rate(c, "F_PIM"), lambda c: rate(c, "A_PIM"), higher_better=False)
    row("Attack zone time (s)", lambda c: rate(c, "F_AttackZoneTime"), lambda c: rate(c, "A_AttackZoneTime"), fmt="{:.0f}")
    row("Passes completed", lambda c: rate(c, "F_PassComps"), lambda c: rate(c, "A_PassComps"))
    row("Pass completion %", lambda c: 100 * tab[c]["F_PassComps"] / max(1, tab[c]["F_PassTries"]),
        lambda c: 100 * tab[c]["A_PassComps"] / max(1, tab[c]["A_PassTries"]), fmt="{:.1f}")
    w("\n(Penalty minutes: rank 1 = the fewest taken; against = drawn, rank 1 the most drawn.)\n")

    # --- by period
    w("## By period\n")
    w("| Period | GF/G | GA/G | Shots for/G | Shots against/G | League GF/G |")
    w("|---|---|---|---|---|---|")
    for p, lab in ((1, "1st"), (2, "2nd"), (3, "3rd")):
        lg = league_avg(lambda c: rate(c, f"F_GoalsP{p}"))
        w(f"| {lab} | {rate(coach, f'F_GoalsP{p}'):.2f} | {rate(coach, f'A_GoalsP{p}'):.2f} | "
          f"{rate(coach, f'F_ShotsP{p}'):.2f} | {rate(coach, f'A_ShotsP{p}'):.2f} | {lg:.2f} |")
    w("")

    # --- game situations (own games)
    mine = sorted(per[coach], key=lambda g: g["when"])
    sit = Counter()
    for g in mine:
        us, them = g["us"], g["them"]
        res = "W" if us["Score"] > them["Score"] else "L" if us["Score"] < them["Score"] else "T"
        a2, b2 = us["GoalsP1"] + us["GoalsP2"], them["GoalsP1"] + them["GoalsP2"]
        st = "led" if a2 > b2 else "trailed" if a2 < b2 else "tied"
        sit[("after 2", st, res)] += 1
        a1, b1 = us["GoalsP1"], them["GoalsP1"]
        st1 = "led" if a1 > b1 else "trailed" if a1 < b1 else "tied"
        sit[("after 1", st1, res)] += 1
        goals = sorted([(x[0], x[1], "us") for x in us["Goals"]] + [(x[0], x[1], "them") for x in them["Goals"]])
        if goals:
            sit[("first goal", goals[0][2], res)] += 1
        sit[("home" if g["home"] else "away", "", res)] += 1
    w("## Game situations\n")
    w("| | Record |")
    w("|---|---|")
    for lab, key in (("Home", ("home", "")), ("Away", ("away", ""))):
        w(f"| {lab} | {sit[key + ('W',)]}-{sit[key + ('L',)]}" + (f"-{sit[key + ('T',)]}" if sit[key + ('T',)] else "") + " |")
    for when in ("after 1", "after 2"):
        for st in ("led", "tied", "trailed"):
            k = (when, st)
            n = sit[k + ("W",)] + sit[k + ("L",)] + sit[k + ("T",)]
            if n:
                w(f"| {st.capitalize()} {when} period{'s' if when == 'after 2' else ''} | {sit[k + ('W',)]}-{sit[k + ('L',)]}"
                  + (f"-{sit[k + ('T',)]}" if sit[k + ('T',)] else "") + f" ({n} game{'' if n == 1 else 's'}) |")
    for who, lab in (("us", "Scored first"), ("them", "Opponent scored first")):
        k = ("first goal", who)
        w(f"| {lab} | {sit[k + ('W',)]}-{sit[k + ('L',)]}" + (f"-{sit[k + ('T',)]}" if sit[k + ('T',)] else "") + " |")
    w(f"| One-goal games | {me['one_goal_W']}-{me['one_goal_L']} |")
    w(f"| Overtime | {me['OTW']}-{me['OTL']} |")
    w(f"| Won / lost by 3+ | {me['blow_W']} / {me['blow_L']} |")
    w("")
    # league comparison for one-goal and comeback
    comeback = lambda c: sum(1 for g in per[c] if (g['us']['GoalsP1'] + g['us']['GoalsP2'] < g['them']['GoalsP1'] + g['them']['GoalsP2']) and g['us']['Score'] > g['them']['Score'])
    trailed = lambda c: sum(1 for g in per[c] if g['us']['GoalsP1'] + g['us']['GoalsP2'] < g['them']['GoalsP1'] + g['them']['GoalsP2'])
    blown = lambda c: sum(1 for g in per[c] if (g['us']['GoalsP1'] + g['us']['GoalsP2'] > g['them']['GoalsP1'] + g['them']['GoalsP2']) and g['us']['Score'] < g['them']['Score'])
    led = lambda c: sum(1 for g in per[c] if g['us']['GoalsP1'] + g['us']['GoalsP2'] > g['them']['GoalsP1'] + g['them']['GoalsP2'])
    lg_cb = sum(comeback(c) for c in tab) / max(1, sum(trailed(c) for c in tab))
    lg_bl = sum(blown(c) for c in tab) / max(1, sum(led(c) for c in tab))
    w(f"League: teams trailing after two periods came back to win {100 * lg_cb:.0f}% of the time; teams leading after two "
      f"lost {100 * lg_bl:.0f}%. One-goal games, every coach: " + ", ".join(
          f"{c} {tab[c]['one_goal_W']}-{tab[c]['one_goal_L']}" for c in order) + ".\n")

    # --- scoring
    w("## How the goals came\n")
    kinds_us, kinds_them = Counter(), Counter()
    late_us = late_them = 0
    for g in mine:
        for x in g["us"]["Goals"]:
            kinds_us[x[9]] += 1
            late_us += x[0] == 3 and x[1] >= 240
        for x in g["them"]["Goals"]:
            kinds_them[x[9]] += 1
            late_them += x[0] == 3 and x[1] >= 240
    w(f"For: {', '.join(f'{k} {v}' for k, v in kinds_us.most_common())}; against: "
      f"{', '.join(f'{k} {v}' for k, v in kinds_them.most_common())}. In the last minute of the 3rd: {late_us} for, "
      f"{late_them} against.\n")
    pen_types, pen_drawn = Counter(), Counter()
    for g in mine:
        for p in g["us"]["Penalties"]:
            pen_types[p[5]] += 1
        for p in g["them"]["Penalties"]:
            pen_drawn[p[5]] += 1
    w(f"Penalties taken ({sum(pen_types.values())}): " + ", ".join(f"{k} {v}" for k, v in pen_types.most_common()) +
      f". Drawn ({sum(pen_drawn.values())}): " + ", ".join(f"{k} {v}" for k, v in pen_drawn.most_common()) + ".\n")

    # --- players
    pl = defaultdict(Counter)
    gk = defaultdict(Counter)
    for g in mine:
        for p in g["us"]["Players"]:
            k = (p[1], p[2])
            pl[k]["GP"] += 1
            line = player_line(p)
            for f in ("G", "A", "P", "SOG", "PIM"):
                pl[k][f] += line[f]
            if "TOI" in line:
                pl[k]["TOI"] += line["TOI"]
            if line["Chk"] is None:
                pl[k]["nochk"] += 1            # an older row with no checks: the column shows "-"
            else:
                pl[k]["Chk"] += line["Chk"]
        for q in g["us"]["Goalies"]:
            k = q[1]
            gk[k]["GP"] += 1
            gk[k]["GA"] += q[2]
            gk[k]["SV"] += q[3]
            gk[k]["SA"] += q[4]
    ppg = Counter()
    for g in mine:
        for x in g["us"]["Goals"]:
            if x[9] == "PP":
                ppg[x[4]] += 1
    w(f"## {teams[coach]}'s players\n")
    has_toi = any("TOI" in v for v in pl.values())
    w("| Player | Pos | GP | G | A | Pts | Shots | Sh % | PP G | Checks | PIM |" + (" TOI/GP |" if has_toi else ""))
    w("|---|---|---|---|---|---|---|---|---|---|---|" + ("---|" if has_toi else ""))
    for (name, pos), v in sorted(pl.items(), key=lambda kv: (-kv[1]["P"], -kv[1]["G"])):
        if v["P"] == 0 and v["SOG"] == 0 and v["Chk"] < 5:
            continue
        w(f"| {name} | {pos} | {v['GP']} | {v['G']} | {v['A']} | {v['P']} | {v['SOG']} | {pct(v['G'], v['SOG'])} | "
          f"{ppg[name]} | {'-' if v['nochk'] == v['GP'] else v['Chk']} | {v['PIM']} |"
          + (f" {fmt_time(v['TOI'] / v['GP'])} |" if has_toi else ""))
    w("")
    w("| Goalie | GP | Shots | Saves | GA | Save % | GA/G |")
    w("|---|---|---|---|---|---|---|")
    for name, v in sorted(gk.items(), key=lambda kv: -kv[1]["GP"]):
        w(f"| {name} | {v['GP']} | {v['SA']} | {v['SV']} | {v['GA']} | {pct(v['SV'], v['SA'])} | {v['GA'] / v['GP']:.2f} |")
    w("")

    # --- head to head
    w("## Against each opponent\n")
    w("Exp. W: from the two pre-season ratings alone.\n")
    w("| Opponent | Team | GP | W-L | GF-GA | Shots for-against | Exp. W | Their pre-season vs league avg |")
    w("|---|---|---|---|---|---|---|---|")
    h2h = defaultdict(Counter)
    for g in mine:
        o = g["opp"]
        h2h[o]["GP"] += 1
        h2h[o]["W"] += g["us"]["Score"] > g["them"]["Score"]
        h2h[o]["L"] += g["us"]["Score"] < g["them"]["Score"]
        h2h[o]["GF"] += g["us"]["Score"]
        h2h[o]["GA"] += g["them"]["Score"]
        h2h[o]["SF"] += g["us"]["Shots"]
        h2h[o]["SA"] += g["them"]["Shots"]
        h2h[o]["E"] += sig(R(coach) - R(o))
    for o in sorted(h2h, key=lambda o: (order.index(o) if o in order else len(order), o)):
        v = h2h[o]
        w(f"| {o} | {teams.get(o, '')} | {v['GP']} | {v['W']}-{v['L']} | {int(v['GF'])}-{int(v['GA'])} | "
          f"{int(v['SF'])}-{int(v['SA'])} | {v['E']:.1f} | {100 * sig(R(o) - mean_known):.0f}% |")
    tot_e = sum(v["E"] for v in h2h.values())
    w(f"\nTotal: {me['W']} win{'' if me['W'] == 1 else 's'} against {tot_e:.1f} expected from the ratings. Average opponent pre-season rating "
      f"{100 * sig(me['opp_rating'] / me['GP'] - mean_known):.0f}% (league average 50%).\n")

    # --- form
    w("## Over the season\n")
    res = ["W" if g["us"]["Score"] > g["them"]["Score"] else "L" if g["us"]["Score"] < g["them"]["Score"] else "T" for g in mine]
    w("In order: " + "".join(res) + "\n")
    def streak(ch):
        best = cur = 0
        for r_ in res:
            cur = cur + 1 if r_ == ch else 0
            best = max(best, cur)
        return best
    w(f"Longest winning streak {streak('W')}, losing streak {streak('L')}.\n")
    chunk = 10
    w("| Games | W-L | GF-GA | Shots for-against |")
    w("|---|---|---|---|")
    for i in range(0, len(mine), chunk):
        part = mine[i:i + chunk]
        wv = sum(g["us"]["Score"] > g["them"]["Score"] for g in part)
        lv = sum(g["us"]["Score"] < g["them"]["Score"] for g in part)
        w(f"| {i + 1}-{i + len(part)} | {wv}-{lv} | {int(sum(g['us']['Score'] for g in part))}-{int(sum(g['them']['Score'] for g in part))} | "
          f"{int(sum(g['us']['Shots'] for g in part))}-{int(sum(g['them']['Shots'] for g in part))} |")
    w("")

    # --- luck check
    w("## Luck and repeatability\n")
    gf, ga = me["F_Score"], me["A_Score"]
    pyth = gf ** 2 / (gf ** 2 + ga ** 2)
    w(f"- Pythagorean win % (GF^2 / (GF^2 + GA^2)) {100 * pyth:.1f}% against an actual {100 * me['W'] / me['GP']:.1f}% "
      f"(about {me['W'] - pyth * me['GP']:+.1f} wins from how the goals fell).")
    pdo = lambda c: 100 * tab[c]["F_Score"] / max(1, tab[c]["F_Shots"]) + 100 - 100 * tab[c]["A_Score"] / max(1, tab[c]["A_Shots"])
    w(f"- PDO {pdo(coach):.1f} (league {league_avg(pdo):.1f}); one-goal games {me['one_goal_W']}-{me['one_goal_L']}, "
      f"overtime {me['OTW']}-{me['OTL']}.")
    at = 3 if my_level else 2  # after the title and the header lines
    L[at:at] = narrative(coach, tab, order, teams, per, mine, res, R, rank, league_avg, rate, pdo, pl, gk, sig,
                         new=lambda c: newcomer(system, first, c, league), level=my_level, rated_label=rated_word(league))
    return "\n".join(L) + "\n"


def nth(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def narrative(coach, tab, order, teams, per, mine, res, R, rank, league_avg, rate, pdo, pl, gk, sig,
              new=lambda c: False, level=None, rated_label="Classic games"):
    """'Their season': the season told from the numbers in the report below it (nothing else), so every line can be
    checked against a table. (2026-11-10, the user: a scripted narrative for every coach.) new(c): the coach's
    rating is only a newcomer's starting one; level: the coach's level of a two-level league."""
    me, n = tab[coach], len(tab)
    place = order.index(coach) + 1
    # the pre-season place among the coaches whose ratings rest on games
    rated = [c for c in tab if not new(c)]
    pre = sorted(rated, key=lambda c: -R(c)).index(coach) + 1 if coach in rated else None
    w_, l_, gp = me["W"], me["L"], me["GP"]
    diff = (me["F_Score"] - me["A_Score"]) / gp
    beat = w_ - me["exp_W"]
    out = ["## Their season\n"]
    # 1. the result against expectations
    if place == 1:
        where, tail = (f"won the {level} level" if level else "won the league"), f", first of {n}"
    else:
        where = f"finished {nth(place)} of {n}" + (f" in the {level} level" if level else "")
        tail = (", near the top" if place <= max(2, n // 4) else ", near the bottom" if place > n - max(2, n // 4) else "")
    how = "above" if beat >= 3 else "below" if beat <= -3 else "about"
    exp_txt = ((f"well {how} " if how != "about" else "about ") + "what the pre-season ratings expected (" +
               (f"{me['exp_W']:.1f} wins; they had {coach} {nth(pre)} of the {len(rated)} with {rated_label} before"
                if pre else f"{me['exp_W']:.1f} wins from a newcomer's starting rating, so a weak guide") + ")")
    out.append(f"{coach} {where} as {teams[coach]}{tail}, going {w_}-{l_}" + (f"-{me['T']}" if me["T"] else "") +
               f" with {me['F_Score'] / gp:.2f} goals for and {me['A_Score'] / gp:.2f} against a game ({diff:+.2f}). "
               f"That is {exp_txt}.\n")
    # 2. the arc
    chunks = [mine[i:i + 10] for i in range(0, len(mine), 10)]
    rec = lambda part: (sum(g["us"]["Score"] > g["them"]["Score"] for g in part), sum(g["us"]["Score"] < g["them"]["Score"] for g in part))
    if len(chunks) >= 2:
        f0, fl = rec(chunks[0]), rec(chunks[-1])
        best = max(range(len(chunks)), key=lambda i: rec(chunks[i])[0] - rec(chunks[i])[1])
        worst = min(range(len(chunks)), key=lambda i: rec(chunks[i])[0] - rec(chunks[i])[1])
        start = "started strongly" if f0[0] > f0[1] + 2 else "started poorly" if f0[1] > f0[0] + 2 else "started evenly"
        finish = ("finished strongly" if fl[0] > fl[1] + 2 else
                  "never turned it around" if fl[1] > fl[0] + 2 and start == "started poorly" else
                  "faded at the end" if fl[1] > fl[0] + 2 else "finished about even")
        span = lambda i: f"games {10 * i + 1}-{10 * i + len(chunks[i])}"
        arc = f"They {start} ({f0[0]}-{f0[1]} in the first {len(chunks[0])} games) and {finish} ({fl[0]}-{fl[1]} in the last {len(chunks[-1])})."
        if best not in (0, len(chunks) - 1):
            arc += f" The best stretch was {span(best)} ({rec(chunks[best])[0]}-{rec(chunks[best])[1]})."
        if worst not in (0, len(chunks) - 1) and worst != best and rec(chunks[worst])[0] < rec(chunks[worst])[1]:
            arc += f" The hardest was {span(worst)} ({rec(chunks[worst])[0]}-{rec(chunks[worst])[1]})."
    else:
        arc = f"In {gp} games they went {w_}-{l_}."
    # a tie ends a streak, as in the league report (review 2026-11-10: splitting on the other letter alone ran
    # an 11-game streak through a tie into 20)
    run = lambda ch: max((len(s) for s in re.split(f"[^{ch}]", "".join(res))), default=0)
    sw, sl = run("W"), run("L")
    if sw >= 4:
        arc += f" Their longest winning streak was {sw} games."
    if sl >= 4:
        arc += f" They also lost {sl} in a row at one point." if sw >= 4 else f" Their longest losing streak was {sl} games."
    out.append(arc + "\n")
    # 3. strengths and weaknesses: ranks on the stats of the table below
    pp = lambda c: 100 * tab[c]["F_PPGoals"] / max(1, tab[c]["F_PPTries"])
    pk = lambda c: 100 - 100 * tab[c]["A_PPGoals"] / max(1, tab[c]["A_PPTries"])
    stats = [
        ("goal difference", lambda c: rate(c, "F_Score") - rate(c, "A_Score"), True, "{:+.2f} a game"),
        ("attack", lambda c: rate(c, "F_Score"), True, "{:.2f} goals a game"),
        ("defence", lambda c: rate(c, "A_Score"), False, "{:.2f} goals against a game"),
        ("shots", lambda c: rate(c, "F_Shots"), True, "{:.1f} shots a game"),
        ("shots allowed", lambda c: rate(c, "A_Shots"), False, "{:.1f} shots against a game"),
        ("shooting", lambda c: 100 * tab[c]["F_Score"] / max(1, tab[c]["F_Shots"]), True, "{:.1f}% shooting"),
        ("goaltending", lambda c: 100 - 100 * tab[c]["A_Score"] / max(1, tab[c]["A_Shots"]), True, "a {:.1f}% save percentage"),
        ("power play", pp, True, "a {:.1f}% power play"),
        ("penalty kill", pk, True, "a {:.1f}% penalty kill"),
        ("faceoffs", lambda c: 100 * tab[c]["F_FaceoffWins"] / max(1, tab[c]["F_FaceoffWins"] + tab[c]["A_FaceoffWins"]), True, "{:.1f}% of faceoffs won"),
        ("discipline", lambda c: rate(c, "F_PIM"), False, "{:.1f} penalty minutes a game"),
        ("possession", lambda c: rate(c, "F_AttackZoneTime"), True, "{:.0f} s a game in the attacking zone"),
        ("passing", lambda c: 100 * tab[c]["F_PassComps"] / max(1, tab[c]["F_PassTries"]), True, "{:.1f}% of passes completed"),
        ("hitting", lambda c: rate(c, "F_Checks"), True, "{:.1f} body checks a game"),
    ]
    ranked = [(rank(f, hb)[0], name, fmt.format(f(coach))) for name, f, hb, fmt in stats]
    good = sorted((x for x in ranked if x[0] <= max(2, n // 4)), key=lambda x: x[0])[:3]
    bad = sorted((x for x in ranked if x[0] > n - max(2, n // 4)), key=lambda x: -x[0])[:3]
    phr = lambda x: f"{x[1]} ({x[2]}, {'the best' if x[0] == 1 else 'the worst' if x[0] == n else nth(x[0])} in the league)"
    sw_txt = ""
    if good:
        sw_txt += "Their strengths: " + "; ".join(phr(x) for x in good) + ". "
    if bad:
        sw_txt += ("Where it went wrong: " if place > n // 2 else "Their weak spots: ") + "; ".join(phr(x) for x in bad) + "."
    if not good and not bad:
        sw_txt = "No part of their game stood out at either end of the league: they were in the middle on nearly everything."
    out.append(sw_txt.strip() + "\n")
    # 4. key games
    def result(g):
        return g["us"]["Score"] - g["them"]["Score"]
    # opponents left out of the table have no place, so they don't make a best win or a surprising loss
    wins = [g for g in mine if result(g) > 0 and g["opp"] in order]
    losses = [g for g in mine if result(g) < 0 and g["opp"] in order]
    bits = []
    if wins:
        g = min(wins, key=lambda g: (order.index(g["opp"]), -result(g)))
        bits.append(f"the best win was {int(g['us']['Score'])}-{int(g['them']['Score'])} over {g['opp']} "
                    f"({nth(order.index(g['opp']) + 1)} in the standings, {g['when'][:10]})")
    wins = [g for g in mine if result(g) > 0]
    if wins:
        g = max(wins, key=result)
        if result(g) >= 4:
            bits.append(f"the biggest {int(g['us']['Score'])}-{int(g['them']['Score'])} over {g['opp']} ({g['when'][:10]})")
    if losses:
        g = max(losses, key=lambda g: (order.index(g["opp"]), -result(g)))
        if order.index(g["opp"]) > order.index(coach):
            bits.append(f"the most surprising loss {int(g['us']['Score'])}-{int(g['them']['Score'])} to {g['opp']} "
                        f"({nth(order.index(g['opp']) + 1)}, {g['when'][:10]})")
    cb = [g for g in mine if g["us"]["GoalsP1"] + g["us"]["GoalsP2"] < g["them"]["GoalsP1"] + g["them"]["GoalsP2"] and result(g) > 0]
    bl = [g for g in mine if g["us"]["GoalsP1"] + g["us"]["GoalsP2"] > g["them"]["GoalsP1"] + g["them"]["GoalsP2"] and result(g) < 0]
    if cb:
        bits.append(f"{len(cb)} comeback win{'s' if len(cb) > 1 else ''} from behind after two periods")
    if bl:
        bits.append(f"{len(bl)} game{'s' if len(bl) > 1 else ''} lost after leading going into the third")
    if bits:
        s = "; ".join(bits)
        out.append(s[0].upper() + s[1:] + ".\n")
    # 5. luck and the players
    gf, ga = me["F_Score"], me["A_Score"]
    pyth = gf ** 2 / (gf ** 2 + ga ** 2) if gf + ga else 0.5
    luck = w_ - pyth * gp
    one = f"{me['one_goal_W']}-{me['one_goal_L']}"
    if luck >= 2:
        lk = f"They won about {luck:.0f} more games than their goals for and against would suggest, helped by a {one} record in one-goal games."
    elif luck <= -2:
        lk = f"They won about {-luck:.0f} fewer games than their goals for and against would suggest, with a {one} record in one-goal games."
    else:
        lk = f"Their record matches their goals for and against (one-goal games {one})."
    lp = league_avg(pdo)
    if pdo(coach) - lp >= 3:
        lk += f" Their shooting and save percentages together (PDO {pdo(coach):.1f}, league {lp:.1f}) ran hot, which rarely lasts."
    elif pdo(coach) - lp <= -3:
        lk += f" Their shooting and save percentages together (PDO {pdo(coach):.1f}, league {lp:.1f}) ran cold, which also rarely lasts."
    if pl:
        (name, pos), v = max(pl.items(), key=lambda kv: (kv[1]["P"], kv[1]["G"]))
        lk += f" {name} led the team with {v['G']} goals and {v['P']} points in {v['GP']} games."
    if gk:
        name, v = max(gk.items(), key=lambda kv: kv[1]["GP"])
        lk += f" {name} was in goal for {v['GP']}, saving {100 * v['SV'] / max(1, v['SA']):.1f}%."
    out.append(lk + "\n")
    return out


def main():
    league, coach = sys.argv[1], sys.argv[2]
    OUT.mkdir(parents=True, exist_ok=True)
    text = build(league, coach)
    lv = LEVELS.get(league, {})
    p = OUT / f"{level_title(league, lv[coach]) if coach in lv else league}_{coach}.md"
    p.write_text(text, encoding="utf-8")
    print(p)


if __name__ == "__main__":
    main()
