"""Easy goals: how the low-chance goals go in (2026-11-08; docs/GAME_VARIABLES_PLAN.md study 6: "the goalie letting in
easy goals").

The recorded games (both systems): every goal, matched to its shot (the shot list's goal by the same team within 2 s
before it), and those with low expected goals (under 0.1) or none (deflections and scrambles, which the models don't
price) sorted by what the recording shows: the goal's own tags (through the legs, the top net's shoulder-save bobble,
an own goal, an EA Special, a wraparound ...), a rebound, the goalie 5+ ft off the shot line at the release, a person
in net, the shot's kind and range. Also how many goals each band of expected goals gave against what it said.

python analysis/easy_goals.py"""
import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from share_game import load_js_object  # noqa: E402

HOME = Path(os.environ.get("NHL94_HOME") or Path.home() / "Documents" / "NHL94 Viewer")
BANDS = [(0, 0.1), (0.1, 0.3), (0.3, 0.6), (0.6, 2)]


def main():
    tags = defaultdict(Counter)
    totals = defaultdict(Counter)
    bands = defaultdict(lambda: [[0, 0.0, 0] for _ in BANDS])
    for p in sorted((HOME / "matches").glob("*.js")):
        if p.stem == "season" or p.stem.endswith(".heat") or not (HOME / "captures" / p.stem).is_dir():
            continue
        m = json.loads(load_js_object(p))
        sysn = m.get("system", "genesis")
        t = m["t"]
        shots = [s for s in m.get("shotList", []) if s.get("team") in (0, 1)]
        for s in shots:
            if s.get("xg") is not None and s["result"] != "blocked":
                for i, (lo, hi) in enumerate(BANDS):
                    if lo <= s["xg"] < hi:
                        b = bands[sysn][i]
                        b[0] += s["result"] == "goal"
                        b[1] += s["xg"]
                        b[2] += 1
        for g in m.get("goals", []):
            totals[sysn]["goals"] += 1
            sh = min((s for s in shots if s["team"] == g["team"] and s["result"] == "goal" and 0 <= t[g["f"]] - t[s["f"]] <= 2000),
                     key=lambda s: t[g["f"]] - t[s["f"]], default=None)
            x = sh.get("xg") if sh else None
            if x is not None and x >= 0.1:
                continue
            totals[sysn]["easy (under 0.1 xG, or none)"] += 1
            tg = tags[sysn]
            tg["no shot found / scramble" if sh is None else f"kind: {sh['kind']}" if x is None else "a priced shot under 0.1"] += 1
            for k in g.get("kinds", []):
                tg[f"tag: {k}"] += 1
            if sh:
                if sh.get("rebound"):
                    tg["off a rebound"] += 1
                if sh.get("gOff") is not None and sh["gOff"] >= 15:
                    tg["goalie 5+ ft off the line"] += 1
                if sh.get("gctl") == "human":
                    tg["a person in net"] += 1
                ny = 264 if sh["y"] > 0 else -264
                d = math.hypot(sh["x"], ny - sh["y"])
                tg["from 40 ft (120) or more" if d >= 120 else "within 40 ft"] += 1
    for sysn in sorted(totals):
        print(f"{sysn.upper()}: {totals[sysn]['goals']} goals; {totals[sysn]['easy (under 0.1 xG, or none)']} under 0.1 xG or unpriced")
        for k, v in tags[sysn].most_common():
            print(f"   {v:4d}  {k}")
        print("   by band (goals / expected / attempts): " + "; ".join(
            f"{lo}-{hi if hi < 2 else '1'}: {b[0]} / {b[1]:.1f} / {b[2]}" for (lo, hi), b in zip(BANDS, bands[sysn])))


if __name__ == "__main__":
    main()
