"""The SNES goalie's save areas: the game's own stops against the xG model's collision test (2026-11-01, SNES_SHOOTING
4.7: the gliding goalie, right close in, is far too weak from range; the game's save choice made no difference). One-
timers from the overnight check (paths.RUNS / ot_glide / ot_xg_check_snes.jsonl, the given distance band) are struck
again in the retail game with one seed and followed frame by frame. Each frame the model's test (xg_snes.play_out: the
save frame's hot area with its height band, then the body box) is asked with the game's own goalie spot and sprite frame
and the puck's spot and height. Per strike: where the game stopped it (the frame the puck's speed turned or the goalie
held it), where the model's test would first have stopped it, and the game's result.
python snes_save_geometry.py [lo] [hi] [n]   (default 120 200 150)"""
import json
import math
import random
import sys
import zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as XS  # noqa: E402

from lowload import breathe, gentle  # noqa: E402
from ot_harness import OneTimer  # noqa: E402
from paths import RUNS, SNES_ROM  # noqa: E402

FRAME, PFALOCK, PUCKC = 0x0D97, 0x14E3, 0x0AD9


def model_hit(data, gx, gy, frame, x, y, h):
    hot = data.hot(frame)
    if hot:
        hx, hy, d2, top, bottom = hot
        ex, ey = gx + hx - x, gy + hy - y
        if abs(ex) < d2 and abs(ey) < d2 and h <= top and (bottom < 0 or bottom < h) and ex * ex + ey * ey <= d2 * d2:
            return "hot"
    if -11 <= gx - x <= 10 and -11 <= gy - y <= 10:
        return "body"
    return None


def main():
    lo = float(sys.argv[1]) if len(sys.argv) > 1 else 120
    hi = float(sys.argv[2]) if len(sys.argv) > 2 else 200
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    gentle()
    data = XS.RomData(SNES_ROM.read_bytes())
    rows = [json.loads(l) for l in open(RUNS / "ot_glide" / "ot_xg_check_snes.jsonl")]
    dist = lambda r: math.hypot(r["puck"][0], (264 if r["net"] == "top" else -264) - r["puck"][1])
    rows = [r for r in rows if lo <= dist(r) < hi]
    random.Random(2).shuffle(rows)
    ot = OneTimer("snes")
    s, e = ot.s, ot.e
    H, g = s.H, 2 * s.GOALIE
    table, examples = Counter(), []
    for r in rows[:n]:
        net, R, P = r["net"], r["R"], r["P"]
        rnd = random.Random(zlib.crc32(f"xgcheck-snes,{net},{R},{P}".encode()))
        ot.setup(net, P, R, r["p"], rnd)
        by = 2 + r["p"] % 4 if r["timing"] == "early" else 2 + (r["p"] * 5) % 9
        press, info = ot.pass_to_press(r["timing"], by=by)
        if press is None:
            continue
        pre, frames = ot.swing(press, r["aim"])
        if pre is None:
            continue
        ot.strike(pre, r["aim"], 12345)
        s0, sg = s.score(), 1 if net == "top" else -1
        vy0 = s.sw(H.YVEL + 2 * s.PUCK) * sg
        game_stop = model_stop = None
        result, trace = "miss", []
        for f in range(60):
            px, py = s.xy(s.PUCK)
            gx, gy = s.xy(s.GOALIE)
            pz = s.sw(H.PUCKZ)
            fr = e.w(FRAME + g)
            trace.append((f, px, py, pz, gx, gy, fr, e.w(PFALOCK + g)))
            if model_stop is None:
                hit = model_hit(data, gx, gy, fr, px, py, pz)
                if hit:
                    model_stop = (f, hit)
            vy = s.sw(H.YVEL + 2 * s.PUCK) * sg
            if game_stop is None and (vy < vy0 // 2 or e.w(PUCKC) == g):
                game_stop = f
                result = "saved"
                break
            if s.score() != s0:
                result = "goal"
                break
            if abs(py) > 275 or abs(px) > 130:
                break
            ot.run()
        key = (result, "model stops" if model_stop else "model misses")
        table[key] += 1
        if result == "saved" and not model_stop and len(examples) < 4:
            examples.append(trace[-6:])
        breathe()
    print(f"{sum(table.values())} strikes {lo}-{hi} out:")
    for k, v in sorted(table.items()):
        print("  ", k, v)
    for ex in examples:
        print("game saved, the model's test missed: (f, puck x, y, z, goalie x, y, frame, lock)")
        for t in ex:
            print("    ", t, data.hot(t[6]))


if __name__ == "__main__":
    main()
