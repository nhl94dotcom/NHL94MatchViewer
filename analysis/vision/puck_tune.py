"""Puck placement tuned offline from a puck_eval cache (2026-11-14; no video decoding): puck.Finder's two scorings, the
possession star's candidates and the recording's truth, as puck_eval --star --players caches them.

The per-frame candidates handed to puck_track: the classic scoring's (few, 67% / 79% of carried / loose frames hold
the puck), plus the partial scoring's within NEAR_STAR pixels of the frame's best star (a carried puck is within about
18 px of the star, which is under the carrier in 95% of carried frames; partial candidates hold the puck in 92% /
98% of frames, but about 130 a frame), each weighted by STAR_W and by how near the star it is; then persist()'s
penalty for candidates at a rink place that keeps coming back. Variants are scored as puck_eval does (within 6 px of
a recorded spot) and printed best first. place(seq, stars) is the tuned pipeline: on BOS-CHI's 8,000 frames 53.0%
placed (46.7% classic candidates alone), tuned on those frames: to be checked on another stretch.

python analysis/vision/puck_tune.py CACHE.pkl"""
import itertools
import pickle
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import puck_track  # noqa: E402

NEAR = 6


def build(seq, stars, near_star, star_w, classic_star_bonus, star_min):
    out = []
    for n, h, v, cands, *_ in seq:
        cl = list(cands["classic"]) if isinstance(cands, dict) else list(cands)
        st = stars.get(n) or []
        best = st[0] if st and st[0][2] >= star_min else None
        if best and classic_star_bonus:
            cl = [(x, y, s, w * (1 + classic_star_bonus * np.exp(-((x - best[0]) ** 2 + (y - best[1]) ** 2) / (2 * 12 ** 2))), f)
                  for x, y, s, w, f in cl]
        if best and near_star and isinstance(cands, dict):
            for x, y, s, w, f in cands["partial"]:
                d = np.hypot(x - best[0], y - best[1])
                if d <= near_star and all(abs(x - c[0]) > 3 or abs(y - c[1]) > 3 for c in cl):
                    cl.append((x, y, s, s * star_w * np.exp(-d * d / (2 * 12 ** 2)), f))
        out.append((n, h, v, sorted(cl, key=lambda c: -c[3])))
    return out


def persist(s, win=15, cell=6, f0=0.3, alpha=3.0):
    """Down-weight candidates at a rink place that keeps coming back: the share of the WIN looked-at frames either
    side with a candidate within a cell (CELL units) of it; above F0, the weight x exp(-ALPHA (share - F0)). The
    false pucks that hold a path are stationary: the goalies' pads and sticks in front of each net, the faceoff dots;
    the puck itself seldom stays put in live play. (BOS-CHI's 8,000 frames: 48.9% -> 53.0% placed.)"""
    cells = [{(round((x + h - 128) / cell), round((107 + v - y) / cell)) for x, y, *_ in cl[:16]} for n, h, v, cl in s]
    out, N = [], len(s)
    for k, (n, h, v, cl) in enumerate(s):
        lo, hi = max(0, k - win), min(N, k + win + 1)
        new = []
        for x, y, sc, w, fr in cl:
            c = (round((x + h - 128) / cell), round((107 + v - y) / cell))
            frac = sum(1 for j in range(lo, hi) if j != k and any(abs(c[0] - a) <= 1 and abs(c[1] - b) <= 1
                                                                for a, b in cells[j])) / max(1, hi - lo - 1)
            new.append((x, y, sc, w * np.exp(-alpha * max(0.0, frac - f0)), fr))
        out.append((n, h, v, sorted(new, key=lambda c: -c[3])))
    return out


def place(seq, stars):
    """The tuned pipeline: classic candidates, partial ones near the star, the persistence penalty, the path."""
    return puck_track.path(persist(build(seq, stars, 20, 0.3, 1.0, 0.1)))


def score(path, truth):
    tally = defaultdict(lambda: [0, 0])
    for n, kind, spots in truth:
        k = kind.split(",")[0]
        tally[k][1] += 1
        est = path.get(n)
        if est is not None and min(np.hypot(est[0] - sx, est[1] - sy) for sx, sy in spots) <= NEAR:
            tally[k][0] += 1
    allp = sum(a for a, _ in tally.values()) / max(1, sum(b for _, b in tally.values()))
    return allp, {k: round(100 * a / max(b, 1), 1) for k, (a, b) in tally.items()}


def main():
    seq, truth, stars, carriers = pickle.loads(Path(sys.argv[1]).read_bytes())
    res = []
    for near_star, star_w, bonus, star_min in itertools.product((0, 20, 26), (0.3, 0.6, 1.0), (0, 1.0, 3.0), (0.1, 0.3)):
        if near_star == 0 and star_w != 0.3:
            continue
        s = build(seq, stars, near_star, star_w, bonus, star_min)
        p, parts = score(puck_track.path(s), truth)
        res.append((p, parts, dict(near_star=near_star, star_w=star_w, bonus=bonus, star_min=star_min)))
        print(f"{100 * p:.1f}% {parts} {res[-1][2]}", flush=True)
    res.sort(key=lambda r: -r[0])
    print("best:")
    for p, parts, cfg in res[:5]:
        print(f"  {100 * p:.1f}% {parts} {cfg}")


if __name__ == "__main__":
    main()
