"""The rink's cross lines in each frame of a RetroArch video (Genesis): the rows where a blue line (the blue lines) or
a red line (the centre line, dashed; the goal lines) runs across the ice. With the game's camera (BD18) they pin the
video's timing to a Helper recording (video_align.py): the rows move with the camera and never drift. One line per
frame: time (s), then the blue rows and the red rows found (each a run of rows, written as its middle row).
Gentle mode (one process, resting: analysis/scoring_map/lowload.py).
python analysis/video/video_lines.py <video.mkv> <out.tsv> [start s] [end s]"""
import sys
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
from lowload import breathe, gentle  # noqa: E402

HUD_ROWS = 34
MIN_BLUE, MIN_RED = 100, 70     # pixels of the colour across a row (sprites and the dashes hide part of a line)


def runs(rows):
    """Middle rows of runs of consecutive rows."""
    out, start = [], None
    for i, r in enumerate(rows):
        if start is None:
            start = r
        if i + 1 == len(rows) or rows[i + 1] != r + 1:
            out.append((start + r) / 2)
            start = None
    return out


def lines(a):
    a = a[:-HUD_ROWS].astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    blue = ((b > 150) & (r < 120) & (g < 160)).sum(axis=1)
    red = ((r > 150) & (g < 110) & (b < 130)).sum(axis=1)
    return runs([y for y in range(len(blue)) if blue[y] >= MIN_BLUE]), runs([y for y in range(len(red)) if red[y] >= MIN_RED])


def main():
    path, out = sys.argv[1], sys.argv[2]
    start = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    end = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
    gentle()
    c = av.open(path)
    v = c.streams.video[0]
    if start:
        c.seek(int(start * 1000), stream=v, backward=True)
    with open(out, "w") as f:
        for fr in c.decode(v):
            t = fr.time
            if t < start:
                continue
            if t > end:
                break
            bl, rd = lines(fr.to_ndarray(format="rgb24"))
            f.write(f"{t:.4f}\t{','.join(f'{x:g}' for x in bl)}\t{','.join(f'{x:g}' for x in rd)}\n")
            breathe()


if __name__ == "__main__":
    main()
