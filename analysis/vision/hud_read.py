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


BLURS = (0.0, 0.15, 0.25, 0.33)   # horizontal [a, 1 - 2a, a] tried on the game's own (crisp) templates
NATIVE_FAR = 36.0                 # with the fitted levels and geometry, the most a read cell may differ (on
                                  # average; a compressed video's cells run 20-35 against the right character)


def blur(t, a):
    """[a, 1 - 2a, a] across and down (a stretched picture resized back blurs both ways)."""
    if not a:
        return t
    p = np.pad(t, ((0, 0), (1, 1)), mode="edge")
    t = a * p[:, :-2] + (1 - 2 * a) * p[:, 1:-1] + a * p[:, 2:]
    p = np.pad(t, ((1, 1), (0, 0)), mode="edge")
    return a * p[:-2] + (1 - 2 * a) * p[1:-1] + a * p[2:]


SHIFT = 2                         # the margin a native template is drawn in (scaled and shifted inside it)
SLIDE = 2                         # and then tried up to this many pixels further off each way, per cell


def around(f, rc, m=None):
    m = SHIFT + SLIDE if m is None else m
    r, c = rc
    y0, x0 = r * 8 - m, c * 8 - m
    g = f[max(0, y0):r * 8 + 8 + m, max(0, x0):c * 8 + 8 + m].mean(axis=2)
    g = np.pad(g, ((max(0, -y0), 0), (max(0, -x0), 0)), mode="edge")
    n = 8 + 2 * m
    return np.pad(g, ((0, max(0, n - g.shape[0])), (0, max(0, n - g.shape[1]))), mode="edge")


def slid(g, t):
    """The best fitted difference of template t (8 + 2 SHIFT square) anywhere within SLIDE pixels in g, over the
    character's own 8 x 8 only (the margin would take in the next character's edge: in a stretched video a pixel
    or two away)."""
    c = t[SHIFT:SHIFT + 8, SHIFT:SHIFT + 8]
    return min(fitted(g[dy + SHIFT:dy + SHIFT + 8, dx + SHIFT:dx + SHIFT + 8], c)
               for dy in range(2 * SLIDE + 1) for dx in range(2 * SLIDE + 1))


def fitted(g, t):
    """The mean difference after the template's levels are fitted to the cell (scale 0.7-1.3 and an offset: emulators
    and videos draw the same colours a little differently)."""
    tc, gc = t - t.mean(), g - g.mean()
    v = (tc * tc).sum()
    a = 1.0 if v < 1 else float(np.clip((tc * gc).sum() / v, 0.7, 1.3))
    return float(np.abs(gc - a * tc).mean())


class Reader:
    """Templates learnt from a video (learn) or drawn by the game (hud_glyphs.py, native: blurred to fit the video,
    the blur chosen by fit(), levels fitted per cell)."""

    def __init__(self, templates):
        d = np.load(templates)
        self.native = bool(d["native"]) if "native" in d else False
        self.raw = defaultdict(list)
        for k, t in zip(d["keys"], d["tmpl"]):
            kind, ch = str(k).split("|", 1)
            self.raw[kind].append((ch, t))
        self.set_blur(0.25 if self.native else 0.0)

    def set_blur(self, a):
        self.set_geometry((1.0, 1.0, 0.0, 0.0, a))

    def set_geometry(self, geo):
        """geo = (scale x, scale y, shift x, shift y, blur): each native template drawn into the cell's surroundings
        (around: SHIFT pixels each side) scaled about the cell's corner, shifted, blurred."""
        from PIL import Image
        self.geo = geo
        sx, sy, dx, dy, a = geo
        n = 8 + 2 * SHIFT
        self.t = {}
        for k, v in self.raw.items():
            out = []
            for ch, t in v:
                canvas = np.zeros((n, n), np.float32)
                canvas[SHIFT:SHIFT + 8, SHIFT:SHIFT + 8] = t
                if self.native:
                    im = Image.fromarray(canvas, "F").transform(
                        (n, n), Image.AFFINE, (1 / sx, 0, SHIFT - (SHIFT + dx) / sx, 0, 1 / sy, SHIFT - (SHIFT + dy) / sy),
                        resample=Image.BILINEAR)
                    out.append((ch, blur(np.array(im, np.float64), a)))
                else:
                    out.append((ch, blur(t, a)))
            self.t[k] = out

    def fit(self, frames):
        """The geometry that matches these frames' score-box cells best (the mean of each cell's best difference):
        blur first, then scale, then shift."""
        cells = [(f, rc, kind) for f in frames for kind, rcs in
                 (("clk", CELLS["min"] + CELLS["sec"]), ("score", CELLS["vis"] + CELLS["home"])) for rc in rcs]

        def cost(geo):
            self.set_geometry(geo)
            return np.mean([self.best(f, rc, kind)[1] for f, rc, kind in cells])
        sx, sy, dx, dy, a = 1.0, 1.0, 0.0, 0.0, 0.15
        for _ in range(2):
            a = min(BLURS, key=lambda v: cost((sx, sy, dx, dy, v)))
            sx, sy = min(((x, y) for x in (1.0, 1.06, 1.12, 1.18) for y in (1.0, 1.06, 1.12, 1.18)),
                         key=lambda q: cost((q[0], q[1], dx, dy, a)))
            dx, dy = min(((x, y) for x in np.arange(-1.5, 1.6, 0.5) for y in np.arange(-1.5, 1.6, 0.5)),
                         key=lambda q: cost((sx, sy, q[0], q[1], a)))
        self.set_geometry((sx, sy, float(dx), float(dy), a))
        return self.geo

    def best(self, f, rc, kind):
        if self.native:
            g = around(f, rc)
            return min(((ch, slid(g, t)) for ch, t in self.t[kind]), key=lambda c: c[1])
        g = cell(f, rc)
        return min(((ch, float(np.abs(g - t).mean())) for ch, t in self.t[kind]), key=lambda c: c[1])

    def value_cost(self, f, key, v):
        """How unlike a score of v the visitors' or home team's ("vis" / "home") score cells are (the two cells'
        differences added)."""
        want = (str(v // 10) if v >= 10 else " ", str(v % 10))
        total = 0.0
        for rc, ch in zip(CELLS[key], want):
            t = dict(self.t["score"]).get(ch)
            if t is None:
                return 1e9
            if self.native:
                total += slid(around(f, rc), t)
            else:
                total += float(np.abs(cell(f, rc) - t).mean())
        return total

    def read_score(self, f, key, prev):
        """The score as one of prev, prev + 1 or 0 (a score only goes up by one; 0 at a new game), or None when even
        the nearest is unlike the cells (more than 2 x the cut-off)."""
        cands = sorted({prev, prev + 1, 0})
        cost, v = min((self.value_cost(f, key, c), c) for c in cands)
        return v if cost <= 2 * (NATIVE_FAR if self.native else FAR) else None

    def costs(self, f, rc, kind):
        """Every template's difference from this cell: {char: difference}."""
        if self.native:
            g = around(f, rc)
            return {ch: slid(g, t) for ch, t in self.t[kind]}
        g = cell(f, rc)
        return {ch: float(np.abs(g - t).mean()) for ch, t in self.t[kind]}

    def read_clock(self, f, prev=None, step_cost=6.0):
        """The clock as the valid value (0:00-20:00) whose four digit cells match best, each value's summed
        difference plus step_cost when it isn't prev or up to 3 below it (the clock only runs down; a new period
        jumps). None when even the best averages more than the cut-off a cell."""
        c = [self.costs(f, rc, "clk") for rc in CELLS["min"] + CELLS["sec"]]
        best = None
        for v in range(0, 1201):
            m, s_ = divmod(v, 60)
            chars = (str(m // 10) if m >= 10 else " ", str(m % 10), str(s_ // 10), str(s_ % 10))
            if any(ch not in c[i] for i, ch in enumerate(chars)):
                continue
            cost = sum(c[i][ch] for i, ch in enumerate(chars))
            if prev is not None and not 0 <= prev - v <= 3:
                cost += step_cost
            if best is None or cost < best[0]:
                best = (cost, v)
        limit = 4 * (NATIVE_FAR if self.native else FAR)
        return best[1] if best and best[0] <= limit else None

    def char(self, f, rc, kind):
        ch, d = self.best(f, rc, kind)
        return ch if d <= (NATIVE_FAR if self.native else FAR) else None

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
