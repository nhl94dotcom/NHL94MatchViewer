"""The camera's position up and down the ice (Vpos, the game's BD18) from a RetroArch video alone (Genesis), frame by
frame, from the rink's cross lines found by video_lines.py: a line of game y drawn on row r means Vpos = r + y - CY.
The blue lines are at +-86, the red ones at 0 (the centre, dashed) and +-263 (the goal lines); each row seen gives a
candidate per line of its colour. A lone blue line doesn't say which one it is, so each candidate is scored by how
well the frame's rows (their share of red and of blue pixels) match the rink's rows there - the rink's row profile
taken from a picture of the whole rink in rink coordinates (video_pilot.py's rink_from_video.png) - plus a small
penalty for moving far from the previous frame's position. With nothing seen, the last position is held. The camera
follows the puck, so the screen's middle row says roughly where the play is.
python analysis/video/video_camera.py <video.mkv> <lines.tsv> <rink.png> <out.npy>"""
import sys

import av
import numpy as np
from PIL import Image

CY = 111
BLUE, RED = (86, -86), (0, 263, -263)
VPOS = (-210, 262)          # the camera's range (Vpos) in the recordings
STEP = 40                   # largest believable move between frames seen (a few frames apart at most)


def read_lines(path):
    blue, red = [], []
    for line in open(path):
        p = line.rstrip("\n").split("\t")
        blue.append([float(x) for x in p[1].split(",") if x])
        red.append([float(x) for x in p[2].split(",") if x])
    return blue, red


Y_TOP = 380                 # rink_from_video.png: row 0 is rink y 380 (video_pilot.WORLD)
ROWS = 190                  # the picture's rows above the HUD


def profile(img):
    """Each row's share of red and of blue pixels."""
    a = img.astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    red = ((r > 150) & (g < 110) & (b < 130)).mean(axis=1)
    blue = ((b > 150) & (r < 120) & (g < 200)).mean(axis=1)
    return np.stack([red, blue], axis=1)


def track(video, blue, red, rink_png):
    rink = profile(np.array(Image.open(rink_png))[:, 60:380])      # the ice's width only
    c = av.open(video)
    v = c.streams.video[0]
    cam = np.full(len(blue), np.nan)
    prev = None
    for j, fr in enumerate(c.decode(v)):
        if j >= len(blue):
            break
        cands = [r + y - CY for r in blue[j] for y in BLUE] + [r + y - CY for r in red[j] for y in RED]
        cands = sorted({round(x) for x in cands if VPOS[0] - 5 <= x <= VPOS[1] + 5})
        if not cands:
            cam[j] = prev if prev is not None else np.nan
            continue
        if len(cands) > 1 or prev is None or abs(cands[0] - prev) > STEP:
            f = profile(fr.to_ndarray(format="rgb24")[:ROWS])
            def cost(x):
                top = int(Y_TOP - (x + CY))         # rink row of the frame's first row
                if top < 0 or top + ROWS > len(rink):
                    return 1e9
                return np.abs(f - rink[top:top + ROWS]).sum() + (0.01 * abs(x - prev) if prev is not None else 0)
            best = min(cands, key=cost)
        else:
            best = cands[0]
        cam[j] = prev = best
    return cam


if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "scoring_map"))
    from lowload import gentle
    gentle()
    b, r = read_lines(sys.argv[2])
    np.save(sys.argv[4], track(sys.argv[1], b, r, sys.argv[3]))
