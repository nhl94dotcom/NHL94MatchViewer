"""Goals backward (2026-11-22): each goal the score box shows, traced back along the read to its shot, and rated.
From the read alone (pseudo_run_any's set-up, the pseudo match's arrays):
- a goal: the score box's total going up and staying up (3 read rows); the scoring team from which score rose;
- the release: the puck's deepest point toward the net just before the score changed is where it went in; back from
  there along the read puck's path while it moves fast (FAST units a sample) and straight (within TURN degrees): the
  start of that final run is the release, the scoring team's nearest skater the shooter; a one-timer when the puck
  came in fast and wasn't his, else a shot. (Tried first and dropped: the last carrier, which a phantom catch at the
  net mouth misleads; the shooting animation, whose frames passes share and the frame-to-animation table mislabels.)
- the shot: the puck's spot at the release, its speed from the flight after it, the goalie as read there; xG by
  tools/xg.py with what a viewer can know (xg_from_read's ratings and aim: the side from the flight, heights averaged).
Against the recording's goal shots: the release's time, the spot, the kind, the xG.

python goals_back.py READ.json   (NHL94_INV_* and TEST_GAME as pseudo_run_any.py)"""
import json
import math
import sys
from pathlib import Path

import numpy as np

path = sys.argv[1]
src = Path(__file__).with_name("pseudo_run_any.py").read_text(encoding="utf-8").split("total = {}")[0]
sys.argv = [sys.argv[0], path]
exec(src)
import xg as XG  # noqa: E402

BACK, KINK, NEAR = 150, 30, 16
rows = json.loads(Path(path).read_text())
fis = [r["fi"] for r in rows]
qs = np.nonzero((vf >= min(fis)) & (vf <= max(fis)))[0]
q0, q1 = int(qs[0]), int(qs[-1]) + 1
tm = PM.slice_match(m, q0, q1)
truth = PM.analyse(tm, str(ROMP))
pm = PM.build(m, vf, rows, maps, q0, q1)
n = q1 - q0
P, pos, owner, role = pm["puck"], pm["pos"], pm["owner"], pm["role"]
fi_of = [int(round(vf[q0 + i])) if vf[q0 + i] == vf[q0 + i] else None for i in range(n)]
by_fi = {r["fi"]: r for r in rows}

# goals from the score box
goals, last, pend = [], None, None
for i in range(n):
    r = by_fi.get(fi_of[i]) if fi_of[i] is not None else None
    h = (r or {}).get("hud") or {}
    if h.get("home") is None or h.get("vis") is None:
        continue
    sc = (h["home"], h["vis"])
    if last is None:
        last = sc
        continue
    if sc != last:
        if pend and pend[0] == sc:
            pend[2] += 1
            if pend[2] >= 3:
                d = (sc[0] - last[0], sc[1] - last[1])
                if d in ((1, 0), (0, 1)):
                    goals.append((pend[1], 0 if d[0] else 1))
                last, pend = sc, None
        else:
            pend = [sc, i, 1]
    else:
        pend = None


def rec_xy(i, k):
    return pos[(i * 12 + k) * 2], pos[(i * 12 + k) * 2 + 1]


def heading(a, b):
    return math.degrees(math.atan2(P[3 * b + 1] - P[3 * a + 1], P[3 * b] - P[3 * a]))


FAST, TURN, GAP = 2.2, 40, 8                              # units a video frame; degrees; frames a path may skip
found = []
first_i = {}
for i in range(n):
    if fi_of[i] is not None:
        first_i.setdefault(fi_of[i], i)


def puck_gap(i, k):
    return math.hypot(rec_xy(i, k)[0] - P[3 * i], rec_xy(i, k)[1] - P[3 * i + 1])


def seen_path(fa, fb):
    """(video frame, X, Y) for each read frame fa..fb whose puck was seen or placed on a stick (not coasted, not out
    of view), in rink units."""
    out = []
    for fi in range(fa, fb + 1):
        r = by_fi.get(fi)
        if not r or not r.get("cam") or not r.get("puck") or r["puck"][3] in ("out of view", "coasting"):
            continue
        hpos, vpos = r["cam"]
        out.append((fi, r["puck"][1] - 128 + hpos, 112 - r["puck"][0] + vpos))
    return out


for i_s, team in goals:
    mine = range(team * 6, team * 6 + 5)
    lo = max(1, i_s - BACK)
    gl = 264 if XG.attacks_top(pm, max(0, i_s - 30), team) else -264
    sg = 1 if gl > 0 else -1
    path_ = seen_path(fi_of[lo] or 0, fi_of[i_s]) if fi_of[i_s] is not None else []
    shot = None
    tail = [q for q in range(len(path_)) if path_[q][0] >= fi_of[i_s] - 50]
    if len(path_) >= 3 and tail:
        e = max(tail, key=lambda q: sg * path_[q][2])      # the deepest seen point: where it went in
        r, ref = e, None
        q = e
        while q >= 1:
            (f1, x1, y1), (f0, x0, y0) = path_[q], path_[q - 1]
            if f1 - f0 > GAP:
                break
            vx, vy = (x1 - x0) / (f1 - f0), (y1 - y0) / (f1 - f0)
            if math.hypot(vx, vy) < FAST:
                break
            if ref is not None:
                turn = abs((math.degrees(math.atan2(vy, vx)) - math.degrees(math.atan2(ref[1], ref[0])) + 180) % 360 - 180)
                if turn > TURN:
                    break
            ref = (vx, vy) if ref is None else (ref[0] + vx, ref[1] + vy)
            r = q - 1
            q -= 1
        if ref is not None and path_[r][0] in first_i:
            f = first_i[path_[r][0]]
            k = min(mine, key=lambda k: math.hypot(rec_xy(f, k)[0] - path_[r][1], rec_xy(f, k)[1] - path_[r][2]))
            gap = math.hypot(rec_xy(f, k)[0] - path_[r][1], rec_xy(f, k)[1] - path_[r][2])
            vin = 0.0
            if r >= 1 and path_[r][0] - path_[r - 1][0] <= GAP:
                vin = math.hypot(path_[r][1] - path_[r - 1][1], path_[r][2] - path_[r - 1][2]) / (path_[r][0] - path_[r - 1][0])
            carried = sum(owner[i] == k for i in range(max(lo, f - 8), f + 1))
            pm["puck"][3 * f:3 * f + 2] = [float(path_[r][1]), float(path_[r][2])]
            shot = dict(f=f, rec=k, kind="shot" if carried >= 3 or vin < FAST else "one-timer",
                        how=f"final run of {path_[e][0] - path_[r][0]} frames, shooter {gap:.0f} away")
    if shot is None:
        i_c = next((i for i in range(i_s, lo, -1) if owner[i] in mine), None)
        if i_c is not None:
            shot = dict(f=min(n - 1, i_c + 1), rec=owner[i_c], kind="shot", how="last carrier")
    found.append((i_s, team, shot))

# ratings and aim as xg_from_read
first = {}
for r in tm.get("work", []):
    first.setdefault(r[1], r[2:])
role0 = tm["role"][:12]
work, grow = [], {}
for team in (0, 1):
    sk = [first[k] for k in range(team * 6, team * 6 + 6) if k in first and role0[k] not in "0x"]
    mean = [round(sum(c) / len(c)) for c in zip(*sk)] if sk else [64, 15, 15, 15, 15, 15]
    grow[team] = next((first[k] for k in range(team * 6, team * 6 + 6) if k in first and role0[k] == "0"), None)
    for k in range(team * 6, team * 6 + 6):
        work.append([0, k, *mean])
HEIGHTS = {1: [(1, .30), (2, .68), (3, .02)], -1: [(7, .30), (6, .68), (5, .02)], 0: [(0, .45), (8, .27), (4, .27)]}
rom_bytes = ROMP.read_bytes()


def video_xg(sh):
    f, team = sh["f"], sh["team"]
    gk = next((k for k in range((1 - team) * 6, (1 - team) * 6 + 6) if role[f * 12 + k] == "0"), None)
    w2 = [r for r in work if r[1] != gk]
    if gk is not None and grow.get(1 - team):
        w2.append([0, gk, *grow[1 - team]])
    side = 0
    la = XG.launched(pm, f)
    gl = 264 if XG.attacks_top(pm, f, team) else -264
    if la and la[1] and (gl - P[3 * f + 1]) / la[1] > 0:
        cx = P[3 * f] + la[0] * (gl - P[3 * f + 1]) / la[1]
        side = 1 if cx > 8 else -1 if cx < -8 else 0
    tot = 0.0
    for d, wgt in HEIGHTS[side]:
        one = dict(sh, aim={"d": d})
        XG._CACHE.clear()
        XG.add_expected_goals(dict(pm, work=sorted(w2), shotList=[one]), stick_rom=rom_bytes, lock=True)
        tot += wgt * (one.get("xg") or 0.0)
    return round(tot, 3)


T = [s for s in truth.get("shotList", []) if s.get("result") == "goal" and s["kind"] in ("shot", "one-timer", "pass shot")]
print(f"{Path(path).stem}: recorded goals {len(T)}, score-box goals read {len(goals)}")
res = []
for s in T:
    when = f"P{truth['period'][s['f']] + 1} {truth['clock'][s['f']]}"
    cand = [(abs(i_s - s["f"]), i_s, team, shot) for i_s, team, shot in found if team == s["team"] and -30 <= i_s - s["f"] <= 240]
    if not cand:
        print(f"  {when}: no score-box goal read for it")
        res.append(None)
        continue
    _, i_s, team, shot = min(cand, key=lambda c: c[0])
    if shot is None:
        print(f"  {when}: goal seen, no release found")
        res.append(dict(found=False))
        continue
    f = shot["f"]
    la = XG.launched(pm, f)
    sh = dict(f=f, team=team, idx=int(pm["roster"][f * 12 + shot["rec"]], 36), x=P[3 * f], y=P[3 * f + 1],
              speed=round(math.hypot(la[0], la[1])) if la else 12000, kind=shot["kind"], result="goal",
              human=bool(pm["ctrl"][f] >> shot["rec"] & 1))
    v = video_xg(sh)
    dist = math.hypot(sh["x"] - s["x"], sh["y"] - s["y"])
    r = dict(found=True, dt=f - s["f"], dist=round(dist, 1), kind_ok=(shot["kind"] == "one-timer") == (s["kind"] == "one-timer"),
             xg=s.get("xg") or 0.0, xg_video=v, human_ok=sh["human"] == bool(s.get("human")))
    res.append(r)
    print(f"  {when}: {s['kind']:9s} read as {shot['kind']:9s} ({shot['how']}) release {r['dt']:+4d} samples, spot off {r['dist']:5.1f}, xG {r['xg']:.2f} / video {v:.2f}")
ok = [r for r in res if r and r.get("found")]
if ok:
    a = np.array([r["xg"] for r in ok])
    b = np.array([r["xg_video"] for r in ok])
    good = [r for r in ok if abs(r["dt"]) <= 6 and r["dist"] <= 12]
    print(f"  SUMMARY goals {len(T)}: release found {len(ok)}; right (within 6 samples and 12 units) {len(good)}; kind right {sum(r['kind_ok'] for r in ok)}; "
          f"xG recorded {a.sum():.2f} / video {b.sum():.2f}, mean difference {np.abs(a - b).mean():.3f}, within 0.2: {int((np.abs(a - b) <= 0.2).sum())}")
Path(path.replace(".json", "_goals.json")).write_text(json.dumps(res))
