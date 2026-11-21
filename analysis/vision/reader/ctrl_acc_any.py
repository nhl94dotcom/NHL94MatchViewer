import sys, json, math
from pathlib import Path
import numpy as np
path = sys.argv[1]
src = Path(__file__).with_name("pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
sys.argv = [sys.argv[0], path]
exec(src)
rows = json.loads(Path(path).read_text())
fis = [r["fi"] for r in rows]
qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
q0, q1 = int(qs[0]), int(qs[-1]) + 1
tm = PM.slice_match(m, q0, q1); rm = PM.build(m, vf, rows, maps, q0, q1)
P = lambda mm, f, k: (mm["pos"][(f * 12 + k) * 2], mm["pos"][(f * 12 + k) * 2 + 1])
for team in (0, 1):
    n = ok = none = 0
    for f in range(0, q1 - q0, 3):
        tk = next((j for j in range(team * 6, team * 6 + 6) if tm["ctrl"][f] >> j & 1 and tm["role"][f * 12 + j] in "12345"), None)
        if tk is None: continue
        n += 1
        rk = next((j for j in range(team * 6, team * 6 + 6) if rm["ctrl"][f] >> j & 1), None)
        if rk is None: none += 1; continue
        ok += math.dist(P(tm, f, tk), P(rm, f, rk)) <= 15
    print(path, "team", team, "samples with a person's skater", n, "read right (within 15)", f"{ok / max(1, n):.0%}", "no read ctrl", f"{none / max(1, n):.0%}")
