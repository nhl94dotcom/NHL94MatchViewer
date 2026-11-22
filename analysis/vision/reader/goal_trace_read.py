"""A read around one recorded goal, sample by sample (2026-11-22): python goal_trace_read.py READ.json GOAL_INDEX"""
import json, math, sys
from pathlib import Path
import numpy as np
path, gi = sys.argv[1], int(sys.argv[2])
src = Path(__file__).with_name("pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
sys.argv = [sys.argv[0], path]
exec(src)
rows = json.loads(Path(path).read_text())
fis = [r["fi"] for r in rows]
qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
q0, q1 = int(qs[0]), int(qs[-1]) + 1
pm = PM.build(m, vf, rows, maps, q0, q1)
by_fi = {r["fi"]: r for r in rows}
G = [s for s in m["shotList"] if s.get("result") == "goal" and s["kind"] in ("shot", "one-timer")]
s = G[gi]
q, team = s["f"], s["team"]
sh = next(k for k in range(team * 6, team * 6 + 6) if m["role"][q * 12 + k] != "x" and int(m["roster"][q * 12 + k], 36) == s["idx"])
print(s["kind"], "team", team, "true shooter record", sh, "at", s["x"], s["y"], "xg", s.get("xg"))
for d in range(-40, 30, 2):
    qq = q + d; i = qq - q0
    r = by_fi.get(int(round(vf[qq]))) if vf[qq] == vf[qq] else None
    tp = (round(m["puck"][3 * qq]), round(m["puck"][3 * qq + 1])); to = m["owner"][qq]
    tsx, tsy = m["pos"][(qq * 12 + sh) * 2], m["pos"][(qq * 12 + sh) * 2 + 1]
    rp = (round(pm["puck"][3 * i]), round(pm["puck"][3 * i + 1])); ro = pm["owner"][i]
    how = r["puck"][3] if r and r.get("puck") else None
    # the read record nearest the true shooter, and its anim / frame
    near = min(range(team * 6, team * 6 + 5), key=lambda k: math.hypot(pm["pos"][(i * 12 + k) * 2] - tsx, pm["pos"][(i * 12 + k) * 2 + 1] - tsy))
    nd = math.hypot(pm["pos"][(i * 12 + near) * 2] - tsx, pm["pos"][(i * 12 + near) * 2 + 1] - tsy)
    an = "".join(pm["anim"][(i * 12 + near) * 4:(i * 12 + near) * 4 + 4]); fr = "".join(pm["frame"][(i * 12 + near) * 3:(i * 12 + near) * 3 + 3])
    ta = m["anim"][(qq * 12 + sh) * 4:(qq * 12 + sh) * 4 + 4]; tf = m["frame"][(qq * 12 + sh) * 3:(qq * 12 + sh) * 3 + 3]
    sc = (r or {}).get("hud", {})
    print(f"{d:+4d} true puck {tp} owner {to:2d} shooter anim {ta} fr {tf} | read puck {rp} owner {ro:2d} ({how}); read rec {near} near shooter ({nd:4.1f}) anim {an} fr {fr}; score {sc.get('home')}-{sc.get('vis')}")
