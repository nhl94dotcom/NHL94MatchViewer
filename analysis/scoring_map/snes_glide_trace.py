"""Where the gliding goalie parts from the game's (2026-11-01, SNES_SHOOTING 4.7): on the game's own puck path he stops
as often as the game (snes_goalie_path.py), but played out by the model (xg_snes.play_out) from the game's launch, with
the game's goalie speed, no blur and his inner state from RAM, he lets in 15 goals where the game lets in 3 from 120-200
out (snes_glide_inputs.py). Here each one-timer (the overnight check's, the distance band) is struck again (one seed)
and followed frame by frame in the game; the model's play-out (gliding, one random stream) is logged step by step from
the same start. Lined up by the puck's y, per strike: the outcomes, where the two pucks and goalies first part, and the
save moves' start; with --show, the full side-by-side for the strikes the game saved and the model let in.
python snes_glide_trace.py [lo] [hi] [n] [--show k]   (default 120 200 60)"""
import json
import math
import random
import statistics as st
import sys
import zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import xg_snes as XS  # noqa: E402

from lowload import breathe, gentle  # noqa: E402
from ot_harness import OneTimer  # noqa: E402
from paths import RUNS, SNES_ROM  # noqa: E402
from snes_goalie_state import internals as read_internals  # noqa: E402

FRAME, PFALOCK, PUCKC, FACING = 0x0D97, 0x14E3, 0x0AD9, 0x1163
WORK = (0x12C3, 0x12E3, 0x1303, 0x1343)


def model_run(G, launch, px, py, ty, rng):
    """xg_snes.play_out's loop (no rebound), logging each step: (puck x, y, h, goalie x, y, vx, vy, frame, in save)."""
    vx, vy, vz = launch
    x, y, h = px, py, 0.0
    front = 259 if ty > 0 else -259
    log = []
    for _ in range(0, 300, XS.STEP):
        seen = (x, y, vx, vy, h, vz)
        nx, ny = x + XS.STEP * vx / 4096, y + XS.STEP * vy / 4096
        vz -= 96 * XS.STEP
        nh = h + XS.STEP * vz / 4096
        if nh < 0:
            nh, vz = 0.0, -vz / 2 if vz < 0 else vz
        if (ny - front) * (y - front) <= 0 and ny != y:
            q = (front - y) / (ny - y)
            cx, cz = x + q * (nx - x), h + q * (nh - h)
            res = "over" if cz >= 13 else "goal" if abs(cx) <= 17 else "post" if abs(cx) <= 22 else "wide"
            return res, log
        x, y, h = nx, ny, nh
        G.step(*(seen if XS.STALE_PUCK else (x, y, vx, vy, h, vz)), rng)
        log.append((x, y, h, G.x, G.y, G.vx, G.vy, G.frame, G.save is not None))
        hot = G.data.hot(G.frame)
        if hot:
            hx, hy, d2, top, bottom = hot
            ex, ey = G.x + hx - x, G.y + hy - y
            if abs(ex) < d2 and abs(ey) < d2 and h <= top and (bottom < 0 or bottom < h) and ex * ex + ey * ey <= d2 * d2:
                return "save", log
        if -11 <= G.x - x <= 10 and -11 <= G.y - y <= 10:
            return "save", log
        if abs(y) > 300 or abs(x) > 140:
            return "wide", log
    return "wide", log


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show = int(sys.argv[sys.argv.index("--show") + 1]) if "--show" in sys.argv else 0
    if show:
        args = [a for a in args if a != str(show)]
    lo = float(args[0]) if len(args) > 0 else 120
    hi = float(args[1]) if len(args) > 1 else 200
    n = int(args[2]) if len(args) > 2 else 60
    gentle()
    XS.GLIDE_IN_SAVE, XS.GOALIE_SPREAD = True, 0.0
    data = XS.RomData(SNES_ROM.read_bytes())
    rows = [json.loads(l) for l in open(RUNS / "ot_glide" / "ot_xg_check_snes.jsonl")]
    dist = lambda r: math.hypot(r["puck"][0], (264 if r["net"] == "top" else -264) - r["puck"][1])
    rows = [r for r in rows if lo <= dist(r) < hi]
    random.Random(5).shuffle(rows)
    ot = OneTimer("snes")
    s, e = ot.s, ot.e
    H, g = s.H, 2 * s.GOALIE
    table, shown = Counter(), 0
    part_puck, part_goalie, save_game, save_model, gap_at_line = [], [], [], [], []
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
        ty = 264 * sg
        px, py = s.xy(s.PUCK)
        gx, gy = s.xy(s.GOALIE)
        gv = s.v(s.GOALIE)
        facing, frame0 = e.w(FACING + g) & 7, e.w(FRAME + g)
        ratings = [e.w(a + g) for a in WORK]
        state = read_internals(bytes(e.ram[:0x4000]), s.GOALIE, data, net == "top")
        launch = (*s.v(s.PUCK), s.sw(H.PUCKVZ))
        vy0 = launch[1] * sg
        glog, gres, s0 = [], "wide", s.score()
        for f in range(80):
            x, y = s.xy(s.PUCK)
            gxx, gyy = s.xy(s.GOALIE)
            glog.append((f, x, y, s.sw(H.PUCKZ), gxx, gyy, *s.v(s.GOALIE), e.w(FRAME + g),
                         e.w(PFALOCK + g) in XS.SAVES))
            if s.sw(H.YVEL + 2 * s.PUCK) * sg < vy0 // 2 or e.w(PUCKC) == g:
                gres = "save"
                break
            if s.score() != s0:
                gres = "goal"
                break
            if abs(y) > 275 or abs(x) > 130:
                break
            ot.run()
        G = XS.Goalie(data, gx, gy, gv[0], gv[1], facing, frame0, *ratings)
        G.set_internals(**state)
        rng = random.Random(f"{net}{R}{P}{r['timing']}{r['p']}{r['aim']}")
        G.randomise(rng)
        G.x, G.y = gx, gy
        mres, mlog = model_run(G, launch, px, py, ty, rng)
        table[(gres, mres)] += 1
        # line up each model step with the game frame whose puck y is nearest
        pp = pg = None
        for k, m in enumerate(mlog):
            gf = min(glog, key=lambda q: abs(q[2] - m[1]))
            if pp is None and math.hypot(gf[1] - m[0], gf[2] - m[1]) > 3:
                pp = (k, abs(gf[2] - py))
            if pg is None and math.hypot(gf[4] - m[3], gf[5] - m[4]) > 3:
                pg = (k, abs(gf[2] - py), gf[4] - m[3])
        if pp:
            part_puck.append(pp[1])
        if pg:
            part_goalie.append(pg[1])
        gs = next((q for q in glog if q[9]), None)
        ms = next((m for m in mlog if m[8]), None)
        if gs:
            save_game.append(abs(gs[2] - py))
        if ms:
            save_model.append(abs(ms[1] - py))
        gl = next((q for q in glog if (q[2] - q[5]) * sg >= 0), None)
        ml = next((m for m in mlog if (m[1] - m[4]) * sg >= 0), None)
        if gl and ml:
            gap_at_line.append((gl[4] - gl[1], ml[3] - ml[0]))
        if show and shown < show and gres == "save" and mres == "goal":
            shown += 1
            print(f"\n== {net} R{R} P{P} {r['timing']} aim {r['aim']}: game {gres}, model {mres}; puck from "
                  f"({px},{py}) launch {launch}; goalie ({gx},{gy}) v {gv} facing {facing}")
            print("   game: f  puck x   y    z | goalie x   y    vx    vy  frame save ||  model: puck x   y    h | "
                  "goalie x     y      vx     vy  frame save")
            for k, m in enumerate(mlog):
                q = min(glog, key=lambda q: abs(q[2] - m[1]))
                print(f"   {q[0]:6} {q[1]:5} {q[2]:5} {q[3]:4} | {q[4]:5} {q[5]:5} {q[6]:6} {q[7]:6} {q[8]:5X} {int(q[9])}"
                      f"    ||  {m[0]:7.1f} {m[1]:6.1f} {m[2]:4.1f} | {m[3]:7.1f} {m[4]:6.1f} {m[5]:6} {m[6]:6} "
                      f"{m[7]:5X} {int(m[8])}")
        breathe()
    total = sum(table.values())
    print(f"\n{total} strikes {lo}-{hi} out (gliding, the game's goalie speed and inner state, no blur, one stream)")
    for (a, b), c in sorted(table.items()):
        print(f"  game {a:5} model {b:5}: {c}")
    if part_puck:
        print(f"  the pucks part (>3 apart) in {len(part_puck)}: median {st.median(part_puck):.0f} out from the shot")
    if part_goalie:
        print(f"  the goalies part (>3 apart) in {len(part_goalie)}: median {st.median(part_goalie):.0f} out from the shot")
    if save_game:
        print(f"  save move starts: game {len(save_game)} (median {st.median(save_game):.0f} after the shot), "
              f"model {len(save_model)} ({st.median(save_model) if save_model else 0:.0f})")
    if gap_at_line:
        print(f"  goalie x - puck x as the puck reaches him: game median |{st.median(abs(a) for a, b in gap_at_line):.1f}|, "
              f"model |{st.median(abs(b) for a, b in gap_at_line):.1f}|")


if __name__ == "__main__":
    main()
