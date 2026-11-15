"""Possession from a Genesis video: the puck-possession star (2026-11-14; the video reader's possession).

The game draws a filled star under the puck carrier (pad object 0 at $FFBDB4, frame 392; in the recordings shown
through almost all live play, on the carrier in 92% of carried samples, on the last carrier while the puck is loose).
Per looked-at frame: the star's filled inside (extract_sprites.compose(392), colours 3, D, F: the joypad stars 390 /
391 have the same outline but no fill) scored in its pale blue sprite pixels (R 100-190, G 120-205, B 200+; none near
either team's colours), the best TOP places; the star's path through the frames
chosen at once (puck_track.path: a star moves at skating speed); the carrier's team: the team of the detected player
(sprites.players) nearest the star's spot (8 px above it: the body). The team's possession over time: a two-state
path (home, visitors) with SWITCH to change, each frame's team counting ACC.

python analysis/vision/possession.py VIDEO CAMERA_TRACK.npz STATIC.npz HOME AWAY OUT.json [FIRST] [COUNT] [STEP]
  [--check] [--soft] [--crop=X,Y,W,H]   (--soft: the players by the uniforms drawn as a soft copy shows them, sprites.soft_lr,
  and the star by its change to the ice, STAR_LR; --check: against the recordings' last carrier's team, through tools/video_sync.py's timeline)
python analysis/vision/possession.py --learn-star SOFT_VIDEO CAMERA_TRACK.npz [SKIP_FIRST SKIP_LAST]   (STAR_LR from a
  soft copy with a timeline; the frames between SKIP_FIRST and SKIP_LAST left out)"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import camera_track as C  # noqa: E402
import puck_track  # noqa: E402
import sprites as S  # noqa: E402

TOP, SWITCH, ACC = 8, 5.0, 0.8          # SWITCH 5: a whole game's changes nearest the recording's (100 vs 94)
FILL = (0x3, 0xD, 0xF)           # the star's inside: the joypad stars (390 / 391, the same shape) are outlines
SOFT_BLUR = (0.3, 0.25)            # the YouTube video's blur against the drawn rink (2026-11-15)
UNIFORM_GAP = 40                  # a pixel this near a team's colour isn't the star's
STAR_DX, STAR_DY = 1, 5           # the star's frame offsets from the y = 107 - Y + Vpos rule (measured)


def star_points(rom_bytes):
    import extract_sprites as X
    left, top, rows = X.compose(rom_bytes, 392)
    return [(y + top, x + left) for y, r in enumerate(rows) for x, (s, c) in enumerate(r) if c in FILL]


def uniform_colours(rom, home, away):
    """Both teams' whole palettes (in the video's levels): a star pixel isn't near any (Boston's jersey shading is
    a blue that passed the star's test, and the star search found Boston players)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
    from systems import genesis
    teams = {t["abbr"]: t for t in genesis.read_teams(Path(rom))}
    cols = [S.video_rgb(c) for c in teams[home]["palettes"][0][1:] + teams[away]["palettes"][1][1:]]
    return np.array(cols, np.int16)


def star_candidates(f, fg, pts, top=TOP, uniforms=None):
    r, g, b = f[:, :, 0], f[:, :, 1], f[:, :, 2]
    star = fg & (r >= 100) & (r <= 190) & (g >= 120) & (g <= 205) & (b >= 200)   # the pale blue fill
    if uniforms is not None and len(uniforms):
        near = (np.abs(f[:, :, None, :] - uniforms[None, None]).sum(axis=3) < UNIFORM_GAP).any(axis=2)
        star &= ~near
    H, W = C.HUD_TOP, C.NATIVE_W
    score = np.zeros((H, W))
    for dy, dx in pts:
        ys0, ys1 = max(0, -dy), min(H, H - dy)
        xs0, xs1 = max(0, -dx), min(W, W - dx)
        score[ys0:ys1, xs0:xs1] += star[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
    score /= len(pts)
    out = []
    flat = np.argsort(score.ravel())[::-1]
    for idx in flat:
        y, x = divmod(int(idx), W)
        if score[y, x] < 0.05 or len(out) >= top:
            break
        if all(abs(x - a) > 6 or abs(y - b_) > 4 for a, b_, *_ in out):
            out.append((float(x), float(y), float(score[y, x]), float(score[y, x]), 392))
    return out


# ---- the star in a soft copy (YouTube: 4:2:0 colour, blurred; 2026-11-15) ----
# There the star's pale blue fill blurs into the blue lines' colours and the carrier's body covers its middle, so the
# colour search above finds it in a third of frames. What stays: how the star changes the ice under its arms
# (beside and below the skater's feet): red about the same, green and blue down, green more. Each pixel's change from
# the drawn rink (degraded as the video is) is scored by a log-likelihood table (STAR_LR: the star's arms against
# every other changed pixel, learnt from a soft copy of BOS-CHI through the recordings: learn_star), and the star's
# arms summed over it.
STAR_LR = Path(__file__).with_name("star_soft_lr.npy")
LR_BINS, LR_LO, LR_SPAN, LR_CLIP = 12, -160, 320, (-2.0, 4.0)
STAR_SURE = 3.5                   # a candidate's mean log ratio at which its weight reaches 1
SOFT_PATH = {"REWARD": 8.0, "TOP": 8}  # the path's settings for these candidates (tuned on a game 1 stretch of the
                                        # soft BOS-CHI copy, checked on game 3: team right 72.5 -> 79.0%, 79.3 -> 81.4%)


def star_arms(rom_bytes):
    """The star's pixels the carrier's body leaves showing: its lower half and the side points."""
    import extract_sprites as X
    left, top, rows = X.compose(rom_bytes, 392)
    pts = [(y + top, x + left) for y, r in enumerate(rows) for x, (s, c) in enumerate(r) if c]
    return [(dy, dx) for dy, dx in pts if dy >= 0 or abs(dx) >= 6]


def soft_background(rink, hpos, vpos, blur=SOFT_BLUR):
    """The drawn rink at the camera, degraded as a soft copy shows it (the frame's own size)."""
    u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
    win = rink.img[v - 2:v + C.H + 2, u - 2:u + C.NATIVE_W + 2].astype(float)
    return S.degrade(win, blur)[2:-2, 2:-2]


def lr_bin(res):
    return np.clip(((res - LR_LO) * LR_BINS / LR_SPAN).astype(int), 0, LR_BINS - 1)


def soft_star_candidates(f, bg, table, arms, ice, top=TOP):
    """[(x, y, score, weight, 392)]: the star's arms' summed change-likelihood at each anchor on the ice."""
    q = lr_bin(f.astype(float) - bg)
    L = np.clip(table[q[..., 0], q[..., 1], q[..., 2]], *LR_CLIP)
    H, W, pad = C.HUD_TOP, C.NATIVE_W, 40
    M = np.zeros((H + 2 * pad, W + 2 * pad))
    M[pad:pad + H, pad:pad + W] = L[:H]
    score = np.zeros((H, W))
    for dy, dx in arms:
        score += M[pad + dy:pad + dy + H, pad + dx:pad + dx + W]
    score /= len(arms)
    score[~ice[:H]] = -9
    out = []
    for idx in np.argsort(score.ravel())[::-1][:4000]:
        y, x = divmod(int(idx), W)
        if score[y, x] <= 0 or len(out) >= top:
            break
        if all(abs(x - a) > 8 or abs(y - b_) > 5 for a, b_, *_ in out):
            w = min(1.0, math.exp(score[y, x] - STAR_SURE))
            out.append((float(x), float(y), float(score[y, x]), w, 392))
    return out


def learn_star(video, cams, out, skip=(0, 0), step=90, rom=None, blur=SOFT_BLUR):
    """The table from a soft copy whose recordings are on its timeline (VIDEO.timeline.json): every `step`th frame of
    live play with the star shown, frames in skip (first, last) left out (the stretch a check runs on). The star's
    arms (the recorded spot) against every changed pixel 14 / 20 or more away."""
    import rink_mosaic as RM
    rom = Path(rom) if rom else Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
    rink = C.Rink(rom)
    arms = star_arms(rom.read_bytes())
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    truth = RM.Truth(tl)
    star = np.ones((LR_BINS,) * 3)
    other = np.ones((LR_BINS,) * 3)
    used = 0
    for n, f in C.frames(video):
        if n % step or skip[0] <= n <= skip[1] or n not in cams or not cams[n][4]:
            continue
        cam = truth.camera(n / tl.get("fps", 59.92))
        if not cam or not cam[6]:
            continue
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        if c.word(i, 0xBDB4 + 0x18) == 0xFFFF:
            continue
        _, h, v = (int(x) for x in cams[n][:3])
        sx = int(S16(c.word(i, 0xBDB4)) - h + 129)
        sy = int(112 - S16(c.word(i, 0xBDB4 + 0x14)) + v)
        if not (20 < sx < C.NATIVE_W - 20 and 20 < sy < C.HUD_TOP - 20):
            continue
        q = lr_bin(f.astype(float) - soft_background(rink, h, v, blur))
        for dy, dx in arms:
            a = q[sy + dy, sx + dx]
            star[a[0], a[1], a[2]] += 1
        m = np.zeros(q.shape[:2], bool)
        m[:C.HUD_TOP] = True
        m[max(0, sy - 14):sy + 14, max(0, sx - 20):sx + 20] = False
        a = q[m]
        np.add.at(other, (a[:, 0], a[:, 1], a[:, 2]), 1)
        used += 1
    table = np.log(star / star.sum()) - np.log(other / other.sum())
    np.save(out, table)
    print(f"star table from {used} frames: {out}")
    return table


def S16(v):
    return v - 65536 if v & 0x8000 else v


def team_path(obs):
    """obs: per frame None or a team (0, 1): the cheapest two-state path."""
    cost, back = [0.0, 0.0], []
    for o in obs:
        e = [0.0, 0.0] if o is None else [-math.log(ACC if o == s else 1 - ACC) for s in (0, 1)]
        nb, nc = [], []
        for s in (0, 1):
            stay, move = cost[s], cost[1 - s] + SWITCH
            nb.append(s if stay <= move else 1 - s)
            nc.append(min(stay, move) + e[s])
        back.append(nb)
        cost = nc
    s = 0 if cost[0] <= cost[1] else 1
    path = []
    for nb in reversed(back):
        path.append(s)
        s = nb[s]
    return path[::-1]


def run(video, cams, static, home, away, first=0, count=None, step=4, rom=None, soft=None):
    """The star's path and each looked-at frame's team: (seq, obs) for team_path. soft: (blur across, blur down) of a
    soft copy such as YouTube's: the players labelled by sprites.soft_lr (the uniforms drawn as such a video shows them)."""
    try:
        import lowload
    except ImportError:
        lowload = None
    rom = Path(rom) if rom else Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
    rink = C.Rink(rom)
    pts = star_points(rom.read_bytes())
    colours = S.team_colours(rom, home, away)
    uniforms = uniform_colours(rom, home, away)
    lr = S.soft_lr(rom, home, away, soft) if soft else None
    table = np.load(STAR_LR) if soft else None
    arms = star_arms(rom.read_bytes())
    seq, dets_at, boxes_at = [], {}, {}
    for n, f in C.frames(video, first, count):
        if lowload:
            lowload.breathe()
        if n % step or n not in cams or not cams[n][4]:
            continue
        _, hpos, vpos = (int(x) for x in cams[n][:3])
        u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
        ice = rink.ice()[v:v + C.H, u:u + C.NATIVE_W]
        if table is not None:
            ice = ice & ~static[v:v + C.H, u:u + C.NATIVE_W]
            seq.append((n, hpos, vpos, soft_star_candidates(f, soft_background(rink, hpos, vpos, soft), table, arms, ice)))
        else:
            fg = S.fg_mask(rink, f, hpos, vpos, static) & ice   # the star is under a skater's feet: on the ice
            seq.append((n, hpos, vpos, star_candidates(f, fg, pts, uniforms=uniforms)))
        if soft:
            boxes_at[n] = S.soft_skaters(rink, f, hpos, vpos, static)
        else:
            dets_at[n] = S.players(rink, f, hpos, vpos, colours, static, lr=lr)
    if soft:                                   # the teams learnt from this stretch's own skaters
        teams = S.SoftTeams(lr).fit([px for sk in boxes_at.values() for _, _, px in sk])
        dets_at = {n: teams.label(sk) for n, sk in boxes_at.items()}
    keep = {k: getattr(puck_track, k) for k in SOFT_PATH}
    if soft:
        for k, val in SOFT_PATH.items():
            setattr(puck_track, k, val)
    try:
        path = puck_track.path(seq)
    finally:
        for k, val in keep.items():
            setattr(puck_track, k, val)
    obs = []
    for n, *_ in seq:
        p, dets = path.get(n), dets_at.get(n)
        if p is None or not dets:
            obs.append(None)
            continue
        d = min(dets, key=lambda z: np.hypot(z[1] - p[0] + STAR_DX, z[2] - (p[1] - STAR_DY - 8)))
        obs.append(d[0] if np.hypot(d[1] - p[0], d[2] - p[1] + 8) < 30 else None)
    return [(n, h, v, path.get(n)) for n, h, v, _ in seq], obs


def which_home(video, cams, static, a, b, first, count, rom=None, samples=24):
    """Which of two teams is home in a stretch of video: each assignment's player detections' pixels added over
    `samples` frames (a team's home and away uniforms differ; the right assignment labels more)."""
    rom = Path(rom) if rom else Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
    rink = C.Rink(rom)
    cols = {(a, b): S.team_colours(rom, a, b), (b, a): S.team_colours(rom, b, a)}
    total = {k: 0 for k in cols}
    every = max(1, count // samples)
    for n, f in C.frames(video, first, count):
        if n % every or n not in cams or not cams[n][4]:
            continue
        _, hpos, vpos = (int(x) for x in cams[n][:3])
        for k, c in cols.items():
            total[k] += sum(px for _, _, _, px in S.players(rink, f, hpos, vpos, c, static))
    return max(total, key=total.get), total


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if "--learn-star" in sys.argv:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
            import lowload
            lowload.gentle()
        except ImportError:
            pass
        cams = {int(r[0]): r for r in np.load(a[1])["rows"]}
        skip = (int(a[2]), int(a[3])) if len(a) > 3 else (0, -1)
        learn_star(Path(a[0]), cams, STAR_LR, skip)
        return
    video, track, static = Path(a[0]), a[1], np.load(a[2])["mask"]
    home, away, out = a[3], a[4], Path(a[5])
    first = int(a[6]) if len(a) > 6 else 0
    count = int(a[7]) if len(a) > 7 else None
    step = int(a[8]) if len(a) > 8 else 4
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
        lowload.gentle()
    except ImportError:
        pass
    cams = {int(r[0]): r for r in np.load(track)["rows"]}
    if "--crop" in " ".join(sys.argv):
        C.CROP = tuple(int(v) for v in next(x for x in sys.argv if x.startswith("--crop=")).split("=")[1].split(","))
    seq, obs = run(video, cams, static, home, away, first, count, step, soft=SOFT_BLUR if "--soft" in sys.argv else None)
    teams = team_path(obs)
    res = {"frames": [n for n, *_ in seq], "star": [p for *_, p in seq], "team": teams, "obs": obs}
    out.write_text(json.dumps(res))
    share = np.mean(np.array(teams) == 0)
    print(f"{len(seq)} frames: home's share of possession (the star's team) {share:.1%}")
    if "--check" in sys.argv:
        import rink_mosaic as RM
        tl = json.loads(Path(str(video) + ".timeline.json").read_text())
        truth = RM.Truth(tl)
        P = 0xB04A + 0x80 * 14
        right = tot = right_raw = tot_raw = 0
        th = []
        for (n, *_), t, o in zip(seq, teams, obs):
            cam = truth.camera(n / tl.get("fps", 59.92))
            if not cam or not cam[6]:
                continue
            c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
            want = 0 if c.byte(i, P + 0x61) < 6 else 1
            th.append(want)
            right += t == want
            tot += 1
            if o is not None:
                right_raw += o == want
                tot_raw += 1
        print(f"  the team with the puck (the last carrier's) right on {right / max(tot, 1):.1%} of {tot} live frames "
              f"(each frame alone {right_raw / max(tot_raw, 1):.1%} of {tot_raw}); home's share in the recording "
              f"{np.mean(np.array(th) == 0):.1%}")


if __name__ == "__main__":
    main()
