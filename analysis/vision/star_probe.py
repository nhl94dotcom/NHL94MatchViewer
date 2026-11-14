"""Probe (2026-11-14): the puck-possession star (frame 392, drawn under the carrier: NOSE4Web's note on uppads) found
by its shape in star-coloured sprite pixels, against the recorded star (pad object 0, $FFBDB4: X +$00, Y +$14,
Z +$18 $FFFF hidden; on screen at x = X - Hpos + 129, y = 112 - Y + Vpos). Gentle; one decode."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import camera_track as C  # noqa: E402
import rink_mosaic as RM  # noqa: E402
import sprites as S  # noqa: E402
import extract_sprites as X  # noqa: E402


def s16(v):
    return v - 65536 if v & 0x8000 else v


def main():
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scoring_map"))
        import lowload
        lowload.gentle()
    except ImportError:
        lowload = None
    V = Path.home() / "Documents/NHL94 Viewer/replay/nhl94_playoffs-261113-133619.mkv"
    R = Path.home() / "NHL94_scoring_map/runs/vision"
    tl = json.loads(Path(str(V) + ".timeline.json").read_text())
    truth = RM.Truth(tl)
    cams = {int(r[0]): r for r in np.load(R / "track_full.npz")["rows"]}
    static = np.load(R / "static_boschi.npz")["mask"]
    rink = C.Rink(Path.home() / "NHL94_scoring_map/nhl94_retail.bin")
    rom = (Path.home() / "NHL94_scoring_map/nhl94_retail.bin").read_bytes()
    left, top, rows = X.compose(rom, 392)
    pts = [(y + top, x + left) for y, r in enumerate(rows) for x, (s, c) in enumerate(r) if c]
    A = 0xBDB4
    errs, n_ok, found = [], 0, {}
    for n, f in C.frames(V, 40000, 12000):
        if lowload:
            lowload.breathe()
        if n % 20 or n not in cams or not cams[n][4]:
            continue
        cam = truth.camera(n / 59.92)
        if not cam or not cam[6]:
            continue
        _, h, v = (int(x) for x in cams[n][:3])
        c, i = truth.caps[tl["games"][cam[3]]][0], cam[4]
        if c.word(i, A + 0x18) == 0xFFFF:
            continue
        spots = [(s16(c.word(j, A)) - h + 129, 112 - s16(c.word(j, A + 0x14)) + v)
                 for j in range(max(0, i - 6), min(c.count, i + 7))]
        fg = S.fg_mask(rink, f, h, v, static)
        r, g, b = f[:, :, 0], f[:, :, 1], f[:, :, 2]
        star = fg & (b - r > 40) & (g < 200)
        H, W = C.HUD_TOP, C.NATIVE_W
        score = np.zeros((H, W))
        for dy, dx in pts:
            ys0, ys1 = max(0, -dy), min(H, H - dy)
            xs0, xs1 = max(0, -dx), min(W, W - dx)
            score[ys0:ys1, xs0:xs1] += star[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
        y0, x0 = np.unravel_index(score.argmax(), score.shape)
        found[n] = (float(x0), float(y0), float(score.max()) / len(pts))
        e = min(np.hypot(x0 - tx, y0 - ty) for tx, ty in spots)
        errs.append(e)
        n_ok += e <= 6
    import pickle
    (R / "star_cache.pkl").write_bytes(pickle.dumps(found))
    e = np.array(errs)
    print(f"{len(e)} frames of live play with the star shown: found within 6 px {n_ok / len(e):.1%}, within 12 "
          f"{np.mean(e <= 12):.1%}; median error {np.median(e):.1f}")


if __name__ == "__main__":
    main()
