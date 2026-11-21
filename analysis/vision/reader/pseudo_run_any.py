"""Build the pseudo match from read_<first>.json and compare its events with game 1's recorded file.
python pseudo_run.py read_6200.json [read_17000.json ...]"""
import json
import os
TEST_GAME = int(os.environ.get('TEST_GAME', 0))   # the game read; everything learnt comes from the others
import sys
from pathlib import Path

import numpy as np

V = Path(__file__).resolve().parents[3]          # the repository
sys.path.insert(0, str(V / "analysis/vision"))
sys.path.insert(0, str(V / "tools"))
import pseudo_match as PM
import replay_pack

HOME = Path.home() / "Documents/NHL94 Viewer"
VIDEO = Path(os.environ.get("NHL94_INV_VIDEO", HOME / "replay/nhl94_playoffs-261113-133619.mkv"))
ROMP = Path(os.environ.get("NHL94_INV_ROM", HOME / "roms/7a7a876f_a738ea1c.bin"))
tl = json.loads(Path(os.environ.get("NHL94_INV_TIMELINE", str(VIDEO) + ".timeline.json")).read_text())
FPS = tl["fps"]


def load(n):
    s = (HOME / "matches" / f"{n}.js").read_text()
    return json.loads(s[s.index("{"):s.rindex("}") + 1])


m = load(tl["games"][TEST_GAME])
N = len(m["t"])
vf = np.full(N, np.nan)
for sg in tl["segments"]:
    if sg[2] != TEST_GAME:
        continue
    for q in range(N):
        v = sg[0] + (m["t"][q] - sg[3]) * (1 + replay_pack.rate(sg)) / 1000
        if sg[0] <= v <= sg[1]:
            vf[q] = v * FPS
POOL = [g for g in os.environ.get("NHL94_INV_TRANS_GAMES", "").split(",") if g]
maps_path = Path(os.environ["NHL94_INV_MAPS"]) if os.environ.get("NHL94_INV_MAPS") else Path("pseudo_maps.json" if TEST_GAME == 0 else f"pseudo_maps_g{TEST_GAME}.json")
if maps_path.exists():
    mp = json.loads(maps_path.read_text())
    maps = dict(anim={int(k): v for k, v in mp["anim"].items()}, facing={int(k): v for k, v in mp["facing"].items()}, goalie=set(mp["goalie"]))
else:
    maps = PM.learn_maps([load(n) for n in POOL] if POOL else [load(n) for i, n in enumerate(tl["games"]) if i != TEST_GAME])
    maps_path.write_text(json.dumps(dict(anim=maps["anim"], facing=maps["facing"], goalie=sorted(maps["goalie"]))))
total = {}
for path in sys.argv[1:]:
    rows = json.loads(Path(path).read_text())
    fis = [r["fi"] for r in rows]
    qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
    q0, q1 = int(qs[0]), int(qs[-1]) + 1
    truth = PM.analyse(PM.slice_match(m, q0, q1), str(ROMP))
    read = PM.analyse(PM.build(m, vf, rows, maps, q0, q1), str(ROMP))
    res = PM.compare(truth, read)
    print(path, f"samples {q0}-{q1} ({(m['t'][q1 - 1] - m['t'][q0]) / 1000:.0f} s real)")
    for k, v in res.items():
        print("  ", k, v)
        for kk, vv in v.items():
            total.setdefault(k, {}).setdefault(kk, 0)
            total[k][kk] += vv
    Path(path.replace(".json", "_events.json")).write_text(json.dumps({k: dict(recorded=truth.get(k), read=read.get(k))
                                                                        for k in ("shotList", "passes", "turnovers", "hits")}, default=str))
print("total", json.dumps(total))
