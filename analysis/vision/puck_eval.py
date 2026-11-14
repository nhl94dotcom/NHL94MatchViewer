"""The video reader's puck against the recordings, on every frame of live play (2026-11-14).

Every STEP-th placed frame of live play: the recorded puck's screen spots over +-WINDOW samples (the timeline is good
to a fraction of a second), the puck carried or loose. The estimate: puck.Finder's best-weighted candidate (or, with
--track, puck_track's). Counted: placed (an estimate within NEAR pixels of a recorded spot), wrong (an estimate
elsewhere), none (no estimate); by carried / loose; and how far off.

--cache=FILE: the per-frame candidates and truth kept in FILE (written the first time, read after: tuning the tracker
needs no video decoding). Gentle mode (lowload).

python analysis/vision/puck_eval.py VIDEO CAMERA_TRACK.npz STATIC.npz [FIRST] [COUNT] [STEP] [--track] [--cache=FILE]"""
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


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    video, track, static = Path(a[0]), a[1], np.load(a[2])["mask"]
    first, count, step = (int(a[3]) if len(a) > 3 else 0), (int(a[4]) if len(a) > 4 else None), (int(a[5]) if len(a) > 5 else 10)
    use_track = "--track" in sys.argv
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
    tally = defaultdict(lambda: defaultdict(int))
    errs = []
    P = 0xB04A + 0x80 * 14
    seq, frames_truth = [], []
    import pickle
    if cache and cache.exists():                     # the candidates and the truth from an earlier run: no video
        seq, frames_truth = pickle.loads(cache.read_bytes())
    for n, f in ([] if cache and cache.exists() else C.frames(video, first, count)):
        if lowload:
            lowload.breathe()
        if n % step or n not in cams or not cams[n][4]:
            continue
        cam = truth.camera(n / fps)
        if not cam or not cam[6]:
            continue
        _, hpos, vpos = (int(x) for x in cams[n][:3])
        cands = finder.find(f, hpos, vpos, static=static)
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
        frames_truth.append((n, kind, spots))
    if cache and not cache.exists():
        cache.write_bytes(pickle.dumps((seq, frames_truth)))
    if use_track:
        import puck_track
        est_at = puck_track.path(seq)
    else:
        est_at = {n: cands[0][:2] for n, _, _, cands in seq if cands}
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
