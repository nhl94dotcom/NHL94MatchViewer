"""The puck tracked again over a finished read (2026-11-26): the players of each frame taken from the read's rows as
they stand (track id, team, frame, mirror, sprite point), only inverse.PuckTracker run over the video's frames. A
whole game in minutes where the read took an hour and a half, so the puck tracker can be changed and tried.

Each row's `puck`, `carrier` and `stars` are written again; everything else is kept (the star pass's `star2` too).
A carrier the tracker finds hidden behind another sprite (not among the read's tracks) is tied to the read's track of
his team at that spot when one turns up.

Set-up as run_reader.py (NHL94_INV_*, TEST_GAME).  python puck_replay.py READ.json OUT.json [FIRST_ROW COUNT]
With the tracker unchanged the result should be the read's own puck: the script prints how often it is."""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

read_path, out_path = sys.argv[1], sys.argv[2]
rows = json.loads(Path(read_path).read_text())
if len(sys.argv) > 4:
    rows = rows[int(sys.argv[3]):int(sys.argv[3]) + int(sys.argv[4])]
fis = [r["fi"] for r in rows]
sys.argv = [sys.argv[0], str(min(fis)), str(max(fis) - min(fis) + 1)]
import track_test as T  # noqa: E402
import hud_read  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scoring_map"))
import lowload  # noqa: E402
import os  # noqa: E402
QUICK = os.environ.get("NHL94_REPLAY_QUICK") == "1"     # a short profiling run: no rests
if not QUICK:
    lowload.gentle()
INV = T.INV
INV.Track._next = 10 ** 9                       # the tracker's own finds never share a number with the read's tracks
by = {r["fi"]: r for r in rows}
hud = hud_read.Reader(Path.home() / "NHL94_scoring_map/runs/vision/hud_native.npz")
hud.fit_cached(T.VIDEO)
# NHL94_REPLAY_SWINGS=1: only the stretches around swings (a track on a shooting frame: 20 frames before the first to 45
# after the last), the tracker started afresh at each; the other rows are left as they are
SWINGS = os.environ.get("NHL94_REPLAY_SWINGS") == "1"
if SWINGS:
    SW = {f for f in range(96, 144) if (f - 96) % 6}
    order = [r["fi"] for r in rows]
    mark = np.zeros(len(rows), bool)
    for i, r in enumerate(rows):
        if r.get("cam") is not None and any(t[2] in SW for t in r["tracks"]):
            mark[max(0, i - 20):i + 46] = True
    inwin = {fi for fi, k in zip(order, mark) if k}
    print("swing stretches:", int(mark.sum()), "of", len(rows), "rows", flush=True)
reader, pt, known, t0, done = None, None, {}, time.time(), 0
last_fi = None
same, moved, hows = Counter(), 0, Counter()
for fi, fr in T.frames(min(fis), max(fis) - min(fis) + 1):
    r = by.get(fi)
    if r is None or r.get("cam") is None or (SWINGS and fi not in inwin):
        continue
    if SWINGS and pt is not None and last_fi is not None and fi - last_fi > 3:
        pt = INV.PuckTracker(reader)                    # a new stretch
    last_fi = fi
    if not QUICK:
        lowload.breathe()
    hpos, vpos, bg, ign = T.view(fi)
    img = INV.code(INV.native(fr)[:INV.H_PLAY])
    if reader is None:
        for _, sq in T.C.frames(T.VIDEO, fi, 1):
            vis_ab, home_ab = hud.read_teams(sq)
        ab = {t["abbr"][:3].upper().ljust(3): i for i, t in enumerate(T.teams)}
        S = INV.Sprites(T.ROM, T.teams[ab[home_ab]]["palettes"][0], T.teams[ab[vis_ab]]["palettes"][1])
        reader = INV.Reader(S, T.trans)
        pt = INV.PuckTracker(reader)
    # the read's players for this frame, each track the same object as long as it lives (the tracker compares them)
    live, drawn = [], np.zeros(img.shape, bool)
    for tid, team, f_, mir, sy, sx in r["tracks"]:
        tr = known.get(tid)
        if tr is None:
            tr = known[tid] = INV.Track(team, f_, bool(mir), sy, sx, 1.0)
            tr.id = tid
            tr._fi = fi - 1
        gap = max(1, fi - tr._fi)
        cam0 = getattr(tr, "_cam", (hpos, vpos))
        py, px = tr.sy + (vpos - cam0[1]), tr.sx - (hpos - cam0[0])          # where he stood, on today's screen
        tr.vy, tr.vx = (0.5 * tr.vy + 0.5 * (sy - py) / gap, 0.5 * tr.vx + 0.5 * (sx - px) / gap) if gap <= 8 else (0.0, 0.0)
        tr.team, tr.fr, tr.mir, tr.sy, tr.sx, tr.miss, tr._fi, tr._cam = team, f_, bool(mir), sy, sx, 0, fi, (hpos, vpos)
        tp = S.get(f_, team, bool(mir))
        if tp is not None:
            Y, X = reader.place(img, tp, sy, sx)
            drawn[Y, X] = True
        live.append(tr)
    c = pt.carrier
    if c is not None and c.id >= 10 ** 9:                                    # the tracker's own hidden carrier: the
        near = [t for t in live if t.team == c.team and abs(t.sy - c.sy) + abs(t.sx - c.sx) <= 6]   # read's track there
        if near:
            pt.carrier = min(near, key=lambda t: abs(t.sy - c.sy) + abs(t.sx - c.sx))
    reader.tracks = live
    reader.n += 1
    reader.cam = (hpos, vpos)
    drawn |= reader.feet_marks(np.where(ign, -1, img), bg)
    reader.drawn = drawn
    img_m = np.where(ign, -1, img)
    pk = pt.step(np.where(T.view_puck(fi), -1, img) if T.GROW else img_m, bg, (hpos, vpos), raw=img)
    new = None if pk is None else (int(pk[0]), int(pk[1]), int(pk[3]) if isinstance(pk[3], (int, np.integer)) else 0, pk[5])
    old = r.get("puck")
    same[(old[3] if old else "none") == (new[3] if new else "none")] += 1
    moved += bool(old and new and abs(old[0] - new[0]) + abs(old[1] - new[1]) > 3)
    hows[new[3] if new else "none"] += 1
    r["puck"] = new
    r["carrier"] = pt.carrier.id if pt.mode == "carried" and pt.carrier is not None and pt.carrier.id < 10 ** 9 else None
    r["stars"] = {str(k): sorted(v) for k, v in pt.stars.items() if k < 10 ** 9}
    done += 1
    if done % 2000 == 0:
        print(done, f"{done / (time.time() - t0):.1f} frames a second", flush=True)
Path(out_path).write_text(json.dumps(rows))
print("done", done, "frames in", round(time.time() - t0), "s; the puck's state as the read's in", same[True], "of", sum(same.values()),
      "; over 3 pixels from the read's in", moved, "; states:", dict(hows))
