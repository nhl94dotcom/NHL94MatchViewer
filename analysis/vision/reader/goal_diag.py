"""Goals backward, step 1 (2026-11-22): what a read holds at each recorded goal's release. For every goal shot of the
recording (shotList result goal), at the read row nearest its sample: the shooter (a track of his team within R px of
his sprite point), whether the track's frame is his recorded frame, the goalie the same, the puck (within R), and the
frames around it (the release -30 .. +10 video frames: how many have the shooter and the goalie). And from the read
alone: the frame the score box changes, and how long after the release that is.
python goal_diag.py READ.json   (NHL94_INV_* and TEST_GAME as pseudo_run_any.py)"""
import json
import sys
from pathlib import Path

import numpy as np

path = sys.argv[1]
src = Path(__file__).with_name("pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
sys.argv = [sys.argv[0], path]
exec(src)
R = 8
rows = json.loads(Path(path).read_text())
by_fi = {r["fi"]: r for r in rows}
K = 12
def at(q, k):
    x, y = m["pos"][(q * K + k) * 2], m["pos"][(q * K + k) * 2 + 1]
    return x, y, int(m["frame"][(q * K + k) * 3:(q * K + k) * 3 + 3], 16)
def near(row, team, x, y):
    hpos, vpos = row["cam"]
    sx, sy = 128 + x - hpos, 112 - y + vpos
    best = None
    for t in row.get("tracks", []):
        if t[1] != team:
            continue
        d = max(abs(t[5] - sx), abs(t[4] - sy))
        if best is None or d < best[0]:
            best = (d, t[2])
    return best, (sx, sy)
out = []
for s in m.get("shotList", []):
    if s.get("result") != "goal" or s["kind"] not in ("shot", "one-timer", "pass shot"):
        continue
    q, team = s["f"], s["team"]
    if np.isnan(vf[q]):
        continue
    fi = int(round(vf[q]))
    row = by_fi.get(fi) or by_fi.get(fi + 1) or by_fi.get(fi - 1)
    ro = m["roster"]
    shooter = next((k for k in range(team * 6, team * 6 + 6) if m["role"][q * K + k] != "x" and int(ro[q * K + k], 36) == s["idx"]), None)
    gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if m["role"][q * K + k] == "0"), None)
    rec = dict(period=m["period"][q] + 1, clock=m["clock"][q], team=team, kind=s["kind"], xg=s.get("xg"), row=bool(row and row.get("cam")))
    if row and row.get("cam") and shooter is not None:
        x, y, fr = at(q, shooter)
        b, pt = near(row, team, x, y)
        rec.update(shooter_px=b[0] if b else None, shooter_frame_ok=bool(b and b[0] <= R and b[1] == fr), on_screen=0 <= pt[0] <= 255 and 0 <= pt[1] <= 223)
        if gk is not None:
            gx, gy, gfr = at(q, gk)
            g, _ = near(row, 1 - team, gx, gy)
            rec.update(goalie_px=g[0] if g else None, goalie_frame_ok=bool(g and g[0] <= R and g[1] == gfr))
        px, py = m["puck"][3 * q], m["puck"][3 * q + 1]
        hpos, vpos = row["cam"]
        if row.get("puck"):
            rec["puck_px"] = round(max(abs(row["puck"][1] - (128 + px - hpos)), abs(row["puck"][0] - (112 - py + vpos))))   # stored (y, x)
            rec["puck_how"] = row["puck"][3] if len(row["puck"]) > 3 else None
        have_s = have_g = n = 0
        for d in range(-30, 11):
            r2 = by_fi.get(fi + d)
            qq = int(np.nanargmin(np.abs(vf - (fi + d))))
            if not r2 or not r2.get("cam"):
                continue
            n += 1
            b2, _ = near(r2, team, *at(qq, shooter)[:2])
            have_s += bool(b2 and b2[0] <= R)
            if gk is not None:
                g2, _ = near(r2, 1 - team, *at(qq, gk)[:2])
                have_g += bool(g2 and g2[0] <= R)
        rec.update(window=n, window_shooter=have_s, window_goalie=have_g)
        # the score box: the first read row after the release whose scores sum higher
        base = (row.get("hud") or {})
        tot0 = (base.get("home") or 0) + (base.get("vis") or 0)
        for d in range(1, 600):
            r2 = by_fi.get(fi + d)
            h = (r2 or {}).get("hud") or {}
            if h.get("home") is not None and h.get("vis") is not None and h["home"] + h["vis"] > tot0:
                rec["score_change_after"] = d
                break
    out.append(rec)
ok = [r for r in out if r.get("on_screen")]
print(f"{Path(path).stem}: goals {len(out)}; shooter within {R} px {sum((r.get('shooter_px') or 99) <= R for r in ok)} of {len(ok)}, his frame right {sum(r.get('shooter_frame_ok', False) for r in ok)}; "
      f"goalie within {R} px {sum((r.get('goalie_px') or 99) <= R for r in ok)}, frame right {sum(r.get('goalie_frame_ok', False) for r in ok)}; puck within {R} px {sum(r.get('puck_px', 99) <= R for r in ok)}")
