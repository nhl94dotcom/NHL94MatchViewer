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
RATING_VALUES.md. python analysis/league_value.py"""
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
FWD = {5: 0.29, 2: 0.22, 9: 0.15, 8: 0.10, 1: 0.09, 0: -0.06}
DEF = {12: 0.060, 6: 0.042, 1: 0.033, 2: 0.026, 5: 0.013, 9: 0.009, 0: -0.022, 3: -0.018, 8: -0.010}
GOALIE_SV_STEP = 0.0225


def team_strengths():
    text = (ROOT / "docs" / "COACH_RATING.md").read_text(encoding="utf-8")
    sec = text[text.index("## 9. Classic team strengths"):text.index("**How far to trust them.**")]
    out = {}
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.fullmatch(r"[A-Z]{2,3}", cells[0]):
            out[cells[0]] = float(cells[1].replace("−", "-"))
    return out


def scale(values):
    lo, hi = min(values.values()), max(values.values())
    return {k: round(40 + 59 * (v - lo) / (hi - lo)) for k, v in values.items()}


def main():
    teams = genesis.read_teams(rom("9438f5dd_a738ea1c.bin"))
    pdata = json.loads((ROOT / "reports" / "classic_players.json").read_text())["Genesis"]
    pos = {(s["team"], s["name"].lower()): s for s in pdata["skaters"]}
    gs = {(g["team"], g["name"].lower()): g for g in pdata["goalies"]}
    shots_per_game = sum(g["sa"] for g in pdata["goalies"]) / sum(g["games"] for g in pdata["goalies"])
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
    print(f"shots a goalie faces a game in Genesis Classic: {shots_per_game:.1f}; an Agility step is "
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
    # the team check
    strength = team_strengths()
    X_lv, X_ovr, y, names = [], [], [], []
    team_rows = []
    for t in teams:
        ab = t["abbr"]
        if ab not in strength:
            continue
        parts_lv, parts_ovr = [], []
        for ps in ("F", "D"):
            ks = [k for k in raw[ps] if k[0] == ab and info[k]["games"] > 0]
            wsum = sum(info[k]["games"] for k in ks)
            if not wsum:
                break
            parts_lv.append(sum(raw[ps][k] * info[k]["games"] for k in ks) / wsum)
            parts_ovr.append(sum(info[k]["ovr"] * info[k]["games"] for k in ks) / wsum)
        gk = [k for k in raw["G"] if k[0] == ab]
        if len(parts_lv) < 2 or not gk:
            continue
        g = max(gk, key=lambda k: info[k]["games"])
        parts_lv.append(raw["G"][g])
        parts_ovr.append(info[g]["ovr"])
        X_lv.append(parts_lv)
        X_ovr.append(parts_ovr)
        y.append(strength[ab])
        names.append(ab)
        team_rows.append((ab, strength[ab], parts_lv, parts_ovr, g[1]))
    y = np.array(y)

    def fit(X, label):
        X = np.array(X, float)
        A = np.column_stack([X, np.ones(len(X))])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        pred = A @ beta
        r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        # leave one out
        loo = []
        for i in range(len(y)):
            m = np.ones(len(y), bool)
            m[i] = False
            b, *_ = np.linalg.lstsq(A[m], y[m], rcond=None)
            loo.append(A[i] @ b)
        loo = np.array(loo)
        r2_loo = 1 - ((y - loo) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        print(f"  {label}: R^2 {r2:.2f}, left-one-out {r2_loo:.2f}; per unit: forwards {beta[0]:+.2f}, defencemen "
              f"{beta[1]:+.2f}, goalie {beta[2]:+.2f}")
        return pred
    print(f"\nTeams ({len(y)}): strength (win chance points) against their parts")
    p_lv = fit(X_lv, "league value parts (forwards' goals, defencemen's points, goalie's goals saved)")
    p_ovr = fit(X_ovr, "the game's Overall (forwards, defencemen, goalie)")
    print("\n| Team | Strength | From league value | From Overall | Main goalie |")
    print("|---|---|---|---|---|")
    for (ab, s, pl, po, gname), a, b in sorted(zip(team_rows, p_lv, p_ovr), key=lambda r: -r[0][1]):
        print(f"| {ab} | {s:+.1f} | {a:+.1f} | {b:+.1f} | {gname} |")
    out = {f"{k[0]}|{k[1]}": dict(lv=lv[k], **{x: info[k][x] for x in ("pos", "ovr", "games")}) for k in lv}
    (ROOT / "reports" / "league_value.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
