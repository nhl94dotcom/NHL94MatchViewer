"""The video reader's loose puck against the recordings (2026-11-14).

Every STEP-th placed frame of live play with the recorded puck loose (record 14, +$60 = $FF) and on screen: the
recorded puck's screen spot at each sample within +-WINDOW of the frame's (the timeline is good to a fraction of a
second, and a loose puck moves fast); found when a candidate (sprites.puck_candidates) is within NEAR pixels of any
of them. Extra: candidates near none. Also the error to the nearest of them.

python analysis/vision/puck_check.py VIDEO CAMERA_TRACK.npz STATIC.npz [FIRST] [COUNT] [STEP]"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import camera_track as C  # noqa: E402
import rink_mosaic as RM  # noqa: E402
import sprites as S  # noqa: E402

WINDOW, NEAR = 6, 6


def s16(v):
    return v - 65536 if v & 0x8000 else v


def main():
    a = sys.argv[1:]
    video, track, static = Path(a[0]), a[1], np.load(a[2])["mask"]
    first, count, step = (int(a[3]) if len(a) > 3 else 0), (int(a[4]) if len(a) > 4 else None), (int(a[5]) if len(a) > 5 else 10)
    tl = json.loads(Path(str(video) + ".timeline.json").read_text())
    truth, fps = RM.Truth(tl), tl.get("fps", 59.92)
    cams = {int(r[0]): r for r in np.load(track)["rows"]}
    rink = C.Rink(Path.home() / "NHL94_scoring_map" / "nhl94_retail.bin")
    found = missed = extra = frames = 0
    errs = []
    P = 0xB04A + 0x80 * 14
    for n, f in C.frames(video, first, count):
        if n % step or n not in cams or not cams[n][4]:
            continue
        cam = truth.camera(n / fps)
        if not cam or not cam[6]:
            continue
        _, hpos, vpos = (int(x) for x in cams[n][:3])
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        spots = []
        for j in range(max(0, i - WINDOW), min(c.count, i + WINDOW + 1)):
            if c.byte(j, P + 0x60) != 0xFF:
                continue
            X, Y, Z = s16(c.word(j, P)), s16(c.word(j, P + 0x14)), s16(c.word(j, P + 0x18))
            spots.append((X - hpos + 128, 107 - Y + vpos - Z + S.PUCK_DY))
        cands = S.puck_candidates(rink, f, hpos, vpos, static)
        loose = c.byte(i, P + 0x60) == 0xFF
        x0, y0 = (spots[len(spots) // 2] if spots else (None, None))
        on = loose and spots and 4 <= x0 < 252 and 4 <= y0 < 180
        frames += 1
        hit = None
        for k, (x, y, _) in enumerate(cands):
            d = min((np.hypot(x - sx, y - sy) for sx, sy in spots), default=99)
            if d <= NEAR:
                hit = d if hit is None else min(hit, d)
            else:
                extra += 1
        if on:
            if hit is not None:
                found += 1
                errs.append(hit)
            else:
                missed += 1
    print(f"{frames} frames of live play: loose puck on screen {found + missed}, found {found} "
          f"({found / max(found + missed, 1):.1%}); candidates near no puck {extra} ({extra / max(frames, 1):.2f} a frame)")
    if errs:
        print(f"  error (pixels, to the nearest recorded spot in the window): median {np.median(errs):.1f}")


if __name__ == "__main__":
    main()
