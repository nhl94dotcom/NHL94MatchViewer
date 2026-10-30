"""Goalie ratings and save percentage in the leagues' own results (2026-10-30). The Classic leagues play the retail
rosters, so each goalie's ratings can be read from the ROM (Genesis nhl94.bin, SNES NHL94_Classic: roms/ or the
Documents folder's roms/) and set beside his save percentage over every Classic league game in the user's databases
(%USERPROFILE%\\NHL94_League_Data, outside the repository; goalie lines: number, name, goals against, saves, shots
against, ...). Prints aggregates only. The mechanics say a Genesis goalie's Agility is his reach (GENESIS_SHOOTING
5.1) and every SNES goalie is the same size (SNES_SHOOTING 5.1).
python analysis/league_goalie_study.py"""
import ast
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from systems import genesis, snes  # noqa: E402

DATA = Path.home() / "NHL94_League_Data"
ROMS = [Path(__file__).resolve().parents[1] / "roms", Path.home() / "Documents" / "NHL94 Viewer" / "roms"]
RATINGS = ("Weight", "Agility", "Speed", "Off. Awareness", "Def. Awareness", "Puck Control")


def rom(name):
    return next(d / name for d in ROMS if (d / name).exists())


def goalie_ratings(teams):
    return {p["name"].lower(): p["a"][:6] for t in teams for p in t["players"] if p["g"]}


def study(csv_name, label, ratings):
    tally = defaultdict(lambda: [0, 0])                  # goals against, shots against
    csv.field_size_limit(10 ** 9)
    with open(DATA / csv_name, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("sim") == "1" or "classic" not in r["League"].lower():
                continue
            for col in ("HomeGoalies", "AwayGoalies"):
                try:
                    lines = ast.literal_eval(r[col]) if r[col] else []
                except (ValueError, SyntaxError):
                    continue
                for g in lines:
                    name = str(g[1]).lower()
                    if name in ratings and g[4] > 0:
                        tally[name][0] += g[2]
                        tally[name][1] += g[4]
    rows = [(ratings[n], 1 - ga / sa, sa) for n, (ga, sa) in tally.items() if sa >= 400]
    print(f"\n{label} Classic leagues: {len(rows)} goalies with 400+ shots against, {sum(r[2] for r in rows)} shots")
    by = defaultdict(lambda: [0.0, 0])
    for rt, sv, sa in rows:
        by[rt[1]][0] += sv * sa
        by[rt[1]][1] += sa
    print("  save % by Agility: " + ", ".join(f"{k}: {100 * v[0] / v[1]:.1f}" for k, v in sorted(by.items())))
    for i, name in enumerate(RATINGS):
        xs, ys, ws = [r[0][i] for r in rows], [r[1] for r in rows], [r[2] for r in rows]
        W = sum(ws)
        mx, my = sum(x * w for x, w in zip(xs, ws)) / W, sum(y * w for y, w in zip(ys, ws)) / W
        cov = sum(w * (x - mx) * (y - my) for x, y, w in zip(xs, ys, ws))
        vx, vy = sum(w * (x - mx) ** 2 for x, w in zip(xs, ws)), sum(w * (y - my) ** 2 for y, w in zip(ys, ws))
        if vx and vy:
            print(f"  {name:15}: correlation {cov / math.sqrt(vx * vy):+.2f}, {100 * cov / vx:+.2f} save-% points a step")


def main():
    study("All_Games_GENS.csv", "GENESIS", goalie_ratings(genesis.read_teams(rom("9438f5dd_a738ea1c.bin"))))
    study("All_Games_SNES.csv", "SNES", goalie_ratings(snes.read_teams(rom("cd85e387.smc"))))


if __name__ == "__main__":
    main()
