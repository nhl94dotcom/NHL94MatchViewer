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
  [--check]   (--check: against the recordings' last carrier's team, through tools/video_sync.py's timeline)"""
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

TOP, SWITCH, ACC = 8, 3.0, 0.8
FILL = (0x3, 0xD, 0xF)           # the star's inside: the joypad stars (390 / 391, the same shape) are outlines
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


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
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
        lowload = None
    rom = Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
    rink = C.Rink(rom)
    pts = star_points(rom.read_bytes())
    colours = S.team_colours(rom, home, away)
    uniforms = uniform_colours(rom, home, away)
    cams = {int(r[0]): r for r in np.load(track)["rows"]}
    seq, dets_at = [], {}
    for n, f in C.frames(video, first, count):
        if lowload:
            lowload.breathe()
        if n % step or n not in cams or not cams[n][4]:
            continue
        _, hpos, vpos = (int(x) for x in cams[n][:3])
        fg = S.fg_mask(rink, f, hpos, vpos, static)
        seq.append((n, hpos, vpos, star_candidates(f, fg, pts, uniforms=uniforms)))
        dets_at[n] = S.players(rink, f, hpos, vpos, colours, static)
    path = puck_track.path(seq)
    obs = []
    for n, *_ in seq:
        p, dets = path.get(n), dets_at.get(n)
        if p is None or not dets:
            obs.append(None)
            continue
        d = min(dets, key=lambda z: np.hypot(z[1] - p[0] + STAR_DX, z[2] - (p[1] - STAR_DY - 8)))
        obs.append(d[0] if np.hypot(d[1] - p[0], d[2] - p[1] + 8) < 30 else None)
    teams = team_path(obs)
    res = {"frames": [n for n, *_ in seq], "star": [path.get(n) for n, *_ in seq], "team": teams, "obs": obs}
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
