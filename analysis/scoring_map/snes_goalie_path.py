"""The SNES goalie's path: the game's against the xG model's, on the game's own puck path (2026-11-01, SNES_SHOOTING 4.7:
the gliding goalie is far too weak from range, though the model's save choice and save areas agree with the game:
snes_save_choice.py, snes_save_geometry.py). One-timers from the overnight check (paths.RUNS / ot_glide /
ot_xg_check_snes.jsonl, the given distance band) are struck again in the retail game with one seed and followed frame
by frame. The model's goalie (xg_snes.Goalie) starts from the game's state at the strike (spot, speed, facing, frame,
ratings and, with "state", his inner state from RAM) and is stepped along the game's own puck (each game step: the frames
since the puck last moved), with and without gliding in a save. Per variant: how often the model's test (save area, then
body box) stops the puck before the goal line, against how often the game stopped it; where the goalie is when the puck
reaches his line, and when the save move starts.
python snes_goalie_path.py [lo] [hi] [n]   (default 120 200 150)"""
import json
import math
import random
import statistics as st
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as XS  # noqa: E402

from lowload import breathe, gentle  # noqa: E402
from ot_harness import OneTimer  # noqa: E402
from paths import RUNS, SNES_ROM  # noqa: E402
from snes_goalie_state import internals as read_internals  # noqa: E402
from snes_save_geometry import model_hit  # noqa: E402

FRAME, PFALOCK, PUCKC, FACING = 0x0D97, 0x14E3, 0x0AD9, 0x1163
WORK = (0x12C3, 0x12E3, 0x1303, 0x1343)
SEEDS = 8


def main():
    lo = float(sys.argv[1]) if len(sys.argv) > 1 else 120
    hi = float(sys.argv[2]) if len(sys.argv) > 2 else 200
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 150
    gentle()
    data = XS.RomData(SNES_ROM.read_bytes())
    rows = [json.loads(l) for l in open(RUNS / "ot_glide" / "ot_xg_check_snes.jsonl")]
    dist = lambda r: math.hypot(r["puck"][0], (264 if r["net"] == "top" else -264) - r["puck"][1])
    rows = [r for r in rows if lo <= dist(r) < hi]
    random.Random(3).shuffle(rows)
    ot = OneTimer("snes")
    s, e = ot.s, ot.e
    H, g = s.H, 2 * s.GOALIE
    stops, off, start, game = defaultdict(list), defaultdict(list), defaultdict(list), Counter()
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
        sg = 1 if net == "top" else -1
        gx0, gy0 = s.xy(s.GOALIE)
        gv0 = s.v(s.GOALIE)
        facing, frame0 = e.w(FACING + g) & 7, e.w(FRAME + g)
        ratings = [e.w(a + g) for a in WORK]
        state = read_internals(bytes(e.ram[:0x4000]), s.GOALIE, data, net == "top")
        vy0 = s.sw(H.YVEL + 2 * s.PUCK) * sg
        path, saved, gsave, garrive = [], False, None, None
        s0 = s.score()
        for f in range(60):
            px, py = s.xy(s.PUCK)
            gx, gy = s.xy(s.GOALIE)
            path.append((px, py, s.sw(H.PUCKZ), s.sw(H.XVEL + 2 * s.PUCK), s.sw(H.YVEL + 2 * s.PUCK),
                         s.sw(H.PUCKVZ)))
            if gsave is None and e.w(PFALOCK + g) in XS.SAVES:
                gsave = f
            if garrive is None and (py - gy) * sg >= 0:
                garrive = gx - px
            vy = s.sw(H.YVEL + 2 * s.PUCK) * sg
            if vy < vy0 // 2 or e.w(PUCKC) == g:
                saved = True
                break
            if s.score() != s0 or abs(py) > 275 or abs(px) > 130:
                break
            ot.run()
        game["saved" if saved else "not"] += 1
        if garrive is not None:
            off["game"].append(abs(garrive))
        if gsave is not None:
            start["game"].append(gsave)
        for glide in (False, True):
            for use in (False, True):
                XS.GLIDE_IN_SAVE = glide
                name = ("glide" if glide else "old") + ("+state" if use else "")
                for k in range(SEEDS if not use else 1):
                    rng = random.Random(k)
                    G = XS.Goalie(data, gx0, gy0, gv0[0], gv0[1], facing, frame0, *ratings)
                    if use:
                        G.set_internals(**state)
                    G.randomise(rng)
                    G.x, G.y = gx0, gy0
                    stop, arrive, last, msave = False, None, path[0], None
                    for f, p in enumerate(path[1:], 1):
                        if (p[0], p[1]) == (last[0], last[1]):
                            continue                          # the game ran no step this frame
                        G.step(p[0], p[1], p[3], p[4], p[2], p[5], rng, frames=2)
                        last = p
                        if msave is None and G.save is not None:
                            msave = f
                        if arrive is None and (p[1] - G.y) * sg >= 0:
                            arrive = G.x - p[0]
                        if model_hit(data, G.x, G.y, G.frame, p[0], p[1], p[2]):
                            stop = True
                            break
                    stops[name].append(stop)
                    if arrive is not None:
                        off[name].append(abs(arrive))
                    if msave is not None:
                        start[name].append(msave)
        XS.GLIDE_IN_SAVE = False
        breathe()
    total = sum(game.values())
    print(f"{total} strikes {lo}-{hi} out: the game stopped {game['saved']} ({100 * game['saved'] / total:.0f}%)")
    for name, v in stops.items():
        print(f"  {name:12} the model's goalie stops {100 * sum(v) / len(v):.0f}%")
    for name, v in off.items():
        print(f"  {name:12} |goalie x - puck x| when the puck reaches his line: median {st.median(v):.1f}, "
              f"within 11 {100 * sum(x <= 11 for x in v) / len(v):.0f}%")
    for name, v in start.items():
        print(f"  {name:12} save move started: {len(v)} times, median frame {st.median(v)}")


if __name__ == "__main__":
    main()
