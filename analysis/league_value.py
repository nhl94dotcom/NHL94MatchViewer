"""A "league value" for the Genesis retail players (2026-11-11, RATING_VALUES chunk D, for NOSE4Web and the commissioner):
one number per player, 0-99 like the game's Overall, weighting each rating by what a roster step was worth in the
Classic leagues' own results, and a check of it against the teams' measured strength.

- Forwards: goals a game per roster step (LEAGUE_RESULTS "Which ratings make scorers", fitted within each team and
  position): Shot Power +0.29, Speed +0.22, Shot Accuracy +0.15, Stickhandling +0.10, Agility +0.09, Weight -0.06;
  the rest about nothing.
- Defencemen: points a game per step (PLAYER_GUIDE_GENESIS): Pass Accuracy +0.060, Checking +0.042, Agility +0.033,
  Speed +0.026, Shot Power +0.013, Shot Accuracy +0.009, Weight -0.022, Off. Awareness -0.018, Stickhandling -0.010.
  What a defenceman's ratings do to goals against has not been measured, so this is his offence only.
- Goalies: save % +2.25 points per Agility step (PLAYER_GUIDE_GENESIS), times the shots a goalie faces a game in these
  leagues: goals saved a game; Puck Control and the rest left at 0 (RATING_VALUES: little or nothing).
Each position's weighted sum is put on 40-99 across its retail players (the lowest 40, the highest 99).

The check: each Classic team's strength (COACH_RATING section 9, "Strength now", win chance against an average team
with the coaches taken out), against (a) the team's league value (its regular forwards and defencemen, weighted by
their games, and its most-used goalie) and (b) the same built from the game's Overall. A least-squares fit of strength
on the three parts (forwards, defencemen, goalie) each way, and how much of the teams' spread each explains.

Reads the ROM (the retail Genesis rosters), reports/classic_players.json (classic_player_guide.py: games and
positions; aggregates of the leagues' results, no person named) and docs/COACH_RATING.md. Prints tables for
RATING_VALUES.md. python analysis/league_value.py [genesis|snes]   (the SNES: its own steps, ROM and team strengths)"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools"))
from league_player_study import rom  # noqa: E402
from systems import genesis  # noqa: E402

# rating index in the ROM's 14 (league_player_study.NAMES): Weight 0, Agility 1, Speed 2, Off. Aware 3, Def. Aware 4,
# Shot Power 5, Checking 6, Handed 7, Stick Hand 8, Shot Acc 9, Endurance 10, Shoot bias 11, Pass Acc 12, Aggression 13
FWD = {5: 0.29, 2: 0.22, 9: 0.15, 8: 0.10, 1: 0.09, 0: -0.06}     # Weight replaced by the team fit's below
WEIGHT = 0
# the SNES (LEAGUE_RESULTS, PLAYER_GUIDE_SNES): forwards' goals a game a step, defencemen's points, goalies' save %
SYSTEMS = {
    "genesis": dict(fwd=dict(FWD), dfn={12: 0.060, 6: 0.042, 1: 0.033, 2: 0.026, 5: 0.013, 9: 0.009, 0: -0.022, 3: -0.018,
                                       8: -0.010},
                    gsv=0.0225, rom="9438f5dd_a738ea1c.bin", key="Genesis", col=0, team_weight=True),
    "snes": dict(fwd={2: 0.18, 5: 0.16, 9: 0.14, 1: 0.14, 8: 0.14, 0: 0.08},
                 dfn={8: 0.182, 2: 0.176, 3: 0.102, 0: 0.067, 6: 0.057, 1: -0.027, 5: -0.016, 9: -0.014, 12: -0.087},
                 gsv=0.0031, rom="cd85e387.smc", key="SNES", col=1, team_weight=False),
}
DEF = {12: 0.060, 6: 0.042, 1: 0.033, 2: 0.026, 5: 0.013, 9: 0.009, 0: -0.022, 3: -0.018, 8: -0.010}
GOALIE_SV_STEP = 0.0225


def team_strengths(col=0):
    """COACH_RATING section 9's "Strength now": col 0 the Genesis table, 1 the SNES one (the same rows, side by side)."""
    text = (ROOT / "docs" / "COACH_RATING.md").read_text(encoding="utf-8")
    sec = text[text.index("## 9. Classic team strengths"):text.index("**How far to trust them.**")]
    out = {}
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 9:
            name, val = cells[5 * col], cells[5 * col + 1]
            if re.fullmatch(r"[A-Z]{2,3}", name):
                out[name] = float(val.replace("−", "-"))
    return out


def scale(values):
    lo, hi = min(values.values()), max(values.values())
    return {k: round(40 + 59 * (v - lo) / (hi - lo)) for k, v in values.items()}


def loo_fit(X, y):
    """Least squares with an intercept: (coefficients, R^2, R^2 with each row predicted from the others)."""
    X = np.array(X, float)
    A = np.column_stack([X, np.ones(len(X))])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ beta
    r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    loo = []
    for i in range(len(y)):
        m = np.ones(len(y), bool)
        m[i] = False
        b, *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
        loo.append(A[i] @ b)
    loo = np.array(loo)
    return beta, pred, r2, 1 - ((y - loo) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def team_parts(teams, pdata, strength, shots_per_game):
    """Per Classic team: its strength; its regular forwards' scoring value without Weight, defencemen's value, the main
    goalie's goals saved, the forwards' average Weight (all weighted by games), and the same skaters' mean Overall."""
    pos = {(s["team"], s["name"].lower()): s for s in pdata["skaters"]}
    gs = {(g["team"], g["name"].lower()): g for g in pdata["goalies"]}
    rows = []
    for t in teams:
        ab = t["abbr"]
        if ab not in strength:
            continue
        F, D = [], []
        for p in t["players"]:
            s = pos.get((ab, p["name"].lower()))
            if p["g"] or not s:
                continue
            (F if s["pos"] == "F" else D).append((p, s["n"]))
        gk = [(p, gs.get((ab, p["name"].lower()), {}).get("games", 0)) for p in t["players"] if p["g"]]
        if not F or not D or not gk:
            continue
        g = max(gk, key=lambda x: x[1])[0]
        avg = lambda L, f: sum(f(p) * n for p, n in L) / sum(n for _, n in L)
        rows.append(dict(team=ab, strength=strength[ab],
                         f=avg(F, lambda p: sum(v * p["a"][i] for i, v in FWD.items() if i != 0)),
                         d=avg(D, lambda p: sum(v * p["a"][i] for i, v in DEF.items())),
                         g=GOALIE_SV_STEP * g["a"][1] * shots_per_game, fw=avg(F, lambda p: p["a"][0]),
                         fovr=avg(F, lambda p: p["ovr"]), dovr=avg(D, lambda p: p["ovr"]), govr=g["ovr"], goalie=g["name"]))
    return rows


def main():
    global WEIGHT, GOALIE_SV_STEP
    system = sys.argv[1] if len(sys.argv) > 1 else "genesis"
    cfg = SYSTEMS[system]
    FWD.clear()
    FWD.update(cfg["fwd"])
    DEF.clear()
    DEF.update(cfg["dfn"])
    GOALIE_SV_STEP = cfg["gsv"]
    mod = genesis if system == "genesis" else __import__("systems.snes", fromlist=["snes"])
    teams = mod.read_teams(rom(cfg["rom"]))
    pdata = json.loads((ROOT / "reports" / "classic_players.json").read_text())[cfg["key"]]
    pos = {(s["team"], s["name"].lower()): s for s in pdata["skaters"]}
    gs = {(g["team"], g["name"].lower()): g for g in pdata["goalies"]}
    shots_per_game = sum(g["sa"] for g in pdata["goalies"]) / sum(g["games"] for g in pdata["goalies"])
    strength = team_strengths(cfg["col"])
    trows = team_parts(teams, pdata, strength, shots_per_game)
    y = np.array([r["strength"] for r in trows])
    # Weight's worth to a team: the forwards' average Weight beside the three value parts; in goals a game of a
    # forward's value per Weight point (its coefficient over the forwards' value coefficient)
    beta, _, r2w, loow = loo_fit([[r["f"], r["d"], r["g"], r["fw"]] for r in trows], y)
    WEIGHT = beta[3] / beta[0] if cfg["team_weight"] else cfg["fwd"][0]
    # (the SNES: its forwards' scoring value doesn't predict its teams, so the ratio means nothing there; Weight stays
    # at its scoring value and the team coefficient is only reported)
    # how sure: the coefficient's standard error, and a bootstrap of the teams for the ratio
    A = np.column_stack([np.array([[r["f"], r["d"], r["g"], r["fw"]] for r in trows], float), np.ones(len(trows))])
    res = y - A @ beta
    cov = (res @ res / (len(y) - A.shape[1])) * np.linalg.inv(A.T @ A)
    rng = np.random.default_rng(1)
    ratios = []
    for _ in range(2000):
        ix = rng.integers(0, len(y), len(y))
        b, *_ = np.linalg.lstsq(A[ix], y[ix], rcond=None)
        if b[0] > 0.5:
            ratios.append(b[3] / b[0])
    lo, hi = np.percentile(ratios, [10, 90])
    print(f"  the forwards' Weight coefficient {beta[3]:+.2f} +- {np.sqrt(cov[3, 3]):.2f} (one s.e.); the ratio's middle 80% "
          f"over resampled teams {lo:+.2f} to {hi:+.2f}")
    FWD[0] = WEIGHT
    print(f"forwards' Weight in the team fit: {beta[3]:+.2f} win-chance points a Weight point of the team's average forward"
          + (f", = {WEIGHT:+.2f} goals a game of a forward's value (his own scoring alone: {cfg['fwd'][0]:+.2f})"
             if cfg["team_weight"] else f"; the value keeps his own scoring's {WEIGHT:+.2f}"))
    raw = {"F": {}, "D": {}, "G": {}}
    info = {}
    for t in teams:
        ab = t["abbr"]
        for p in t["players"]:
            key = (ab, p["name"])
            a = p["a"]
            if p["g"]:
                raw["G"][key] = GOALIE_SV_STEP * a[1] * shots_per_game
                info[key] = dict(pos="G", ovr=p["ovr"], games=gs.get((ab, p["name"].lower()), {}).get("games", 0), a=a)
                continue
            s = pos.get((ab, p["name"].lower()))
            ps = s["pos"] if s else None
            if ps is None:                      # not a regular in the leagues: his position from the roster order
                ps = "D" if a[6] > a[5] and a[12] >= a[9] else "F"     # (a rough guess, only for the scale)
            w = FWD if ps == "F" else DEF
            raw[ps][key] = sum(v * a[i] for i, v in w.items())
            info[key] = dict(pos=ps, ovr=p["ovr"], games=s["n"] if s else 0, a=a)
    lv = {}
    for ps in raw:
        lv.update(scale(raw[ps]))
    print(f"shots a goalie faces a game in {cfg['key']} Classic: {shots_per_game:.1f}; an Agility step is "
          f"{GOALIE_SV_STEP * shots_per_game:.2f} goals saved a game")
    # rankings: regulars (150+ games) by position
    for ps, label, n in (("F", "Forwards", 20), ("D", "Defencemen", 12), ("G", "Goalies", 12)):
        rows = [(k, info[k]) for k in raw[ps] if info[k]["games"] >= 150]
        by_lv = sorted(rows, key=lambda r: -lv[r[0]])
        by_ovr = sorted(rows, key=lambda r: -r[1]["ovr"])
        rk_lv = {r[0]: i + 1 for i, r in enumerate(by_lv)}
        rk_ovr = {r[0]: i + 1 for i, r in enumerate(by_ovr)}
        print(f"\n{label} with 150+ league games ({len(rows)}): top {n} by league value")
        print("| Player | Team | League value | Rank | Game's Overall | Rank |")
        print("|---|---|---|---|---|---|")
        for k, d in by_lv[:n]:
            print(f"| {k[1]} | {k[0]} | {lv[k]} | {rk_lv[k]} | {d['ovr']} | {rk_ovr[k]} |")
        moves = sorted(rows, key=lambda r: rk_ovr[r[0]] - rk_lv[r[0]])
        print(f"  most underrated by Overall: " + "; ".join(f"{k[1]} ({k[0]}) Ovr rank {rk_ovr[k]} -> {rk_lv[k]}"
                                                            for k, _ in moves[-6:][::-1]))
        print(f"  most overrated by Overall: " + "; ".join(f"{k[1]} ({k[0]}) Ovr rank {rk_ovr[k]} -> {rk_lv[k]}"
                                                          for k, _ in moves[:6]))
    # the team check: league value (Weight from the teams) against the game's Overall, each with and without the
    # forwards' average Weight beside it
    print(f"\nTeams ({len(y)}): strength (win-chance points) explained, each team also predicted from the others")
    print("| Built from | R^2 | Left one team out |")
    print("|---|---|---|")
    for label, cols in (("League value: forwards' scoring, defencemen, goalie", ["f", "d", "g"]),
                        ("League value with the forwards' Weight", ["f", "d", "g", "fw"]),
                        ("The game's Overall: forwards, defencemen, goalie", ["fovr", "dovr", "govr"]),
                        ("The game's Overall with the forwards' Weight", ["fovr", "dovr", "govr", "fw"])):
        _, pred, r2, loo = loo_fit([[r[c] for c in cols] for r in trows], y)
        print(f"| {label} | {r2:.2f} | {loo:.2f} |")
    _, p_lv, _, _ = loo_fit([[r["f"], r["d"], r["g"], r["fw"]] for r in trows], y)
    _, p_ovr, _, _ = loo_fit([[r["fovr"], r["dovr"], r["govr"]] for r in trows], y)
    print("\n| Team | Strength | From league value | From Overall | Forwards' weight | Main goalie |")
    print("|---|---|---|---|---|---|")
    for r, a, b in sorted(zip(trows, p_lv, p_ovr), key=lambda x: -x[0]["strength"]):
        print(f"| {r['team']} | {r['strength']:+.1f} | {a:+.1f} | {b:+.1f} | {r['fw']:.1f} | {r['goalie']} |")
    out = {f"{k[0]}|{k[1]}": dict(lv=lv[k], **{x: info[k][x] for x in ("pos", "ovr", "games")}) for k in lv}
    (ROOT / "reports" / f"league_value_{system}.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
