"""Pilot (2026-10-23): can a RetroArch video of a Genesis game stand in for a Helper recording? A video and a recording
of the same game: line the video's frames up with the game's frames, then find the players and the puck in sampled
frames and compare with where the recording says they were.
- Mapping (found on 2026-10-23_1107_LA-BOS): the game draws 256 x 224 (H32) and RetroArch's video stretches it to
  320 wide; a game position (x, y) is at pixel (SX x (x - camX + 126.5), camY - y + CY), camX / camY the camera words
  Hpos BD1C / Vpos BD18 (updatescroll: Hscroll = -64 - Hpos), at the skates.
- Line-up: video frame = game frame (the frame counter B03E) + an offset that grows at each pause (the video keeps
  recording the pause screen, the game's counter stops). Found stretch by stretch from the blue lines (video_lines.py):
  the offset at which the recorded camera puts the blue lines (+-BLUE_Y) on the rows the video shows them.
- The rink: the median of many aligned frames, pixel by pixel in rink coordinates (the sprites move, the rink doesn't).
- Sprites: pixels far from the rink's colour, in connected blobs; a player's spot is the bottom middle of his blob,
  the puck a small dark blob. Each recorded skater or goalie on screen is matched to the nearest blob spot within MATCH.
Gentle mode. python analysis/video/video_pilot.py <video.mkv> <lines.tsv> <capture folder> <out folder> [every n frames]"""
import json
import sys
from collections import Counter
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
from export_match import Capture  # noqa: E402
from lowload import breathe, gentle  # noqa: E402

SX, CY, BLUE_Y, HUD_ROWS = 1.25, 111, 86, 34
CX = SX * 126.5
MATCH, FG, FEET = 10, 60, 6         # pixels: a recorded spot to a blob's; colour distance from the rink that counts as sprite
WORLD = (-220, 220, -380, 380)   # rink coordinates kept for the background (x0, x1, y0, y1)


def sw(v):
    return v - 65536 if v >= 32768 else v


def recording(folder):
    cap = Capture(Path(folder))
    raw = [cap.word(i, 0xB03E) for i in range(cap.count)]
    fc = [raw[0]]
    for i in range(1, len(raw)):                      # step by step: the 16-bit counter wraps, and the game resets it
        d = (raw[i] - raw[i - 1] + 32768) % 65536 - 32768   # at each period's start (to just below 0): a step of 1
        fc.append(fc[-1] + (d if abs(d) < 1000 else 1))    # there, the line-up finds the new offset
    return cap, np.array(fc, np.int64)


def blue_rows(lines_path):
    rows = []
    for line in open(lines_path):
        p = line.rstrip("\n").split("\t")
        rows.append([float(x) for x in p[1].split(",") if x])
    B = np.zeros((len(rows), 192), bool)
    for j, r in enumerate(rows):
        for y in r:
            for d in (-1, 0, 1):
                if 0 <= int(round(y)) + d < 192:
                    B[j, int(round(y)) + d] = True
    return B


def align(cap, fc, B, start_k=0, window=600, span=60 * 180):
    """[(first sample, last sample, offset)]: video frame = fc + offset, stretch by stretch."""
    cy = np.array([sw(cap.word(i, 0xBD18)) for i in range(cap.count)], float)
    out, k0 = [], start_k
    for a in range(0, cap.count, window):
        s = np.arange(a, min(cap.count, a + window), 2)
        r1 = np.round(cy[s] + CY - BLUE_Y).astype(int)
        r2 = np.round(cy[s] + CY + BLUE_Y).astype(int)
        vis = ((r1 >= 0) & (r1 < 190)) | ((r2 >= 0) & (r2 < 190))
        best = search(B, fc, s, r1, r2, vis, k0 - 3, k0 + (span if out else len(B)))   # the first: anywhere
        if best[0] < 0.45:                       # lost (an intermission longer than `span`): look further on
            wide = search(B, fc, s, r1, r2, vis, k0 - 3, len(B))
            best = max(best, wide)
        out.append((a, int(s[-1]), best[1], round(float(best[0]), 3)))
        k0 = best[1]
    return out


def search(B, fc, s, r1, r2, vis, k_from, k_to):
    best = (-1, k_from)
    for k in range(k_from, k_to):
        j = fc[s] + k
        if j.min() >= len(B):
            break
        if j.min() < 0 or j.max() >= len(B):
            continue
        h = (B[j, np.clip(r1, 0, 191)] & (r1 >= 0) & (r1 < 190)) | (B[j, np.clip(r2, 0, 191)] & (r2 >= 0) & (r2 < 190))
        score = h[vis].mean() if vis.any() else 0
        if score > best[0]:
            best = (score, k)
    return best


def offset_at(stretches, i):
    return next(k for a, b, k, _ in stretches if a <= i <= b + 1)


class Frames:
    """Video frames by index, read forward (decoding is sequential)."""

    def __init__(self, path):
        self.c = av.open(path)
        self.v = self.c.streams.video[0]
        self.it, self.j = self.c.decode(self.v), -1

    def get(self, j):
        while self.j < j:
            fr = next(self.it)
            self.j += 1
            if self.j == j:
                return fr.to_ndarray(format="rgb24")
        raise ValueError("frames must be asked for in order")


def to_world(sy, sx, camX, camY):
    return np.round((sx - CX) / SX + camX), camY + CY - sy


def to_screen(x, y, camX, camY):
    return SX * (x - camX) + CX, camY - y + CY


def main():
    vid, lines, folder, out = sys.argv[1:5]
    every = int(sys.argv[5]) if len(sys.argv) > 5 else 30
    gentle()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    cap, fc = recording(folder)
    B = blue_rows(lines)
    stretches = align(cap, fc, B)
    (out / "align.json").write_text(json.dumps(stretches))
    cam = lambda i: (sw(cap.word(i, 0xBD1C)), sw(cap.word(i, 0xBD18)))
    live = [i for i in range(cap.count) if cap.byte(i, 0xFFF7) == 0]
    # ---- the rink: median of aligned frames in rink coordinates
    x0, x1, y0, y1 = WORLD
    # frames where the camera is moving: standing players (faceoffs) would stay in the median
    moving = [i for i in live[5:] if abs(sw(cap.word(i, 0xBD18)) - sw(cap.word(i - 5, 0xBD18))) >= 6
              or abs(sw(cap.word(i, 0xBD1C)) - sw(cap.word(i - 5, 0xBD1C))) >= 6]
    picks = moving[::max(1, len(moving) // 400)]
    stack = np.zeros((y1 - y0, x1 - x0, 3, 15), np.uint8)
    count = np.zeros((y1 - y0, x1 - x0), np.int16)
    F = Frames(vid)
    ys, xs = np.mgrid[0:224 - HUD_ROWS, 0:320]
    good = {a for a, b, k, score in stretches if score >= 0.45}      # stretches that lined up
    usable = lambda i: (i // 600) * 600 in good
    for j, i in sorted({int(fc[i] + offset_at(stretches, i)): i for i in picks if usable(i)}.items()):
        a = F.get(j)[:224 - HUD_ROWS]
        camX, camY = cam(i)
        wx, wy = to_world(ys, xs, camX, camY)
        ok = (wx >= x0) & (wx < x1) & (wy > y0) & (wy <= y1)
        X, Y = (wx[ok] - x0).astype(int), (y1 - wy[ok]).astype(int)
        n = count[Y, X]
        keep = n < 15
        stack[Y[keep], X[keep], :, n[keep]] = a[ok][keep]
        count[Y[keep], X[keep]] += 1
        breathe()
    rink = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
    for yy in range(y1 - y0):
        for xx in np.nonzero(count[yy])[0]:
            rink[yy, xx] = np.median(stack[yy, xx, :, :count[yy, xx]], axis=1)
        if yy % 40 == 0:
            breathe()
    from PIL import Image
    Image.fromarray(rink).save(out / "rink_from_video.png")
    # ---- sprites in sampled frames, against the recording
    F = Frames(vid)
    st = Counter()
    errs, puck_errs = [], []
    for j, i in sorted({int(fc[i] + offset_at(stretches, i)): i for i in live[::every] if usable(i)}.items()):
        a = F.get(j)[:224 - HUD_ROWS].astype(np.int16)
        camX, camY = cam(i)
        wx, wy = to_world(ys, xs, camX, camY)
        ok = (wx >= x0) & (wx < x1) & (wy > y0) & (wy <= y1)
        bg = np.zeros_like(a)
        bg[ok] = rink[(y1 - wy[ok]).astype(int), (wx[ok] - x0).astype(int)]
        on_ice = (bg[..., 1] > 120) | (bg[..., 2] > 180)          # ice and its lines, not the boards or the crowd
        sh = register(a, bg, on_ice & ok)              # a frame or two of timing error moves the rink a few pixels
        bg, on_ice, ok = (np.roll(np.roll(z, sh[0], axis=0), sh[1], axis=1) for z in (bg, on_ice, ok))
        st["shift_" + str(sh)] += 1
        fg = foreground(a, bg) & ok & on_ice
        blobs = label(fg)
        spots = []
        for pix in blobs:
            if len(pix) < 4 or len(pix) > 1500:
                continue
            py = np.array([p[0] for p in pix])
            px = np.array([p[1] for p in pix])
            bottom = py.max()
            spots.append((px[py >= bottom - 2].mean(), bottom, len(pix), a[py, px].mean()))
        st["frames"] += 1
        st["blobs"] += len(spots)
        for k in range(12):
            role = cap.byte(i, 0xB04A + 0x80 * k + 0x35)
            if role == 0xFF:
                continue
            x, y = sw(cap.word(i, 0xB04A + 0x80 * k)), sw(cap.word(i, 0xB04A + 0x80 * k + 0x14))
            sx, sy = to_screen(x, y, camX, camY)
            if not (4 <= sx < 316 and 8 <= sy < 224 - HUD_ROWS - 2):
                continue
            st["onscreen"] += 1
            sy += FEET                                  # the blob's bottom is the skates' bottom, below his spot
            d = min(((abs(bx - sx) ** 2 + abs(by - sy) ** 2) ** 0.5, bx - sx, by - sy) for bx, by, n, c in spots if n >= 30) \
                if any(n >= 30 for *_, n, c in spots) else None
            if d and d[0] <= MATCH:
                st["found"] += 1
                errs.append((d[1], d[2]))
        x, y = sw(cap.word(i, 0xB04A + 0x80 * 14)), sw(cap.word(i, 0xB04A + 0x80 * 14 + 0x14))
        z = sw(cap.word(i, 0xB04A + 0x80 * 14 + 0x18))
        sx, sy = to_screen(x, y, camX, camY)
        sy -= z
        if 4 <= sx < 316 and 8 <= sy < 224 - HUD_ROWS - 2 and z > -100:
            st["puck_onscreen"] += 1
            small = [(bx, by) for bx, by, n, c in spots if n < 20 and c < 90]
            if small:
                d = min(((bx - sx) ** 2 + (by - sy) ** 2) ** 0.5 for bx, by in small)
                if d <= 6:
                    st["puck_found"] += 1
                    puck_errs.append(d)
        breathe()
    e = np.array(errs) if errs else np.zeros((0, 2))
    res = {"stretches": len(stretches), "align_score_median": float(np.median([s[3] for s in stretches])),
           "frames": st["frames"], "players_onscreen": st["onscreen"], "players_found": st["found"],
           "found_share": st["found"] / max(1, st["onscreen"]),
           "err_x_median": float(np.median(e[:, 0])) if len(e) else None, "err_y_median": float(np.median(e[:, 1])) if len(e) else None,
           "err_abs_median": float(np.median(np.hypot(e[:, 0], e[:, 1]))) if len(e) else None,
           "blobs_per_frame": st["blobs"] / max(1, st["frames"]),
           "puck_onscreen": st["puck_onscreen"], "puck_found": st["puck_found"],
           "rink_shifts": sorted(((v, k[6:]) for k, v in st.items() if k.startswith("shift_")), reverse=True)[:10]}
    (out / "pilot.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def register(a, bg, mask, reach=4):
    """The (rows, columns) shift of the rink picture, within `reach`, that best matches the frame on the ice."""
    best = None
    sub = mask[::2, ::2]
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            sh = np.roll(np.roll(bg, dy, axis=0), dx, axis=1)[::2, ::2]
            e = np.minimum(np.abs(a[::2, ::2] - sh).sum(axis=2), 120)[sub].mean() if sub.any() else 0
            if best is None or e < best[0]:
                best = (e, dy, dx)
    return best[1], best[2]


def foreground(a, bg):
    """Pixels unlike every rink pixel within one pixel of them: the stretch from 256 to 320 wide draws the rink's edges
    a little differently at each scroll position, which a plain difference shows as outlines."""
    d = np.full(a.shape[:2], 10 ** 6, np.int32)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            sh = np.roll(np.roll(bg, dy, axis=0), dx, axis=1)
            d = np.minimum(d, np.abs(a - sh).sum(axis=2))
    return d > FG


def label(mask):
    """Connected blobs of a boolean mask (8-neighbour), as lists of (row, col)."""
    seen = np.zeros_like(mask)
    H, W = mask.shape
    blobs = []
    for r, c in zip(*np.nonzero(mask)):
        if seen[r, c]:
            continue
        stack, pix = [(r, c)], []
        seen[r, c] = True
        while stack:
            y, x = stack.pop()
            pix.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and mask[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        stack.append((yy, xx))
        blobs.append(pix)
    return blobs


if __name__ == "__main__":
    main()
