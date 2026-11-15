"""Sprites found in a Genesis video frame (2026-11-14; the video reader's third step, first part).

With the camera known (camera_track.py), the rink as the ROM draws it is the frame's exact background: every pixel
whose colour isn't within the range of the background's pixel and its two horizontal neighbours (each channel, give
or take MARGIN: a recording stretched from 256 to 320 and squeezed back blends neighbours) belongs to a sprite (the players, the puck, the referee, the centre-ice
logo, the goal nets' fronts) or to the crowd's animation. The differing pixels above the score boxes are grouped into
blobs (8-connected, after closing gaps of one pixel); each blob's box, pixel count and bottom centre (a skater's
feet) are kept.

Screen and rink: x = X - Hpos + 128, y = 107 - Y + Vpos - Z for a skater's body (fitted on 12 still-camera frames of
nhl94_playoffs-261113-133619.mkv against the recordings); the feet a few pixels lower.

python analysis/vision/sprites.py static VIDEO CAMERA_TRACK.npz OUT.npz   (learn_static: the nets and the logo)
python analysis/vision/sprites.py check VIDEO CAMERA_TRACK.npz [FIRST] [COUNT]
  each recorded player on screen against the blobs: found (a blob's box within 3 px of his body point) or missed, by
  how crowded the spot was."""
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import camera_track as C  # noqa: E402

BODY_X, BODY_Y = 128, 107
MIN_PIXELS = 12
MARGIN = 28                       # per channel: the emulators' colour levels differ by up to 16


STATIC_SHARE = 0.6                # a rink pixel unlike the drawn rink in this share of the frames that show it: a
                                  # sprite that stays put (the nets, the centre-ice logo), left out of every mask


def learn_static(video, track_npz, rom, out, step=20):
    """The static sprites: per rink pixel (the padded render's coordinates), how often it differs from the drawn rink
    in the placed frames (every step-th); those at STATIC_SHARE or more saved as a mask."""
    cams = {int(r[0]): r for r in np.load(track_npz)["rows"]}
    rink = C.Rink(rom)
    seen = np.zeros(rink.img.shape[:2], np.int32)
    diff = np.zeros(rink.img.shape[:2], np.int32)
    for n, f in C.frames(video):
        if n % step or n not in cams or not cams[n][4]:
            continue
        _, hpos, vpos = (int(x) for x in cams[n][:3])
        u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
        m = fg_mask(rink, f, hpos, vpos)
        seen[v:v + C.HUD_TOP - 2, u:u + C.NATIVE_W] += 1
        diff[v:v + C.HUD_TOP - 2, u:u + C.NATIVE_W] += m[:C.HUD_TOP - 2]
    mask = (seen >= 20) & (diff >= STATIC_SHARE * np.maximum(seen, 1))
    np.savez_compressed(out, mask=mask, seen=seen, diff=diff)
    print(f"static sprite pixels: {int(mask.sum())} ({out})")
    return mask


def fg_mask(rink, f, hpos, vpos, static=None):
    u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
    near = np.stack([rink.img[v:v + C.H, u + du:u + du + C.NATIVE_W] for du in (-1, 0, 1)])
    lo, hi = near.min(axis=0) - MARGIN, near.max(axis=0) + MARGIN
    m = ((f < lo) | (f > hi)).any(axis=2)
    m[C.HUD_TOP - 2:] = False
    if static is not None:
        m &= ~static[v:v + C.H, u:u + C.NATIVE_W]
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
    if sys.argv[1] == "static":
        learn_static(Path(sys.argv[2]), sys.argv[3], Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin", sys.argv[4])
    elif sys.argv[1] == "check":
        check(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0,
              int(sys.argv[5]) if len(sys.argv) > 5 else 20000)


# ---- players by team (2026-11-14) ----
# Each team's uniform palette from the ROM (tools/systems/genesis.read_teams: the home palette for the home team, the
# away palette for the visitors, as the game loads them into lines 2 and 3), each slot weighted by how often the
# player sprites use it (the colour indices of every tile in Spritetiles, $5DE84-$9E724 on retail: slots 11 and 12,
# the jersey, most). Only the slots where the two palettes differ by more than OWN_GAP speak for a team. A sprite pixel
# is a team's when that team's weight for its colour (slots within PIX_GAP) is at least RATIO times the other's; the
# rest of each sprite blob (shared colours: skin, black, white on both) goes to its nearest labelled pixel. Each team's
# part of a blob, grouped (gaps of TEAM_CLOSE filled), is a player (or a few of one team, together) when it has
# TEAM_MIN pixels or more and at least SAT_MIN of its labelled pixels saturated (not grey: the nets and the referee
# are grey and white). A group of n x PLAYER_PIXELS (rounded) is split into n players by k-means on its pixels'
# places. The close-up faceoff box (a sprite block of 2,500+ pixels, at least 60% filled) is left out
# first.

OWN_GAP, PIX_GAP, RATIO, TEAM_CLOSE, TEAM_MIN, SAT_MIN, GREY = 60, 30, 2.0, 2, 120, 3, 40
PLAYER_PIXELS = 316                # one player's part (median of 117 matched on nhl94_playoffs-261113-133619.mkv)
SPRITETILES = (0x5DE84, 0x9E724)


def video_rgb(hexcolour):
    from rink_render import LEVELS
    v = [int(hexcolour[i:i + 2], 16) for i in (1, 3, 5)]
    return np.array([LEVELS[round(c * 7 / 255)] for c in v], np.int16)


def slot_weights(rom_bytes):
    t = np.frombuffer(rom_bytes[SPRITETILES[0]:SPRITETILES[1]], np.uint8)
    c = np.bincount(np.concatenate([t >> 4, t & 15]), minlength=16).astype(float)
    c[0] = 0
    return c / c.sum()


def team_colours(rom, home_abbr, away_abbr):
    """[(slot colours (k, 3), weights (k,)) for home, visitors]: the slots where the two teams differ."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    from systems import genesis
    teams = {t["abbr"]: t for t in genesis.read_teams(Path(rom))}
    w = slot_weights(Path(rom).read_bytes())
    home = [video_rgb(c) for c in teams[home_abbr]["palettes"][0]]
    away = [video_rgb(c) for c in teams[away_abbr]["palettes"][1]]
    diff = [k for k in range(1, 16) if np.abs(home[k] - away[k]).sum() > OWN_GAP]
    return [(np.array([pal[k] for k in diff]), w[diff]) for pal in (home, away)]


def grow(m, k):
    for _ in range(k):
        p = np.pad(m, 1)
        m = m | p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:]
    return m


def team_evidence(f, colours):
    ev = []
    for cols, w in colours:
        near = np.abs(f[:, :, None, :] - cols[None, None, :, :]).sum(axis=3) <= PIX_GAP
        ev.append((near * w).sum(axis=2))
    return ev


def kmeans(xs, ys, k, rounds=12):
    """k centres of the points (x, y, count each), started evenly along the group's longer side."""
    if k == 1:
        return [(float(xs.mean()), float(ys.mean()), len(xs))]
    pts = np.stack([xs, ys], axis=1).astype(float)
    axis = 0 if np.ptp(xs) >= np.ptp(ys) else 1
    order = np.argsort(pts[:, axis])
    cen = np.array([pts[order[int((j + 0.5) * len(pts) / k)]] for j in range(k)])
    for _ in range(rounds):
        a = ((pts[:, None, :] - cen[None]) ** 2).sum(axis=2).argmin(axis=1)
        cen = np.array([pts[a == j].mean(axis=0) if (a == j).any() else cen[j] for j in range(k)])
    return [(float(cen[j, 0]), float(cen[j, 1]), int((a == j).sum())) for j in range(k)]


_NEAR_ICE = {}
ICE_MARGIN = 20                   # a skater's height above the ice's edge: none of the crowd beyond it


def near_ice(rink, hpos, vpos, margin=ICE_MARGIN):
    """The ice in this frame's view, grown by margin pixels (a skater at the boards shows over their edge)."""
    u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
    key = (id(rink), margin)
    if key not in _NEAR_ICE:
        _NEAR_ICE[key] = grow(rink.ice(), margin)
    return _NEAR_ICE[key][v:v + C.H, u:u + C.NATIVE_W]



def players(rink, f, hpos, vpos, colours, static=None, lr=None):
    """[(team 0 home / 1 visitors, x, y, pixels)]: each player group's centre, in screen pixels (only on or near the
    ice: the crowd's animation left out)."""
    fg = fg_mask(rink, f, hpos, vpos, static) & near_ice(rink, hpos, vpos)
    lab = np.full(fg.shape, -1, np.int8)
    if lr is not None:                                         # a soft video: soft_lr's table (2026-11-15)
        L = lr_image(f, lr)
        lab[fg & (L > LR_SURE)] = 0
        lab[fg & (L < -LR_SURE)] = 1
    else:
        eh, ea = team_evidence(f, colours)
        lab[fg & (eh > 0) & (eh >= RATIO * ea)] = 0
        lab[fg & (ea > 0) & (ea >= RATIO * eh)] = 1
    sat = (f.max(axis=2) - f.min(axis=2)) >= GREY
    out = []
    for ys, xs in label(close1(fg)):
        w, h = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
        if w * h >= 2500 and len(ys) >= 0.6 * w * h:          # the close-up faceoff box
            continue
        keep = fg[ys, xs]
        ys, xs = ys[keep], xs[keep]
        l = lab[ys, xs]
        if not (l >= 0).any():
            continue
        known = np.flatnonzero(l >= 0)
        if (l < 0).any():                                      # the rest to the nearest labelled pixel
            unk = np.flatnonzero(l < 0)
            d = (ys[unk, None] - ys[None, known]) ** 2 + (xs[unk, None] - xs[None, known]) ** 2
            l = l.copy()
            l[unk] = l[known[d.argmin(axis=1)]]
        for team in (0, 1):
            sel = l == team
            if sel.sum() < TEAM_MIN:
                continue
            m = np.zeros(fg.shape, bool)
            m[ys[sel], xs[sel]] = True
            for gy, gx in label(grow(m, TEAM_CLOSE)):
                inside = m[gy, gx]
                py, px = gy[inside], gx[inside]
                if len(py) < TEAM_MIN:
                    continue
                if (sat[py, px] & (lab[py, px] == team)).sum() < SAT_MIN:
                    continue
                k = max(1, round(len(py) / PLAYER_PIXELS))
                for cx, cy, cn in kmeans(px, py, k):
                    out.append((team, cx, cy, cn))
    return out


# ---- the teams' colours as a soft video shows them (2026-11-15) ----
# Blur and half-resolution colour (4:2:0) turn a uniform's stripes into colours no palette slot has, and the ice
# blends into every edge. So the two uniforms are drawn as the video would show them: every frame with team colours
# (extract_sprites.compose, both facings) in each team's palette over the ice, blurred [a, 1 - 2a, a] across and down
# (the video's own blur, fit_blur) and its colour averaged over 2 x 2 (YCbCr); the sprite pixels (unlike the ice by
# MARGIN) give each team a colour histogram (SOFT_BINS levels a channel), and a video pixel's log likelihood ratio,
# home against visitors, is soft_lr's table at its colour.

SOFT_BINS, SOFT_ICE, LR_SURE = 8, (140, 239, 239), 0.7    # LR_SURE: a pixel's team when twice as likely


def _ycc(img):
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return y, 0.564 * (b - y), 0.713 * (r - y)


def _rgb(y, cb, cr):
    r = y + 1.403 * cr
    b = y + 1.773 * cb
    g = (y - 0.299 * r - 0.114 * b) / 0.587
    return np.stack([r, g, b], axis=-1)


def degrade(img, blur=(0.3, 0.25), chroma=True):
    """img (h, w, 3) float: blurred [a, 1 - 2a, a] across then down, and its colour averaged over 2 x 2."""
    ah, av = blur
    p = np.pad(img, ((1, 1), (1, 1), (0, 0)), mode="edge")
    hz = ah * p[:, :-2] + (1 - 2 * ah) * p[:, 1:-1] + ah * p[:, 2:]
    out = av * hz[:-2] + (1 - 2 * av) * hz[1:-1] + av * hz[2:]
    if chroma:
        y, cb, cr = _ycc(out)
        h, w = y.shape
        for c in (cb, cr):
            c2 = c[:h - h % 2, :w - w % 2].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))
            c[:h - h % 2, :w - w % 2] = np.repeat(np.repeat(c2, 2, axis=0), 2, axis=1)
        out = _rgb(y, cb, cr)
    return np.clip(out, 0, 255)


def soft_lr(rom, home_abbr, away_abbr, blur=(0.3, 0.25), chroma=True):
    """(SOFT_BINS,) * 3 table: log P(colour | home) - log P(colour | visitors), from the uniforms drawn degraded."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    import extract_sprites as X
    from systems import genesis
    rb = Path(rom).read_bytes()
    teams = {t["abbr"]: t for t in genesis.read_teams(Path(rom))}
    rink_pal = [video_rgb("#%02x%02x%02x" % tuple(((w >> s) & 0xE) * 255 // 14 for s in (0, 4, 8)))
                for w in (struct.unpack_from(">H", rb, X.RINK_PALETTE + 2 * i)[0] for i in range(32))]
    pals = [[video_rgb(c) for c in teams[home_abbr]["palettes"][0]], [video_rgb(c) for c in teams[away_abbr]["palettes"][1]]]
    hist = [np.ones((SOFT_BINS,) * 3), np.ones((SOFT_BINS,) * 3)]
    ice = np.array(SOFT_ICE, float)
    for n in range(1, X.FRAME_COUNT):
        left, top, canvas = X.compose(rb, n)
        slots = np.array([[sl for sl, v in row] for row in canvas]); vals = np.array([[v for sl, v in row] for row in canvas])
        team_px = ((slots == 0) & (vals > 0)).sum()
        if team_px < 0.3 * max(1, (vals > 0).sum()) or (vals > 0).sum() < 60:
            continue
        for t in (0, 1):
            img = np.tile(ice, (vals.shape[0] + 6, vals.shape[1] + 6, 1))
            for (j, i), v in np.ndenumerate(vals):
                if v:
                    sl = slots[j, i]
                    img[j + 3, i + 3] = pals[t][v] if sl == 0 else rink_pal[(sl - 1) * 16 + v]
            for im in (img, img[:, ::-1]):
                d = degrade(im, blur, chroma)
                fg = (np.abs(d - ice) > MARGIN).any(axis=2)
                q = np.clip((d[fg] * SOFT_BINS / 256).astype(int), 0, SOFT_BINS - 1)
                np.add.at(hist[t], (q[:, 0], q[:, 1], q[:, 2]), 1)
    ph, pa = hist[0] / hist[0].sum(), hist[1] / hist[1].sum()
    return np.log(ph) - np.log(pa)


def lr_image(f, table):
    q = np.clip((f.astype(int) * SOFT_BINS) // 256, 0, SOFT_BINS - 1)
    return table[q[..., 0], q[..., 1], q[..., 2]]


# ---- the puck (2026-11-14) ----
# A loose puck is a small dark sprite on its own, on the ice (camera_track.Rink.ice), or, beside or over a player,
# the flat puck's ring shape (rings: found inside player groups too): a group of sprite pixels (no gap filling) of PUCK_MIN-PUCK_MAX pixels
# with at least PUCK_DARK of them near black (every channel under DARK_MAX; the stars' outlines are dark blue). Its centre is the dark pixels' mean; on the rink the
# recorded puck is at x = X - Hpos + 128, y = 107 - Y + Vpos - Z (+ PUCK_DY: the sprite sits that much lower).

PUCK_MIN, PUCK_MAX, PUCK_DARK, DARK_MAX = 3, 30, 0.2, 70
PUCK_DY = 4


def puck_candidates(rink, f, hpos, vpos, static=None):
    """[(x, y, pixels)] in screen pixels."""
    fg = fg_mask(rink, f, hpos, vpos, static)
    dark = f.max(axis=2) < DARK_MAX                      # near black: not the stars' dark blue
    u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
    ice = rink.ice()[v:v + C.H, u:u + C.NATIVE_W]       # on the ice only: not the crowd's animation
    out = []
    for ys, xs in label(fg):
        n = len(ys)
        if not PUCK_MIN <= n <= PUCK_MAX:
            continue
        d = dark[ys, xs]
        if d.mean() < PUCK_DARK:
            continue
        cx, cy = float(xs[d].mean()), float(ys[d].mean())
        if not ice[int(cy), int(cx)]:
            continue
        out.append((cx, cy, n))
    for cx, cy in rings(dark, fg & ice):                    # the flat puck's ring, on or beside a player
        if all(abs(cx - x) > 4 or abs(cy - y) > 3 for x, y, _ in out):
            out.append((cx, cy, 0))
    return out


def rings(dark, where):
    """The flat puck's shape (a 256-wide frame): a dark row of 4 over a row dark at both ends (x-2 or x-3, and x+3
    or x+4) and light in its middle two (x, x+1), over a dark row of 4; the light middle in a sprite pixel. Returns
    the middles' centres."""
    H, W = dark.shape
    d = np.zeros((H + 8, W + 8), bool)
    d[4:-4, 4:-4] = dark

    def at(dy, dx):
        return d[4 + dy:4 + dy + H, 4 + dx:4 + dx + W]
    top = at(-1, -1) & at(-1, 0) & at(-1, 1) & at(-1, 2)
    bot = at(1, -1) & at(1, 0) & at(1, 1) & at(1, 2)
    ends = (at(0, -2) | at(0, -3)) & (at(0, 3) | at(0, 4))
    mid = ~at(0, 0) & ~at(0, 1)
    ys, xs = np.nonzero(top & bot & ends & mid & where)
    return [(float(x) + 0.5, float(y)) for y, x in zip(ys, xs)]
