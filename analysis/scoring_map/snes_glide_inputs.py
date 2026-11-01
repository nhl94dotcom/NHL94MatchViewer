"""Which of the one-timer check's inputs make the gliding goalie weak from range (2026-11-01, SNES_SHOOTING 4.7): on
the game's own puck path he stops as often as the game (snes_goalie_path.py), but ot_xg_check_snes gives him 4x the
game's goals from 120-200 out, with or without the game's launch. That check estimates his speed from his movement
over the swing and blurs his spot (GOALIE_SPREAD 2); here each one-timer (the overnight check's, the distance band) is
struck again (one seed), and the model (gliding, the game's launch) is asked with his speed estimated as the check does
or read from the game, and with the blur or without, and seeing the puck a step late (xg_snes.STALE_PUCK) or not; summed against the game's rate over the overnight check's seeds.
python snes_glide_inputs.py [lo] [hi] [n]   (default 120 200 300)"""
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

FRAME, FACING = 0x0D97, 0x1163
WORK = (0x12C3, 0x12E3, 0x1303, 0x1343)
SAMPLES = 200


def main():
    lo = float(sys.argv[1]) if len(sys.argv) > 1 else 120
    hi = float(sys.argv[2]) if len(sys.argv) > 2 else 200
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    gentle()
    data = XS.RomData(SNES_ROM.read_bytes())
    rows = [json.loads(l) for l in open(RUNS / "ot_glide" / "ot_xg_check_snes.jsonl")]
    dist = lambda r: math.hypot(r["puck"][0], (264 if r["net"] == "top" else -264) - r["puck"][1])
    rows = [r for r in rows if lo <= dist(r) < hi]
    random.Random(4).shuffle(rows)
    ot = OneTimer("snes")
    s, e = ot.s, ot.e
    H, g = s.H, 2 * s.GOALIE
    tot, game, count = Counter(), 0.0, 0
    for r in rows[:n]:
        net, R, P = r["net"], r["R"], r["P"]
        rnd = random.Random(zlib.crc32(f"xgcheck-snes,{net},{R},{P}".encode()))
        ot.setup(net, P, R, r["p"], rnd)
        by = 2 + r["p"] % 4 if r["timing"] == "early" else 2 + (r["p"] * 5) % 9
        press, info = ot.pass_to_press(r["timing"], by=by)
        if press is None:
            continue
        e.unserialize(press)
        g0 = s.xy(s.GOALIE)
        pre, frames = ot.swing(press, r["aim"])
        if pre is None:
            continue
        ot.strike(pre, r["aim"], 12345)
        px, py = s.xy(s.PUCK)
        gx, gy = s.xy(s.GOALIE)
        nf = max(1, frames)
        est = ((gx - g0[0]) / nf * 4096, (gy - g0[1]) / nf * 4096)
        real = s.v(s.GOALIE)
        facing, frame = e.w(FACING + g) & 7, e.w(FRAME + g)
        ratings = [e.w(a + g) for a in WORK]
        launch = (*s.v(s.PUCK), s.sw(H.PUCKVZ))
        ty = 264 if net == "top" else -264
        count += 1
        game += r["game"]["GOAL"] / sum(r["game"].values())
        tot["overnight glide"] += r["models"]["glide"]
        VARIANTS = [("glide, est. v, spread 2", est, 2.0, True, False), ("glide, real v, spread 0", real, 0.0, True, False),
                    ("glide+stale, est. v, spread 2", est, 2.0, True, True),
                    ("glide+stale, real v, spread 0", real, 0.0, True, True),
                    ("old, est. v, spread 2", est, 2.0, False, False), ("old+stale, est. v, spread 2", est, 2.0, False, True)]
        for vname, v, spread, glide, stale in VARIANTS:
            if True:
                XS.GOALIE_SPREAD, XS.GLIDE_IN_SAVE, XS.STALE_PUCK = spread, glide, stale
                rng = random.Random(f"{net}{R}{P}{r['timing']}{r['p']}{r['aim']}")
                goals = sum(XS.play_out(px, py, 0, ty, 0, 1.0, 10, 0.5,
                                        XS.Goalie(data, gx, gy, v[0], v[1], facing, frame, *ratings), rng,
                                        launch=launch) == "goal" for _ in range(SAMPLES))
                tot[vname] += goals / SAMPLES
        XS.GLIDE_IN_SAVE, XS.GOALIE_SPREAD, XS.STALE_PUCK = False, 2.0, False
        breathe()
    print(f"{count} strikes {lo}-{hi} out: the game {game:.1f} goals (the overnight check's seeds)")
    for k, v in tot.items():
        print(f"  {k:28} {v:.1f}")


if __name__ == "__main__":
    main()
