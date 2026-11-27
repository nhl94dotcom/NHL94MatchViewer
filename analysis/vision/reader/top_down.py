"""A team's xG estimated top-down, from how the game was played (2026-11-26, the user's go-ahead): instead of adding
up shots (each one's error piles up), a model from the measures a video gives reliably (possession, time in the
attacking zone, zone entries, passes and their completion, pucks lost) and the shot count and goals, fitted on the
recorded games where the true xG is known.

measures(m): the inputs for both teams of a match (a recorded match file, or a pseudo match after analyse).
fit(...): a ridge regression on the recorded Genesis games in <home>/matches, with a leave-games-out check.

python top_down.py fit OUT.json [--skip PART ...]      prints the check on the recordings themselves"""
import json
import os
import sys
from pathlib import Path

import numpy as np

import swing_events as SE

HOME = Path(os.environ.get("NHL94_HOME", Path.home() / "Documents/NHL94 Viewer"))
BLUE = 88
NAMES = ["possession share", "own zone time", "their zone time", "entries a minute", "their entries a minute", "passes a minute",
         "pass completion", "pucks lost a minute", "their pucks lost a minute", "shots a minute", "their shots a minute", "goals", "minutes"]
USE = None            # indices of NAMES used (None: all); set by fit's --use


def measures(m, shots=None, goals=None):
    """Per team: the list in NAMES' order. shots: [n0, n1] to override the shot count (a video's calls); goals too."""
    n = len(m["t"])
    live = [i for i in range(n) if m["puck"][3 * i + 2] > -100]
    mins = max(len(live) / 3600.0, 0.5)
    car = [sum(1 for i in live if m["owner"][i] >= 0 and m["owner"][i] // 6 == t) for t in (0, 1)]
    zone = [0, 0]
    for i in live:
        y = m["puck"][3 * i + 1]
        if abs(y) > BLUE:
            zone[0 if (y > 0) == SE.attacks_top(m, i, 0) else 1] += 1
    P = m.get("passes") or []
    ent = [sum(e.get("team") == t for e in m.get("zoneEntries") or []) for t in (0, 1)]
    lost = [sum(x.get("from") == t for x in m.get("turnovers") or []) for t in (0, 1)]
    if shots is None:
        shots = [sum(s.get("team") == t and s.get("kind") in ("shot", "one-timer") for s in m.get("shotList") or []) for t in (0, 1)]
    if goals is None:
        goals = [sum(g.get("team") == t for g in m.get("goals") or []) for t in (0, 1)]
    out = []
    for t in (0, 1):
        o = 1 - t
        np_ = sum(p["team"] == t for p in P)
        out.append([car[t] / max(1, sum(car)), zone[t] / max(1, len(live)), zone[o] / max(1, len(live)), ent[t] / mins, ent[o] / mins,
                    np_ / mins, sum(p["team"] == t and p.get("result") != "failed" for p in P) / max(1, np_), lost[t] / mins, lost[o] / mins,
                    shots[t] / mins, shots[o] / mins, float(goals[t]), mins])
    return out


def true_xg(m):
    return [sum((s.get("xg") or 0) for s in m.get("shotList") or [] if s.get("team") == t and s.get("kind") in ("shot", "one-timer")
                and s.get("result") != "blocked") for t in (0, 1)]


def load(path):
    s = Path(path).read_text()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


def ridge(X, y, lam):
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    A = Z.T @ Z + lam * np.eye(Z.shape[1])
    w = np.linalg.solve(A, Z.T @ (y - y.mean()))
    return dict(mu=mu.tolist(), sd=sd.tolist(), w=w.tolist(), b=float(y.mean()))


def predict(model, X):
    X = np.asarray(X, float)
    if model.get("use") is not None:
        X = X[:, model["use"]]
    return ((X - np.array(model["mu"])) / np.array(model["sd"])) @ np.array(model["w"]) + model["b"]


def collect(skip):
    rows = []
    for p in sorted((HOME / "matches").glob("20*.js")):
        if any(k in p.name for k in skip):
            continue
        m = load(p)
        if m.get("system") != "genesis" or m.get("bot") or len(m["t"]) < 8000:
            continue
        f, x = measures(m), true_xg(m)
        rows.append((p.stem, f, x))
    return rows


def check(rows, use, lam):
    """Leave one game out: each team's error, the margin's, the side ahead."""
    E, M, flips, clear = [], [], 0, 0
    for i, (name, f, x) in enumerate(rows):
        tr = [r for j, r in enumerate(rows) if j != i]
        X = np.array([ft for _, fs, _ in tr for ft in fs])[:, use]
        y = np.array([v for _, _, xs in tr for v in xs])
        mdl = ridge(X, y, lam)
        mdl["use"] = None
        pr = predict(mdl, np.array(f)[:, use])
        E += [pr[0] - x[0], pr[1] - x[1]]
        M.append((pr[0] - pr[1]) - (x[0] - x[1]))
        if abs(x[0] - x[1]) >= 0.5:
            clear += 1
            flips += (pr[0] - pr[1]) * (x[0] - x[1]) < 0
    E = np.array(E)
    return dict(team_sd=float(E.std()), team_abs=float(np.abs(E).mean()), margin_sd=float(np.std(M)), flips=int(flips), clear=clear)


def main():
    out = sys.argv[2]
    skip = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--skip"]
    rows = collect(skip)
    y = np.array([v for _, _, xs in rows for v in xs])
    print(f"{len(rows)} recorded games; a team's true xG mean {y.mean():.2f}, sd {y.std():.2f}; the margin's sd {np.std([x[0] - x[1] for _, _, x in rows]):.2f}")
    sets = {"territory only (no shots, no goals)": [0, 1, 2, 3, 4, 5, 6, 7, 8, 12],
            "territory and the shot counts": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12],
            "territory, shot counts and goals": list(range(13)),
            "shot counts and goals alone": [9, 10, 11, 12]}
    best = None
    for lab, use in sets.items():
        for lam in (1.0, 10.0, 30.0):
            c = check(rows, use, lam)
            print(f"  {lab}, ridge {lam:g}: a team's error sd {c['team_sd']:.2f} (mean abs {c['team_abs']:.2f}); the margin's error sd {c['margin_sd']:.2f}; "
                  f"wrong side ahead in {c['flips']} of {c['clear']}")
            if lab.startswith("territory and the shot") and (best is None or c["margin_sd"] < best[0]):
                best = (c["margin_sd"], use, lam)
    models = {}
    for lab, use in sets.items():
        X = np.array([ft for _, fs, _ in rows for ft in fs])[:, use]
        mdl = ridge(X, y, 10.0)
        mdl["use"] = use
        models[lab] = mdl
        print("  weights,", lab + ":", {NAMES[j]: round(w, 2) for j, w in zip(use, mdl["w"])})
    Path(out).write_text(json.dumps(models))


if __name__ == "__main__":
    main()
