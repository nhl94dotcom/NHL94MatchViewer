"""The puck followed through a video (2026-11-14; the video reader's puck, step 2).

A video is read after the fact, so the puck's path is chosen over all its frames at once (a Viterbi path) rather
than frame by frame. Per looked-at frame, the candidates (puck.Finder: up to TOP, each with its weight: the
template's match times the camera's lead) on the rink (X = x + Hpos - 128, Y = 107 + Vpos - y: the camera moves).
A path goes from a candidate to one in a later frame, up to SKIP looked-at frames later; its cost:
  -log(weight) - REWARD for each candidate it takes,
  the move: d^2 / (2 sigma^2) + log(sigma), sigma = SIGMA0 + SPEED x the frames between (a puck moves up to about 6
  units a frame: a hard shot; most of the time 1-3),
  GAP for each frame passed over (the puck hidden or merged into a player there),
and a path may start and end anywhere (START), and break into stretches (START again, and JUMP_GAP for each frame
between: whistles, breaks). Frames passed over get the place drawn straight between the two it
joins; frames before the first or after the last candidate on the path get none.

Tuned on 8,000 frames of BOS-CHI (every 4th, the cache of puck_eval.py): every frame of live play placed within 6
pixels 46.7% (frame by frame 31.3%).

path(seq) -> {frame: (x, y) in screen pixels at that frame}, seq = [(frame, hpos, vpos, candidates)] in order."""
import math

TOP, SKIP = 16, 12
SIGMA0, SPEED = 3.0, 4.0
GAP, START, JUMP_GAP = 0.5, 6.0, 0.5
REWARD = 5.0                      # each candidate taken earns this (else the shortest path is the cheapest)


def path(seq):
    pts = []                                    # per looked-at frame: [(X, Y, cost)]
    for n, hpos, vpos, cands in seq:
        row = []
        for x, y, s, w, _ in cands[:TOP]:
            row.append((x + hpos - 128, 107 + vpos - y, -math.log(max(w, 1e-6)) - REWARD))
        pts.append(row)
    best, back = [], []
    jump = (math.inf, None)                     # the cheapest place to have ended a stretch, less JUMP_GAP a frame
    for k, row in enumerate(pts):
        if k:
            for a, c0 in enumerate(best[k - 1]):
                v = c0 - JUMP_GAP * (k - 1)
                if v < jump[0]:
                    jump = (v, (k - 1, a))
        bk, bb = [], []
        for X, Y, e in row:
            c, frm = START + e, None
            if jump[1] is not None and jump[0] + JUMP_GAP * (k - 1) + START + e < c:   # a new stretch after
                c, frm = jump[0] + JUMP_GAP * (k - 1) + START + e, ("jump",) + jump[1]  # an earlier one
            for j in range(1, SKIP + 1):
                if k - j < 0:
                    break
                frames = seq[k][0] - seq[k - j][0]
                sigma = SIGMA0 + SPEED * frames
                for a, (X0, Y0, _) in enumerate(pts[k - j]):
                    d2 = (X - X0) ** 2 + (Y - Y0) ** 2
                    cost = best[k - j][a] + d2 / (2 * sigma * sigma) + math.log(sigma) + GAP * (j - 1) + e
                    if cost < c:
                        c, frm = cost, (k - j, a)
            bk.append(c)
            bb.append(frm)
        best.append(bk)
        back.append(bb)
    # the best end: any candidate, paying START for ending there too and GAP for the frames after it
    end, cend = None, math.inf
    for k in range(len(pts)):
        for a, c in enumerate(best[k]):
            cc = c
            if cc < cend:
                cend, end = cc, (k, a)
    chosen, jumps = [], set()
    while end is not None:
        chosen.append(end)
        prev = back[end[0]][end[1]]
        if prev is not None and prev[0] == "jump":
            prev = prev[1:]
            jumps.add(prev)                     # no line drawn from here to the next stretch
        end = prev
    chosen.reverse()
    out = {}
    for (k0, a0), (k1, a1) in zip(chosen, chosen[1:]):
        if (k0, a0) in jumps:
            X, Y, _ = pts[k0][a0]
            n, hpos, vpos, _ = seq[k0]
            out[n] = (X - hpos + 128, 107 + vpos - Y)
            continue
        X0, Y0, _ = pts[k0][a0]
        X1, Y1, _ = pts[k1][a1]
        for k in range(k0, k1):
            t = (k - k0) / (k1 - k0)
            X, Y = X0 + t * (X1 - X0), Y0 + t * (Y1 - Y0)
            n, hpos, vpos, _ = seq[k]
            out[n] = (X - hpos + 128, 107 + vpos - Y)
    if chosen:
        k, a = chosen[-1]
        X, Y, _ = pts[k][a]
        n, hpos, vpos, _ = seq[k]
        out[n] = (X - hpos + 128, 107 + vpos - Y)
    return out
