"""Are the league Elo's ratings fair between levels? Coaches mostly play inside their own level, so a rating earned at -C might not mean what one earned at -A does. (2026-11-04, the user.) Aggregates only.

The Elo is the league's method (league_team_elo.py), with the team table. Classic leagues only, as their names give a level. Three tests:
1. By level: how well Elo predicts games at each level, and how much a rating gap is worth there.
2. Moves: a coach's win % in a league minus what their Elo predicted at the league's start, for coaches who moved up, moved down or stayed since their last Classic league (20+ games in each). Moves are not
   random: a coach moves up after doing well, and high ratings run a little hot, so it's also fitted with the rating gap to the field and the coach's previous over- or under-performance held still.
3. Elo against the coach Rating, which solves every game at once: among active coaches, is Elo above or below what the Rating suggests for those who mostly play at lower levels?
python analysis/league_elo_levels.py     prints the results and writes reports/league_elo_levels.json (git-ignored)"""
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
import coach_rating as C  # noqa: E402
import league_ratings as LR  # noqa: E402
import league_team_elo as E  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

MIN_LEAGUE, MIN_SEEN, RECENT_YEARS = 20, 30, 3
SYSTEMS = (("All_Games_GENS.csv", "Genesis", "GENESIS"), ("All_Games_SNES.csv", "SNES", "SNES"))


def rank_of(level):
    """A = 1, B = 2 ...; AB = 1.5, CD = 3.5; extra As, and -E, -W or a number after a letter, count as that letter."""
    if not level:
        return None
    text = level.upper()
    if re.fullmatch(r"A+", text):
        return 1.0
    if re.fullmatch(r"[A-H]{2}", text) and ord(text[1]) == ord(text[0]) + 1:
        return (ord(text[0]) - 64 + ord(text[1]) - 64) / 2
    m = re.match(r"([A-H])", text)
    return float(ord(m.group(1)) - 64) if m else None


def run(games, table):
    """Every game, with each coach's Elo now and at the start of that league, in order."""
    R = defaultdict(lambda: E.START)
    seen = defaultdict(int)
    start = {}
    out = []
    for g in games:
        for who in (g["hp"], g["ap"]):
            start.setdefault((g["league"], who), R[who])
        tab = table.get(g["ht"], 0) - table.get(g["at"], 0) if g["wide"] else 0
        live = R[g["hp"]] - R[g["ap"]] + E.HOME + tab
        fixed = start[(g["league"], g["hp"])] - start[(g["league"], g["ap"])] + E.HOME + tab
        p = 1 / (1 + 10 ** (-live / 400))
        s = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
        if g["classic"] and g["ht"] != g["at"]:
            out.append((g, live, fixed, s, seen[g["hp"]], seen[g["ap"]]))
        d = E.K * (1 + g["coast"]) * (s - p)
        R[g["hp"]] += d
        R[g["ap"]] -= d
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    return out, R, seen


def loss(x, y):
    p = np.clip(1 / (1 + np.exp(-x)), 1e-6, 1 - 1e-6)
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


def by_level(rows):
    print("  1. By level, decided games between coaches with 30+ earlier games, from 2020 (log loss; a rating gap's worth, 1.00 is the right size):")
    res = {}
    groups = defaultdict(list)
    for g, live, fixed, s, a, b in rows:
        rk = rank_of(LR.level_of(g["league"]))
        if rk is None or s == 0.5 or a < MIN_SEEN or b < MIN_SEEN or g["when"][0] < 2020:
            continue
        groups["A" if rk <= 1.5 else "B" if rk <= 2.5 else "C" if rk <= 3.5 else "D and below"].append((live, fixed, s))
    for k in ("A", "B", "C", "D and below"):
        if not groups[k]:
            continue
        a = np.array(groups[k])
        x, f, y = a[:, 0] * math.log(10) / 400, a[:, 1] * math.log(10) / 400, a[:, 2]
        wl, wf = C.scale_for(x, y), C.scale_for(f, y)
        res[k] = {"games": len(y), "loss": loss(x, y), "worth_now": float(wl), "worth_start": float(wf), "gap": float(np.abs(a[:, 0]).mean())}
        print(f"     {k}: {len(y)} games; log loss {res[k]['loss']:.4f}; typical gap {res[k]['gap']:.0f} points; worth {wl:.2f} using ratings now, {wf:.2f} using ratings at the league's start", flush=True)
    return res


def seasons(rows):
    """{coach: [(start day, league, rank, decided games, wins, expected wins, mean gap to the field)]} in order."""
    tally = defaultdict(lambda: [0, 0.0, 0.0, 0.0, 0])
    first = {}
    for g, live, fixed, s, a, b in rows:
        first[g["league"]] = min(first.get(g["league"], g["day"]), g["day"])
        if s == 0.5:
            continue
        e = 1 / (1 + 10 ** (-fixed / 400))
        for who, score, exp, gap in ((g["hp"], s, e, fixed), (g["ap"], 1 - s, 1 - e, -fixed)):
            t = tally[(who, g["league"])]
            t[0] += 1
            t[1] += score
            t[2] += exp
            t[3] += gap
    out = defaultdict(list)
    for (who, lg), t in tally.items():
        rk = rank_of(LR.level_of(lg))
        if rk is not None and t[0] >= MIN_LEAGUE:
            out[who].append((first[lg], lg, rk, t[0], t[1], t[2], t[3] / t[0]))
    for v in out.values():
        v.sort()
    return out


def moves(rows):
    print("  2. Moves between levels (win % minus what Elo at the league's start predicted):")
    data = seasons(rows)
    points = []
    for who, v in data.items():
        for a, b in zip(v, v[1:]):
            if b[0] - a[0] > 1100:              # away for three years or more: not a move
                continue
            points.append((b[2] - a[2], 100 * (b[4] - b[5]) / b[3], 100 * (a[4] - a[5]) / a[3], b[6], b[3]))
    p = np.array(points)
    res = {}
    for name, m in (("stayed", p[:, 0] == 0), ("moved up", p[:, 0] < 0), ("moved down", p[:, 0] > 0), ("moved up 1 level", p[:, 0] == -1), ("moved down 1 level", p[:, 0] == 1)):
        if m.sum() < 5:
            continue
        w = p[m, 4]
        mean = float(np.average(p[m, 1], weights=w))
        se = float(p[m, 1].std() / m.sum() ** .5)
        res[name] = {"n": int(m.sum()), "raw": mean, "se": se, "before": float(np.average(p[m, 2], weights=w)), "gap": float(np.average(p[m, 3], weights=w))}
        print(f"     {name}: {m.sum()} coach-seasons; {mean:+.1f} +- {se:.1f} points; the league before they were {res[name]['before']:+.1f}; rating gap to the field {res[name]['gap']:+.0f}", flush=True)
    X = np.column_stack([np.ones(len(p)), p[:, 0] < 0, p[:, 0] > 0, p[:, 3] / 100, p[:, 2]])
    w = p[:, 4] / p[:, 4].mean()
    sw = np.sqrt(w)
    beta = np.linalg.lstsq(X * sw[:, None], p[:, 1] * sw, rcond=None)[0]
    resid = (p[:, 1] - X @ beta) * sw
    bread = np.linalg.inv((X * sw[:, None]).T @ (X * sw[:, None]))
    meat = (X * sw[:, None] * resid[:, None]).T @ (X * sw[:, None] * resid[:, None])
    se = np.sqrt(np.diag(bread @ meat @ bread))
    names = ("baseline", "moved up", "moved down", "each 100 points of rating gap to the field", "each point of doing better than Elo in the league before")
    res["fit"] = {n: (float(b_), float(s_)) for n, b_, s_ in zip(names, beta, se)}
    print("     With those held still: " + "; ".join(f"{n} {b_:+.2f} +- {s_:.2f}" for n, b_, s_ in zip(names, beta, se)), flush=True)
    return res


def against_rating(rows, R, seen, label):
    print("  3. Elo against the coach Rating, active coaches with 100+ games, by the level they've mostly played at over the last 3 years:")
    with open(C.DATA / f"coach_ratings_{label}.csv", encoding="utf-8") as fh:
        pub = {r["coach"]: r for r in csv.DictReader(fh)}
    now = max(g["day"] for g, *_ in rows)
    level = defaultdict(Counter)
    for g, *_ in rows:
        rk = rank_of(LR.level_of(g["league"]))
        if rk is not None and g["day"] >= now - 365.25 * RECENT_YEARS:
            for who in (g["hp"], g["ap"]):
                level[who.strip().lower()][1 if rk <= 1.5 else 2 if rk <= 2.5 else 3 if rk <= 3.5 else 4] += 1
    pts = []
    for p, r in R.items():
        key = p.strip().lower()
        if seen[p] >= 100 and key in pub and level[key] and sum(level[key].values()) >= MIN_LEAGUE:
            q = float(pub[key]["win_chance_vs_average"]) / 100
            pts.append((math.log(q / (1 - q)) * 400 / math.log(10), r, level[key].most_common(1)[0][0]))
    a = np.array(pts)
    slope, base = np.polyfit(a[:, 0], a[:, 1], 1)
    resid = a[:, 1] - (base + slope * a[:, 0])
    res = {"coaches": len(a), "slope": float(slope), "levels": {}}
    print(f"     {len(a)} coaches; Elo = {base:.0f} + {slope:.2f} x Rating on the Elo scale; typical distance from that {np.abs(resid).mean():.0f} points")
    for k, name in ((1, "A"), (2, "B"), (3, "C"), (4, "D and below")):
        m = a[:, 2] == k
        if m.any():
            res["levels"][name] = {"n": int(m.sum()), "mean": float(resid[m].mean()), "se": float(resid[m].std() / m.sum() ** .5), "elo": float(a[m, 1].mean())}
            print(f"     mostly {name}: {m.sum()} coaches; mean Elo {a[m, 1].mean():.0f}; Elo {resid[m].mean():+.0f} +- {resid[m].std() / m.sum() ** .5:.0f} points against what their Rating suggests", flush=True)
    return res


def main():
    gentle()
    tables = json.loads((Path(__file__).resolve().parents[1] / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    saved = {}
    for name, title, label in SYSTEMS:
        games = E.load_games(name)
        table = {t: v["adj"] for t, v in tables[title]["teams"].items()}
        rows, R, seen = run(games, table)
        print(f"\n{title}: {len(rows)} Classic games")
        saved[title] = {"levels": by_level(rows), "moves": moves(rows), "rating": against_rating(rows, R, seen, label)}
        breathe()
    (Path(__file__).resolve().parents[1] / "reports" / "league_elo_levels.json").write_text(json.dumps(saved), encoding="utf-8")


if __name__ == "__main__":
    main()
