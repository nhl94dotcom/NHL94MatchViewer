"""The player guides: docs/PLAYER_GUIDE_GENESIS.md and docs/PLAYER_GUIDE_SNES.md, every retail skater and goalie in the Classic leagues against the ROM's ratings (2026-11-04, the user, to hand out).
Aggregates only; no coach is named. Also writes reports/classic_players.json for classic_draft_guide.py.

Skaters. Genesis lines give ice time, so a game counts when a skater played 10+ minutes. Most SNES lines list only skaters who recorded something and have no ice time, so a SNES regular
(listed in at least half their team's games) is rated per team game; anyone else is a part-timer, shown with their games listed and no comparison. Checks are Genesis only.
Against the ratings: inside each team and position (forwards, defencemen), points a game are fitted on the ratings, all teams sharing one value per rating step, which gives what a skater's
ratings suggest beside their teammates'; the team, its opponents and who plays it cancel. Random halves of the leagues, compared, show how repeatable those differences are.
Goalies. Save % against what's usual for the goalie's Agility (a straight line through goalies with 400+ shots against).
python analysis/classic_player_guide.py"""
import ast
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scoring_map"))
sys.path.insert(0, str(HERE.parent / "tools"))
from league_player_study import DATA, NAMES, USE, rom  # noqa: E402
from lowload import breathe, gentle  # noqa: E402
from systems import genesis, snes  # noqa: E402

ROOT = HERE.parent
CLASSIC = ("classic_spring", "classic_summer", "classic_fall")
SYSTEMS = (("All_Games_GENS.csv", "Genesis", genesis, "9438f5dd_a738ea1c.bin", "PLAYER_GUIDE_GENESIS.md", True),
           ("All_Games_SNES.csv", "SNES", snes, "cd85e387.smc", "PLAYER_GUIDE_SNES.md", False))
MIN_GAMES = 50          # skater games for a row with a comparison
MIN_FIT = 150           # skater games to help fit the rating steps
REGULAR = 0.5           # SNES: listed in this share of the team's games
MIN_SHOTS, MIN_LINE = 100, 400      # goalie shots against: for a row; for the line through Agility
SPLITS = 20
FIELDS = ("n", "g", "a", "p", "sog", "chk", "pim", "toi", "p2")


def blank():
    return dict.fromkeys(FIELDS, 0.0)


def read(csv_name, rosters, has_toi):
    """Per (team, name, league) tallies of skaters and goalies, and each team's games per league."""
    skaters = defaultdict(lambda: defaultdict(blank))
    goalies = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    position = {}
    team_games = defaultdict(lambda: defaultdict(int))
    games = lost = 0
    csv.field_size_limit(10 ** 9)
    with open(DATA / csv_name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            league = r["League"]
            if r.get("sim") == "1" or not league.lower().startswith(CLASSIC):
                continue
            games += 1
            for side in ("Home", "Away"):
                team = r[side + "TeamAbbrev"].strip()
                try:
                    lines = ast.literal_eval(r[side + "Players"]) if r[side + "Players"] else []
                    keepers = ast.literal_eval(r[side + "Goalies"]) if r[side + "Goalies"] else []
                except (ValueError, SyntaxError):
                    continue
                if not lines:
                    continue
                team_games[team][league] += 1
                for p in lines:
                    key = (team, str(p[1]).lower())
                    if key not in rosters:
                        lost += 1
                        continue
                    if has_toi and p[9] < 600:
                        continue
                    s = skaters[key][league]
                    s["n"] += 1
                    s["g"] += p[3]
                    s["a"] += p[4]
                    s["p"] += p[5]
                    s["sog"] += p[6]
                    s["p2"] += p[5] ** 2
                    if has_toi:
                        s["chk"] += p[7]
                        s["pim"] += p[8]
                        s["toi"] += p[9]
                    else:
                        s["pim"] += p[8] if len(p) >= 9 else p[7]
                    position[key] = "D" if p[2] == "D" else "F"
                for g in keepers:
                    key = (team, str(g[1]).lower())
                    if key in rosters and g[4] > 0:
                        t = goalies[key][league]
                        t[0] += 1
                        t[1] += g[2]
                        t[2] += g[4]
    return skaters, goalies, position, team_games, games, lost


def totals(skaters, team_games, has_toi, leagues=None):
    """Each skater's totals over the leagues given. n is the games their rates are per."""
    out = {}
    for key, per in skaters.items():
        s = blank()
        for lg, v in per.items():
            if leagues is None or lg in leagues:
                for f in FIELDS:
                    s[f] += v[f]
        if not s["n"]:
            continue
        tg = sum(c for lg, c in team_games[key[0]].items() if leagues is None or lg in leagues)
        s["team"] = tg
        s["share"] = s["n"] / tg if tg else 0
        s["regular"] = has_toi or s["share"] >= REGULAR
        if not has_toi and s["regular"]:
            s["n"] = tg                 # zero games aren't listed: a regular's rate is per team game
        out[key] = s
    return out


def compare(stats, position, rosters):
    """Rating steps, and each skater's points a game against what the ratings suggest beside teammates: {key: (expected, diff, se)}."""
    steps, out = {}, {}
    for pos in ("F", "D"):
        group = defaultdict(list)
        for k, s in stats.items():
            if position[k] == pos and s["regular"] and s["n"] >= MIN_GAMES:
                group[k[0]].append(k)
        X, y, w = [], [], []
        for members in group.values():
            fit = [k for k in members if stats[k]["n"] >= MIN_FIT]
            if len(fit) < 2:
                continue
            xs = np.array([[rosters[k]["a"][i] for i in USE] for k in fit], float)
            ys = np.array([stats[k]["p"] / stats[k]["n"] for k in fit])
            ws = np.array([stats[k]["n"] for k in fit], float)
            X.append(xs - np.average(xs, axis=0, weights=ws))
            y.append(ys - np.average(ys, weights=ws))
            w.append(ws)
        X, y, w = np.vstack(X), np.concatenate(y), np.concatenate(w)
        sw = np.sqrt(w / w.mean())
        beta = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
        res = (y - X @ beta) * sw
        se = np.sqrt(np.diag(np.linalg.pinv((X * sw[:, None]).T @ (X * sw[:, None])) * (res @ res / max(1, len(y) - len(USE)))))
        steps[pos] = {NAMES[USE[i]]: (float(beta[i]), float(se[i])) for i in range(len(USE))}
        for members in group.values():
            if len(members) < 2:
                continue
            xs = np.array([[rosters[k]["a"][i] for i in USE] for k in members], float)
            ys = np.array([stats[k]["p"] / stats[k]["n"] for k in members])
            ws = np.array([stats[k]["n"] for k in members], float)
            mean_x, mean_y = np.average(xs, axis=0, weights=ws), np.average(ys, weights=ws)
            for i, k in enumerate(members):
                e = float(mean_y + (xs[i] - mean_x) @ beta)
                s = stats[k]
                var = max(s["p2"] / s["n"] - (s["p"] / s["n"]) ** 2, 0.01)
                out[k] = (e, float(ys[i] - e), float((var / s["n"]) ** 0.5))
    return steps, out


def repeat(skaters, team_games, position, rosters, has_toi, rng):
    """How well random halves of the leagues agree, over skaters with MIN_FIT+ games in each half: on points a game, and on points a game against the ratings."""
    leagues = np.array(sorted({lg for per in skaters.values() for lg in per}))
    raw, against = [], []
    for _ in range(SPLITS):
        half = set(rng.permutation(leagues)[: len(leagues) // 2])
        a = totals(skaters, team_games, has_toi, half)
        b = totals(skaters, team_games, has_toi, set(leagues) - half)
        _, da = compare(a, position, rosters)
        _, db = compare(b, position, rosters)
        both = [k for k in da if k in db and a[k]["n"] >= MIN_FIT and b[k]["n"] >= MIN_FIT]
        if len(both) > 10:
            raw.append(np.corrcoef([a[k]["p"] / a[k]["n"] for k in both], [b[k]["p"] / b[k]["n"] for k in both])[0, 1])
            against.append(np.corrcoef([da[k][1] for k in both], [db[k][1] for k in both])[0, 1])
        breathe()
    return float(np.mean(raw)), float(np.mean(against)), len(both)


def goalie_table(goalies, rosters):
    rows = []
    for key, per in goalies.items():
        g = sum(v[0] for v in per.values())
        ga = sum(v[1] for v in per.values())
        sa = sum(v[2] for v in per.values())
        rows.append({"key": key, "games": g, "ga": ga, "sa": sa, "sv": 1 - ga / sa, "agl": rosters[key]["a"][1], "ovr": rosters[key]["ovr"]})
    big = [r for r in rows if r["sa"] >= MIN_LINE]
    slope, level = np.polyfit([r["agl"] for r in big], [r["sv"] for r in big], 1, w=np.sqrt([r["sa"] for r in big]))
    for r in rows:
        r["expected"] = float(level + slope * r["agl"])
        r["diff"] = r["sv"] - r["expected"]
        r["se"] = float((r["sv"] * (1 - r["sv"]) / r["sa"]) ** 0.5)
    return rows, float(slope)


def signed(v, d=2):
    return f"{v:+.{d}f}".replace("-", "−")


def skater_row(k, s, rosters, position, diffs, with_team, has_toi):
    p = rosters[k]
    a = p["a"]
    n = s["n"]
    d = diffs.get(k)
    mark = "—"
    if d and n >= MIN_GAMES:
        mark = signed(d[1]) + (" **clear**" if abs(d[1]) > 2 * d[2] else "")
    cols = [p["name"]] + ([k[0]] if with_team else []) + [position[k], f"{n:.0f}", f"{s['g'] / n:.2f}", f"{s['a'] / n:.2f}", f"**{s['p'] / n:.2f}**", f"{s['sog'] / n:.2f}"]
    if has_toi:
        cols.append(f"{s['chk'] / n:.2f}")
    cols += [f"{s['pim'] / n:.2f}", str(p["ovr"]), str(a[0]), str(a[1]), str(a[2]), str(a[5]), str(a[9]), str(a[6]), f"{d[0]:.2f}" if d else "—", mark]
    return "| " + " | ".join(cols) + " |"


def skater_head(with_team, has_toi):
    cols = ["Skater"] + (["Team"] if with_team else []) + ["Pos", "Games", "G", "A", "P", "SOG"] + (["Chk"] if has_toi else []) + ["PIM", "Ovr", "Wgt", "Agl", "Spd", "ShP", "ShA", "ChkR", "Expected P", "P vs expected"]
    return "| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |"


def goalie_head(with_team):
    cols = ["Goalie"] + (["Team"] if with_team else []) + ["Games", "Shots against", "Goals against", "Save %", "Agl", "Ovr", "Usual for that Agl", "Vs usual"]
    return "| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |"


def goalie_row(r, rosters, with_team):
    k = r["key"]
    vs = signed(100 * r["diff"], 1) + (" **clear**" if abs(r["diff"]) > 2 * r["se"] else "")
    cols = [rosters[k]["name"]] + ([k[0]] if with_team else []) + [str(r["games"]), str(r["sa"]), str(r["ga"]), f"{100 * r['sv']:.1f}", str(r["agl"]), str(r["ovr"]), f"{100 * r['expected']:.1f}", vs]
    return "| " + " | ".join(cols) + " |"


def build(csv_name, label, mod, romfile, outfile, has_toi, rng):
    teams = mod.read_teams(rom(romfile))
    names = {t["abbr"]: t["name"] for t in teams}
    rosters = {(t["abbr"], p["name"].lower()): p for t in teams for p in t["players"]}
    skaters, goalies, position, team_games, games, lost = read(csv_name, rosters, has_toi)
    stats = totals(skaters, team_games, has_toi)
    steps, diffs = compare(stats, position, rosters)
    raw, against, pairs = repeat(skaters, team_games, position, rosters, has_toi, rng)
    keepers, slope = goalie_table(goalies, rosters)
    shown = [k for k, s in stats.items() if s["regular"] and s["n"] >= MIN_GAMES]
    compared = [k for k in shown if k in diffs]
    clear = [k for k in compared if abs(diffs[k][1]) > 2 * diffs[k][2]]
    print(f"{label}: {games} games; {lost} lines with a name not on that team's roster; {len(shown)} regulars, {len(compared)} compared, {len(clear)} clear; repeat raw {raw:+.2f}, against ratings {against:+.2f} over {pairs} skaters; goalie slope {100 * slope:+.2f}", flush=True)
    out = [f"# {label} Classic player guide", ""]
    leagues = {lg for per in skaters.values() for lg in per}
    out.append(f"Every retail skater and goalie in the {label} Classic leagues (names starting `Classic_Spring`, `Classic_Summer` or `Classic_Fall`): {games:,} games in {len(leagues)} leagues. No coach is named. Teams themselves are in [TEAM_GUIDE_{label.upper()}.md](TEAM_GUIDE_{label.upper()}.md).")
    out.append("")
    used = sorted(t for t in team_games if any(k[0] == t for k in shown) and t in names)
    out.append("**Jump to a team:** " + " · ".join(f"[{names[t]}](#{names[t].lower().replace(' ', '-').replace('.', '')})" for t in sorted(used, key=lambda t: names[t])))
    out.append("")
    out += ["## How to read this guide", ""]
    if has_toi:
        out += ["- **Games:** games in which the skater played 10 or more minutes. Every per-game number counts only these games.", ""]
    else:
        out += ["- **Games:** the team's games, for a skater listed in at least half of them. Many SNES game records leave out a skater with nothing to show, so dividing by the games listed would flatter everyone. This slightly understates anyone who was often taken out of the lineup. A skater listed in under half of the team's games is a part-timer and is left out of these tables, because how much they played isn't known.", ""]
    out += ["- **Pos:** F forward, D defenceman, as the game records list them.", "",
            "- **G, A, P, SOG:** goals, assists, points and shots on goal per game.", ""]
    if has_toi:
        out += ["- **Chk:** checks per game.", ""]
    out += ["- **PIM:** penalty minutes per game.", "",
            "- **Ovr:** the overall rating in the game's roster.", "",
            "- **Wgt, Agl, Spd, ShP, ShA, ChkR:** roster Weight, Agility, Speed, Shot Power, Shot Accuracy and Checking, each on the roster's own scale, before hot and cold.", "",
            "- **Expected P:** the points per game the skater's ratings suggest, given their teammates at the same position. All teams share one value for each rating step.", "",
            "- **P vs expected:** actual points per game minus Expected P. Comparing teammates takes out the team, its opponents and the coaches using it. **clear** means more than two standard errors from zero. — means it can't be compared: no regular teammate at that position.", "",
            "- **Shots against, Goals against, Save %:** for goalies, over all their Classic games.", "",
            "- **Usual for that Agl:** the save % that is usual for a goalie with that roster Agility, from a straight line through the goalies with 400+ shots against.", "",
            "- **Vs usual:** Save % minus that, in points. **clear** means more than two standard errors from zero, counting shots as independent.", ""]
    n_check = sum(1 for k in compared)
    out += ["## What these numbers can and can't say", "",
            f"- **What a skater did isn't only the skater.** People choose who to pass to and shoot with, so \"above expected\" often means people have found that skater useful. It isn't a hidden rating, and it doesn't say the same skater would do it for everyone.",
            f"- **How repeatable it is.** Random halves of the leagues, fitted apart, agree at {raw:.2f} on points per game and {against:.2f} on points per game against expected (skaters with {MIN_FIT}+ games in each half).",
            f"- **Chance.** {len(clear)} of {n_check} compared skaters are marked clear. About {max(1, round(0.05 * n_check))} would be by chance alone even if ratings explained everything.",
            "- **Line-mates matter.** A skater who shares a line with a star gets more assists. Comparing with teammates doesn't remove that.",
            "- **Goalies depend on who plays in front of them.** Save % isn't adjusted for shot quality, so a goalie behind a team that gives up good chances looks worse than they are.",
            "- **Raw rates reflect the team.** The lists of top scorers aren't adjusted for who used the team. Only the \"vs expected\" numbers take that out.", ""]
    out += ["## What the ratings are worth", "", "Points per game for one roster step of each rating, among teammates, with the other ratings held still. **Bold** is more than two standard errors from zero.", ""]
    head = list(steps["F"])
    out += ["| Position | " + " | ".join(head) + " |", "| --- | " + " | ".join("---" for _ in head) + " |"]
    for pos, name in (("F", "Forwards"), ("D", "Defencemen")):
        cells = [(f"**{signed(steps[pos][h][0], 3)}**" if abs(steps[pos][h][0]) > 2 * steps[pos][h][1] else signed(steps[pos][h][0], 3)) for h in head]
        out.append(f"| {name} | " + " | ".join(cells) + " |")
    out.append("")
    if has_toi:
        out.append(f"A goalie's save % moves {signed(100 * slope)} points per step of Agility.")
    else:
        out.append(f"A goalie's save % moves {signed(100 * slope)} points per step of Agility, which is little beside the Genesis.")
    out.append("")
    by_p = sorted(shown, key=lambda k: -stats[k]["p"] / stats[k]["n"])
    big = [k for k in shown if stats[k]["n"] >= MIN_FIT]
    sections = [("Most points per game", sorted(big, key=lambda k: -stats[k]["p"] / stats[k]["n"])[:15]),
                ("Most goals per game", sorted(big, key=lambda k: -stats[k]["g"] / stats[k]["n"])[:15]),
                ("Most points above expected", sorted([k for k in compared if stats[k]["n"] >= MIN_FIT], key=lambda k: -diffs[k][1])[:15]),
                ("Most points below expected", sorted([k for k in compared if stats[k]["n"] >= MIN_FIT], key=lambda k: diffs[k][1])[:15])]
    if has_toi:
        sections.append(("Most checks per game", sorted(big, key=lambda k: -stats[k]["chk"] / stats[k]["n"])[:15]))
    out.append(f"The lists below use skaters with {MIN_FIT}+ games.")
    out.append("")
    for title, keys in sections:
        out += [f"## {title}", "", skater_head(True, has_toi)]
        out += [skater_row(k, stats[k], rosters, position, diffs, True, has_toi) for k in keys]
        out.append("")
    big_g = sorted([r for r in keepers if r["sa"] >= MIN_LINE], key=lambda r: -r["diff"])
    out += [f"## Goalies against what's usual ({MIN_LINE}+ shots against)", "", goalie_head(True)]
    out += [goalie_row(r, rosters, True) for r in big_g]
    out.append("")
    out += ["## Team by team", "", f"Skaters with {MIN_GAMES}+ games, then goalies with {MIN_SHOTS}+ shots against.", ""]
    for t in sorted(used, key=lambda t: names[t]):
        tg = sum(team_games[t].values())
        out += [f"### {names[t]}", "", f"{t}: {tg:,} appearances.", "", skater_head(False, has_toi)]
        out += [skater_row(k, stats[k], rosters, position, diffs, False, has_toi) for k in sorted((k for k in shown if k[0] == t), key=lambda k: -stats[k]["p"] / stats[k]["n"])]
        out.append("")
        team_g = sorted((r for r in keepers if r["key"][0] == t and r["sa"] >= MIN_SHOTS), key=lambda r: -r["sa"])
        if team_g:
            out += [goalie_head(False)] + [goalie_row(r, rosters, False) for r in team_g] + [""]
        breathe()
    (ROOT / "docs" / outfile).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return {"names": names,
            "skaters": [{"team": k[0], "name": rosters[k]["name"], "pos": position[k], "n": stats[k]["n"], "p": stats[k]["p"] / stats[k]["n"], "g": stats[k]["g"] / stats[k]["n"], "ovr": rosters[k]["ovr"],
                         "diff": diffs[k][1] if k in diffs else None, "se": diffs[k][2] if k in diffs else None} for k in shown],
            "goalies": [{"team": r["key"][0], "name": rosters[r["key"]]["name"], "games": r["games"], "sa": r["sa"], "sv": r["sv"], "agl": r["agl"], "ovr": r["ovr"], "diff": r["diff"], "se": r["se"]} for r in keepers],
            "repeat": [raw, against]}


def main():
    gentle()
    rng = np.random.default_rng(94)
    res = {}
    for csv_name, label, mod, romfile, outfile, has_toi in SYSTEMS:
        res[label] = build(csv_name, label, mod, romfile, outfile, has_toi, rng)
    (ROOT / "reports" / "classic_players.json").write_text(json.dumps(res), encoding="utf-8")


if __name__ == "__main__":
    main()
