"""The reader over a stretch of BOS-CHI game 1 (track_test's set-up), keeping per frame each live track (id, team,
frame, mirror, sprite point) and the puck tracker's answer (point, height, how, carrier track id), the camera.
python run_reader.py FIRST COUNT OUT.json"""
import json
import sys
import time
from pathlib import Path

sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], *sys.argv[3:]]
import track_test as T
import numpy as np

OUT = Path(sys.argv[3])
import os
RAW = os.environ.get("NHL94_INV_RAW") == "1"
CAM_LEAST = 0.6    # the camera match share below which a frame is not read (0.8 had left out good play frames: half of game 2)
first, count = int(sys.argv[1]), int(sys.argv[2])
INV = T.INV
import hud_read
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scoring_map'))
import lowload
lowload.gentle()
import game_events as GE
hud = hud_read.Reader(Path.home() / "NHL94_scoring_map/runs/vision/hud_native.npz")
t_fit = time.time(); hud.fit_cached(T.VIDEO); print("hud fit", hud.geo, round(time.time() - t_fit), "s", flush=True)
reader, rows, t0, prev_clock = None, [], time.time(), None
for fi, fr in T.frames(first, count):
    lowload.breathe()
    nat = INV.native(fr)
    hr = hud.read(nat)
    clk = hud.read_clock(nat, prev_clock)
    prev_clock = clk if clk is not None else prev_clock
    hudrow = dict(clock=clk, period=hr["period"], home=hr["home"], vis=hr["vis"])
    if T.cam[fi][3] < CAM_LEAST:
        rows.append(dict(fi=fi, cam=None, hud=hudrow, **({"cam_share": round(float(T.cam[fi][3]), 3)} if RAW else {})))
        continue
    hpos, vpos, bg, ign = T.view(fi)
    img = INV.code(INV.native(fr)[:INV.H_PLAY])
    if reader is None:
        for _, sq in T.C.frames(T.VIDEO, fi, 1):
            vis_ab, home_ab = hud.read_teams(sq)
        by_abbr = {t["abbr"][:3].upper().ljust(3): i for i, t in enumerate(T.teams)}
        home, away = by_abbr[home_ab], by_abbr[vis_ab]
        S = INV.Sprites(T.ROM, T.teams[home]["palettes"][0], T.teams[away]["palettes"][1])
        reader = INV.Reader(S, T.trans)
        reader.max_new = 40
        pt = INV.PuckTracker(reader)
    img_m = np.where(ign, -1, img)
    reader.step(img_m, bg, cam=(hpos, vpos))
    reader.max_new = 6
    pk = pt.step(np.where(T.view_puck(fi), -1, img) if T.GROW else img_m, bg, (hpos, vpos), raw=img)
    live = [t for t in reader.tracks if t.miss == 0]
    # NHL94_INV_RAW=1 (2026-11-20, the learning plan): the read's own confidences kept too: the camera's match share,
    # each live track's match score and speed, tracks hidden for a few frames, the puck tracker's state
    raw = dict(cam_share=round(float(T.cam[fi][3]), 3),
               tracks_x=[(t.id, round(float(t.sc), 3), round(float(t.vy), 2), round(float(t.vx), 2)) for t in live],
               hidden=[(t.id, t.team, int(t.miss), int(t.sy), int(t.sx)) for t in reader.tracks if 0 < t.miss <= 30],
               puck_x=dict(mode=pt.mode, unseen=int(pt.unseen), out_of_view=int(getattr(pt, "out_of_view", 0)),
                           pos=None if pt.pos is None else [round(float(v), 1) for v in pt.pos],
                           vel=[round(float(v), 2) for v in pt.vel])) if RAW else {}
    rows.append(dict(fi=fi, cam=(hpos, vpos), hud=hudrow, tracks=[(t.id, t.team, t.fr, int(t.mir), int(t.sy), int(t.sx)) for t in live],
                     **raw,
                     stars={str(k): sorted(v) for k, v in pt.stars.items()},
                     puck=None if pk is None else (int(pk[0]), int(pk[1]), int(pk[3]) if isinstance(pk[3], (int, np.integer)) else 0, pk[5]),
                     carrier=pt.carrier.id if pt.mode == "carried" and pt.carrier is not None else None))
    if len(rows) % 200 == 0:
        print(len(rows), f"{len(rows) / (time.time() - t0):.2f} frames a second", flush=True)
        OUT.write_text(json.dumps(rows))
OUT.write_text(json.dumps(rows))
print("done", len(rows))
