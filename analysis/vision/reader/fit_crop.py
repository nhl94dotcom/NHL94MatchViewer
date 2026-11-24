"""A stream's game picture fitted exactly (2026-11-23: a Twitch video inside a TV-frame overlay; stream_locate's box
was a few pixels and a few percent off, the rink's lines missed and the reader found no player).

From N placed frames of the camera track (made with stream_locate's box), at the video's full size: the box (x0, y0,
w, h, real numbers) for which the video, sampled at the 256 x 224 screen pixels' centres, agrees best with the drawn
rink where the rink has something drawn (lines, circles, boards: flat ice says nothing about the line-up). Each
frame's camera may move +-SLIP pixels (it was tracked through the rough box). Coordinate descent, steps 2 -> 0.25.

Set-up as track_test's (NHL94_INV_VIDEO, _ROM, _CAM, _TIMELINE, _CROP = the rough box).
python fit_crop.py [N]   -> prints the box; the reader takes it as NHL94_INV_FIT=x0,y0,w,h"""
import subprocess
import sys

import numpy as np

sys.argv = [sys.argv[0], "0", "1", *sys.argv[1:]]
import track_test as T
import imageio_ffmpeg

N = int(sys.argv[3]) if len(sys.argv) > 3 else 12
SLIP, ROWS = 4, 186
cam = T.cam
good = [int(r[0]) for r in cam if r[4] and r[3] >= 0.8]
picks = [good[int(k * (len(good) - 1) / (N - 1))] for k in range(N)]
W, H = T.C.video_size(T.VIDEO)
full = []
for fi in picks:
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-hide_banner", "-loglevel", "fatal", "-threads", "1", "-ss", f"{fi / T.FPS:.4f}",
           "-i", str(T.VIDEO), "-an", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    b = subprocess.run(cmd, capture_output=True).stdout
    full.append(np.frombuffer(b[:W * H * 3], np.uint8).reshape(H, W, 3).astype(np.float32))
rink = T.rink.astype(np.float32)
# where the rink has something drawn: a pixel unlike its neighbours 2 away
edge = np.zeros(rink.shape[:2], bool)
for dy, dx in ((0, 2), (2, 0), (0, -2), (-2, 0)):
    edge |= np.abs(rink - np.roll(rink, (dy, dx), (0, 1))).sum(-1) > 60


def sample(img, box):
    x0, y0, w, h = box
    xs = x0 + (np.arange(256) + 0.5) * w / 256 - 0.5
    ys = y0 + (np.arange(ROWS) + 0.5) * h / 224 - 0.5
    xi, yi = np.clip(np.floor(xs).astype(int), 0, W - 2), np.clip(np.floor(ys).astype(int), 0, H - 2)
    fx, fy = (xs - xi)[None, :, None], (ys - yi)[:, None, None]
    a, b = img[yi][:, xi], img[yi][:, xi + 1]
    c, d = img[yi + 1][:, xi], img[yi + 1][:, xi + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def score(box, detail=False):
    tot, slips = [], []
    for fi, img in zip(picks, full):
        s = sample(img, box)
        hpos, vpos = int(cam[fi][1]), int(cam[fi][2])
        best = (-1, 0, 0)
        for dv in range(-SLIP, SLIP + 1):
            for dh in range(-SLIP, SLIP + 1):
                v, u = 256 - (vpos + dv), hpos + dh + 64
                if v < 0 or u < 0:
                    continue
                r, e = rink[v:v + ROWS, u:u + 256], edge[v:v + ROWS, u:u + 256]
                if r.shape[:2] != (ROWS, 256) or e.sum() < 500:
                    continue
                ok = (np.abs(s - r).sum(-1) < 90)[e].mean()
                best = max(best, (float(ok), dh, dv))
        tot.append(best[0])
        slips.append(best[1:])
    return (float(np.mean(tot)), slips) if detail else float(np.mean(tot))


box = [float(v) for v in T.CROP]
cur = score(box)
print("start", box, round(cur, 4), flush=True)
for step in (2, 1, 0.5, 0.25):
    moved = True
    while moved:
        moved = False
        for k in range(4):
            for d in (-step, step):
                b2 = list(box)
                b2[k] += d
                s2 = score(b2)
                if s2 > cur + 1e-4:
                    box, cur, moved = b2, s2, True
        print("step", step, [round(v, 2) for v in box], round(cur, 4), flush=True)
sc, slips = score(box, True)
print("fitted box", ",".join(f"{v:.2f}" for v in box), "share of drawn rink pixels agreeing", round(sc, 4), "camera slips", slips)
