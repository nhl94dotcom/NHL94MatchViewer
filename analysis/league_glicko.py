"""Glicko beside the league's Elo: which predicts the next game better, and how would the ratings behave? (2026-11-04, the user.) Aggregates only; nothing published depends on it.

Both play every game the league's Elo counts, in order, from 1500, with +7 for home and the team adjustments (reports/classic_team_elo.json, fitted on the Elo, which favours the Elo a little).
Glicko keeps an uncertainty RD for each coach: it starts high, falls with games and rises with time away. A big RD means the rating moves more, and a game between uncertain coaches is predicted
closer to even. One game counts as one rating period, so ratings change at once, as Elo's do. Settings: the starting RD, how fast it grows with time away, and a floor on it, which keeps a veteran's rating
able to move, like K. Each is tried with the league's coasting multiplier on a rating's change and with none. Settings are chosen only on decided games from 2016 to 2019; the test is decided games from 2020.
python analysis/league_glicko.py     prints the results and writes reports/league_glicko.json (git-ignored)"""
import json
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "scoring_map"))
import coach_rating as C  # noqa: E402
import league_team_elo as E  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

Q = math.log(10) / 400
GROW, FLOORS, STARTS = (1.0, 2.0, 3.0, 5.0, 8.0), (0.0, 30.0, 50.0, 75.0, 100.0), (250.0, 350.0)
TRAIN, TEST = date(2016, 1, 1).toordinal(), date(2020, 1, 1).toordinal()
HOME, START, K, MIN_SEEN = 7, 1500.0, 20, 30


def g(rd):
    return 1 / math.sqrt(1 + 3 * Q * Q * rd * rd / (math.pi * math.pi))


def results():
    return {"x": [], "won": [], "day": [], "classic": [], "new": []}


def note(out, gap_scaled, s, game, seen):
    if s != 0.5:
        out["x"].append(gap_scaled * math.log(10) / 400)
        out["won"].append(s)
        out["day"].append(game["day"])
        out["classic"].append(game["classic"])
        out["new"].append(seen[game["hp"]] < MIN_SEEN or seen[game["ap"]] < MIN_SEEN)


def run_elo(games, table):
    R = defaultdict(lambda: START)
    seen = defaultdict(int)
    out, moves = results(), []
    for gm in games:
        gap = R[gm["hp"]] - R[gm["ap"]] + HOME + (table.get(gm["ht"], 0) - table.get(gm["at"], 0) if gm["wide"] else 0)
        p = 1 / (1 + 10 ** (-gap / 400))
        s = 1.0 if gm["hs"] > gm["as"] else 0.0 if gm["hs"] < gm["as"] else 0.5
        note(out, gap, s, gm, seen)
        d = K * (1 + gm["coast"]) * (s - p)
        moves.append((abs(d), seen[gm["hp"]] < MIN_SEEN, seen[gm["hp"]] >= 300))
        R[gm["hp"]] += d
        R[gm["ap"]] -= d
        seen[gm["hp"]] += 1
        seen[gm["ap"]] += 1
    return out, moves, R, seen, None


def run_glicko(games, table, grow, floor, start, bonus):
    R = defaultdict(lambda: START)
    RD = defaultdict(lambda: start)
    last = {}
    seen = defaultdict(int)
    out, moves = results(), []
    for gm in games:
        hp, ap = gm["hp"], gm["ap"]
        for who in (hp, ap):
            if who in last:
                RD[who] = min(start, math.sqrt(RD[who] ** 2 + grow * grow * (gm["day"] - last[who])))
            last[who] = gm["day"]
        gap = R[hp] - R[ap] + HOME + (table.get(gm["ht"], 0) - table.get(gm["at"], 0) if gm["wide"] else 0)
        s = 1.0 if gm["hs"] > gm["as"] else 0.0 if gm["hs"] < gm["as"] else 0.5
        note(out, g(math.sqrt(RD[hp] ** 2 + RD[ap] ** 2)) * gap, s, gm, seen)
        extra = 1 + gm["coast"] if bonus else 1.0
        new = {}
        for who, other, sign, score in ((hp, ap, 1, s), (ap, hp, -1, 1 - s)):
            gj = g(RD[other])
            e = 1 / (1 + 10 ** (-gj * sign * gap / 400))
            precision = 1 / RD[who] ** 2 + Q * Q * gj * gj * e * (1 - e)
            new[who] = (R[who] + extra * (Q / precision) * gj * (score - e), max(floor, 1 / math.sqrt(precision)))
        moves.append((abs(new[hp][0] - R[hp]), seen[hp] < MIN_SEEN, seen[hp] >= 300))
        for who, (r, rd) in new.items():
            R[who], RD[who] = r, rd
        seen[hp] += 1
        seen[ap] += 1
    return out, moves, R, seen, RD


def arrays(out):
    return {k: np.array(v) for k, v in out.items()}


def losses(a):
    p = np.clip(1 / (1 + np.exp(-a["x"])), 1e-6, 1 - 1e-6)
    return -(a["won"] * np.log(p) + (1 - a["won"]) * np.log(1 - p))


def show(a, b, mask, text):
    d = losses(b)[mask] - losses(a)[mask]
    print(f"  {text} ({mask.sum()} games): Elo {losses(a)[mask].mean():.4f}, Glicko {losses(b)[mask].mean():.4f}; difference {d.mean():+.4f} +- {d.std() / len(d) ** .5:.4f}; rating gap worth Elo {C.scale_for(a['x'][mask], a['won'][mask]):.2f}, Glicko {C.scale_for(b['x'][mask], b['won'][mask]):.2f}", flush=True)
    return {"games": int(mask.sum()), "elo": float(losses(a)[mask].mean()), "glicko": float(losses(b)[mask].mean()), "diff": float(d.mean()), "se": float(d.std() / len(d) ** .5)}


def movement(moves, R, seen):
    m = np.array(moves, dtype=float)
    reg = np.array([R[p] for p, n in seen.items() if n >= 100])
    return {"typical": float(m[:, 0].mean()), "largest": float(m[:, 0].max()), "first_30": float(m[m[:, 1] == 1, 0].mean()), "after_300": float(m[m[:, 2] == 1, 0].mean()), "sd": float(reg.std()), "top": float(reg.max()), "median": float(np.median(reg))}


def main():
    gentle()
    tables = json.loads((Path(__file__).resolve().parents[1] / "reports" / "classic_team_elo.json").read_text(encoding="utf-8"))
    saved = {}
    for name, label in E.SYSTEMS:
        games = E.load_games(name)
        table = {t: v["adj"] for t, v in tables[label]["teams"].items()}
        elo, emoves, eR, seen, _ = run_elo(games, table)
        ea = arrays(elo)
        train = (ea["day"] >= TRAIN) & (ea["day"] < TEST)
        trials = []
        for start in STARTS:
            for grow in GROW:
                for floor in FLOORS:
                    for bonus in (True, False):
                        o = arrays(run_glicko(games, table, grow, floor, start, bonus)[0])
                        trials.append((float(losses(o)[train].mean()), start, grow, floor, bonus))
                        breathe()
        trials.sort()
        best = trials[0]
        print(f"\n{label}: {len(games)} games. Best settings on 2016-2019: start RD {best[1]:g}, growth {best[2]:g} a day^0.5, floor {best[3]:g}, bonus {best[4]}; {best[0]:.4f} there, Elo {losses(ea)[train].mean():.4f}. Next best: " + "; ".join(f"{t[0]:.4f} ({t[1]:g}, {t[2]:g}, {t[3]:g}, {t[4]})" for t in trials[1:4]), flush=True)
        go, gmoves, gR, _, RD = run_glicko(games, table, best[2], best[3], best[1], best[4])
        ga = arrays(go)
        test = ea["day"] >= TEST
        res = {"settings": best[1:], "train_elo": float(losses(ea)[train].mean()), "train_glicko": best[0]}
        res["classic_known"] = show(ea, ga, test & ea["classic"] & ~ea["new"], "From 2020, Classic, both coaches 30+ earlier games")
        res["all_known"] = show(ea, ga, test & ~ea["new"], "From 2020, all leagues, both coaches 30+ earlier games")
        res["new"] = show(ea, ga, test & ea["new"], "From 2020, a coach with under 30 earlier games")
        res["all"] = show(ea, ga, test, "From 2020, every decided game")
        res["elo_moves"], res["glicko_moves"] = movement(emoves, eR, seen), movement(gmoves, gR, seen)
        print(f"  Points a game: Elo {res['elo_moves']['typical']:.1f}, largest {res['elo_moves']['largest']:.1f}, a coach's first 30 games {res['elo_moves']['first_30']:.1f}, after 300 games {res['elo_moves']['after_300']:.1f}", flush=True)
        print(f"                 Glicko {res['glicko_moves']['typical']:.1f}, largest {res['glicko_moves']['largest']:.1f}, a coach's first 30 games {res['glicko_moves']['first_30']:.1f}, after 300 games {res['glicko_moves']['after_300']:.1f}", flush=True)
        print(f"  Coaches with 100+ games: spread Elo {res['elo_moves']['sd']:.0f}, Glicko {res['glicko_moves']['sd']:.0f}; highest {res['elo_moves']['top']:.0f}, {res['glicko_moves']['top']:.0f}; median {res['elo_moves']['median']:.0f}, {res['glicko_moves']['median']:.0f}", flush=True)
        reg = [p for p, n in seen.items() if n >= 100]
        x, y = np.array([eR[p] for p in reg]), np.array([gR[p] for p in reg])
        ra, rb = (-x).argsort().argsort(), (-y).argsort().argsort()
        res["rank_corr"] = float(np.corrcoef(ra, rb)[0, 1])
        rds = np.array([RD[p] for p in reg])
        print(f"  Order of coaches against Elo: correlation {res['rank_corr']:.3f}, typical move {np.abs(ra - rb).mean():.1f} places, largest {np.abs(ra - rb).max()}. RD now among them: median {np.median(rds):.0f}, from {rds.min():.0f} to {rds.max():.0f}", flush=True)
        saved[label] = res
    (Path(__file__).resolve().parents[1] / "reports" / "league_glicko.json").write_text(json.dumps(saved), encoding="utf-8")


if __name__ == "__main__":
    main()
