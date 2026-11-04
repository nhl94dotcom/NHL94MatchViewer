"""League ratings: docs/LEAGUE_RATINGS.md, how strong each league-season's coaches were (2026-11-04, the user). No coach is named. Run coach_history.py first.

A league's field is every coach with MIN_GAMES+ games in it, each counted once. Its rating is the win chance an average coach would have against that field, the mean over the field of 1 / (1 + exp(value)).
Value "at the start" is the coach's Rating as of the league's first day, from earlier games only (coach_history.py). Value "on one scale" is the coach's strength over all years with every game counting
equally: it uses hindsight, but the baseline doesn't move with the years. A Classic league uses Classic ratings, as Classic takes team strength out, with the all-leagues number beside it.
python analysis/league_ratings.py"""
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
import coach_history as H  # noqa: E402
import coach_rating as C  # noqa: E402
from lowload import gentle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MIN_GAMES, NEW_GAMES, ROUGH_SHARE, MIN_FAMILY, LIST_TOP = 5, 30, 0.25, 3, 15
SMALL_FIELD, SMALL_GAMES = 4, 20      # a league below either is listed and marked, but left out of rankings and averages
SYSTEMS = (("All_Games_GENS.csv", "GENESIS", 0, "Genesis"), ("All_Games_SNES.csv", "SNES", 1, "SNES"))
SEASON = re.compile(r"(?i)classic_(spring|summer|fall)(\d{4})_(?:GENS|SNES)(?:[-_](.+))?$")


def win(v):
    return 100 / (1 + np.exp(np.asarray(v, float)))


def rating(v):
    return 100 / (1 + np.exp(-np.asarray(v, float)))


def one_scale(fit):
    """{coach: log odds against the average coach with 100+ games} with every game counting equally."""
    beta = fit.D.fit(np.ones(len(fit.games), dtype=bool), np.ones(len(fit.games)), fit.y, fit.ridge)[0]
    n = Counter()
    for g in fit.games:
        n[g["hp"]] += 1
        n[g["ap"]] += 1
    zero = np.mean([beta[fit.D.people[p]] for p, c in n.items() if c >= 100])
    return {p: float((beta[i] - zero) * fit.scale) for p, i in fit.D.people.items()}


def family(lg):
    low = lg.lower()
    if low.startswith(C.CLASSIC):
        return "Classic"
    if low.startswith("chaos"):
        return "Chaos"
    if low.startswith("snes_draft"):
        return "SNES_Draft"
    name = re.sub(r"(?i)([-_ ]?(s|season[-_ ]?)\d+.*|[-_][a-e]{1,3}\d?$|[-_]?\d{4}.*|_\d+.*)$", "", lg)
    return name if name and not name.isdigit() else lg


def level_of(lg):
    m = SEASON.match(lg)
    return (m.group(3).upper() if m.group(3) else None) if m else None


def season_of(lg):
    m = SEASON.match(lg)
    return (int(m.group(2)), {"spring": 0, "summer": 1, "fall": 2}[m.group(1).lower()], f"{m.group(1).capitalize()} {m.group(2)}") if m else None


def build_system(name, label, at, sets):
    fit_all = H.Fit(name, "all", at, sets)
    fit_cl = H.Fit(name, "classic", at, sets)
    hist_all = json.loads((H.OUT / f"{label}_all.json").read_text(encoding="utf-8"))
    hist_cl = json.loads((H.OUT / f"{label}_classic.json").read_text(encoding="utf-8"))
    scale_all, scale_cl = one_scale(fit_all), one_scale(fit_cl)
    by_league = defaultdict(Counter)
    first, last = {}, {}
    for g in fit_all.games:
        by_league[g["league"]][g["hp"]] += 1
        by_league[g["league"]][g["ap"]] += 1
        first[g["league"]] = min(first.get(g["league"], g["day"]), g["day"])
        last[g["league"]] = max(last.get(g["league"], g["day"]), g["day"])
    rows = []
    for lg, coaches in by_league.items():
        field = [p for p, c in coaches.items() if c >= MIN_GAMES]
        if len(field) < 2:
            continue
        classic = lg.lower().startswith(C.CLASSIC)
        day = str(first[lg])
        now_all = hist_all.get(day, {})
        now_cl = hist_cl.get(day, {})
        main_hist, main_scale = (now_cl, scale_cl) if classic else (now_all, scale_all)
        have = [p for p in field if p in main_hist]
        vals = [main_hist[p][0] for p in have]
        new = sum(1 for p in have if main_hist[p][1] < NEW_GAMES) + len(field) - len(have)
        row = {"league": lg, "family": family(lg), "classic": classic, "start": first[lg], "end": last[lg], "field": len(field), "left_out": len(coaches) - len(field),
               "games": sum(coaches.values()) // 2, "small": False, "new": new, "rough": new / len(field) >= ROUGH_SHARE, "level": level_of(lg), "season": season_of(lg)}
        row["start_rating"] = float(np.mean(win(vals))) if vals else None
        sorted_vals = sorted(vals, reverse=True)
        row["top3"] = float(np.mean(rating(sorted_vals[:3]))) if vals else None
        row["bottom3"] = float(np.mean(rating(sorted_vals[-3:]))) if vals else None
        row["scale_rating"] = float(np.mean(win([main_scale[p] for p in field if p in main_scale])))
        if classic:
            other = [now_all[p][0] for p in field if p in now_all]
            row["start_all"] = float(np.mean(win(other))) if other else None
            row["scale_all"] = float(np.mean(win([scale_all[p] for p in field if p in scale_all])))
        row["small"] = row["field"] < SMALL_FIELD or row["games"] < SMALL_GAMES
        rows.append(row)
    rows.sort(key=lambda r: r["start"])
    return rows


def fmt(v, d=1):
    return "—" if v is None else f"{v:.{d}f}"


def dated(r):
    return date.fromordinal(r["start"]).isoformat()


def league_row(r, extra=False):
    cells = [("`" + r["league"] + "`") + (" †" if r["rough"] else "") + (" ‡" if r["small"] else ""), dated(r), str(r["field"]), str(r["games"]), fmt(r["start_rating"]), fmt(r["scale_rating"]), fmt(r["top3"]), fmt(r["bottom3"])]
    if extra:
        cells += [fmt(r.get("start_all")), fmt(r.get("scale_all"))]
    return "| " + " | ".join(cells) + " |"


def league_head(extra=False):
    cols = ["League", "First game", "Coaches", "Games", "Average coach wins, at the start", "Average coach wins, one scale", "Top 3", "Bottom 3"] + (["All-leagues, at the start", "All-leagues, one scale"] if extra else [])
    return "| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |"


def section(title, rows):
    out = [f"## {title}", ""]
    every = rows
    rows = [r for r in every if not r["small"]]
    classic = [r for r in rows if r["classic"]]
    named = [r for r in classic if r["level"]]
    # Classic levels
    out += [f"### {title} Classic: by level", "",
            "Each league's level comes from its name, as a season's divisions run from the most As down. A lower number is a tougher league.", "",
            "| Level | Leagues | Coaches a league | Average coach wins, at the start | Average coach wins, one scale | Top 3 | Bottom 3 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    groups = defaultdict(list)
    for r in named:
        groups[r["level"]].append(r)
    order = sorted(groups, key=lambda k: (-len(re.match(r"A*", k).group(0)), k))
    for k in order:
        g = groups[k]
        have = [r for r in g if r["start_rating"] is not None]
        out.append(f"| {k} | {len(g)} | {np.mean([r['field'] for r in g]):.1f} | {fmt(float(np.mean([r['start_rating'] for r in have])) if have else None)} | {np.mean([r['scale_rating'] for r in g]):.1f} | {fmt(float(np.mean([r['top3'] for r in have])) if have else None)} | {fmt(float(np.mean([r['bottom3'] for r in have])) if have else None)} |")
    out.append("")
    # top division by year
    seasons = defaultdict(list)
    for r in named:
        seasons[r["season"][:3]].append(r)
    top = {}
    for s, g in seasons.items():
        most = max(len(re.match(r"A*", r["level"]).group(0)) for r in g)
        if most:
            top[s] = [r for r in g if len(re.match(r"A*", r["level"]).group(0)) == most]
    by_year = defaultdict(list)
    for s, g in top.items():
        by_year[s[0]] += g
    out += [f"### {title} Classic: the top league by year", "", "| Year | Top leagues | Average coach wins, one scale | Average coach wins, at the start | Top 3 |", "| --- | --- | --- | --- | --- |"]
    for y in sorted(by_year):
        g = by_year[y]
        have = [r for r in g if r["start_rating"] is not None]
        out.append(f"| {y} | {len(g)} | {np.mean([r['scale_rating'] for r in g]):.1f} | {fmt(float(np.mean([r['start_rating'] for r in have])) if have else None)} | {fmt(float(np.mean([r['top3'] for r in have])) if have else None)} |")
    out.append("")
    tough = sorted([r for r in rows], key=lambda r: r["scale_rating"])
    out += [f"### {title}: the toughest leagues, on one scale", "", league_head()] + [league_row(r) for r in tough[:LIST_TOP]] + [""]
    tough_c = sorted(classic, key=lambda r: r["scale_rating"])
    out += [f"### {title} Classic: the toughest leagues, on one scale", "", league_head(True)] + [league_row(r, True) for r in tough_c[:LIST_TOP]] + [""]
    fams = defaultdict(list)
    for r in rows:
        fams[r["family"]].append(r)
    out += [f"### {title}: league families", "", f"Families with {MIN_FAMILY}+ leagues, toughest first. The name is what's left of a league's name without its season and level, so a few may be split or joined wrongly.", "",
            "| Family | Leagues | First | Last | Average coach wins, one scale |", "| --- | --- | --- | --- | --- |"]
    for fam, g in sorted(((f, g) for f, g in fams.items() if len(g) >= MIN_FAMILY), key=lambda kv: np.mean([r["scale_rating"] for r in kv[1]])):
        out.append(f"| `{fam}` | {len(g)} | {date.fromordinal(min(r['start'] for r in g)).year} | {date.fromordinal(max(r['start'] for r in g)).year} | {np.mean([r['scale_rating'] for r in g]):.1f} |")
    out.append("")
    out += [f"### {title}: every Classic league", "", league_head(True)] + [league_row(r, True) for r in reversed([r for r in every if r["classic"]])] + [""]
    others = [r for r in every if not r["classic"]]
    out += [f"### {title}: every other league", "", league_head()] + [league_row(r) for r in reversed(others)] + [""]
    return out


def main():
    gentle()
    sets = H.settings()
    data = {}
    out = ["# League ratings", "",
           "How strong the coaches in each league-season were, on both systems, from every league game since 2013. No coach is named. The method behind the ratings is in [COACH_RATING.md](COACH_RATING.md).", "",
           "**Jump to:** [Genesis](#genesis) · [SNES](#snes)", "",
           "## How to read this", "",
           "- **Average coach wins:** the win chance an average coach would have against this league's coaches, with neutral teams and no home edge. **Lower means a tougher league.** An average coach is the mean of coaches with 100+ games.",
           "- **At the start:** each coach's Rating as of the league's first day, from earlier games only, so the league's own results don't count. Compare leagues from about the same time with this. The average coach moves with the years, so it isn't a fair way to compare 2016 with 2026.",
           "- **One scale:** each coach's strength over all their years, with every game counting equally. Its baseline doesn't move, so use this to compare across years. It uses hindsight: a coach is judged partly by what they did later.",
           "- **Top 3 and Bottom 3:** the mean Rating at the start of the league's three strongest and three weakest coaches, so you can see whether a league is top-heavy. Both are win chances against an average coach.",
           "- **Classic leagues use Classic ratings,** which take team strength out. **All-leagues** columns show the same two numbers from all leagues' ratings.",
           f"- **Coaches:** those with {MIN_GAMES}+ games in the league, each counted once, including playoff games. Fill-ins and early drop-outs are left out.",
           f"- **†:** {int(ROUGH_SHARE * 100)}% or more of the league's coaches had under {NEW_GAMES} earlier games (in Classic games, for a Classic league), so its rating at the start is rough. The earliest leagues all show this.",
           f"- **‡:** a very small league, with under {SMALL_FIELD} coaches or under {SMALL_GAMES} games, such as a championship series between two divisions' winners. It's listed but left out of every ranking and average.",
           "- **—:** no earlier games to go on.",
           "- **Levels with only one or two leagues** rest on very few coaches, so don't read much into them.", "",
           "**What this can't tell you.** It rates who played, not how they played that season. A coach who improved in the league counts at their earlier level in the \"at the start\" number. Numbers are for one system at a time: a Genesis and a SNES league can't be compared.", ""]
    for name, label, at, title in SYSTEMS:
        rows = build_system(name, label, at, sets)
        data[label] = rows
        print(title, len(rows), "leagues; rough", sum(r["rough"] for r in rows), flush=True)
        out += section(title, rows)
    (ROOT / "docs" / "LEAGUE_RATINGS.md").write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    (ROOT / "reports" / "league_ratings.json").write_text(json.dumps(data), encoding="utf-8")


if __name__ == "__main__":
    main()
