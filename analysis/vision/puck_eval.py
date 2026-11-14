"""The video reader's puck against the recordings, on every frame of live play (2026-11-14).

Every STEP-th placed frame of live play: the recorded puck's screen spots over +-WINDOW samples (the timeline is good
to a fraction of a second), the puck carried or loose. The estimate: puck.Finder's best-weighted candidate (or, with
--track, puck_track's). Counted: placed (an estimate within NEAR pixels of a recorded spot), wrong (an estimate
elsewhere), none (no estimate); by carried / loose and by where (in the crease or the net's mouth, within 12 units of
a player, free); and how far off. Both of puck.Finder's scorings are found and cached; --mode picks (classic by
default, partial, or union).

--cache=FILE: the per-frame candidates and truth kept in FILE (written the first time, read after: tuning the tracker
needs no video decoding); --players=HOME,AWAY keeps each frame's player detections there too (sprites.players);
--star (with --players) the possession star's candidates too, and the recording's last carrier's screen spot.
Gentle mode (lowload).

python analysis/vision/puck_eval.py VIDEO CAMERA_TRACK.npz STATIC.npz [FIRST] [COUNT] [STEP] [--track] [--cache=FILE] [--players=HOME,AWAY] [--star] [--mode=classic|partial|union]"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import camera_track as C  # noqa: E402
import puck as PK  # noqa: E402
import rink_mosaic as RM  # noqa: E402

WINDOW, NEAR = 6, 6


def s16(v):
    return v - 65536 if v & 0x8000 else v


def pick(cands, mode):
    """A frame's candidates by scoring: classic, partial, or union (classic's, then partial's not within 4 px of one,
    their weights x UNION_W). A cache from before 2026-11-14 evening holds a list: one scoring."""
    if isinstance(cands, list):
        return cands
    if mode != "union":
        return cands[mode]
    out = list(cands["classic"])
    for c in cands["partial"]:
        if all(abs(c[0] - o[0]) > 4 or abs(c[1] - o[1]) > 4 for o in out):
            out.append((c[0], c[1], c[2] * UNION_W, c[3] * UNION_W, c[4]))
    return sorted(out, key=lambda c: -c[3])


UNION_W = 0.8


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    video, track, static = Path(a[0]), a[1], np.load(a[2])["mask"]
    first, count, step = (int(a[3]) if len(a) > 3 else 0), (int(a[4]) if len(a) > 4 else None), (int(a[5]) if len(a) > 5 else 10)
    use_track = "--track" in sys.argv
    pass
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
        lowload.gentle()
    except ImportError:
        lowload = None
    cache = next((Path(x.split("=", 1)[1]) for x in sys.argv if x.startswith("--cache=")), None)
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    truth, fps = RM.Truth(tl), tl.get("fps", 59.92)
    cams = {int(r[0]): r for r in np.load(track)["rows"]}
    rom = Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin"
    finder = PK.Finder(rom)
    teams = next((x.split("=", 1)[1].split(",") for x in sys.argv if x.startswith("--players=")), None)
    if teams:
        import sprites as S
        colours = S.team_colours(rom, teams[0], teams[1])
    tally = defaultdict(lambda: defaultdict(int))
    errs = []
    P = 0xB04A + 0x80 * 14
    seq, frames_truth, stars, carriers = [], [], {}, {}
    use_star = "--star" in sys.argv
    if use_star:
        import possession as PO
        import sprites as S
        star_pts = PO.star_points(rom.read_bytes())
        uniforms = PO.uniform_colours(rom, *teams) if teams else None
    import pickle
    if cache and cache.exists():                     # the candidates and the truth from an earlier run: no video
        loaded = pickle.loads(cache.read_bytes())
        seq, frames_truth = loaded[:2]
        if len(loaded) > 2:
            stars, carriers = loaded[2], loaded[3]
    for n, f in ([] if cache and cache.exists() else C.frames(video, first, count)):
        if lowload:
            lowload.breathe()
        if n % step or n not in cams or not cams[n][4]:
            continue
        cam = truth.camera(n / fps)
        if not cam or not cam[6]:
            continue
        _, hpos, vpos = (int(x) for x in cams[n][:3])
        cands = finder.find(f, hpos, vpos, static=static, both=True)     # both scorings, chosen at evaluation
        if use_star:                                 # the possession star's candidates (possession.py's search)
            fg = S.fg_mask(finder.rink, f, hpos, vpos, static)
            u, v = hpos + C.OFF_X + C.PAD, C.OFF_Y - vpos + C.PAD
            fg = fg & finder.rink.ice()[v:v + C.H, u:u + C.NATIVE_W]
            stars[n] = PO.star_candidates(f, fg, star_pts, uniforms=uniforms)
        if teams:
            import sprites as S
            dets = S.players(finder.rink, f, hpos, vpos, colours, static)
            seq.append((n, hpos, vpos, cands, dets))
        else:
            seq.append((n, hpos, vpos, cands))
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        spots = []
        for j in range(max(0, i - WINDOW), min(c.count, i + WINDOW + 1)):
            X, Y, Z = s16(c.word(j, P)), s16(c.word(j, P + 0x14)), s16(c.word(j, P + 0x18))
            spots.append((X - hpos + 128, 107 - Y + vpos - Z))
        x0, y0 = spots[len(spots) // 2]
        if not (0 <= x0 < 256 and 0 <= y0 < C.HUD_TOP):
            continue
        kind = "loose" if c.byte(i, P + 0x60) == 0xFF else "carried"
        X, Y = s16(c.word(i, P)), s16(c.word(i, P + 0x14))
        near = min(abs(s16(c.word(i, 0xB04A + 0x80 * r)) - X) + abs(s16(c.word(i, 0xB04A + 0x80 * r + 0x14)) - Y)
                   for r in range(12))
        kind += ", crease / net" if abs(X) < 32 and abs(Y) > 225 else ", near a player" if near <= 12 else ", free"
        frames_truth.append((n, kind, spots))
        k = c.byte(i, P + 0x61)                      # the last carrier's screen spot (his record's anchor)
        if k < 12:
            carriers[n] = (s16(c.word(i, 0xB04A + 0x80 * k)) - hpos + 128,
                           107 - s16(c.word(i, 0xB04A + 0x80 * k + 0x14)) + vpos, k)
    if cache and not cache.exists():
        cache.write_bytes(pickle.dumps((seq, frames_truth, stars, carriers)))
    mode = next((x.split("=", 1)[1] for x in sys.argv if x.startswith("--mode=")), "classic")
    seq = [(q[0], q[1], q[2], pick(q[3], mode)) + tuple(q[4:]) for q in seq]
    if use_track:
        import puck_track
        est_at = puck_track.path([q[:4] for q in seq])
    else:
        est_at = {q[0]: q[3][0][:2] for q in seq if q[3]}
    for n, kind, spots in frames_truth:
        est = est_at.get(n)
        t = tally[kind]
        t["frames"] += 1
        if est is None:
            t["none"] += 1
            continue
        d = min(np.hypot(est[0] - sx, est[1] - sy) for sx, sy in spots)
        if d <= NEAR:
            t["placed"] += 1
            errs.append(d)
        else:
            t["wrong"] += 1
    for kind, t in tally.items():
        fr = max(t["frames"], 1)
        print(f"{kind}: {t['frames']} frames; placed {t['placed']} ({t['placed'] / fr:.1%}), wrong {t['wrong']} "
              f"({t['wrong'] / fr:.1%}), none {t['none']} ({t['none'] / fr:.1%})")
    allf = sum(t["frames"] for t in tally.values())
    print(f"all: placed {sum(t['placed'] for t in tally.values()) / max(allf, 1):.1%}; error when placed median "
          f"{np.median(errs) if errs else float('nan'):.1f} px")


if __name__ == "__main__":
    main()
