"""Two checks on the Classic team strengths (2026-11-04, the user). Aggregates only.
1. Coaches change: one strength per coach per era against one per coach over all years, using the same fit. Do team values depend on coaches staying the same?
2. The pull on team terms: strength uses one light pull on coaches and teams alike. Each pull on the teams alone is tested by predicting later games, half year by half year from 2020.
Halves of the leagues fitted apart show how repeatable each set of team values is.
python analysis/team_strength_checks.py     prints the results and writes reports/team_strength_checks.json (git-ignored)"""
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
import coach_rating as C  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

TABLES = (("All_Games_GENS.csv", "Genesis", 0), ("All_Games_SNES.csv", "SNES", 1))
ERAS = {"3 eras": (2020, 2023), "4 eras": (2017, 2020, 2023), "6 eras": (2015, 2017, 2019, 2021, 2023)}
PULLS = (2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 200.0, 400.0)
SPLITS = 30


def fit(D, mask, w, y, coach, team):
    """As Design.fit, with a separate pull on the teams."""
    cols, vals, wt = D.cols[mask], D.vals[mask], w[mask]
    A = np.zeros((D.size, D.size))
    b = np.zeros(D.size)
    for i in range(5):
        np.add.at(b, cols[:, i], wt * vals[:, i] * y[mask])
        for j in range(5):
            np.add.at(A, (cols[:, i], cols[:, j]), wt * vals[:, i] * vals[:, j])
    pen = np.full(D.size, coach)
    for i in D.teams.values():
        pen[i] = team
    pen[D.home] = 1e-6
    A[np.diag_indices(D.size)] += pen
    return np.linalg.solve(A, b)


def team_values(D, beta, used, scale):
    ts = sorted(D.teams)
    weight = np.array([used[t] for t in ts], float)
    v = np.array([beta[D.teams[t]] for t in ts])
    v = v - (v * weight).sum() / weight.sum()
    return dict(zip(ts, 100 / (1 + np.exp(-v * scale)) - 50))


def repeatable(D, games, y, used, scale, coach, team, rng):
    names = np.array([g["league"] for g in games])
    leagues = np.array(sorted(set(names)))
    rs = []
    n = len(games)
    big = [t for t in sorted(D.teams) if used[t] >= 300]
    for _ in range(SPLITS):
        half = rng.permutation(leagues)[: len(leagues) // 2]
        a = np.isin(names, half)
        va = team_values(D, fit(D, a, np.ones(n), y, coach, team), used, scale)
        vb = team_values(D, fit(D, ~a, np.ones(n), y, coach, team), used, scale)
        rs.append(np.corrcoef([va[t] for t in big], [vb[t] for t in big])[0, 1])
        breathe()
    return float(np.mean(rs))


def main():
    gentle()
    text = (C.DATA / "coach_rating_groups.md").read_text(encoding="utf-8")
    conv = [float(x) for x in re.findall(r"Conversion factor ([\d.]+)", text)]
    fits = re.findall(r"Final fit: coast, half-life ([\d.]+), ridge ([\d.]+)", text)
    C.PREFIX = "classic"
    out = {}
    for name, label, at in TABLES:
        games, _ = C.prepare(name)
        n = len(games)
        y = C.values(games)["coast"]
        scale = conv[at]
        hl, ridge = float(fits[at][0]), float(fits[at][1])
        D = C.Design(games)
        used = Counter()
        for g in games:
            used[g["ht"]] += 1
            used[g["at"]] += 1
        rng = np.random.default_rng(94)
        base = team_values(D, fit(D, np.ones(n, dtype=bool), np.ones(n), y, ridge, C.TEAM_PULL), used, scale)
        big = [t for t in sorted(D.teams) if used[t] >= 300]
        rep0 = repeatable(D, games, y, used, scale, ridge, C.TEAM_PULL, rng)
        print(f"\n{label}: {n} games; one strength per coach, halves of the leagues repeat at {rep0:+.2f}", flush=True)
        res = {"one": base, "one_repeat": rep0}
        for era_name, cuts in ERAS.items():
            copies = []
            for g in games:
                e = sum(date.fromordinal(g["day"]).year >= c for c in cuts)
                copies.append({**g, "hp": f"{g['hp']}|{e}", "ap": f"{g['ap']}|{e}"})
            De = C.Design(copies)
            vals = team_values(De, fit(De, np.ones(n, dtype=bool), np.ones(n), y, ridge, C.TEAM_PULL), used, scale)
            rep = repeatable(De, copies, y, used, scale, ridge, C.TEAM_PULL, rng)
            moved = sorted(((abs(vals[t] - base[t]), t) for t in big), reverse=True)[:5]
            print(f"  {era_name}: coach-era terms {len(De.people)}; team values against one strength {np.corrcoef([vals[t] for t in big], [base[t] for t in big])[0, 1]:+.3f}, typical move {np.mean([abs(vals[t] - base[t]) for t in big]):.1f} points; repeat {rep:+.2f}; largest " + ", ".join(f"{t} {base[t]:+.1f} to {vals[t]:+.1f}" for _, t in moved), flush=True)
            res[era_name] = {"values": vals, "repeat": rep}
        # how much coaches change between eras
        cuts = ERAS["3 eras"]
        copies = []
        for g in games:
            e = sum(date.fromordinal(g["day"]).year >= c for c in cuts)
            copies.append({**g, "hp": f"{g['hp']}|{e}", "ap": f"{g['ap']}|{e}"})
        De = C.Design(copies)
        be = fit(De, np.ones(n, dtype=bool), np.ones(n), y, ridge, C.TEAM_PULL)
        counts = Counter()
        for g in copies:
            counts[g["hp"]] += 1
            counts[g["ap"]] += 1
        by = {}
        for key, i in De.people.items():
            p, e = key.rsplit("|", 1)
            if counts[key] >= 100:
                by.setdefault(p, {})[e] = be[i]
        steps = [abs(d[b] - d[a]) * scale for d in by.values() for a, b in (("0", "1"), ("1", "2")) if a in d and b in d]
        print(f"  coaches with 100+ games in two straight eras: {len(steps)} steps, typical change {np.mean(steps):.2f} logit, which at even is about {100 / (1 + np.exp(-np.mean(steps))) - 50:.0f} points of win chance", flush=True)
        # the pull on teams, predicting later games
        days = np.array([g["day"] for g in games])
        decided = np.array([g["hs"] != g["as"] for g in games])
        won = np.array([1.0 if g["hs"] > g["as"] else 0.0 for g in games])
        seen = Counter()
        rated = np.zeros(n, dtype=bool)
        for i, g in enumerate(games):
            rated[i] = seen[g["hp"]] >= C.MIN_SEEN and seen[g["ap"]] >= C.MIN_SEEN and decided[i]
            seen[g["hp"]] += 1
            seen[g["ap"]] += 1
        now = days.max()
        folds = [f for f in (date(yy, mm, 1).toordinal() for yy in range(2020, 2027) for mm in (1, 7)) if f < now]
        scores = {}
        for team in PULLS:
            ll, cnt, prev = 0.0, 0, None
            for a, b_ in zip(folds, folds[1:] + [now + 1]):
                ids = np.nonzero((days >= a) & (days < b_) & rated)[0]
                if not len(ids):
                    continue
                w = 0.5 ** ((a - days) / (365.25 * hl))
                beta = fit(D, days < a, w, y, ridge, team)
                x = D.predict(beta, ids)
                if prev is not None:
                    s = C.scale_for(*prev)
                    ll += C.log_loss(1 / (1 + np.exp(-np.clip(s * x, -30, 30))), won[ids])
                    cnt += len(ids)
                prev = (x, won[ids])
                breathe()
            scores[team] = ll / cnt
        print("  pull on teams, predicting later games: " + ", ".join(f"{k:g}: {v:.4f}" for k, v in scores.items()), flush=True)
        for team in PULLS:
            vals = team_values(D, fit(D, np.ones(n, dtype=bool), 0.5 ** ((now - days) / (365.25 * hl)), y, ridge, team), used, scale)
            print(f"    pull {team:g} now: " + ", ".join(f"{t} {vals[t]:+.1f}" for t in ("CHI", "PIT", "NJ", "NYI", "SJ", "DAL", "TB", "HFD", "NYR") if t in vals))
        res["pull_scores"] = {str(k): v for k, v in scores.items()}
        out[label] = res
    (Path(__file__).resolve().parents[1] / "reports" / "team_strength_checks.json").write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main()
