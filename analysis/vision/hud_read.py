"""The Genesis score boxes read from video (2026-11-14; the video reader's game clock and score).

The boxes are on the game's fixed text layer in 8 x 8 cells (frames at the native 256 width, camera_track.frames):
- clock box, columns 0-8, rows 23-27: the period in columns 1-2 of row 24 ("1st" ... "OT"), the clock's minutes in
  columns 3-4 and seconds in 6-7 (the colon in 5);
- score box, columns 23-30: the visitors' abbreviation and score on row 24, the home team's on row 26, the score in
  columns 28-29 (tens, ones).
Cells are compared as grey 8 x 8 pictures with templates learnt from frames whose recording gives the truth
(tools/video_sync.py's timeline; the clock $C468 in seconds left, the period $C466, the scores $C6DA home / $CA3E
visitors), only where the clock stood for 10 samples each way (a game second is 24) (the timeline is good to a fraction of a second). A
cell is read as the nearest template, or as unreadable when even that is far (no box: a menu, a replay, the close-up
faceoff box over it).

python analysis/vision/hud_read.py learn VIDEO TEMPLATES.npz [UPTO_FRAME]   (the video's .timeline.json beside it)
python analysis/vision/hud_read.py check VIDEO TEMPLATES.npz [STEP] [FROM_FRAME]
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_track as C  # noqa: E402

CLOCK_ROW, VIS_ROW, HOME_ROW = 24, 24, 26
CELLS = {"per": [(24, 1), (24, 2)], "min": [(24, 3), (24, 4)], "sec": [(24, 6), (24, 7)],
         "vis": [(24, 28), (24, 29)], "home": [(26, 28), (26, 29)]}
FAR = 40.0                       # mean grey difference per pixel above which a cell isn't read
PERIODS = ["1st", "2nd", "3rd", "OT"]


def cell(f, rc):
    r, c = rc
    return f[r * 8:r * 8 + 8, c * 8:c * 8 + 8].mean(axis=2)


def labels(c, i):
    """The truth at sample i: {cell: label}; ' ' for a blank cell."""
    def w(a):
        return c.word(i, a)
    per, clock, home, vis = w(0xC466), w(0xC468), w(0xC6DA), w(0xCA3E)
    if per > 3 or clock > 1200 or home > 99 or vis > 99:
        return None
    m, s = divmod(clock, 60)
    out = {}
    out[CELLS["per"][0]], out[CELLS["per"][1]] = ("p" + PERIODS[per]), ("q" + PERIODS[per])   # the two halves
    out[CELLS["min"][0]] = str(m // 10) if m >= 10 else " "
    out[CELLS["min"][1]] = str(m % 10)
    out[CELLS["sec"][0]], out[CELLS["sec"][1]] = str(s // 10), str(s % 10)
    for k, v in (("vis", vis), ("home", home)):
        out[CELLS[k][0]] = str(v // 10) if v >= 10 else " "
        out[CELLS[k][1]] = str(v % 10)
    return out


def group(rc):
    return next(k for k, cs in CELLS.items() if rc in cs)


def learn(video, out, step=7, upto=None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import rink_mosaic as RM
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    truth, fps = RM.Truth(tl), tl.get("fps", 59.92)
    sums, counts = defaultdict(lambda: np.zeros((8, 8))), defaultdict(int)
    used = 0
    for n, f in C.frames(video, 0, upto):
        if n % step:
            continue
        cam = truth.camera(n / fps)
        if not cam or not cam[6]:
            continue
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        lo, hi = max(0, i - 10), min(c.count, i + 11)
        if len({c.word(j, 0xC468) for j in range(lo, hi, 2)} | {c.word(hi - 1, 0xC468)}) != 1:
            continue
        lab = labels(c, i)
        if not lab:
            continue
        for rc, ch in lab.items():
            key = (group(rc) if group(rc) in ("per",) else "clk" if group(rc) in ("min", "sec") else "score", ch)
            sums[key] += cell(f, rc)
            counts[key] += 1
        used += 1
    keys = sorted(sums)
    np.savez_compressed(out, keys=np.array(["|".join(k) for k in keys]),
                        tmpl=np.stack([sums[k] / counts[k] for k in keys]), counts=np.array([counts[k] for k in keys]))
    print(f"{used} frames; templates: " + ", ".join(f"{k[0]}:{k[1]!r} {counts[k]}" for k in keys))


class Reader:
    def __init__(self, templates):
        d = np.load(templates)
        self.t = defaultdict(list)
        for k, t in zip(d["keys"], d["tmpl"]):
            kind, ch = str(k).split("|", 1)
            self.t[kind].append((ch, t))

    def char(self, f, rc, kind):
        g = cell(f, rc)
        ch, t = min(self.t[kind], key=lambda ct: np.abs(g - ct[1]).mean())
        return ch if np.abs(g - t).mean() <= FAR else None

    def read(self, f):
        """{'period': 0-3, 'clock': seconds left, 'vis': n, 'home': n}, each None when unreadable."""
        per = self.char(f, CELLS["per"][0], "per")
        mins = [self.char(f, rc, "clk") for rc in CELLS["min"]]
        secs = [self.char(f, rc, "clk") for rc in CELLS["sec"]]
        out = {"period": PERIODS.index(per[1:]) if per else None, "clock": None}
        if None not in mins + secs and " " not in mins[1:] + secs:
            out["clock"] = (int(mins[0]) * 10 if mins[0] != " " else 0) * 60 + int(mins[1]) * 60 + int(secs[0]) * 10 + int(secs[1])
        for k in ("vis", "home"):
            a, b = (self.char(f, rc, "score") for rc in CELLS[k])
            out[k] = None if a is None or b is None or b == " " else (int(a) * 10 if a != " " else 0) + int(b)
        return out


def check(video, templates, step=11, start=0):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import rink_mosaic as RM
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    truth, fps = RM.Truth(tl), tl.get("fps", 59.92)
    rd = Reader(templates)
    tally = defaultdict(lambda: [0, 0, 0])            # field: right, wrong, unread
    wrong = []
    for n, f in C.frames(video, start):
        if n % step:
            continue
        cam = truth.camera(n / fps)
        if not cam or not cam[6]:
            continue
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        lo, hi = max(0, i - 10), min(c.count, i + 11)
        if c.word(lo, 0xC468) != c.word(hi - 1, 0xC468):
            continue
        r = rd.read(f)
        want = {"period": c.word(i, 0xC466), "clock": c.word(i, 0xC468), "vis": c.word(i, 0xCA3E), "home": c.word(i, 0xC6DA)}
        for k, v in want.items():
            t = tally[k]
            if r[k] is None:
                t[2] += 1
            elif r[k] == v:
                t[0] += 1
            else:
                t[1] += 1
                if len(wrong) < 12:
                    wrong.append((n, k, r[k], v))
    for k, (a, b, u) in tally.items():
        print(f"{k}: right {a}, wrong {b}, unread {u}")
    for w in wrong:
        print("  wrong:", w)


if __name__ == "__main__":
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
        lowload.gentle()
    except ImportError:
        pass
    if sys.argv[1] == "learn":
        learn(Path(sys.argv[2]), sys.argv[3], upto=int(sys.argv[4]) if len(sys.argv) > 4 else None)
    else:
        check(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 11,
              int(sys.argv[5]) if len(sys.argv) > 5 else 0)
