"""The possession star looked for again under every read player (2026-11-24): a fast second pass over a read.

The reader's own star check (inverse.read_stars) wants 60% of the star's pixels right, but the carrier stands on his
star and hides much of it: the nine reads show it on about one frame in five, where the game draws it nearly always
(under the carrier, and under the last carrier while the puck is loose). Here each frame is decoded again, the read's
own tracks drawn (no search), and the star's pixels that no read sprite covers compared: per track the visible count
and the share of them right. Kept per frame: the tracks with at least LEAST_VISIBLE visible star pixels and a share of
KEEP or more, [track id, team, visible, share, pixels right].

Set-up as run_reader's (NHL94_INV_*, TEST_GAME).  python star_pass.py FIRST COUNT READ.json OUT.json"""
import json
import sys
import time
from pathlib import Path

read_path, out_path = sys.argv[3], Path(sys.argv[4])
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2]]
import track_test as T
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scoring_map"))
import lowload
lowload.gentle()
import hud_read

INV = T.INV
LEAST_VISIBLE, KEEP = 6, 0.3
first, count = int(sys.argv[1]), int(sys.argv[2])
rows = {r["fi"]: r for r in json.loads(Path(read_path).read_text()) if r.get("cam")}
hud = hud_read.Reader(Path.home() / "NHL94_scoring_map/runs/vision/hud_native.npz")
hud.fit_cached(T.VIDEO)
S, star, out, t0 = None, None, {}, time.time()
for fi, fr in T.frames(first, count):
    lowload.breathe()
    r = rows.get(fi)
    if r is None or not r.get("tracks"):
        continue
    if S is None:
        for _, sq in T.C.frames(T.VIDEO, fi, 1):
            vis_ab, home_ab = hud.read_teams(sq)
        by_abbr = {t["abbr"][:3].upper().ljust(3): i for i, t in enumerate(T.teams)}
        S = INV.Sprites(T.ROM, T.teams[by_abbr[home_ab]]["palettes"][0], T.teams[by_abbr[vis_ab]]["palettes"][1])
        star = S.get(392, 0, False)
    img = INV.code(INV.native(fr)[:INV.H_PLAY])
    H, W = img.shape
    covered = np.zeros(img.shape, bool)
    for tid, team, f, mir, sy, sx in r["tracks"]:
        tp = S.get(f, team, bool(mir))
        if tp is None:
            continue
        Y, X = tp[0] + sy, tp[1] + sx
        ok = (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
        covered[Y[ok], X[ok]] = True
    ys, xs, cs = star
    found = []
    for tid, team, f, mir, sy, sx in r["tracks"]:
        best = None
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                Y, X = ys + sy + dy, xs + sx + dx
                ok = (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
                Yo, Xo = Y[ok], X[ok]
                vis = ~covered[Yo, Xo]
                n = int(vis.sum())
                if n < LEAST_VISIBLE:
                    continue
                right = int((img[Yo, Xo][vis] == cs[ok][vis]).sum())
                if best is None or right / n > best[1]:
                    best = (n, right / n, right)
        if best and best[1] >= KEEP:
            found.append([tid, team, best[0], round(best[1], 3), best[2]])
    out[fi] = found
    if len(out) % 2000 == 0:
        print(len(out), f"{len(out) / (time.time() - t0):.1f} frames a second", flush=True)
        out_path.write_text(json.dumps(out))
out_path.write_text(json.dumps(out))
print("done", len(out), f"{len(out) / max(1e-9, time.time() - t0):.1f} frames a second")
