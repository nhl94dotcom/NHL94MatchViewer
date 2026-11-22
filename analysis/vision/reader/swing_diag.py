"""How often a read shows the swing at a recorded shot (2026-11-22): for each recorded shot and one-timer, a read
record of the shooter's team within NEAR units of him showing a swing frame (the shooting frames' 5th of 6 by facing:
100 + 6d, at the release in every recorded shot) within +-WIN samples of the release. By the shot's xG and result.
python swing_diag.py READ.json   (NHL94_INV_* and TEST_GAME as pseudo_run_any.py)"""
import json, math, sys
from pathlib import Path
import numpy as np
path = sys.argv[1]
src = Path(__file__).with_name("pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
sys.argv = [sys.argv[0], path]
exec(src)
NEAR, WIN = 10, 6
REL = {100 + 6 * d for d in range(8)}
rows = json.loads(Path(path).read_text())
fis = [r["fi"] for r in rows]
qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
q0, q1 = int(qs[0]), int(qs[-1]) + 1
pm = PM.build(m, vf, rows, maps, q0, q1)
n = q1 - q0
F = lambda i, k: int("".join(pm["frame"][(i * 12 + k) * 3:(i * 12 + k) * 3 + 3]), 16)
tot = {}
for s in m["shotList"]:
    if s["kind"] not in ("shot", "one-timer") or s.get("team") not in (0, 1) or not q0 <= s["f"] < q1:
        continue
    q, team = s["f"], s["team"]
    sh = next((k for k in range(team * 6, team * 6 + 6) if m["role"][q * 12 + k] != "x" and int(m["roster"][q * 12 + k], 36) == s["idx"]), None)
    if sh is None:
        continue
    hit = False
    for d in range(-WIN, WIN + 1):
        i = q + d - q0
        if not 0 <= i < n:
            continue
        tx, ty = m["pos"][((q + d) * 12 + sh) * 2], m["pos"][((q + d) * 12 + sh) * 2 + 1]
        for k in range(team * 6, team * 6 + 5):
            if F(i, k) in REL and math.hypot(pm["pos"][(i * 12 + k) * 2] - tx, pm["pos"][(i * 12 + k) * 2 + 1] - ty) <= NEAR:
                hit = True
    xg = s.get("xg") or 0
    for key in ("all", s["kind"], "goal" if s["result"] == "goal" else "not a goal", "xG 0.3+" if xg >= 0.3 else "xG under 0.3"):
        t = tot.setdefault(key, [0, 0]); t[0] += hit; t[1] += 1
print(Path(path).stem, {k: f"{v[0]}/{v[1]}" for k, v in tot.items()})
Path(path.replace(".json", "_swing.json")).write_text(json.dumps(tot))
