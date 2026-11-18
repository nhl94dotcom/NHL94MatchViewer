"""Inverse rendering of a clean Genesis recording (2026-11-16; VIEWER_NOTES "Inverse rendering"): the players read as
the ROM's own sprites, frame by frame, without the match file.

A clean RetroArch recording is lossless and stretched 256 -> 320 nearest-neighbour, so the game's own 256-wide frame
comes back exactly (native()). Every pixel is coded by snapping each channel to the nearest of the eight 3-bit levels
(the recording's green is off by up to 2). With the camera known (camera_track.py), the ROM's rink is the background.

A player is a ROM animation frame (extract_sprites.compose) in his team's palette (palette line 2 the team's colours,
0 and 1 the rink's), mirrored or not, at a screen point (the player's position): a template. A template at a point
scores its pixels matching the frame, less half those that don't, less those that show the rink exactly (the sprite
should cover them). Tracking: a player's next frame is searched among the frames that follow his current one in the
recorded games (a transition table) within a few pixels of where his motion puts him; pixels that differ from the rink
and no track explains form blobs, and a blob gets the full search (every frame, both mirrorings, both teams, anchored
on its box). Teams: the two palettes (home, away) that explain the first frames best, from every team's in the ROM.

Screen <-> rink: sx = 128 + X - Hpos, sy = 120 - Y + Vpos (the record's position; the sprite's pieces are offsets
from it)."""
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools"))
import rink_render  # noqa: E402
import extract_sprites as XS  # noqa: E402

LV = rink_render.LEVELS.astype(int)
H_PLAY = 186                                   # rows above the score boxes
FIRST = np.array([int(np.nonzero(np.floor((np.arange(320) + 0.5) * 0.8 - 0.25).astype(int) == j)[0][0]) for j in range(256)])
PUCK_FRAMES = tuple(range(394, 405))            # 394 the shadow, 395-404 the puck


def native(frame):
    """The game's 256-wide frame from a recording frame (320 wide: nearest-stretched; 256: as it is)."""
    return frame[:, FIRST] if frame.shape[1] == 320 else frame


def code(img):
    idx = np.abs(img[..., None].astype(int) - LV).argmin(-1)
    return idx[..., 0] * 64 + idx[..., 1] * 8 + idx[..., 2]


def hexcode(h):
    v = [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    return code(np.array([[[LV[min(7, round(c * 14 / 255) // 2)] for c in v]]]))[0, 0]


class Sprites:
    """Coded templates of every ROM frame for a palette pair."""

    def __init__(self, rom, home_pal, away_pal):
        self.rom = rom
        fixed = [[rink_render.colour(struct.unpack_from(">H", rom, XS.RINK_PALETTE + 32 * line + 2 * i)[0]) for i in range(16)]
                 for line in (0, 1)]
        self.fixed = [[int(code(np.array([[c]]))[0, 0]) for c in line] for line in fixed]
        self.team = [[int(hexcode(c)) for c in p] for p in (home_pal, away_pal)]
        self.cache = {}

    def get(self, fr, team, mir):
        key = (fr, team, mir)
        if key not in self.cache:
            try:
                left, top, canvas = XS.compose(self.rom, fr)
            except Exception:
                self.cache[key] = None
                return None
            ys, xs, cs = [], [], []
            for j, row in enumerate(canvas):
                for i, (slot, v) in enumerate(row):
                    if v:
                        ys.append(j + top)
                        xs.append(i + left)
                        cs.append(self.team[team][v] if slot == 0 else self.fixed[slot - 1][v])
            ys, xs, cs = np.array(ys), np.array(xs), np.array(cs)
            if mir:
                xs = -1 - xs
            self.cache[key] = (ys, xs, cs) if len(ys) else None
        return self.cache[key]


def score(img, bg, tpl, pts):
    """Scores of a template at screen points pts (n, 2: sy, sx) in a coded frame: (score, matched, pixels)."""
    ys, xs, cs = tpl
    H, W = img.shape
    Y = ys[None, :] + pts[:, :1]
    X = xs[None, :] + pts[:, 1:]
    ok = (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
    Yc, Xc = Y.clip(0, H - 1), X.clip(0, W - 1)
    v, b = img[Yc, Xc], bg[Yc, Xc]
    ok &= v >= 0                                  # pixels marked -1 (static sprites, off the ice) count neither way
    match = ((v == cs) & ok).sum(1)
    bgm = ((v == b) & (cs != b) & ok).sum(1)
    n = ok.sum(1)
    return match - 0.5 * (n - match) - bgm, match, n


def blobs(mask, least=20):
    """Connected regions (8-way) of a boolean mask: lists of (y, x) arrays, at least `least` pixels."""
    lab = np.zeros(mask.shape, np.int32)
    out = []
    ys, xs = np.nonzero(mask)
    for y0, x0 in zip(ys, xs):
        if lab[y0, x0]:
            continue
        n = len(out) + 1
        stack = [(y0, x0)]
        lab[y0, x0] = n
        pts = []
        while stack:
            y, x = stack.pop()
            pts.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        stack.append((yy, xx))
        out.append(np.array(pts))
    return [p for p in out if len(p) >= least]


def transitions(matches, K=12, steps=(1, 2, 3)):
    """frame -> the frames that follow it within a few samples in recorded games (Counter), from match dicts."""
    nxt = defaultdict(Counter)
    for m in matches:
        fr = m["frame"]
        N = len(m["t"])
        for k in range(K):
            seq = [int(fr[(q * K + k) * 3:(q * K + k) * 3 + 3], 16) for q in range(N)]
            for s in steps:
                for a, b in zip(seq, seq[s:]):
                    if 1 <= a < 846 and 1 <= b < 846:
                        nxt[a][b] += 1
    return nxt


class Track:
    _next = 0

    def __init__(self, team, fr, mir, sy, sx, sc):
        self.team, self.fr, self.mir, self.sy, self.sx, self.sc = team, fr, mir, sy, sx, sc
        self.id = Track._next                       # a track's own number, kept while it lives
        Track._next += 1
        self.vy = self.vx = 0.0
        self.miss = 0


class Reader:
    def __init__(self, sprites, trans, players=range(1, 846)):
        self.S = sprites
        self.trans = trans
        self.players = [f for f in players if f not in PUCK_FRAMES and self.team_pixels(f) >= 40]
        self.player_set = set(self.players)
        self.tracks = []
        self.n = 0
        self.max_new = 6                            # full searches a frame (new sprites are rare once tracking)
        self.detect_every = 6                       # frames between searches for new sprites
        self.unexplained = 250                      # ... or sooner when this many sprite pixels are unexplained

    def team_pixels(self, fr):
        """Pixels of frame fr drawn in the team's palette line (a frame with none can't be told by team: sticks, the
        referee's pieces, effects)."""
        try:
            left, top, canvas = XS.compose(self.S.rom, fr)
        except Exception:
            return 0
        return sum(1 for row in canvas for slot, v in row if v and slot == 0)

    def seeds(self, blob):
        """Feet: the blob's lowest pixel in each 4-pixel column band (a skater's feet are at the bottom of his
        sprite), less those within 4 of a lower one."""
        out = {}
        for y, x in blob:
            band = x // 4
            if band not in out or y > out[band][0]:
                out[band] = (y, x)
        pts = sorted(out.values(), key=lambda p: -p[0])
        keep = []
        for y, x in pts:
            if all(abs(x - kx) > 5 or abs(y - ky) > 5 for ky, kx in keep):
                keep.append((y, x))
        return keep

    def bank(self, team):
        """Every player template of a team, padded into arrays for batched scoring: (keys, ys, xs, cs, valid, bottom,
        foot x)."""
        if not hasattr(self, "_bank"):
            self._bank = {}
        if team not in self._bank:
            keys, tpls = [], []
            for fr in self.players:
                for mir in (False, True):
                    t = self.S.get(fr, team, mir)
                    if t is not None and len(t[0]) >= 100:
                        keys.append((fr, mir))
                        tpls.append(t)
            M = max(len(t[0]) for t in tpls)
            P = len(tpls)
            ys = np.zeros((P, M), np.int32); xs = np.zeros((P, M), np.int32); cs = np.full((P, M), -9, np.int32)
            valid = np.zeros((P, M), bool)
            bot = np.zeros(P, np.int32); fx = np.zeros(P, np.int32)
            for i, (y, x, c) in enumerate(tpls):
                n = len(y)
                ys[i, :n], xs[i, :n], cs[i, :n], valid[i, :n] = y, x, c, True
                bot[i] = y.max()
                fx[i] = int(x[y == bot[i]].mean())
            self._bank[team] = (keys, ys, xs, cs, valid, bot, fx)
        return self._bank[team]

    SIL = 80                                        # the silhouette window (pixels), feet at its bottom middle

    def silhouettes(self):
        """FFTs of every player template's silhouette (shape only: the same for both teams), padded to SIL x SIL,
        with each one's top-left offset from its point, lowest row and foot x."""
        if getattr(self, "_sil", None) is None:
            keys, ys, xs, cs, valid, bot, fx = self.bank(0)
            S = self.SIL
            masks = np.zeros((len(keys), S, S), np.float32)
            top = np.zeros(len(keys), np.int32)
            lef = np.zeros(len(keys), np.int32)
            for i in range(len(keys)):
                y, x = ys[i][valid[i]], xs[i][valid[i]]
                top[i], lef[i] = y.min(), x.min()
                yy, xx = y - top[i], x - lef[i]
                k = (yy < S) & (xx < S)
                masks[i, yy[k], xx[k]] = 1
            self._sil = (np.fft.rfft2(masks), masks.sum((1, 2)), top, lef)
        return self._sil

    def full_search(self, img, bg, seed, teams=(0, 1), dys=(-2, -1, 0, 1, 2), keep=30):
        """The best template with its lowest pixels at the seed (rows dys, within 5 columns): every template's
        silhouette against the sprite pixels around the seed by FFT correlation (all offsets at once), then the best
        `keep` placements scored in full, both teams."""
        sy0, sx0 = seed
        S = self.SIL
        F, size, top, lef = self.silhouettes()
        keys, ys, xs, cs, valid, bot, fx = self.bank(0)
        r0, c0 = sy0 - S + 4, sx0 - S // 2                          # the window's top-left in the frame
        H, W = img.shape
        win = np.zeros((S, S), np.float32)
        known = np.zeros((S, S), np.float32)
        ya, yb, xa, xb = max(0, r0), min(H, r0 + S), max(0, c0), min(W, c0 + S)
        if ya >= yb or xa >= xb:
            return None
        sub = img[ya:yb, xa:xb]
        win[ya - r0:yb - r0, xa - c0:xb - c0] = ((sub != bg[ya:yb, xa:xb]) & (sub >= 0))
        known[ya - r0:yb - r0, xa - c0:xb - c0] = (sub >= 0)
        # correlation: hits[i, u, v] = sprite pixels under template i with its top-left at (u, v)
        hits = np.fft.irfft2(np.conj(F) * np.fft.rfft2(win)[None], s=(S, S))
        # the placements allowed: lowest row at the seed's row + dy, foot within 5 columns
        dyr = np.array(dys)
        dxr = np.arange(-5, 6)
        u = (sy0 - bot[:, None] + top[:, None] + dyr[None, :]) - r0          # (P, len(dys))
        v = (sx0 - fx[:, None] + lef[:, None] + dxr[None, :]) - c0           # (P, 11)
        U = np.broadcast_to(u[:, :, None], (len(keys), len(dyr), len(dxr))) % S
        V = np.broadcast_to(v[:, None, :], (len(keys), len(dyr), len(dxr))) % S
        h = hits[np.arange(len(keys))[:, None, None], U, V]
        sil = (1.5 * h - 0.5 * size[:, None, None]) / size[:, None, None]
        flat = sil.reshape(len(keys), -1)
        bi = flat.argmax(1)
        order = np.argsort(-flat[np.arange(len(keys)), bi])[:keep]
        best = None
        for i in order:
            fr, mir = keys[i]
            j = bi[i]
            dy, dx = dyr[j // len(dxr)], dxr[j % len(dxr)]
            pts = np.array([(sy0 - bot[i] + dy + a, sx0 - fx[i] + dx + b) for a in (-1, 0, 1) for b in (-1, 0, 1)])
            for team in teams:
                t = self.S.get(fr, team, mir)
                sc, mt, n = score(img, bg, t, pts)
                k = int(sc.argmax())
                if best is None or sc[k] > best[0]:
                    best = (float(sc[k]), team, fr, mir, int(pts[k][0]), int(pts[k][1]), int(n[k]))
        return best

    LABEL = (438, 292)                              # the greys of the number and pad letter under a pad star

    def feet_marks(self, img, bg):
        """The stars at the live tracks' feet (390 / 391 a person's pad, 392 the puck carrier: drawn at the sprite's
        point, checked within a pixel, 60% of their pixels right) and, under a pad star, the player's number and pad
        letter (its greys in the box below it): explained, so they no longer read as a new sprite every frame."""
        out = np.zeros(img.shape, bool)
        if not hasattr(self, "_feet"):
            self._feet = {fr: self.S.get(fr, 0, False) for fr in (390, 391, 392)}
        H, W = img.shape
        for tr in self.tracks:
            if tr.miss:
                continue
            pts = np.array([(tr.sy + dy, tr.sx + dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1)])
            for fr, t in self._feet.items():
                if t is None:
                    continue
                sc, mt, n = score(img, bg, t, pts)
                share = mt / np.maximum(1, len(t[0]))
                k = int(share.argmax())
                if share[k] < 0.6:
                    continue
                sy, sx = int(pts[k][0]), int(pts[k][1])
                Y, X = t[0] + sy, t[1] + sx
                ok = (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
                out[Y[ok], X[ok]] |= img[Y[ok], X[ok]] == t[2][ok]
                if fr != 392:
                    ya, yb, xa, xb = max(0, sy + 8), min(H, sy + 20), max(0, sx - 12), min(W, sx + 18)
                    box = img[ya:yb, xa:xb]
                    out[ya:yb, xa:xb] |= np.isin(box, self.LABEL) & (box != bg[ya:yb, xa:xb])
        return out

    def place(self, img, t, sy, sx):
        Y, X = t[0] + sy, t[1] + sx
        ok = (Y >= 0) & (Y < img.shape[0]) & (X >= 0) & (X < img.shape[1])
        return Y[ok], X[ok]

    def detect(self, img, bg, diff, limit=24):
        """New sprites in the unexplained pixels, front to back: seeds at the residual's bottoms (a blob cut by the
        score boxes' top also tries feet below it), the best template accepted, its pixels then occluded (-1) for
        the sprites behind it."""
        work = img.copy()
        res = diff.copy()
        out, tries = [], 0
        while tries < limit:
            bl = blobs(res, least=40 if self.n <= 1 else 120)
            if not bl:
                break
            cand = []
            for b in bl:
                for seed in self.seeds(b)[:3]:
                    edge = seed[0] >= img.shape[0] - 2
                    cand.append((seed, (-2, 0, 2, 4, 6, 8, 10, 14) if edge else tuple(range(-12, 3, 2))))
            best = None
            for seed, dys in cand[:6]:
                tries += 1
                r = self.full_search(work, bg, seed, dys=dys)
                if r and (best is None or r[0] / max(1, r[6]) > best[0] / max(1, best[6])):
                    best = r
            if best is None or best[0] / max(1, best[6]) < 0.45:
                break
            _, team, fr, mir, sy, sx, n = best
            out.append(best)
            Y, X = self.place(img, self.S.get(fr, team, mir), sy, sx)
            res[Y, X] = False
            work[Y, X] = -1
            # whatever is left of a blob after its sprite is taken out: drop specks
        return out

    def step(self, img, bg, R=3, cam=None):
        if cam is not None:                                         # tracks follow the rink: the camera's move shifts
            if getattr(self, "cam", None) is not None:              # every sprite on the screen
                dh, dv = cam[0] - self.cam[0], cam[1] - self.cam[1]
                for tr in self.tracks:
                    tr.sx -= dh
                    tr.sy += dv
            self.cam = cam
        work = img.copy()
        drawn = np.zeros(img.shape, bool)
        keep = []
        for tr in sorted(self.tracks, key=lambda t: -t.sy):        # front (lower on the screen) first
            py, px = tr.sy + tr.vy, tr.sx + tr.vx
            cands = [tr.fr] + [f for f, _ in self.trans.get(tr.fr, Counter()).most_common(16) if f != tr.fr and f in self.player_set][:12]
            best = None
            pts = np.array([(int(round(py)) + dy, int(round(px)) + dx) for dy in range(-R, R + 1) for dx in range(-R, R + 1)])
            for fr in cands:
                for mir in (tr.mir, not tr.mir):
                    t = self.S.get(fr, tr.team, mir)
                    if t is None:
                        continue
                    s, mt, n = score(work, bg, t, pts)
                    i = int(s.argmax())
                    val = s[i] - (2 if mir != tr.mir else 0)
                    if best is None or val > best[0]:
                        best = (val, fr, mir, int(pts[i][0]), int(pts[i][1]), float(s[i]) / max(1, n[i]))
            if best is None or best[5] < 0.35:
                tr.miss += 1
                if tr.miss <= 8:
                    keep.append(tr)
                continue
            _, fr, mir, sy, sx, per = best
            tr.vy, tr.vx = 0.5 * tr.vy + 0.5 * (sy - tr.sy), 0.5 * tr.vx + 0.5 * (sx - tr.sx)
            tr.fr, tr.mir, tr.sy, tr.sx, tr.sc, tr.miss = fr, mir, sy, sx, per, 0
            Y, X = self.place(img, self.S.get(fr, tr.team, mir), sy, sx)
            drawn[Y, X] = True
            work[Y, X] = -1                                         # occluded for the sprites behind
            keep.append(tr)
        self.tracks = keep
        self.n += 1
        if self.n % 15 == 0:                                        # a track's identity checked again: both teams,
            for tr in self.tracks:                                  # every frame, where it stands
                if tr.miss:
                    continue
                t = self.S.get(tr.fr, tr.team, tr.mir)
                bot = int(t[0].max())
                fx = int(t[1][t[0] == bot].mean())
                r = self.full_search(img, bg, (tr.sy + bot, tr.sx + fx), dys=(-2, 0, 2))
                if r and r[0] / max(1, r[6]) > tr.sc + 0.1 and (r[1], r[2]) != (tr.team, tr.fr):
                    _, tr.team, tr.fr, tr.mir, tr.sy, tr.sx, n = r
                    tr.sc = r[0] / n
        drawn |= self.feet_marks(img, bg)
        self.drawn = drawn
        near = drawn.copy()
        for d in (-2, -1, 1, 2):                                    # pixels next to a drawn sprite: its stick, specks
            near |= np.roll(drawn, d, 0) | np.roll(drawn, d, 1)
        diff = (img != bg) & (img >= 0) & ~near
        # look for new sprites every detect_every frames, or at once when enough is unexplained (a player coming
        # into view, one lost)
        if self.n > 1 and self.n % self.detect_every and diff.sum() < self.unexplained:
            return [(t.team, t.fr, t.mir, t.sy, t.sx, t.sc) for t in self.tracks if t.miss == 0]
        for best in self.detect(work, bg, diff, limit=self.max_new):
            _, team, fr, mir, sy, sx, n = best
            if any(abs(sx - t.sx) < 6 and abs(sy - t.sy) < 6 for t in self.tracks if t.miss == 0):
                continue
            self.tracks = [t for t in self.tracks if not (t.miss and abs(sx - t.sx) < 12 and abs(sy - t.sy) < 12)]
            self.tracks.append(Track(team, fr, mir, sy, sx, best[0] / n))
        return [(t.team, t.fr, t.mir, t.sy, t.sx, t.sc) for t in self.tracks if t.miss == 0]


def puck_templates(S):
    """The puck's frames (395-404) and its shadow (394): (frame, ys, xs, codes), drawn in the rink's fixed palette."""
    out = []
    for fr in PUCK_FRAMES:
        t = S.get(fr, 0, False)
        if t is not None:
            out.append((fr,) + t)
    return out


def _ring(ys, xs):
    """The pixels touching a template but not in it (8-way)."""
    inside = set(zip(ys.tolist(), xs.tolist()))
    ring = {(y + dy, x + dx) for y, x in inside for dy in (-1, 0, 1) for dx in (-1, 0, 1)} - inside
    r = np.array(sorted(ring))
    return r[:, 0], r[:, 1]


def read_puck(reader, img, bg, pred=None, R=3, near=12):
    """The puck where no player sprite explains the pixels. Near the predicted point first (within `near`), else every
    small leftover blob (2-40 pixels); each puck frame within R pixels of a candidate counts when 80% of its pixels
    match exactly and at most 20% of the ring of pixels around it shows the puck's own colours (a puck is a small
    separate thing: a dark sliver inside a skate or stick doesn't count). Its shadow (394) is then looked for
    straight below, 0-60 rows down: the gap is the height (no shadow: on the ice, the shadow under the puck).
    Returns (sy of the ice point, sx, frame, z, share matched) or None."""
    if not hasattr(reader, "_puck"):
        reader._puck = [(fr, ys, xs, cs) + _ring(ys, xs) for fr, ys, xs, cs in puck_templates(reader.S)]
    drawn = getattr(reader, "drawn", np.zeros(img.shape, bool))
    H, W = img.shape

    def search(pts, rad):
        best = None
        for cy, cx in pts:
            for fr, ys, xs, cs, ry, rx in reader._puck:
                if fr == 394:
                    continue
                oy, ox = int(round(ys.mean())), int(round(xs.mean()))
                grid = np.array([(cy - oy + dy, cx - ox + dx) for dy in range(-rad, rad + 1) for dx in range(-rad, rad + 1)])
                # a cheap first test: a placement matching 80% of a puck frame's n pixels has at most n // 5 wrong,
                # so at least one of any n // 5 + 1 of them right; placements with none right are skipped
                k3 = min(len(cs), len(cs) // 5 + 1)
                Y3 = ys[None, :k3] + grid[:, :1]
                X3 = xs[None, :k3] + grid[:, 1:]
                ok3 = (Y3 >= 0) & (Y3 < H) & (X3 >= 0) & (X3 < W)
                Y3c, X3c = Y3.clip(0, H - 1), X3.clip(0, W - 1)
                hit3 = ((img[Y3c, X3c] == cs[None, :k3]) & ok3 & ~drawn[Y3c, X3c]).any(1)
                grid = grid[hit3]
                if not len(grid):
                    continue
                Y = ys[None, :] + grid[:, :1]
                X = xs[None, :] + grid[:, 1:]
                ok = (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
                v = img[Y.clip(0, H - 1), X.clip(0, W - 1)]
                m = ((v == cs) & ok & ~drawn[Y.clip(0, H - 1), X.clip(0, W - 1)]).sum(1) / len(cs)
                RY = ry[None, :] + grid[:, :1]
                RX = rx[None, :] + grid[:, 1:]
                rv = img[RY.clip(0, H - 1), RX.clip(0, W - 1)]
                ringbad = np.isin(rv, cs).mean(1)
                m = np.where(ringbad <= 0.2, m, 0)
                i = int(m.argmax())
                if m[i] >= 0.8 and (best is None or m[i] > best[0]):
                    best = (float(m[i]), int(grid[i][0]), int(grid[i][1]), fr, len(cs))
        return best

    best = search([pred], near) if pred is not None else None
    if best is None:
        res = (img != bg) & (img >= 0) & ~drawn
        pts = []
        for b in blobs(res, least=2):
            if len(b) <= 40:
                cy, cx = b.mean(0)
                pts.append((int(round(cy)), int(round(cx))))
        best = search(pts, R)
    if best is None:
        return None
    share, py, px, fr, n = best
    sh = next(t for t in reader._puck if t[0] == 394)
    _, ys, xs, cs = sh[:4]
    z = 0
    for dz in range(1, 61):
        for dx in (0, -1, 1):
            Y, X = ys + py + dz, xs + px + dx
            if Y.max() >= H or X.min() < 0 or X.max() >= W:
                continue
            if (img[Y, X] == cs).mean() >= 0.8:
                z = dz
                break
        if z:
            break
    return (py + z, px, fr, z, share)


def blade(reader, tr):
    """The stick blade of a read sprite (team, frame, mirror, sy, sx): the ROM's HotList point of its frame ($A44C8,
    a signed (x, y) byte pair a frame; x negated when mirrored, y up the rink so down the screen)."""
    if not hasattr(reader, "_hot"):
        rom = reader.S.rom
        reader._hot = [struct.unpack_from(">bb", rom, 0xA44C8 + 2 * fr) for fr in range(846)]
    team, fr, mir, sy, sx = tr[:5]
    hx, hy = reader._hot[fr] if 0 < fr < 846 else (0, 0)
    if mir:
        hx = -hx
    return sy + hy, sx + hx


def read_puck_all(reader, img, bg, read, pred=None):
    """The puck: loose and seen (read_puck), else on a carrier's stick: the read player whose blade point shows the
    most of a flat puck (frames 395 / 399, 50% of its pixels matching within 1 pixel) or, if none shows it, whose
    blade is nearest the last puck (within 16 pixels). Returns (sy, sx, frame or 'carried', z, how)."""
    p = read_puck(reader, img, bg, pred)
    if p:
        return p + ("seen",)
    if not hasattr(reader, "_puck"):
        read_puck(reader, img, bg, None)
    flat = [t for t in reader._puck if t[0] in (395, 399)]
    H, W = img.shape
    best = None
    for tr in read:
        by, bx = blade(reader, tr)
        for fr, ys, xs, cs, _, _ in flat:
            oy, ox = int(round(ys.mean())), int(round(xs.mean()))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    Y, X = ys + by - oy + dy, xs + bx - ox + dx
                    if Y.min() < 0 or Y.max() >= H or X.min() < 0 or X.max() >= W:
                        continue
                    share = float((img[Y, X] == cs).mean())
                    if share >= 0.5 and (best is None or share > best[0]):
                        best = (share, by, bx)
    if best:
        return (best[1], best[2], "carried", 0, best[0], "on a stick")
    if pred is not None and read:
        d, by, bx = min((abs(b[0] - pred[0]) + abs(b[1] - pred[1]), b[0], b[1]) for b in (blade(reader, tr) for tr in read))
        if d <= 16:
            return (by, bx, "carried", 0, 0.0, "nearest stick")
    return None


# Frames drawn only for the puck carrier (97% or more of their appearances in BOS-CHI games 2-4 with the puck): the
# skate-with-puck strides 2-39 (not their first frames, 1, 6, 11 ..., shared with plain skating) and four others.
CARRY_FRAMES = {2, 3, 4, 5, 7, 8, 9, 10, 12, 13, 14, 15, 17, 18, 19, 20, 22, 23, 24, 25, 27, 28, 29, 30, 32, 33, 34,
                35, 37, 39, 103, 109, 139, 626}


STAR_FRAMES = (390, 391, 392)   # the joypad stars (pads 1 / 2: outline) and the possession star (filled), fixed colours


def read_stars(reader, img, live, least=0.6):
    """The stars the game draws at a player's feet (the same sprite point as his: offset 0, checked within a pixel):
    {track id: set of star frames}. 392 is under the puck carrier (and the last carrier while the puck is loose);
    390 / 391 under the skaters the people control."""
    if not hasattr(reader, "_stars"):
        reader._stars = {fr: reader.S.get(fr, 0, False) for fr in STAR_FRAMES}
    H, W = img.shape
    out = {}
    for t in live:
        for fr, tp in reader._stars.items():
            if tp is None:
                continue
            ys, xs, cs = tp
            best = 0.0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    Y, X = ys + t.sy + dy, xs + t.sx + dx
                    ok = (Y >= 0) & (Y < H) & (X >= 0) & (X < W)
                    if ok.mean() < 0.9:
                        continue
                    best = max(best, float((img[Y[ok], X[ok]] == cs[ok]).mean()))
            if best >= least:
                out.setdefault(t.id, set()).add(fr)
    return out


OUT_OF_VIEW = 180                # frames a carrier gone out of the read area keeps the puck
NEAR_BLADE, WITH_HIM = 10, 3     # a seen puck this near a blade (L1 pixels), moving with him (pixels a frame): carried


class PuckTracker:
    """The puck from frame to frame, with memory (2026-11-17):
    1. seen (read_puck, near the predicted point first): on the ice within 3 pixels of a read player's blade, or within
       NEAR_BLADE and moving with him (its velocity within WITH_HIM of his), carried by him; else loose, its rink
       velocity from the last seen point;
    2. else a read player's blade showing half a flat puck (pixels in the puck's colours that no read sprite draws
       there itself): carried by him;
    3. else a read player standing on the possession star (frame 392, read_stars): carried by him; else one in a
       carry-only frame (CARRY_FRAMES);
    4. else the last carrier still read: carried by him (his blade); or gone out of the read area (under the score
       box, off a side) for up to OUT_OF_VIEW frames: still his;
    5. else loose and unseen: carried on by its velocity (the game's loose puck keeps about 0.998 of its speed a frame)
       for up to `coast` frames, then given to the blade nearest that point within 16 pixels;
    6. else the blade nearest the last puck within 16 pixels.
    Positions kept in rink units (X = sx - 128 + Hpos, Y = 112 - sy + Vpos) so a camera pan doesn't move them.
    step(...) returns (sy, sx, frame or 'carried', z, share, how) or None."""
    def __init__(self, reader, coast=20):
        self.R, self.coast = reader, coast
        self.mode, self.carrier, self.pos, self.vel, self.unseen = None, None, None, (0.0, 0.0), 0
        self.last_seen = None
        self.out_of_view, self.stars = 0, {}

    @staticmethod
    def to_rink(sy, sx, cam):
        return 112 - sy + cam[1], sx - 128 + cam[0]

    @staticmethod
    def to_screen(Y, X, cam):
        return 112 - Y + cam[1], X + 128 - cam[0]

    def _carried(self, tr, cam, how, share=0.0):
        self.out_of_view = 0
        t = (tr.team, tr.fr, tr.mir, tr.sy, tr.sx)
        by, bx = blade(self.R, t)
        self.mode, self.carrier, self.pos, self.vel, self.unseen = "carried", tr, self.to_rink(by, bx, cam), (0.0, 0.0), 0
        return (by, bx, "carried", 0, share, how)

    def step(self, img, bg, cam):
        R = self.R
        live = [t for t in R.tracks if t.miss == 0]
        pred = None
        if self.pos is not None:
            Y, X = self.pos
            if self.mode == "loose":
                Y, X = Y + self.vel[0], X + self.vel[1]
            pred = self.to_screen(Y, X, cam)
            pred = (int(round(pred[0])), int(round(pred[1])))
        p = read_puck(R, img, bg, pred)
        if p and p[3] == 0:                     # seen on the ice at a read player's blade (3 pixels), or near it (10)
            Yr, Xr = self.to_rink(p[0], p[1], cam)              # and moving with him (3 pixels a frame): he has it
            pv = None
            if self.last_seen is not None and R.n - self.last_seen[2] == 1:
                pv = (-(Yr - self.last_seen[0]), Xr - self.last_seen[1])         # screen rows, columns a frame
            self.last_seen = (Yr, Xr, R.n)
            at = []
            for t in live:
                b = blade(R, (t.team, t.fr, t.mir, t.sy, t.sx))
                d = abs(b[0] - p[0]) + abs(b[1] - p[1])
                if d <= 3 or (d <= NEAR_BLADE and pv is not None and abs(pv[0] - t.vy) + abs(pv[1] - t.vx) <= WITH_HIM):
                    at.append((d, t))
            if at:
                tr = min(at, key=lambda x: x[0])[1]
                self.mode, self.carrier, self.pos, self.vel, self.unseen = "carried", tr, self.to_rink(p[0], p[1], cam), (0.0, 0.0), 0
                return p + ("seen at a stick",)
        if p:
            Y, X = self.to_rink(p[0], p[1], cam)
            if self.mode == "loose" and self.unseen == 0 and self.pos is not None:
                self.vel = (0.5 * self.vel[0] + 0.5 * (Y - self.pos[0]), 0.5 * self.vel[1] + 0.5 * (X - self.pos[1]))
            elif self.mode != "loose":
                self.vel = (0.0, 0.0)
            self.mode, self.carrier, self.pos, self.unseen = "loose", None, (Y, X), 0
            return p + ("seen",)
        if not hasattr(R, "_puck"):
            read_puck(R, img, bg, None)
        flat = [t for t in R._puck if t[0] in (395, 399)]
        H, W = img.shape
        synth = np.full(img.shape, -1)                  # the read sprites as drawn, back to front: a puck colour that
        for t in sorted(live, key=lambda t: t.sy):      # a sprite draws there itself is no sign of the puck
            tp = R.S.get(t.fr, t.team, t.mir)
            if tp is None:
                continue
            Yy, Xx = R.place(img, tp, t.sy, t.sx)
            ys, xs, cs = tp
            ok = (ys + t.sy >= 0) & (ys + t.sy < H) & (xs + t.sx >= 0) & (xs + t.sx < W)
            synth[(ys + t.sy)[ok], (xs + t.sx)[ok]] = cs[ok]
        best = None
        for tr in live:
            by, bx = blade(R, (tr.team, tr.fr, tr.mir, tr.sy, tr.sx))
            for fr, ys, xs, cs, _, _ in flat:
                oy, ox = int(round(ys.mean())), int(round(xs.mean()))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        Yy, Xx = ys + by - oy + dy, xs + bx - ox + dx
                        if Yy.min() < 0 or Yy.max() >= H or Xx.min() < 0 or Xx.max() >= W:
                            continue
                        hit = (img[Yy, Xx] == cs) & (synth[Yy, Xx] != cs)
                        share = float(hit.mean())
                        if share >= 0.5 and (best is None or share > best[0]):
                            best = (share, tr)
        if best:
            return self._carried(best[1], cam, "on a stick", best[0])
        self.stars = read_stars(R, img, live)
        st = [t for t in live if 392 in self.stars.get(t.id, ())]
        if st:                                          # the possession star under him
            return self._carried(st[0], cam, "possession star")
        cf = [t for t in live if t.fr in CARRY_FRAMES]
        if cf:
            if self.carrier in cf:
                return self._carried(self.carrier, cam, "carry frame")
            if pred is not None:
                cf.sort(key=lambda t: sum(abs(a - b) for a, b in zip(blade(R, (t.team, t.fr, t.mir, t.sy, t.sx)), pred)))
            return self._carried(cf[0], cam, "carry frame")
        if self.mode == "carried" and self.carrier in live:
            return self._carried(self.carrier, cam, "same carrier")
        if self.mode == "carried" and self.carrier is not None and self.carrier not in live and self.out_of_view < OUT_OF_VIEW:
            c = self.carrier                            # he went out of the read area (under the score box, off the
            if c.sy > H_PLAY - 24 or c.sx < 16 or c.sx > 240 or c.sy < 16:   # side): he keeps it until it shows again
                self.out_of_view += 1
                by, bx = blade(R, (c.team, c.fr, c.mir, c.sy, c.sx))
                return (by, bx, "carried", 0, 0.0, "out of view")
        if self.mode == "loose" and self.unseen < self.coast and pred is not None:
            self.unseen += 1
            self.vel = (self.vel[0] * 0.998, self.vel[1] * 0.998)
            self.pos = (self.pos[0] + self.vel[0], self.pos[1] + self.vel[1])
            near = [(sum(abs(a - b) for a, b in zip(blade(R, (t.team, t.fr, t.mir, t.sy, t.sx)), pred)), t) for t in live]
            near = [x for x in near if x[0] <= 6]
            if near:
                return self._carried(min(near, key=lambda x: x[0])[1], cam, "caught")
            return (pred[0], pred[1], "coasting", 0, 0.0, "coasting")
        if pred is not None and live:
            d, tr = min(((sum(abs(a - b) for a, b in zip(blade(R, (t.team, t.fr, t.mir, t.sy, t.sx)), pred)), t) for t in live),
                        key=lambda x: x[0])
            if d <= 16:
                return self._carried(tr, cam, "nearest stick")
        return None
