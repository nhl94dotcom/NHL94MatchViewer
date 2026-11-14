"""The puck in a Genesis video (2026-11-14; the video reader's puck, second version: the game's own puck pictures and
the camera's lead, then the puck followed over time).

Templates: the puck's sprite frames from the ROM (extract_sprites.compose: 395 / 399 the flat puck on the ice, the
commonest by far; 396-398 and 400-404 in the air: a bar, a sliver, two diagonals, a round one) and its shadow (394,
drawn as object 15 on the ice), each as colours from the rink's palette line 1 (the puck's: colour 4 near black,
1 / 11 the light middle) with its offset from the object's place. A template matches where its pixels' classes agree
(dark: every channel under DARK; light: R + G + B over LIGHT, counting half: a blurred video washes the middle; the
shadow's: any sprite pixel; videos' colour levels differ, so not exact colours), and the pixels just outside its
outline are not dark (a dark patch of a player's pants or skates matches the small shapes inside; a puck stands
out); the in-air shapes' scores x IN_AIR and its pixels are
sprite pixels (unlike the drawn rink) on the ice; the score is the share agreeing.

Each frame's candidates (score MIN_SCORE or more, the best per spot) are weighed by the camera's lead: the camera
follows the puck, so the puck is near the screen's middle (in the recordings the puck's Y is Vpos - 8, spread 45;
X 1.25 Hpos): prior(x, y) a Gaussian about (128 + 0.25 Hpos, 115) with spreads SPREAD.

find(...) -> [(x, y, score, weight, name)] in screen pixels: the object's place (as the recordings' x = X - Hpos +
128, y = 107 - Y + Vpos - Z)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import camera_track as C  # noqa: E402
import rink_render  # noqa: E402

PUCK_FRAMES = (395, 399, 396, 397, 398, 400, 401, 402, 403, 404)
FLAT = (395, 399, 394)            # the flat puck and the shadow: 97% of the recordings' frames
IN_AIR = 0.9                      # the in-air shapes' scores scaled (a thin dark stroke is common in a player)
SHADOW = 394
DARK, LIGHT, MIN_SCORE = 80, 450, 0.8
SPREAD = (55.0, 60.0)
PARTIAL = False                   # score the visible part only (2026-11-14); measured worse alone (26.8% against 46.7%)
MIN_VISIBLE = 0.4                 # at least this share of the picture showing


def templates(rom_bytes):
    import extract_sprites as X
    import struct
    a = rink_render.find_rink(rom_bytes)
    p, _ = struct.unpack(">II", rom_bytes[a:a + 8])
    pal = np.array([rink_render.colour(w) for w in struct.unpack(">64H", rom_bytes[a + p:a + p + 128])], np.int16)
    out = []
    for n in PUCK_FRAMES:                  # not the shadow: "any sprite pixel" matched inside every player
        left, top, rows = X.compose(rom_bytes, n)
        pts = []
        for y, row in enumerate(rows):
            for x, (slot, c) in enumerate(row):
                if c:
                    tot = int(pal[16 + c].sum())
                    cls = "D" if tot < 200 else "L" if tot > 400 else "M"   # dark, light, other (the shadow)
                    weight = 0.5 if cls == "L" else 1.0                      # the light middle: half
                    pts.append((y + top, x + left, cls, weight))
        if pts:
            inside = {(dy, dx) for dy, dx, _, _ in pts}
            ring = {(dy + a, dx + b) for dy, dx in inside for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1))} - inside
            pts += [(dy, dx, "N", 1.0) for dy, dx in sorted(ring)]     # just outside the puck: not dark
            out.append((n, pts))
    return out


class Finder:
    def __init__(self, rom):
        self.rink = C.Rink(rom) if not isinstance(rom, C.Rink) else rom
        self.t = templates(Path(rom).read_bytes() if not isinstance(rom, C.Rink) else
                           (Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin").read_bytes())

    def find(self, f, hpos, vpos, fg=None, static=None, partial=None, both=False):
        """Candidates [(x, y, score, weighted score, frame)], best first.
        Classic scoring (2026-11-14 morning, 31% placed frame by frame, 46.7% tracked): each puck picture's pixels by
        class, the ring just outside not dark, every matching pixel a sprite pixel (the static sprites, the nets,
        masked out).
        partial (PARTIAL; False by default since the evening's measurement): score only the visible part: pixels that
        are sprite pixels of another class taken as covered and left out, plain rink counting against; at least
        MIN_VISIBLE showing; the nets not masked (the crease and the net's mouth searched too).
        both=True: {"classic": [...], "partial": [...]} from one pass (puck_eval caches both)."""
        import sprites as S
        partial = PARTIAL if partial is None else partial
        modes = ("classic", "partial") if both else ("partial",) if partial else ("classic",)
        u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
        ice = self.rink.ice()[v:v + C.H, u:u + C.NATIVE_W]
        H, W = C.HUD_TOP, C.NATIVE_W
        dark = f.max(axis=2) < DARK
        light = f.sum(axis=2) > LIGHT
        res = {}
        for mode in modes:
            fgm = fg if fg is not None else S.fg_mask(self.rink, f, hpos, vpos, static if mode == "classic" else None)
            classes = {"D": dark, "L": light, "M": fgm, "N": ~dark}       # by class, not exact colour: levels differ
            cands = {}
            for n, pts in self.t:
                if mode == "classic":
                    total = sum(w for _, _, _, w in pts)
                    score = np.zeros((H, W))
                    onfg = np.zeros((H, W))
                else:
                    total = sum(w for _, _, c, w in pts if c != "N")
                    matched = np.zeros((H, W))
                    against = np.zeros((H, W))
                    ringbad = np.zeros((H, W))
                    nring = sum(1 for _, _, c, _ in pts if c == "N")
                for dy, dx, col, w in pts:
                    # template pixel (dy, dx) of an object at (y, x) is frame pixel (y + dy, x + dx)
                    ys0, ys1 = max(0, -dy), min(H, H - dy)
                    xs0, xs1 = max(0, -dx), min(W, W - dx)
                    if ys0 >= ys1 or xs0 >= xs1:
                        continue
                    ok = classes[col][ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
                    sp = fgm[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
                    if mode == "classic":
                        score[ys0:ys1, xs0:xs1] += w * ok
                        onfg[ys0:ys1, xs0:xs1] += w * (ok & (sp if col != "N" else True))
                        continue
                    if col == "N":
                        ringbad[ys0:ys1, xs0:xs1] += ~ok         # dark just outside: part of something bigger
                        continue
                    matched[ys0:ys1, xs0:xs1] += w * (ok & sp)
                    against[ys0:ys1, xs0:xs1] += w * (~ok & ~sp)   # plain rink where the puck would show
                if mode == "classic":
                    sc = np.minimum(score, onfg) / total
                    floor = MIN_SCORE
                else:
                    visible = matched + against
                    sc = matched / np.maximum(visible + 0.5 * ringbad * total / max(nring, 1), 1e-6)
                    sc = np.where(visible >= MIN_VISIBLE * total,
                                  sc * (0.6 + 0.4 * np.minimum(1.0, visible / (0.8 * total))), 0)
                    floor = MIN_SCORE * 0.75
                sc *= 1.0 if n in FLAT else IN_AIR
                ys, xs = np.nonzero((sc >= floor) & ice[:H])
                for y, x in zip(ys, xs):
                    key = (y // 3, x // 3)
                    if key not in cands or sc[y, x] > cands[key][2]:
                        cands[key] = (float(x), float(y), float(sc[y, x]), n)
            res[mode] = self._weigh(cands, hpos)
        return res if both else res[modes[0]]

    def _weigh(self, cands, hpos):
        cx, cy = 128 + 0.25 * hpos, 115.0
        out = []
        for x, y, s, n in cands.values():
            prior = np.exp(-0.5 * (((x - cx) / SPREAD[0]) ** 2 + ((y - cy) / SPREAD[1]) ** 2))
            out.append((x, y, s, s * prior, n))
        return sorted(out, key=lambda c: -c[3])
