"""A "league value" for the Genesis retail players (2026-11-11, RATING_VALUES chunk D, for NOSE4Web and the commissioner):
one number per player, 0-99 like the game's Overall, weighting each rating by what a roster step was worth in the
Classic leagues' own results, and a check of it against the teams' measured strength.

- Forwards: goals a game per roster step (LEAGUE_RESULTS "Which ratings make scorers", fitted within each team and
  position): Shot Power +0.29, Speed +0.22, Shot Accuracy +0.15, Stickhandling +0.10, Agility +0.09, Weight -0.06;
  the rest about nothing.
- Defencemen: points a game per step (PLAYER_GUIDE_GENESIS): Pass Accuracy +0.060, Checking +0.042, Agility +0.033,
  Speed +0.026, Shot Power +0.013, Shot Accuracy +0.009, Weight -0.022, Off. Awareness -0.018, Stickhandling -0.010.
  What a defenceman's ratings do to goals against has not been measured, so this is his offence only.
- The SNES: its own steps (SYSTEMS), and a skater at Stickhandling 3 or less loses 0.028 (the catching cutoff, below).
- Goalies: save % +2.25 points per Agility step (PLAYER_GUIDE_GENESIS), times the shots a goalie faces a game in these
  leagues: goals saved a game; Puck Control and the rest left at 0 (RATING_VALUES: little or nothing).
Each position's weighted sum is put on 40-99 across its retail players (the lowest 40, the highest 99).

The check: each Classic team's strength (COACH_RATING section 9, "Strength now", win chance against an average team
with the coaches taken out), against (a) the team's league value (its regular forwards and defencemen, weighted by
their games, and its most-used goalie) and (b) the same built from the game's Overall. A least-squares fit of strength
on the three parts (forwards, defencemen, goalie) each way, and how much of the teams' spread each explains.

Reads the ROM (the retail Genesis rosters), reports/classic_players.json (classic_player_guide.py: games and
positions; aggregates of the leagues' results, no person named) and docs/COACH_RATING.md. Prints tables for
RATING_VALUES.md, and a team rating from the top players only (top 4 forwards, top 3 defencemen, the best goalie).
python analysis/league_value.py [genesis|snes] [both|nobands]   (by default the scoring weights and the
defencemen's Weight bands, which need defence_weight_bands.py SYSTEM --teams first; both: the both-ends weights (they
overfit the teams: RATING_VALUES "Defence"); nobands: without the bands)   (the SNES: its own steps, ROM and team strengths)"""
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
                 gsv=0.0031, rom="cd85e387.smc", key="SNES", col=1, team_weight=False,
                 stk_step=0.028),
}
# The SNES catching cutoff (RATING_VALUES "SNES catching follows the game's hot / cold roll", 2026-11-11): a skater at
# Stickhandling 3 or less bobbles about 7.8% of the passes reaching him over a season (12% in the 54% of games his roll
# doesn't max it, 3% otherwise) against about 3% at 4+: 0.40 more bobbles a game on 8.3 passes; a bobble gives the other
# team the puck 35% of the time, a swing of about 0.2 goals (0.10 a possession each way): about 0.028 goals a game,
# taken off his value as one step (the linear Stickhandling weight stays). The team test can't size it on the SNES.
STK_STEP = 0
BOTH = None          # defencemen's Weight band effects (modes both and bands)
FULL = False         # mode both: the forwards' Weight inside their fitted weights (not the team fit's)


def shrink(est, se):
    """A noisy estimate shrunk by how well it is measured: est x t^2 / (1 + t^2), t = est / se."""
    t2 = (est / se) ** 2 if se > 0 else 0.0
    return est * t2 / (1 + t2)


def d_band(a):
    """The defencemen's Weight band's worth (both-ends value): middleweight 7-9, heavy 10+, light the baseline."""
    if not BOTH:
        return 0.0
    return BOTH["mid"] if 7 <= a[0] <= 9 else BOTH["heavy"] if a[0] >= 10 else 0.0
DEF = {12: 0.060, 6: 0.042, 1: 0.033, 2: 0.026, 5: 0.013, 9: 0.009, 0: -0.022, 3: -0.018, 8: -0.010}
GOALIE_SV_STEP = 0.0225


def forward_counts(system, rom_path):
    """Each team's forward count, from its team record (the byte after the three team bytes: forwards in the high
    nibble, defencemen in the low; NOSE4Web's team.ts / snesteam.ts). A roster lists its goalies, then its forwards,
    then its defencemen."""
    import struct
    if system == "genesis":
        data = rom_path.read_bytes()
        out = []
        for k in range(genesis.team_count(data)):
            team = struct.unpack_from(">I", data, genesis.TEAM_TABLE + 4 * k)[0]
            out.append(data[team + 0x4C + 3] >> 4)
        return out
    from systems import snes
    from systems.snes_layout import layout
    data = snes.strip_header(rom_path.read_bytes())
    lay = layout(data)
    tl = lay.team_list or snes.TEAM_LIST
    out = []
    for k in range(lay.team_count or 28):
        ptr = data[snes.file_offset(tl) + 4 * k:snes.file_offset(tl) + 4 * k + 3]
        team = snes.file_offset(ptr[0] | ptr[1] << 8 | ptr[2] << 16)
        out.append(data[team + 0x0E + 3] >> 4)
    return out


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
                         f=avg(F, lambda p: sum(v * p["a"][i] for i, v in FWD.items() if i != 0 or FULL)
                               - (STK_STEP if p["a"][8] <= 3 else 0)),
                         d=avg(D, lambda p: sum(v * p["a"][i] for i, v in DEF.items()) - (STK_STEP if p["a"][8] <= 3 else 0)
                               + d_band(p["a"])),
                         g=GOALIE_SV_STEP * g["a"][1] * shots_per_game, fw=avg(F, lambda p: p["a"][0]),
                         fovr=avg(F, lambda p: p["ovr"]), dovr=avg(D, lambda p: p["ovr"]), govr=g["ovr"], goalie=g["name"]))
    return rows


def main():
    global WEIGHT, GOALIE_SV_STEP, STK_STEP, BOTH, FULL
    system = sys.argv[1] if len(sys.argv) > 1 else "genesis"
    both = "both" in sys.argv[2:]
    bands = not both and "nobands" not in sys.argv[2:]     # the defencemen's Weight bands: in the value by default
    cfg = SYSTEMS[system]
    FWD.clear()
    FWD.update(cfg["fwd"])
    DEF.clear()
    DEF.update(cfg["dfn"])
    if both:
        # every rating's total at both ends (goals for plus goals against cut, a player's roster step: defence_value's
        # fit with the defencemen's Weight in bands, defence_weight_bands.py), each shrunk by how well it is measured
        be = json.loads((ROOT / "reports" / f"both_ends_{system}.json").read_text())
        FWD.clear()
        FWD.update({int(k): shrink(*v) for k, v in be["F"].items()})
        DEF.clear()
        DEF.update({int(k): shrink(*v) for k, v in be["D"].items()})
        BOTH = {k: shrink(*v) for k, v in be["bands"].items()}
        print("both ends: forwards " + ", ".join(f"{k}:{v:+.3f}" for k, v in sorted(FWD.items())) + "; defencemen "
              + ", ".join(f"{k}:{v:+.3f}" for k, v in sorted(DEF.items())) + f"; bands middle {BOTH['mid']:+.3f}, heavy "
              f"{BOTH['heavy']:+.3f}")
    GOALIE_SV_STEP = cfg["gsv"]
    STK_STEP = cfg.get("stk_step", 0)
    FULL = both
    if bands:
        # the scoring weights kept, and the defencemen's Weight band added (the fit with team fixed effects too, so it
        # is measured by lineup choices within a team: defence_weight_bands.py --teams), shrunk by how well measured
        be = json.loads((ROOT / "reports" / f"both_ends_{system}_teams.json").read_text())
        BOTH = {k: shrink(*v) for k, v in be["bands"].items()}
        print(f"defencemen's Weight bands (within teams): middle {BOTH['mid']:+.3f}, heavy {BOTH['heavy']:+.3f} goals a game")
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
    if not both:
        FWD[0] = WEIGHT

    print(f"forwards' Weight in the team fit: {beta[3]:+.2f} win-chance points a Weight point of the team's average forward"
          + (f", = {WEIGHT:+.2f} goals a game of a forward's value (his own scoring alone: {cfg['fwd'][0]:+.2f})"
             if cfg["team_weight"] else f"; the value keeps his own scoring's {WEIGHT:+.2f}"))
    raw = {"F": {}, "D": {}, "G": {}}
    info = {}
    nfwd = forward_counts(system, rom(cfg["rom"]))
    for ti, t in enumerate(teams):
        ab = t["abbr"]
        if ab in ("ASE", "ASW"):                # the All-Star teams: their players are on their own teams too
            continue
        skater_no = 0
        for p in t["players"]:
            key = (ab, p["name"])
            a = p["a"]
            if p["g"]:
                raw["G"][key] = GOALIE_SV_STEP * a[1] * shots_per_game
                info[key] = dict(pos="G", ovr=p["ovr"], games=gs.get((ab, p["name"].lower()), {}).get("games", 0), a=a)
                continue
            s = pos.get((ab, p["name"].lower()))
            ps = "F" if skater_no < nfwd[ti] else "D"           # the roster's order: goalies, forwards, defencemen
            skater_no += 1
            w = FWD if ps == "F" else DEF
            raw[ps][key] = sum(v * a[i] for i, v in w.items()) - (STK_STEP if a[8] <= 3 else 0) +                 (d_band(a) if ps == "D" else 0)
            info[key] = dict(pos=ps, ovr=p["ovr"], games=s["n"] if s else 0, a=a)
    lv = {}
    for ps in raw:
        lv.update(scale(raw[ps]))
        print(f"scale ends, {ps}: {min(raw[ps].values()):.3f} to {max(raw[ps].values()):.3f}")
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
    (ROOT / "reports" / f"league_value_{system}{'_both' if both else '' if bands else '_nobands'}.json").write_text(json.dumps(out))
    top_players_rating(lv, info, strength, system)


def top_players_rating(lv, info, strength, system):
    """A team rating from its top players only (2026-11-11, the user: line changes off, only the top skaters and the #1
    goalie play): the average league value of its top 4 forwards and top 3 defencemen, and its best goalie's, weighted
    by a fit of the Classic teams' strength on the three (win-chance points against an average team a value point),
    the weights scaled to add up to 1, so the rating is on the players' 0-99 scale."""
    by = defaultdict(lambda: {"F": [], "D": [], "G": []})
    for (ab, name), v in lv.items():
        by[ab][info[(ab, name)]["pos"]].append(v)
    parts = {a: [float(np.mean(sorted(d["F"], reverse=True)[:4])), float(np.mean(sorted(d["D"], reverse=True)[:3])),
                 float(max(d["G"]))] for a, d in by.items() if d["F"] and d["D"] and d["G"]}
    teams = [a for a in parts if a in strength]
    X, y = [parts[a] for a in teams], np.array([strength[a] for a in teams])
    beta, _, r2, loo = loo_fit(X, y)
    A = np.column_stack([np.array(X, float), np.ones(len(X))])
    rng = np.random.default_rng(1)
    shares = []
    for _ in range(4000):
        ix = rng.integers(0, len(y), len(y))
        b, *_ = np.linalg.lstsq(A[ix], y[ix], rcond=None)
        shares.append(b[:3] / b[:3].sum())
    lo, hi = np.percentile(np.array(shares), [10, 90], axis=0)
    w = beta[:3] / beta[:3].sum()
    print(f"\nTop players' team rating (top 4 forwards, top 3 defencemen, top goalie): Classic teams' strength explained "
          f"R^2 {r2:.2f}, left one team out {loo:.2f}; win-chance points a value point F {beta[0]:.2f}, D {beta[1]:.2f}, "
          f"G {beta[2]:.2f}; weights F {w[0]:.2f} ({lo[0]:.2f} to {hi[0]:.2f}), D {w[1]:.2f} ({lo[1]:.2f} to {hi[1]:.2f}), "
          f"G {w[2]:.2f} ({lo[2]:.2f} to {hi[2]:.2f}) (middle 80% over resampled teams)")
    print("| Team | Top-players rating | Top 4 F | Top 3 D | Top G | Strength |")
    print("|---|---|---|---|---|---|")
    for a in sorted(parts, key=lambda a: -float(np.array(parts[a]) @ w)):
        f, d, g = parts[a]
        st = f"{strength[a]:+.1f}" if a in strength else "-"
        print(f"| {a} | {float(np.array(parts[a]) @ w):.1f} | {f:.1f} | {d:.1f} | {g:.0f} | {st} |")


if __name__ == "__main__":
    main()
