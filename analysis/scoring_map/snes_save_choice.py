"""The SNES goalie's save move: the game's choice against the xG model's (2026-11-01, SNES_SHOOTING 4.7: the gliding
goalie is right close in but far too weak from range on the game's own one-timers). One-timers from the overnight check
(paths.RUNS / ot_glide / ot_xg_check_snes.jsonl, the given distance band) are struck again in the retail game with one
seed and followed frame by frame. When the goalie starts a save move (pfalock takes one of GoalieSaveList's
animations), the model's xg_snes.Goalie.save_move is asked from the same moment (the puck's spot, speed and height,
the goalie's spot and facing, read the frame before), and the two are compared (and with xg_snes.SAVE_CHOICE, the game's side rules); so is the game's save start against
the puck's crossing time. Also per strike: whether the goalie made a save move at all, and the game's result.
python snes_save_choice.py [lo] [hi] [n]   (distance band from the goal line's middle, default 60 200; n strikes)"""
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

PFALOCK, FACING, ATTR, PUCKVZ = 0x14E3, 0x1163, 0x0E03, None


def main():
    lo = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    hi = float(sys.argv[2]) if len(sys.argv) > 2 else 200
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    gentle()
    data = XS.RomData(SNES_ROM.read_bytes())
    rows = [json.loads(l) for l in open(RUNS / "ot_glide" / "ot_xg_check_snes.jsonl")]
    dist = lambda r: math.hypot(r["puck"][0], (264 if r["net"] == "top" else -264) - r["puck"][1])
    rows = [r for r in rows if lo <= dist(r) < hi]
    random.Random(1).shuffle(rows)
    ot = OneTimer("snes")
    s, e = ot.s, ot.e
    H, g = s.H, 2 * s.GOALIE
    same, kinds, made, timing, mism = Counter(), Counter(), Counter(), [], Counter()
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
        s0 = s.score()
        prev = None
        started = None
        for f in range(60):
            px, py = s.xy(s.PUCK)
            gx, gy = s.xy(s.GOALIE)
            st = dict(px=px, py=py, pz=s.sw(H.PUCKZ), pvx=s.sw(H.XVEL + 2 * s.PUCK), pvy=s.sw(H.YVEL + 2 * s.PUCK),
                      pvz=s.sw(H.PUCKVZ) if hasattr(H, "PUCKVZ") else 0, gx=gx, gy=gy, facing=e.w(FACING + g) & 7,
                      attr=e.w(ATTR + g), lock=e.w(PFALOCK + g))
            if st["lock"] in XS.SAVES and (prev is None or prev["lock"] not in XS.SAVES):
                started = (f, XS.SAVES.index(st["lock"]), prev or st)
                break
            if s.score() != s0 or abs(py) > 275:
                break
            prev = st
            ot.run()
        result = "goal" if s.score() != s0 else "no goal"
        if started is None:
            for _ in range(60):
                if s.score() != s0:
                    result = "goal"
                    break
                ot.run()
        made[(started is not None, result)] += 1
        if started:
            f, game_i, b = started
            G = XS.Goalie(data, b["gx"], b["gy"] if net == "top" else b["gy"], 0, 0, b["facing"], 0, 48, 8, 8, 7)
            XS.SAVE_CHOICE = True                      # the game's side rules (xg_snes.SAVE_CHOICE)
            fixed_i = G.save_move(b["px"], b["py"], b["pvx"], b["pvy"], b["pz"], b["pvz"], random.Random(f))
            XS.SAVE_CHOICE = False
            model_i = G.save_move(b["px"], b["py"], b["pvx"], b["pvy"], b["pz"], b["pvz"])
            ok = model_i == game_i
            same[ok] += 1
            same[("fixed", fixed_i == game_i)] += 1
            kinds[(game_i, model_i)] += 1
            if not ok:
                mism[(b["facing"], bool(b["attr"] & 0x0800), game_i, model_i)] += 1
            gl = 259 if net == "top" else -259
            timing.append(round((gl - b["py"]) * 4096 / b["pvy"]) if b["pvy"] else None)
        breathe()
    print(f"{sum(made.values())} strikes, {lo}-{hi} out: save move made / result {dict(made)}")
    print(f"the model's choice the game's: {same[True]} of {same[True] + same[False]}; with SAVE_CHOICE "
          f"{same[('fixed', True)]}")
    print("game index -> model index:", dict(kinds.most_common()))
    print("mismatches by (facing, mirrored, game, model):", dict(mism.most_common(20)))
    t = [x for x in timing if x is not None]
    if t:
        t.sort()
        print("frames from the save start to the crossing: median", t[len(t) // 2], "range", t[0], t[-1])


if __name__ == "__main__":
    main()
