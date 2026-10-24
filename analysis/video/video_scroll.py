"""How far the picture scrolls between consecutive frames of a RetroArch video (the camera's motion), by phase
correlation of the ice and boards (the HUD rows at the bottom left out). Writes one line per frame: time (s), dx, dy
(pixels the picture moved: the camera moved the other way), and the correlation peak (low at cuts: a pause screen, an
intermission, a goal banner). Gentle mode: one process, resting between bursts (analysis/scoring_map/lowload.py).
python analysis/video/video_scroll.py <video.mkv> <out.tsv> [start s] [end s]"""
import sys
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
from lowload import breathe, gentle  # noqa: E402

HUD_ROWS = 34          # the clock and score boxes along the bottom


def gray(frame):
    a = frame.to_ndarray(format="gray").astype(np.float32)
    return a[:-HUD_ROWS]


def shift(a, b, win):
    """The (dx, dy) that moves picture a onto b, and the strength of the match."""
    fa, fb = np.fft.rfft2(a * win), np.fft.rfft2(b * win)
    r = fa * np.conj(fb)
    r /= np.abs(r) + 1e-6
    c = np.fft.irfft2(r, s=a.shape)
    y, x = np.unravel_index(np.argmax(c), c.shape)
    peak = float(c[y, x])
    h, w = a.shape
    dy, dx = (y if y <= h // 2 else y - h), (x if x <= w // 2 else x - w)
    return -dx, -dy, peak


def main():
    path, out = sys.argv[1], sys.argv[2]
    start = float(sys.argv[3]) if len(sys.argv) > 3 else 0
    end = float(sys.argv[4]) if len(sys.argv) > 4 else 1e9
    gentle()
    c = av.open(path)
    v = c.streams.video[0]
    v.thread_type = "AUTO"
    if start:
        c.seek(int(start * 1000), stream=v, backward=True)
    prev, win = None, None
    with open(out, "w") as f:
        for fr in c.decode(v):
            t = fr.time
            if t < start:
                continue
            if t > end:
                break
            g = gray(fr)
            if win is None:
                win = np.outer(np.hanning(g.shape[0]), np.hanning(g.shape[1])).astype(np.float32)
            if prev is not None:
                dx, dy, pk = shift(prev, g, win)
                f.write(f"{t:.4f}\t{dx}\t{dy}\t{pk:.3f}\n")
            prev = g
            breathe()


if __name__ == "__main__":
    main()
