"""Does the video tell the game's story as the recording does? (2026-11-24)

For one read: the recording's slice and the video's pseudo match, both through the converter's analysis, and the
measures a match report rests on, per team, side by side: expected goals and the Deserve to Win meter (the video's
shots from swing_events.py test's READ_swingshots.json), shots, possession (share of carried samples), time in the
attacking zone (the puck past the blue line of the net a team attacks), passes and their completion, giveaways,
hits, zone entries. For each: the recording's two values, the video's two, and a verdict: the same side ahead by a
clear margin on both ("agrees"), ahead on one and level on the other ("weaker"), or opposite sides ("FLIPS").

Set-up as pseudo_run_any.py (NHL94_INV_*, TEST_GAME).  python story_compare.py READ.json [OUT.json]"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
read_path = sys.argv[1]
out_path = sys.argv[2] if len(sys.argv) > 2 else read_path.replace(".json", "_story.json")
g = {"__name__": "story", "__file__": str(HERE / "pseudo_run_any.py")}
src = (HERE / "pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
sys.argv = [sys.argv[0], read_path]
exec(src, g)
PM, m, vf, maps, ROMP = g["PM"], g["m"], g["vf"], g["maps"], g["ROMP"]
import numpy as np
import deserve as DZ
import swing_events as SE

rows = json.loads(Path(read_path).read_text())
fis = [r["fi"] for r in rows]
qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
q0, q1 = int(qs[0]), int(qs[-1]) + 1
tm = PM.analyse(PM.slice_match(m, q0, q1), str(ROMP))
pm = PM.analyse(PM.build(m, vf, rows, maps, q0, q1), str(ROMP))
# the recording's shots as the real match file has them (with its xG); the video's from the swing finder
tm["shotList"] = [dict(s, f=s["f"] - q0) for s in m.get("shotList", []) if q0 <= s["f"] < q1]
sw = json.loads(Path(read_path.replace(".json", "_swingshots.json")).read_text())
assert all("team" in p for p in sw["per"]), "run swing_events.py test again: its shots carry no team"
pm["shotList"] = [dict(f=min(len(pm["t"]) - 1, p["f"]), team=p["team"], xg=p["video"], kind=p["kind"], result="save") for p in sw["per"]]
BLUE = 88                                                   # the blue lines' |y| (rink units)


def measures(mm):
    n = len(mm["t"])
    live = [i for i in range(n) if mm["puck"][3 * i + 2] > -100]
    own = [mm["owner"][i] for i in live]
    car = [sum(1 for o in own if o >= 0 and o // 6 == t) for t in (0, 1)]
    zone = [0, 0]
    for i in live:
        y = mm["puck"][3 * i + 1]
        if abs(y) > BLUE:
            top0 = SE.attacks_top(mm, i, 0)
            zone[0 if (y > 0) == top0 else 1] += 1
    shots = [s for s in mm["shotList"] if s.get("kind") in ("shot", "one-timer") and s.get("team") in (0, 1)]
    unb = [s for s in shots if s.get("result") != "blocked"]
    P = mm.get("passes") or []
    d = DZ.deserve(dict(mm, shotList=unb))
    out = {
        "expected goals": [round(sum(s.get("xg") or 0 for s in unb if s["team"] == t), 2) for t in (0, 1)],
        "deserve to win %": [round(100 * d["win"][t]) for t in (0, 1)],
        "shots": [sum(s["team"] == t for s in shots) for t in (0, 1)],
        "dangerous shots (xG 0.3+)": [sum(s["team"] == t and (s.get("xg") or 0) >= 0.3 for s in unb) for t in (0, 1)],
        "possession %": [round(100 * car[t] / max(1, sum(car))) for t in (0, 1)],
        "attacking zone time %": [round(100 * zone[t] / max(1, len(live))) for t in (0, 1)],
        "passes": [sum(p["team"] == t for p in P) for t in (0, 1)],
        "pass completion %": [round(100 * sum(p["team"] == t and p.get("result") != "failed" for p in P) / max(1, sum(p["team"] == t for p in P))) for t in (0, 1)],
        "puck lost (turnovers against)": [sum(x.get("from") == t for x in mm.get("turnovers") or []) for t in (0, 1)],
        "hits": [sum(h["team"] == t for h in mm.get("hits") or []) for t in (0, 1)],
        "zone entries": [sum(e.get("team") == t for e in mm.get("zoneEntries") or []) for t in (0, 1)],
    }
    return out


# a clear margin: the two teams' values differ by this much (absolute, or a share of their mean for counts)
CLEAR = {"expected goals": 0.75, "deserve to win %": 15, "shots": 4, "dangerous shots (xG 0.3+)": 2, "possession %": 6,
         "attacking zone time %": 5, "passes": 10, "pass completion %": 8, "puck lost (turnovers against)": 5, "hits": 5,
         "zone entries": 6}
A, B = measures(tm), measures(pm)
res = {}
print(Path(read_path).name, m.get("team1"), "(home) /", m.get("team2"))
print(f"{'':32s} {'recording':>14s} {'video':>14s}")
for k in A:
    da, db = A[k][0] - A[k][1], B[k][0] - B[k][1]
    sa = 0 if abs(da) < CLEAR[k] else (1 if da > 0 else -1)
    sb = 0 if abs(db) < CLEAR[k] else (1 if db > 0 else -1)
    verdict = "agrees" if sa == sb else "FLIPS" if sa * sb < 0 else "weaker (clear on one, level on the other)"
    if sa == sb == 0:
        verdict = "agrees (level)"
    res[k] = dict(recording=A[k], video=B[k], verdict=verdict)
    print(f"{k:32s} {str(A[k][0]) + ' / ' + str(A[k][1]):>14s} {str(B[k][0]) + ' / ' + str(B[k][1]):>14s}   {verdict}")
Path(out_path).write_text(json.dumps(res))
