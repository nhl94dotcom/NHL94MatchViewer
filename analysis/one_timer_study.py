"""Which one-timers score: the pass that set each up (how far across it moved the puck, whether it crossed the middle,
its length and time in the air), the goalie (how far he had to slide across while it travelled, how far off the line
from the puck to his net he was at the strike), where it was struck, and the result. Both systems.
python analysis/one_timer_study.py"""
import glob
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, "tools")
from share_game import load_js_object  # noqa: E402
from export_match import own_end  # noqa: E402

K = 12


def goalie_at(m, f, team):
    """(x, y) of the goalie of `team` at sample f, or None."""
    for k in range(team * 6, team * 6 + 6):
        if m["role"][f * K + k] == "0":
            return m["pos"][(f * K + k) * 2], m["pos"][(f * K + k) * 2 + 1]
    return None


def off_line(px, py, gx, gy, net_y):
    """How far the goalie stands from the line between the puck and the middle of his net."""
    dx, dy = 0 - px, net_y - py
    n = math.hypot(dx, dy) or 1
    return abs((gx - px) * dy - (gy - py) * dx) / n


rows = []
files = {}
for p in glob.glob("matches/*.js") + glob.glob(r"C:/Users/USER/Documents/NHL94 Viewer/matches/*.js"):
    if not p.endswith(".summary.json") and Path(p).name not in ("season.js", "shot_study.json"):
        files.setdefault(Path(p).name, p)
for name, p in sorted(files.items()):
    try:
        m = json.loads(load_js_object(Path(p)))
    except Exception:
        continue
    if "shotList" not in m or "passes" not in m:
        continue
    t = m["t"]
    sy = m.get("system", "genesis")
    for sh in m["shotList"]:
        if sh["kind"] != "one-timer":
            continue
        team, f = sh["team"], sh["f"]
        cands = [q for q in m["passes"] if q["team"] == team and q["f"] < f and t[f] - t[q["f"]] < 2500 and q.get("result") in ("one-timer", "completed")]
        if not cands:
            continue
        ps = max(cands, key=lambda q: q["f"])
        end = own_end(m, f, team)
        if end is None:
            continue
        net_y = -264 * end  # the net attacked
        g0, g1 = goalie_at(m, ps["f"], 1 - team), goalie_at(m, f, 1 - team)
        if not g0 or not g1:
            continue
        rows.append({
            "system": sy, "result": sh["result"], "xg": sh.get("xg"),
            "across": abs(sh["x"] - ps["x0"]), "crossed": (ps["x0"] > 15 and sh["x"] < -15) or (ps["x0"] < -15 and sh["x"] > 15),
            "length": math.hypot(sh["x"] - ps["x0"], sh["y"] - ps["y0"]), "air_ms": t[f] - t[ps["f"]],
            "goalie_slide": abs(g1[0] - g0[0]), "goalie_off": off_line(sh["x"], sh["y"], g1[0], g1[1], net_y),
            "dist": math.hypot(sh["x"], net_y - sh["y"]), "gctl": sh.get("gctl"),
        })


def show(label, sel):
    n = len(sel)
    if not n:
        return
    g = sum(r["result"] == "goal" for r in sel)
    xs = [r["xg"] for r in sel if r["xg"] is not None]
    print(f"  {label:34} {n:4}  goals {g:3} ({100 * g / n:3.0f}%)" + (f"  xG {100 * sum(xs) / len(xs):3.0f}% a shot" if xs else ""))


for sy in ("genesis", "snes"):
    S = [r for r in rows if r["system"] == sy]
    print(f"\n== {sy.upper()}: {len(S)} one-timers with their pass")
    print(" The pass:")
    show("crossed the middle", [r for r in S if r["crossed"]])
    show("stayed on one side", [r for r in S if not r["crossed"]])
    for lo, hi in ((0, 40), (40, 90), (90, 300)):
        show(f"moved the puck {lo}-{hi} across", [r for r in S if lo <= r["across"] < hi])
    for lo, hi in ((0, 500), (500, 900), (900, 3000)):
        show(f"in the air {lo}-{hi} ms", [r for r in S if lo <= r["air_ms"] < hi])
    print(" The goalie:")
    for lo, hi in ((0, 15), (15, 40), (40, 300)):
        show(f"slid {lo}-{hi} across during the pass", [r for r in S if lo <= r["goalie_slide"] < hi])
    for lo, hi in ((0, 4), (4, 10), (10, 300)):
        show(f"{lo}-{hi} off the puck's line at the strike", [r for r in S if lo <= r["goalie_off"] < hi])
    show("a person in net", [r for r in S if r["gctl"] == "human"])
    show("the computer in net", [r for r in S if r["gctl"] == "cpu"])
    print(" Where it was struck:")
    for lo, hi in ((0, 60), (60, 100), (100, 400)):
        show(f"{lo}-{hi} from the net", [r for r in S if lo <= r["dist"] < hi])
