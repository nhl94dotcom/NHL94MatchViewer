"""The viewer's xG model (tools/xg.py play_out) for the scoring map's shots, against a set goalie at his spot for that
puck, with the map's goalie (Los Angeles: weight 48, Agility 13, Speed 13, Defensive Awareness 10 working) and
shooter (Shot Accuracy 15): python compare_xg.py RUN [GOALIES.json] -> paths.RUNS / RUN / compare.json
With GOALIES.json (xg.goalie_states' output, as map_run.py's 7th argument; 2026-11-07) each try's goalie starts off
his spot and moving as a recorded computer goalie was, mirrored for the bottom net: the "as in games" map."""
import glob
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg  # noqa: E402
from paths import RUNS  # noqa: E402

run = RUNS / sys.argv[1]
rows = [json.loads(l) for f in glob.glob(f"{run}/w*.jsonl") for l in open(f)]
try:
    VALID = json.load(open(run / "validity.json"))
    rows = [r for r in rows if VALID.get(f"{r['net']},{r['hold']},{r['x']},{r['y']}", {"ok": True})["ok"]]
except FileNotFoundError:
    pass
GOALIES = json.load(open(sys.argv[2]))["cpu"] if len(sys.argv) > 2 else None
out = []
for r in rows:
    if not r["aims"]:
        continue
    top = r["net"] == "top"
    sg = 1 if top else -1
    px, py = r["x"], sg * r["y"]
    d3c = 260 * sg
    rx, ry = px, max(-259, min(259, py)) - d3c
    if rx * rx + ry * ry > 900:
        ln = math.isqrt(int(rx * rx + ry * ry)) + 1
        rx, ry = rx * 26 / ln, ry * 18 / ln
    g = xg.Goalie(rx, ry + d3c, 0, 0, 48, 13, 13, 10)
    reach = xg.REACH[(13 + 2) >> 1]
    for a in r["aims"]:
        tx, tz = xg.AIM[a["aim"]]
        rng = random.Random(f"{r['net']}{r['hold']}{r['x']}{r['y']}{a['aim']}")
        n = 600
        goals = 0
        for _ in range(n):
            gg = g
            if GOALIES:
                dx, dy, vx, vy = (sg * v for v in GOALIES[rng.randrange(len(GOALIES))])
                gg = xg.Goalie(rx + dx, ry + d3c + dy, vx * 4096, vy * 4096, 48, 13, 13, 10)
            goals += xg.play_out((px, py, 0), (tx, 264 * sg, tz), r["pout"], 15, (15 + 1) / (15 + 16), gg, reach, 0,
                                 rng) == "goal"
        out.append(dict(net=r["net"], hold=r["hold"], x=r["x"], y=r["y"], aim=a["aim"], game=a["chance"],
                        se=a["se"], model=goals / n, stack=r["stack"] / max(1, r["phases"])))
json.dump(out, open(run / "compare.json", "w"))
print(len(out))
