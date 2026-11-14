"""Sprites found in a Genesis video frame (2026-11-14; the video reader's third step, first part).

With the camera known (camera_track.py), the rink as the ROM draws it is the frame's exact background: every pixel
whose colour isn't within the range of the background's pixel and its two horizontal neighbours (each channel, give
or take MARGIN: a recording stretched from 256 to 320 and squeezed back blends neighbours) belongs to a sprite (the players, the puck, the referee, the centre-ice
logo, the goal nets' fronts) or to the crowd's animation. The differing pixels above the score boxes are grouped into
blobs (8-connected, after closing gaps of one pixel); each blob's box, pixel count and bottom centre (a skater's
feet) are kept.

Screen and rink: x = X - Hpos + 128, y = 107 - Y + Vpos - Z for a skater's body (fitted on 12 still-camera frames of
nhl94_playoffs-261113-133619.mkv against the recordings); the feet a few pixels lower.

python analysis/vision/sprites.py check VIDEO CAMERA_TRACK.npz [FIRST] [COUNT]
  each recorded player on screen against the blobs: found (a blob's box within 3 px of his body point) or missed, by
  how crowded the spot was."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_track as C  # noqa: E402

BODY_X, BODY_Y = 128, 107
MIN_PIXELS = 12
MARGIN = 28                       # per channel: the emulators' colour levels differ by up to 16


def fg_mask(rink, f, hpos, vpos):
    u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
    near = np.stack([rink.img[v:v + C.H, u + du:u + du + C.NATIVE_W] for du in (-1, 0, 1)])
    lo, hi = near.min(axis=0) - MARGIN, near.max(axis=0) + MARGIN
    m = ((f < lo) | (f > hi)).any(axis=2)
    m[C.HUD_TOP - 2:] = False
    return m


def close1(m):
    """Fill one-pixel gaps (a dilation then an erosion by a 3 x 3 square)."""
    p = np.pad(m, 1)
    d = np.zeros_like(m)
    for dy in range(3):
        for dx in range(3):
            d |= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    p = np.pad(d, 1, constant_values=True)
    e = np.ones_like(m)
    for dy in range(3):
        for dx in range(3):
            e &= p[dy:dy + m.shape[0], dx:dx + m.shape[1]]
    return e | m


def label(m):
    """8-connected components: a list of (ys, xs) index arrays. Union-find over horizontal runs."""
    runs = []                                    # (row, x0, x1)
    for y in range(m.shape[0]):
        row = m[y]
        if not row.any():
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
            runs.append((y, a, b))
    parent = list(range(len(runs)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    by_row = {}
    for k, (y, a, b) in enumerate(runs):
        by_row.setdefault(y, []).append(k)
        for j in by_row.get(y - 1, []):
            _, a2, b2 = runs[j]
            if a2 <= b and a <= b2:              # touching, diagonals included (b is exclusive)
                ri, rj = find(k), find(j)
                if ri != rj:
                    parent[ri] = rj
    groups = {}
    for k in range(len(runs)):
        groups.setdefault(find(k), []).append(runs[k])
    out = []
    for g in groups.values():
        ys = np.concatenate([np.full(b - a, y) for y, a, b in g])
        xs = np.concatenate([np.arange(a, b) for y, a, b in g])
        out.append((ys, xs))
    return out


def blobs(rink, f, hpos, vpos):
    m = close1(fg_mask(rink, f, hpos, vpos))
    out = []
    for ys, xs in label(m):
        if len(ys) < MIN_PIXELS:
            continue
        out.append({"x0": int(xs.min()), "x1": int(xs.max()), "y0": int(ys.min()), "y1": int(ys.max()), "n": len(ys),
                    "foot": (float(xs[ys >= ys.max() - 2].mean()), int(ys.max()))})
    return out


def check(video, track, first=0, count=20000, step=15):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import rink_mosaic as RM
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    truth, fps = RM.Truth(tl), tl.get("fps", 59.92)
    rows = {int(r[0]): r for r in np.load(track)["rows"]}
    rink = C.Rink(Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin")

    def s16(v):
        return v - 65536 if v & 0x8000 else v
    found = missed = 0
    by_crowd = {}
    sizes = []
    for n, f in C.frames(video, first, count):
        if n % step or n not in rows or not rows[n][4]:
            continue
        cam = truth.camera(n / fps)
        if not cam or not cam[7]:                # still camera: the recording's sample is right for this frame
            continue
        _, hpos, vpos = rows[n][:3]
        bl = blobs(rink, f, int(hpos), int(vpos))
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        pts = []
        for r in range(12):
            a = 0xB04A + 0x80 * r
            if c.byte(i, a + 0x35) == 0xFF and r % 6:     # off the ice
                continue
            X, Y, Z = s16(c.word(i, a)), s16(c.word(i, a + 0x14)), s16(c.word(i, a + 0x18))
            x, y = X - hpos + BODY_X, BODY_Y - Y + vpos - Z
            if 4 <= x < C.NATIVE_W - 4 and 8 <= y < C.HUD_TOP - 8:
                pts.append((x, y))
        for x, y in pts:
            near = sum(1 for x2, y2 in pts if abs(x2 - x) < 16 and abs(y2 - y) < 24) - 1
            hit = any(b["x0"] - 3 <= x <= b["x1"] + 3 and b["y0"] - 3 <= y <= b["y1"] + 3 for b in bl)
            found += hit
            missed += not hit
            t = by_crowd.setdefault(min(near, 2), [0, 0])
            t[0 if hit else 1] += 1
        sizes += [b["n"] for b in bl]
    print(f"players on screen: found {found}, missed {missed} ({found / max(found + missed, 1):.1%})")
    for k in sorted(by_crowd):
        a, b = by_crowd[k]
        print(f"  with {k}{'+' if k == 2 else ''} others close: found {a}, missed {b}")
    print("blob sizes (pixels): median", np.median(sizes) if sizes else None)


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0,
              int(sys.argv[5]) if len(sys.argv) > 5 else 20000)
