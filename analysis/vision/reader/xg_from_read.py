"""xG from a video read (2026-11-22, the fresh look's option 2: does the reader already see enough to rate shots?).
The pseudo match of a read (pseudo_run_any's set-up) has each found shot's spot, the puck's speed and the goalie's
position, frame and controller, but not what the xG model also takes from memory: the working ratings and the aim.
Here those come from what a video's viewer can know:
- ratings: each team's skaters get their team's mean working ratings (the shooter isn't identified), the goalie his
  own (the starters are on the matchup screen; the recording's first rows stand in for the ROM's roster x 5);
- a person's aim: the side (left, middle, right) from the puck's flight after the release where it crosses the goal
  line, the height not seen: the xG averaged over the three heights by how often people use each (the 1,308 recorded
  launches: sides high 30%, middle 68%, low 2%; the middle column high 45%, mid 27%, low 27%).
Then tools/xg.py as the converter runs it. Against the recording's own xG: the matched shots (same team within 0.5 s)
one by one, and each team's total over all the shots read.

python xg_from_read.py READ.json   (NHL94_INV_* and TEST_GAME as pseudo_run_any.py)"""
import copy
import json
import sys
from pathlib import Path

import numpy as np

path = sys.argv[1]
src = Path(__file__).with_name("pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
sys.argv = [sys.argv[0], path]
exec(src)
import xg as XG  # noqa: E402

rows = json.loads(Path(path).read_text())
fis = [r["fi"] for r in rows]
qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
q0, q1 = int(qs[0]), int(qs[-1]) + 1
tm = PM.slice_match(m, q0, q1)
truth = PM.analyse(tm, str(ROMP))
pm = PM.build(m, vf, rows, maps, q0, q1)
read = PM.analyse(pm, str(ROMP))

# ratings a viewer can know: team means for skaters, the goalie's own
first = {}
for r in tm.get("work", []):
    first.setdefault(r[1], r[2:])
role0 = tm["role"][:12]
work = []
for team in (0, 1):
    sk = [first[k] for k in range(team * 6, team * 6 + 6) if k in first and role0[k] not in "0x"]
    mean = [round(sum(c) / len(c)) for c in zip(*sk)] if sk else [64, 15, 15, 15, 15, 15]
    g = next((first[k] for k in range(team * 6, team * 6 + 6) if k in first and role0[k] == "0"), None)
    for k in range(team * 6, team * 6 + 6):
        work.append([0, k, *(mean)])
    read.setdefault("_goalie_row", {})[team] = g
# the goalie's record can be any of the team's six in a read: his own row wherever role is '0' at the shot
read["work"] = work
HEIGHTS = {1: [(1, .30), (2, .68), (3, .02)], -1: [(7, .30), (6, .68), (5, .02)], 0: [(0, .45), (8, .27), (4, .27)]}
rom_bytes = ROMP.read_bytes()
out = []
for sh in read.get("shotList", []):
    if sh["kind"] not in ("shot", "one-timer", "pass shot") or sh.get("team") not in (0, 1):
        continue
    f, team = sh["f"], sh["team"]
    gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if read["role"][f * 12 + k] == "0"), None)
    grow = read["_goalie_row"].get(1 - team)
    w2 = [r for r in work if not (gk is not None and r[1] == gk)]
    if gk is not None and grow:
        w2.append([0, gk, *grow])
    side = 0
    la = XG.launched(read, f)
    if la:
        gl = 264 if XG.attacks_top(read, f, team) else -264
        px, py = read["puck"][3 * f], read["puck"][3 * f + 1]
        if la[1] and (gl - py) / la[1] > 0:
            cx = px + la[0] * (gl - py) / la[1]
            side = 1 if cx > 8 else -1 if cx < -8 else 0
    tot = 0.0
    for d, wgt in HEIGHTS[side]:
        one = copy.deepcopy(sh)
        one.pop("xg", None)
        one["aim"] = {"d": d}
        mm = dict(read, work=sorted(w2), shotList=[one])
        XG._CACHE.clear()
        XG.add_expected_goals(mm, stick_rom=rom_bytes, lock=True)
        tot += wgt * (one.get("xg") or 0.0)
    sh["xg_video"] = round(tot, 3)
    out.append(sh)

T = [s for s in truth.get("shotList", []) if s["kind"] in ("shot", "one-timer", "pass shot")]
used, pairs = set(), []
for s in T:
    ta = truth["t"][s["f"]]
    best = None
    for j, r in enumerate(out):
        if j in used or r["team"] != s["team"]:
            continue
        d = abs(read["t"][r["f"]] - ta)
        if d <= 500 and (best is None or d < best[0]):
            best = (d, j)
    if best:
        used.add(best[1])
        pairs.append((s, out[best[1]]))
name = Path(path).stem
print(f"{name}: recorded shots {len(T)}, read {len(out)}, matched {len(pairs)}")
if pairs:
    a = np.array([p[0].get("xg") or 0 for p in pairs]); b = np.array([p[1]["xg_video"] for p in pairs])
    print(f"  matched shots: recorded xG {a.sum():.2f}, from video {b.sum():.2f}; mean difference a shot {np.abs(a - b).mean():.3f}; "
          f"correlation {np.corrcoef(a, b)[0, 1]:.2f}; within 0.15: {int((np.abs(a - b) <= 0.15).sum())} of {len(a)}")
for team in (0, 1):
    rt = sum(s.get("xg") or 0 for s in T if s["team"] == team and s["result"] != "blocked")
    vt = sum(s["xg_video"] for s in out if s["team"] == team and s["result"] != "blocked")
    gl = sum(1 for s in T if s["team"] == team and s["result"] == "goal")
    print(f"  team {team}: recorded xG {rt:.2f}, from video {vt:.2f}, goals {gl}")
Path(path.replace(".json", "_xg.json")).write_text(json.dumps(
    [dict(rec=p[0].get("xg"), video=p[1]["xg_video"], team=p[0]["team"], kind=p[0]["kind"], result=p[0]["result"],
          gctl=p[0].get("gctl"), gctl_read=p[1].get("gctl"), gOff=p[0].get("gOff"), gOff_read=p[1].get("gOff")) for p in pairs]))
