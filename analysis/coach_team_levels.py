"""Which Classic teams suit high-level players, which low-level players, and which both (2026-11-04, the user). Aggregates only; no coach is named.

Letters in league names aren't comparable across seasons (SNES Fall 2021 ran AAA, AA, A, B, with A well below AA), so level is measured from the players,
in two ways:
- coach: each coach's career strength in that system's Classic leagues. Coaches are cut into three levels, each with about a third of the team appearances.
- league: each league's mean coach strength. Leagues are cut the same way, so a coach's level can change as they move between leagues.
- name: each season's top league (the most As) against the same season's other leagues.

The rating's equation with one team term per team and level, the term going by the level of the side using the team:
    result value = home coach - away coach + home team at its level - away team at its level + home edge
over all Classic games with equal weights. A team and level with under MIN_SIDES appearances gets no term. Each level's terms are centred on the mean
team as that level used it, so a value says how much better a level does with this team than with its other teams, and the coach terms have taken out who
was using it. Values are in points of win chance, through the table's conversion factor.

Spreads come from resampling whole leagues, and halves of the leagues fitted apart show how repeatable the high-minus-low gaps are.
python analysis/coach_team_levels.py     prints the tables and writes reports/classic_team_levels.md and .json (git-ignored; classic_team_guide.py reads the .json)"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
import coach_rating as C  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

LEVELS = ("High", "Mid", "Low")
MIN_SIDES = 30
DRAWS, SPLITS = 200, 40
TABLES = (("All_Games_GENS.csv", "Genesis", 0, 2.0), ("All_Games_SNES.csv", "SNES", 1, 2.0))


def factors():
    text = (C.DATA / "coach_rating_groups.md").read_text(encoding="utf-8")
    return [float(x) for x in re.findall(r"Conversion factor ([\d.]+)", text)]


def top_leagues(leagues):
    """{league: level} by name: a season's top league has the most As (A1, A-E and AB count as A; AAA beats AA beats A) gets 0, its others 2, and a league
    with no level in its name 1, which is fitted but not compared."""
    seasons, out = defaultdict(dict), {}
    for lg in leagues:
        m = re.match(r"(?i)(classic_(?:spring|summer|fall)\d{4})_(?:GENS|SNES)(?:[-_](.+))?$", lg)
        if not m or not m.group(2):
            out[lg] = 1
            continue
        seasons[m.group(1).lower()][lg] = len(re.match(r"(?i)a*", m.group(2)).group(0))
    for ranks in seasons.values():
        most = max(ranks.values())
        for lg, r in ranks.items():
            out[lg] = 0 if r == most and most > 0 else 2
    return out


def thirds(items):
    """{key: level}, from (key, strength, appearances), each level with about a third of the appearances."""
    total = sum(s for _, _, s in items)
    out, seen = {}, 0
    for key, _, sides in sorted(items, key=lambda r: -r[1]):
        out[key] = 0 if seen < total / 3 else 1 if seen < 2 * total / 3 else 2
        seen += sides
    return out


class Model:
    def __init__(self, games, D, side_level):
        """side_level(game, is_home) gives the level of the side."""
        self.n = len(games)
        self.games = games
        count = defaultdict(int)
        lv = [(side_level(g, True), side_level(g, False)) for g in games]
        for g, (a, b) in zip(games, lv):
            count[(g["ht"], a)] += 1
            count[(g["at"], b)] += 1
        self.sides = dict(count)
        teams = sorted(t for t in D.teams)
        keys = [(t, k) for t in teams for k in range(3) if count[(t, k)] >= MIN_SIDES]
        base = len(D.people)
        self.index = {k: base + i for i, k in enumerate(keys)}
        self.teams = teams
        self.home = base + len(keys)
        self.size = self.home + 1
        self.cols = np.full((self.n, 5), self.home, dtype=int)
        self.vals = np.zeros((self.n, 5))
        for i, (g, (a, b)) in enumerate(zip(games, lv)):
            self.cols[i, 0], self.vals[i, 0] = D.people[g["hp"]], 1
            self.cols[i, 1], self.vals[i, 1] = D.people[g["ap"]], -1
            self.cols[i, 4], self.vals[i, 4] = self.home, 1
            if (g["ht"], a) in self.index:
                self.cols[i, 2], self.vals[i, 2] = self.index[(g["ht"], a)], 1
            if (g["at"], b) in self.index:
                self.cols[i, 3], self.vals[i, 3] = self.index[(g["at"], b)], -1

    def fit(self, w, y, ridge):
        A = np.zeros((self.size, self.size))
        b = np.zeros(self.size)
        for i in range(5):
            np.add.at(b, self.cols[:, i], w * self.vals[:, i] * y)
            for j in range(5):
                np.add.at(A, (self.cols[:, i], self.cols[:, j]), w * self.vals[:, i] * self.vals[:, j])
        pen = np.full(self.size, float(ridge))
        for i in self.index.values():
            pen[i] = C.TEAM_PULL
        pen[self.home] = 1e-6
        A[np.diag_indices(self.size)] += pen
        return np.linalg.solve(A, b)

    def values(self, beta, scale):
        """{(team, level): points}, centred on the level's mean team, weighted by appearances."""
        out = {}
        for k in range(3):
            keys = [key for key in self.index if key[1] == k]
            sides = np.array([self.sides[key] for key in keys], float)
            v = np.array([beta[self.index[key]] for key in keys])
            v = v - (v * sides).sum() / sides.sum()
            for key, x in zip(keys, v):
                out[key] = 100 / (1 + np.exp(-x * scale)) - 50
        return out


def record(games, side_level, won_home):
    rec = defaultdict(lambda: [0, 0])
    for g, win in zip(games, won_home):
        if g["hs"] == g["as"]:
            continue
        rec[(g["ht"], side_level(g, True))][0 if win else 1] += 1
        rec[(g["at"], side_level(g, False))][1 if win else 0] += 1
    return rec


def study(games, D, y, ridge, scale, side_level, title, lines):
    M = Model(games, D, side_level)
    won = np.array([g["hs"] > g["as"] for g in games])
    rec = record(games, side_level, won)
    point = M.values(M.fit(np.ones(M.n), y, ridge), scale)
    leagues = sorted({g["league"] for g in games})
    where = defaultdict(list)
    for i, g in enumerate(games):
        where[g["league"]].append(i)
    rng = np.random.default_rng(94)
    runs = []
    for _ in range(DRAWS):
        w = np.zeros(M.n)
        for lg in rng.choice(leagues, len(leagues)):
            w[where[lg]] += 1
        runs.append(M.values(M.fit(w, y, ridge), scale))
        breathe()
    both = [t for t in M.teams if (t, 0) in point and (t, 2) in point]
    gap = lambda v, t: v[(t, 0)] - v[(t, 2)]
    rs, by_level = [], {0: [], 2: []}
    names = [g["league"] for g in games]
    for _ in range(SPLITS):
        order = rng.permutation(leagues)
        a = np.isin(names, order[: len(order) // 2])
        va = M.values(M.fit(a.astype(float), y, ridge), scale)
        vb = M.values(M.fit((~a).astype(float), y, ridge), scale)
        common = [t for t in both if all((t, k) in va and (t, k) in vb for k in (0, 2))]
        rs.append(np.corrcoef([gap(va, t) for t in common], [gap(vb, t) for t in common])[0, 1])
        for k in by_level:
            by_level[k].append(np.corrcoef([va[(t, k)] for t in common], [vb[(t, k)] for t in common])[0, 1])
        breathe()
    across = np.corrcoef([point[(t, 0)] for t in both], [point[(t, 2)] for t in both])[0, 1]
    lines.append(f"\n### {title}\n")
    lines.append(f"Halves of the leagues fitted apart agree: high-minus-low gaps {float(np.mean(rs)):+.2f}; team values at the high level {float(np.mean(by_level[0])):+.2f}, at the low level {float(np.mean(by_level[2])):+.2f}. "
                 f"High and low team values agree with each other at {across:+.2f}, over {len(both)} teams.\n")
    lines.append("| Team | High | Mid | Low | High minus Low | Sides high / mid / low | Win % high / mid / low |\n|---|---|---|---|---|---|---|")
    se = lambda f: float(np.std([f(r) for r in runs]))
    rows = []
    for t in M.teams:
        cells, sides, pct = [], [], []
        for k in range(3):
            key = (t, k)
            cells.append(f"{point[key]:+.1f} ± {se(lambda r: r[key]):.1f}" if key in point else "")
            sides.append(str(M.sides.get(key, 0)))
            w_, l_ = rec[key]
            pct.append(f"{100 * w_ / (w_ + l_):.0f}" if w_ + l_ else "")
        d = gap(point, t) if t in both else None
        ds = f"{d:+.1f} ± {se(lambda r: gap(r, t)):.1f}" if d is not None else ""
        rows.append((-(d if d is not None else -99), f"| {t} | {cells[0]} | {cells[1]} | {cells[2]} | {ds} | {' / '.join(sides)} | {' / '.join(pct)} |"))
    lines += [r for _, r in sorted(rows)]
    lines.append("")
    detail = {}
    for t in M.teams:
        levels = {str(k): [float(point[(t, k)]), se(lambda r: r[(t, k)]), M.sides[(t, k)]] for k in range(3) if (t, k) in point}
        detail[t] = {"levels": levels, "gap": [float(gap(point, t)), se(lambda r: gap(r, t))] if t in both else None}
    return {t: gap(point, t) for t in both}, {k: v for k, v in point.items()}, detail


def main():
    gentle()
    conv = factors()
    C.PREFIX = "classic"
    lines = ["# Classic teams by level of player\n", "`analysis/coach_team_levels.py`. Aggregates only.\n"]
    saved = {}
    for name, label, at, ridge in TABLES:
        games, _ = C.prepare(name)
        D = C.Design(games)
        y = C.values(games)["coast"]
        n = len(games)
        career, _ = D.fit(np.ones(n, dtype=bool), np.ones(n), y, ridge)
        sides = defaultdict(int)
        for g in games:
            sides[g["hp"]] += 1
            sides[g["ap"]] += 1
        coach_level = thirds([(p, career[i], sides[p]) for p, i in D.people.items()])
        players, league_n = defaultdict(set), defaultdict(int)
        for g in games:
            players[g["league"]] |= {g["hp"], g["ap"]}
            league_n[g["league"]] += 1
        strength = {lg: float(np.mean([career[D.people[p]] for p in ps])) for lg, ps in players.items()}
        league_level = thirds([(lg, strength[lg], league_n[lg]) for lg in players])
        scale = conv[at]
        lines.append(f"\n## {label}\n\n{n} games, {len(D.people)} coaches in {len(players)} leagues; conversion factor {scale}.")
        for k, name_ in enumerate(LEVELS):
            who = [p for p, v in coach_level.items() if v == k]
            lgs = [lg for lg, v in league_level.items() if v == k]
            lines.append(f"{name_}: {len(who)} coaches; {len(lgs)} leagues.")
        a, pa, da = study(games, D, y, ridge, scale, lambda g, home: coach_level[g["hp"] if home else g["ap"]], f"{label}, by the coach's level", lines)
        b, pb, db = study(games, D, y, ridge, scale, lambda g, home: league_level[g["league"]], f"{label}, by the league's level", lines)
        named = top_leagues(players)
        lines.append(f"\nBy name: {sum(v == 0 for v in named.values())} top leagues, {sum(v == 2 for v in named.values())} others, {sum(v == 1 for v in named.values())} with no level (their games are in Mid). Top: {', '.join(sorted(lg for lg, v in named.items() if v == 0))}.")
        _, _, dn = study(games, D, y, ridge, scale, lambda g, home: named[g["league"]], f"{label}, the season's top league (High) against its other leagues (Low)", lines)
        saved[label] = {t: {"coach": da[t], "strength": db[t], "name": dn[t]} for t in da}
        common = sorted(set(a) & set(b))
        same = [k for k in pa if k in pb]
        lines.append(f"The two ways agree: high-minus-low gaps {np.corrcoef([a[t] for t in common], [b[t] for t in common])[0, 1]:+.2f}; all values {np.corrcoef([pa[k] for k in same], [pb[k] for k in same])[0, 1]:+.2f}.\n")
        for k, name_ in enumerate(LEVELS):
            ts = [t for t in D.teams if (t, k) in pa and (t, k) in pb]
            lines.append(f"{name_}: the two ways agree at {np.corrcoef([pa[(t, k)] for t in ts], [pb[(t, k)] for t in ts])[0, 1]:+.2f}.")
        print(f"{label} done", flush=True)
    text = "\n".join(lines) + "\n"
    out = Path(__file__).resolve().parents[1] / "reports" / "classic_team_levels.md"
    out.write_text(text, encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(saved), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
