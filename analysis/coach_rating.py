"""A strength rating for each league coach, per system (2026-11-03, the user). From the league result databases outside the repository
(%USERPROFILE%\\NHL94_League_Data). Prints aggregates only; the table with people's names is written to that folder, never to the repo.

Every game is one equation, solved over all games at once with ridge regression:
    result value = home coach - away coach + home team - away team + home edge
so beating a strong coach counts for more, and a coach and a team are told apart by the same people on other teams. Team terms only in
the Classic leagues (names starting Classic_Spring, Classic_Summer or Classic_Fall: retail rosters, the same abbreviation means the same team); elsewhere
rosters differ by league, and no term is fitted.
Result values tried (a win is positive for the winner, a tie 0, all scaled to the same spread):
- win: win or loss only;
- margin: goal difference capped at +-5;
- coast: win or loss plus the winner's coasting share capped at 100% (the user's rule, league_elo_coasting.py: the final unbroken stretch at a 90%+
  chance on lead and time alone, as a share of the third period; 10% at least for a 2-goal win; none for a 1-goal or overtime win);
- coast200: the same, capped at 200%;
- blend: the mean of margin and coast.
Recent games can count more (half-life in years), and small samples are pulled toward average (the ridge).

Chosen by predicting the future: every half year from 2020, fit on the games before it, predict the next half year's decided games between
people with 30+ earlier games, the win chance from the fitted equation through one scale factor taken from the half year before (so none of the test
games is used). Elo is scored on the same games, both live (updated after every game, an advantage it would have in use) and frozen at the same
half-year points. Scored on all games and on Classic games.

python analysis/coach_rating.py            the test and the private table, all leagues
python analysis/coach_rating.py groups     each of GROUPS fitted alone (Classic on each system, Chaos, SNES_Draft): coach_ratings_<system>_<group>.csv.
                                           Team terms only for Classic; in a draft league a coach's roster is part of the rating.
Both also refit monthly, every version on the table's settings, against Elo updated every game and frozen monthly. Method: docs/COACH_RATING.md."""
import ast
import csv
import math
import sys
import time
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
from league_elo_coasting import coasting, table  # noqa: E402
from league_flow_study import DATA, FILES, load  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

VERSIONS = ("win", "margin", "coast", "coast200", "blend")
HALF_LIVES = (None, 3.0, 1.5)
RIDGES = (2.0, 10.0, 40.0)
SCOPES = ("all", "classic")
MIN_TEAM_GAMES, MIN_SEEN, FIRST_YEAR = 100, 30, 2020
ELO_K = {"GENESIS": 16, "SNES": 20}
REF_GAMES = 100                                         # "average" in the table: the mean coach with this many games or more
CLASSIC = ("classic_spring", "classic_summer", "classic_fall")     # what makes a Classic league (lower case)
TEAM_PULL = 50.0                                        # the pull on team terms: the team Elo adjustments' setting. Tested in team_strength_checks.py: no worse on the Genesis, a little better on the SNES
OUTLIERS = {"SNES_3v3_Pond_Hockey_League", "SNES_3v3_Pond_Hockey_League-A", "SNES_3v3_Pond_Hockey_League-B", "Two_Teams_and_Zero_Friends_GENS_S1", "Two_Teams_and_Zero_Friends_SNES_S1"}   # not the same game: the league's Elo leaves them out too
GROUP_STARTS = {"classic": CLASSIC, "chaos": ("chaos",), "snes_draft": ("snes_draft",)}
PERIOD, MIN_LEAGUE_GAMES = 300, 20                      # seconds in the usual period; games a league needs before its period length is read from its goals
PREFIX = None                                           # only this group's leagues (a key of GROUP_STARTS)
GROUPS = (("All_Games_GENS.csv", "GENESIS", "classic"), ("All_Games_SNES.csv", "SNES", "classic"),
          ("All_Games_GENS.csv", "GENESIS", "chaos"), ("All_Games_SNES.csv", "SNES", "snes_draft"))


def day(text):
    parts = text.replace("-", " ").replace(":", " ").split()
    try:
        y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
        return date(y, m, d).toordinal()
    except (ValueError, IndexError):
        return None


def read_extra(name):
    """What load() doesn't keep: {(date, league, players, score): (home abbr, away abbr, goals as (period, second, home))}, and the period length of each
    league that doesn't play the usual one, from its longest regulation goal."""
    csv.field_size_limit(10 ** 9)
    out, league_games, longest = {}, defaultdict(int), defaultdict(int)
    with open(DATA / name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            key = (r["DateTime"], r["League"], r["HomePlayer"].strip().lower(), r["AwayPlayer"].strip().lower(), r["HomeScore"], r["AwayScore"])
            ht, at = r["HomeTeamAbbrev"].strip(), r["AwayTeamAbbrev"].strip()
            goals = []
            try:
                for col, home in (("HomeGoals", True), ("AwayGoals", False)):
                    goals += [(int(e[0]), int(e[1]), home) for e in (ast.literal_eval(r[col]) if r[col] else [])]
            except (ValueError, SyntaxError, IndexError, TypeError):
                goals = None
            out[key] = (ht, at, goals)
            if r.get("sim") != "1":
                league_games[r["League"]] += 1
                longest[r["League"]] = max([longest[r["League"]]] + [s for p, s, _ in goals or [] if p <= 3])
    lengths = {lg: 60 * math.ceil(longest[lg] / 60) for lg, c in league_games.items() if c >= MIN_LEAGUE_GAMES and longest[lg]}
    return out, {lg: v for lg, v in lengths.items() if v != PERIOD}


def prepare(name):
    games = [g for g in load(name) if g["hp"] and g["ap"] and g["hp"] != g["ap"] and day(g["date"]) and g["league"] not in OUTLIERS
             and (PREFIX is None or g["league"].lower().startswith(GROUP_STARTS[PREFIX]))]
    # Rows with the same score, shots and goal list stay in (about 0.3%): per the user, either a mistake or a real game neither player saved at
    # its end, entered from another save state with the same outcome (its score and stats not the real game's); no telling which, so they count.
    extra, lengths = read_extra(name)
    for g in games:
        g["key"] = (g["date"], g["league"], g["hp"], g["ap"], f"{g['hs']:g}", f"{g['as']:g}")
        goals = extra.get(g["key"], ("", "", None))[2]
        if g["league"] in lengths and goals is not None:    # another period length: time as a share of the period, so 3:00 of 6:00 counts as 2:30 of 5:00
            g["goals"] = sorted(((p - 1) * PERIOD + s * PERIOD / lengths[g["league"]] if p <= 3 else (p - 1) * PERIOD + s, h) for p, s, h in goals)
    good = [g for g in games if g["goals"] is not None and g["hs"] - g["as"] == sum(1 if h else -1 for _, h in g["goals"])]
    tab = table(good)
    no_goals = 0
    for g in games:
        g["day"] = day(g["date"])
        g["classic"] = g["league"].lower().startswith(CLASSIC)
        g["ht"], g["at"] = extra.get(g["key"], ("", "", None))[:2]
        margin = abs(g["hs"] - g["as"])
        if g["goals"] is not None and g["hs"] - g["as"] == sum(1 if h else -1 for _, h in g["goals"]):
            g["coast"] = coasting(g, lambda L, t, g_: tab(L, t))
        else:
            g["coast"] = 0.1 if margin >= 2 else 0.0
            no_goals += 1
    return games, no_goals


def values(games):
    """Each version's result value for the home side, scaled to spread 1."""
    sign = np.array([1.0 if g["hs"] > g["as"] else -1.0 if g["hs"] < g["as"] else 0.0 for g in games])
    coast = np.array([g["coast"] for g in games])
    gd = np.array([g["hs"] - g["as"] for g in games], dtype=float)
    y = {"win": sign, "margin": np.clip(gd, -5, 5), "coast": sign * (1 + np.minimum(coast, 1)), "coast200": sign * (1 + np.minimum(coast, 2))}
    y = {k: v / v.std() for k, v in y.items()}
    y["blend"] = (y["margin"] + y["coast"]) / 2
    y["blend"] = y["blend"] / y["blend"].std()
    return y


class Design:
    """Up to five columns a game: home coach, away coach, home team, away team, home edge."""

    def __init__(self, games):
        people = sorted({g["hp"] for g in games} | {g["ap"] for g in games})
        self.people = {p: i for i, p in enumerate(people)}
        count = defaultdict(int)
        for g in games:
            if g["classic"]:
                count[g["ht"]] += 1
                count[g["at"]] += 1
        kept = sorted(t for t, c in count.items() if c >= MIN_TEAM_GAMES and t)
        self.teams = {t: len(people) + i for i, t in enumerate(kept)}
        self.home = len(people) + len(kept)
        self.size = self.home + 1
        n = len(games)
        self.cols = np.full((n, 5), self.home, dtype=int)
        self.vals = np.zeros((n, 5))
        for i, g in enumerate(games):
            self.cols[i, 0], self.vals[i, 0] = self.people[g["hp"]], 1
            self.cols[i, 1], self.vals[i, 1] = self.people[g["ap"]], -1
            self.cols[i, 4], self.vals[i, 4] = self.home, 1
            if g["classic"] and g["ht"] in self.teams and g["at"] in self.teams and g["ht"] != g["at"]:
                self.cols[i, 2], self.vals[i, 2] = self.teams[g["ht"]], 1
                self.cols[i, 3], self.vals[i, 3] = self.teams[g["at"]], -1

    def fit(self, mask, weights, y, ridge):
        cols, vals, w = self.cols[mask], self.vals[mask], weights[mask]
        A = np.zeros((self.size, self.size))
        b = np.zeros(self.size)
        for i in range(5):
            np.add.at(b, cols[:, i], w * vals[:, i] * y[mask])
            for j in range(5):
                np.add.at(A, (cols[:, i], cols[:, j]), w * vals[:, i] * vals[:, j])
        pen = np.full(self.size, ridge)
        for i in self.teams.values():
            pen[i] = TEAM_PULL
        pen[self.home] = 1e-6
        A[np.diag_indices(self.size)] += pen
        return np.linalg.solve(A, b), A

    def predict(self, beta, idx):
        return (beta[self.cols[idx]] * self.vals[idx]).sum(axis=1)


def scale_for(x, won):
    """The one factor a in P(home wins) = 1 / (1 + exp(-a x)), by Newton steps on decided games."""
    a = 1.0
    for _ in range(30):
        p = 1 / (1 + np.exp(-np.clip(a * x, -30, 30)))
        g = ((won - p) * x).sum()
        h = -(p * (1 - p) * x * x).sum()
        if abs(h) < 1e-9:
            break
        step = g / h
        a -= step
        if abs(step) < 1e-5:
            break
    return max(a, 1e-3)


def log_loss(p, won):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-(won * np.log(p) + (1 - won) * np.log(1 - p)).sum())


def elo_runs(games, k, folds):
    """Pre-game expectations: live, and frozen at each fold's start."""
    R = defaultdict(lambda: 1500.0)
    live = np.zeros(len(games))
    frozen = np.zeros(len(games))
    snap = {}
    next_fold = 0
    for i, g in enumerate(games):
        while next_fold < len(folds) and g["day"] >= folds[next_fold]:
            snap = dict(R)
            next_fold += 1
        rh, ra = R[g["hp"]], R[g["ap"]]
        live[i] = 1 / (1 + 10 ** (-(rh - ra) / 400))
        frozen[i] = 1 / (1 + 10 ** (-(snap.get(g["hp"], 1500.0) - snap.get(g["ap"], 1500.0)) / 400))
        s = 1.0 if g["hs"] > g["as"] else 0.0 if g["hs"] < g["as"] else 0.5
        d = k * (s - live[i])
        R[g["hp"]] += d
        R[g["ap"]] -= d
    return live, frozen


def components(games):
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for g in games:
        parent[find(g["hp"])] = find(g["ap"])
    groups = defaultdict(set)
    for p in list(parent):
        groups[find(p)].add(p)
    return sorted(groups.values(), key=len, reverse=True)


def system(name, label, out_lines):
    t0 = time.time()
    games, no_goals = prepare(name)
    n = len(games)
    days = np.array([g["day"] for g in games])
    classic = np.array([g["classic"] for g in games])
    decided = np.array([g["hs"] != g["as"] for g in games])
    won = np.array([1.0 if g["hs"] > g["as"] else 0.0 for g in games])
    seen_h, seen_a = np.zeros(n, dtype=int), np.zeros(n, dtype=int)
    seen = defaultdict(int)
    for i, g in enumerate(games):
        seen_h[i], seen_a[i] = seen[g["hp"]], seen[g["ap"]]
        seen[g["hp"]] += 1
        seen[g["ap"]] += 1
    rated = (seen_h >= MIN_SEEN) & (seen_a >= MIN_SEEN) & decided
    D = Design(games)
    Y = values(games)
    folds = [date(y, m, 1).toordinal() for y in range(FIRST_YEAR, 2027) for m in (1, 7)]
    folds = [f for f in folds if f < days.max()]
    live, frozen = elo_runs(games, ELO_K[label], folds)
    out_lines.append(f"\n## {label}\n\n{n} games, {len(D.people)} coaches, {len(D.teams)} Classic teams fitted, {100 * classic.mean():.0f}% Classic; "
                     f"{100 * sum(bool(g['coast']) for g in games) / n:.0f}% of games have a coasting bonus; {no_goals} games without usable goal times (bonus by margin only).\n")
    results = {}
    fold_masks = []
    for a_, b_ in zip(folds, folds[1:] + [days.max() + 1]):
        fold_masks.append((a_, (days >= a_) & (days < b_) & rated))
    total = len(VERSIONS) * len(HALF_LIVES) * len(RIDGES)
    done = 0
    for ver in VERSIONS:
        y = Y[ver]
        for hl in HALF_LIVES:
            for ridge in RIDGES:
                x_prev = None
                ll = {"all": 0.0, "classic": 0.0}
                cnt = {"all": 0, "classic": 0}
                for a_, test in fold_masks:
                    train = days < a_
                    w = np.ones(n) if hl is None else 0.5 ** ((a_ - days) / (365.25 * hl))
                    beta, _ = D.fit(train, w, y, ridge)
                    idx = np.nonzero(test)[0]
                    if not len(idx):
                        continue
                    x = D.predict(beta, idx)
                    if x_prev is not None:
                        s = scale_for(*x_prev)
                        p = 1 / (1 + np.exp(-np.clip(s * x, -30, 30)))
                        ll["all"] += log_loss(p, won[idx])
                        cnt["all"] += len(idx)
                        c = classic[idx]
                        ll["classic"] += log_loss(p[c], won[idx][c])
                        cnt["classic"] += int(c.sum())
                    x_prev = (x, won[idx])
                    breathe()
                results[(ver, hl, ridge)] = {k: ll[k] / cnt[k] if cnt[k] else float("nan") for k in ll}
                done += 1
                print(f"{label}: {done}/{total} after {time.time() - t0:.0f} s", flush=True)
    # the same test games for Elo: every fold with games after the first such fold (its factor has nothing before it, so the fit scores none of it)
    test_all = np.zeros(n, dtype=bool)
    for _, test in [f for f in fold_masks if f[1].any()][1:]:
        test_all |= test
    idx = np.nonzero(test_all)[0]
    base = {"Elo, live": live[idx], "Elo, frozen at the half years": frozen[idx]}
    c = classic[idx]
    out_lines.append(f"Test games: {len(idx)} ({int(c.sum())} Classic). Lower is better; a coin flip is 0.6931.\n")
    out_lines.append("| Rating | All games | Classic games |\n|---|---|---|")
    for lab, p in base.items():
        out_lines.append(f"| {lab} | {log_loss(p, won[idx]) / len(idx):.4f} | {log_loss(p[c], won[idx][c]) / c.sum() if c.any() else float('nan'):.4f} |")
    best = {}
    for ver in VERSIONS:
        k = min((k for k in results if k[0] == ver), key=lambda k: results[k]["all"])
        best[ver] = k
        out_lines.append(f"| {ver} (half-life {'none' if k[1] is None else k[1]}, ridge {k[2]:g}) | {results[k]['all']:.4f} | {results[k]['classic']:.4f} |")
    out_lines.append("")
    out_lines.append("Half-life and ridge, the best version's score over each setting:\n")
    top = min(best, key=lambda v: results[best[v]]["all"])
    out_lines.append("| Half-life | " + " | ".join(f"ridge {r:g}" for r in RIDGES) + " |\n|---|" + "---|" * len(RIDGES))
    for hl in HALF_LIVES:
        out_lines.append(f"| {'none' if hl is None else hl} | " + " | ".join(f"{results[(top, hl, r)]['all']:.4f}" for r in RIDGES) + " |")
    out_lines.append("")
    # refitted monthly, every version on the settings the table uses, against Elo
    months = [f for f in (date(y, m, 1).toordinal() for y in range(FIRST_YEAR, 2027) for m in range(1, 13)) if f < days.max()]
    live_m, frozen_m = elo_runs(games, ELO_K[label], months)
    masks = [(a_, (days >= a_) & (days < b_) & rated) for a_, b_ in zip(months, months[1:] + [days.max() + 1])]
    preds = {}
    for ver in ("win", "margin", "coast", "blend"):
        _, hl_, r_ = best["coast"]
        p_, hist = np.full(n, np.nan), []
        for a_, test in masks:
            ids = np.nonzero(test)[0]
            if not len(ids):
                continue
            w_ = np.ones(n) if hl_ is None else 0.5 ** ((a_ - days) / (365.25 * hl_))
            b_, _ = D.fit(days < a_, w_, Y[ver], r_)
            x = D.predict(b_, ids)
            if hist:
                s = scale_for(np.concatenate([h[0] for h in hist[-6:]]), np.concatenate([h[1] for h in hist[-6:]]))
                p_[ids] = 1 / (1 + np.exp(-np.clip(s * x, -30, 30)))
            hist.append((x, won[ids]))
            breathe()
        preds[ver] = p_
    ids = np.nonzero(~np.isnan(preds["coast"]))[0]
    c = classic[ids]
    loss = lambda p: -(won[ids] * np.log(np.clip(p, 1e-6, 1)) + (1 - won[ids]) * np.log(np.clip(1 - p, 1e-6, 1)))
    L = {"Elo, updated every game": loss(live_m[ids]), "Elo, frozen monthly": loss(frozen_m[ids]), **{v: loss(p[ids]) for v, p in preds.items()}}
    out_lines.append(f"Refitted monthly, {len(ids)} test games ({int(c.sum())} Classic):\n\n| Rating | Log loss | Classic games | Coast minus this |\n|---|---|---|---|")
    for k, v in L.items():
        d = L["coast"] - v
        out_lines.append(f"| {k} | {v.mean():.4f} | {v[c].mean() if c.any() else float('nan'):.4f} | {'' if k == 'coast' else f'{d.mean():+.4f} +- {d.std() / len(d) ** .5:.4f}'} |")
    out_lines.append("")
    # the final fit, the coasting version as asked unless another clearly wins; written for both coast and the top version
    final_ver = "coast"
    _, hl, ridge = best[final_ver]
    now = days.max()
    w = np.ones(n) if hl is None else 0.5 ** ((now - days) / (365.25 * hl))
    y = Y[final_ver]
    every = np.ones(n, dtype=bool)
    beta, A = D.fit(every, w, y, ridge)
    career, _ = D.fit(every, np.ones(n), y, ridge)
    res = y - D.predict(beta, np.arange(n))
    sigma2 = float((w * res * res).sum() / w.sum())
    idx_all = np.nonzero(decided)[0]
    in_sample_scale = scale_for(D.predict(beta, idx_all), won[idx_all])
    # the conversion to a win chance: what fitted games not yet seen, in the last 3 years. A factor fitted on the same games the strengths came from
    # overstates (SNES Classic: predictions of 84% won 75% of later games). Used for the career column too, so the two columns stay on one scale.
    xs, ws = [], []
    for a_, test in fold_masks:
        ids = np.nonzero(test)[0]
        if a_ < now - 1096 or not len(ids):
            continue
        w_ = np.ones(n) if hl is None else 0.5 ** ((a_ - days) / (365.25 * hl))
        b_, _ = D.fit(days < a_, w_, y, ridge)
        xs.append(D.predict(b_, ids))
        ws.append(won[ids])
        breathe()
    scale = scale_for(np.concatenate(xs), np.concatenate(ws))
    out_lines.append(f"Conversion factor {scale:.3f} from {sum(map(len, xs))} later games in the last 3 years ({in_sample_scale:.3f} if fitted on the same games as the strengths).\n")
    pred = 1 / (1 + np.exp(-scale * np.concatenate(xs)))
    real = np.concatenate(ws)
    sure, hit = np.where(pred >= 0.5, pred, 1 - pred), np.where(pred >= 0.5, real, 1 - real)
    bands = [(lo, hi, (sure >= lo) & (sure < hi)) for lo, hi in ((0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01))]
    out_lines.append("Those games, predicted against real: " + ", ".join(f"{100 * sure[m].mean():.0f}% won {100 * hit[m].mean():.0f}% ({int(m.sum())})" for _, _, m in bands if m.any()) + ".\n")
    # stability: two halves of the games, fitted apart
    rng = np.random.default_rng(94)
    half = rng.random(n) < 0.5
    b1, _ = D.fit(half, w, y, ridge)
    b2, _ = D.fit(~half, w, y, ridge)
    games_of = defaultdict(int)
    recent = defaultdict(int)
    last = defaultdict(int)
    for g in games:
        for p in (g["hp"], g["ap"]):
            games_of[p] += 1
            last[p] = max(last[p], g["day"])
            recent[p] += g["day"] >= now - 730
    regulars = [i for p, i in D.people.items() if games_of[p] >= 100]
    corr = float(np.corrcoef(b1[regulars], b2[regulars])[0, 1])
    groups = components(games)
    group_of = {p: i for i, s in enumerate(groups) for p in s}
    home_x = beta[D.home] * scale
    out_lines.append(f"Final fit: {final_ver}, half-life {hl}, ridge {ridge:g}. Two random halves of the games fitted apart agree at {corr:.2f} over {len(regulars)} coaches with 100+ games. "
                     f"Home edge {100 / (1 + math.exp(-home_x)):.1f}% for evenly matched coaches on a neutral team. {len(groups)} connected groups of coaches; the largest has {len(groups[0])}. "
                     f"Regulars' spread (sd): {float(np.std(beta[regulars]) * scale):.2f} on the win-chance scale, so a one-sd edge wins {100 / (1 + math.exp(-float(np.std(beta[regulars]) * scale))):.0f}%.\n")
    # the private table: win chance against an average coach, neutral teams and no home edge
    # "average" is the average coach with REF_GAMES+ games (the user: those who've stuck around), each counted once. Only the zero point moves: every
    # coach stays in the table, the gaps between coaches and the fit itself don't change.
    reference = [i for p, i in D.people.items() if games_of[p] >= REF_GAMES]
    zero, zero_career = float(np.mean(beta[reference])), float(np.mean(career[reference]))
    # low / high: the standard error of a coach's gap from that average, as only gaps are measured (an error in all the coaches together doesn't count)
    cov = np.linalg.inv(A)
    gap_var = np.diag(cov) - 2 * cov[:, reference].mean(axis=1) + cov[np.ix_(reference, reference)].mean()
    se = np.sqrt(np.maximum(gap_var * sigma2, 0))
    out_lines.append(f"\"Average\" here: the mean of the {len(reference)} coaches with {REF_GAMES}+ games. On the old zero point (all coaches) they average {100 / (1 + math.exp(-zero * scale)):.1f}%.\n")
    rows = []
    for p, i in D.people.items():
        pct = lambda v: 100 / (1 + math.exp(-v * scale))
        b_ = beta[i] - zero
        rows.append((pct(b_), pct(b_ - se[i]), pct(b_ + se[i]), pct(career[i] - zero_career), games_of[p], recent[p], date.fromordinal(last[p]).isoformat(), p, group_of[p]))
    rows.sort(reverse=True)
    path = DATA / f"coach_ratings_{label}{'_' + PREFIX if PREFIX else ''}.csv"
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["coach", "win_chance_vs_average", "low", "high", "career", "games", "games_last_2_years", "last_played", "group"])
        for r in rows:
            wr.writerow([r[7], f"{r[0]:.1f}", f"{r[1]:.1f}", f"{r[2]:.1f}", f"{r[3]:.1f}", r[4], r[5], r[6], r[8]])
    teams = sorted(D.teams.items(), key=lambda kv: -beta[kv[1]])
    sides = defaultdict(int)
    for g in games:
        if g["classic"]:
            sides[g["ht"]] += 1
            sides[g["at"]] += 1
    out_lines.append(f"Teams (Classic, strongest first, sides): {', '.join(f'{t} {100 / (1 + math.exp(-beta[i] * scale)) - 50:+.1f} ({sides[t]})' for t, i in teams)}.\n")
    out_lines.append(f"Classic labels with no team value: {', '.join(f'{t} {c}' for t, c in sorted(sides.items()) if t not in D.teams)}.\n")
    out_lines.append(f"Middle of the pull (the all-coach mean) on the final scale: {100 / (1 + math.exp(zero * scale)):.1f}.\n")
    print(f"{label} finished in {time.time() - t0:.0f} s; table: {path}", flush=True)


def main():
    global PREFIX
    gentle()
    if sys.argv[1:] == ["groups"]:
        lines = ["# Coach strength rating: league groups, each fitted alone\n", "`analysis/coach_rating.py groups`. Aggregates only.\n"]
        for name, label, prefix in GROUPS:
            PREFIX = prefix
            lines.append(f"\n# {label}, leagues starting \"{prefix}\"")
            system(name, label, lines)
        (DATA / "coach_rating_groups.md").write_text("\n".join(lines), encoding="utf-8")
        print("\n".join(lines))
        return
    lines = ["# Coach strength rating: the test\n", "`analysis/coach_rating.py`. Aggregates only. Each coach's rating is in a file in the private league folder.\n"]
    for name, label in FILES:
        system(name, label, lines)
    (DATA / "coach_rating_test.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
