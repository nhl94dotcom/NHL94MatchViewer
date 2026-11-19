"""The SNES top and bottom nets, the same shots at both, and every rebound (2026-11-19; NOSE4Web's two SNES leads:
checkpuckcoll_ccx's body box one unit off centre in y, `cmp #$000B` at file $F191D, and puckgoalie's rebound
direction rule by the goalie's y speed, `bmi` at file $F71AF; test ROMs NHL94_box_even / _rebound_plain / _both).

The ROM is paths.SNES_ROM (NHL94_SNES_ROM: a patched copy). From the harness states (snes_top.state, period 1, and
snes_bottom.state, period 2: Montreal's goalie at each net), the home centre shoots from each spot of a grid (net
coordinates: x across, d out from the goal line, the bottom net turned half a circle) with each aim (passdir 0-8, the
bottom net's turned the same way: d -> d + 4, 8 stays 8). For a spot the period clock and the settling seed are the
same at both nets, and so are the SEEDS release seeds (harness.fire). Played out 180 frames: goal (the score), held
(the goalie has it 20 frames), else where it ends up. Every touch by the goalie (he holds it, or the puck's speed
changes by over 1,000 within 32 of him): the first one's rebound, its velocity in net coordinates ("out" toward
centre ice, "side" to the goalie's right looking out) and what came next: goal, held, back toward the goal line (the
puck moving goalward within 60 of the line after the rebound), out of the zone, or loose.

python snes_updown_check.py OUT.jsonl [SEEDS]
python snes_updown_check.py report RETAIL.jsonl [OTHER.jsonl ...]"""
import json
import math
import sys
from collections import Counter

XS = (-60, -30, 0, 30, 60)
DS = (40, 70, 100, 130, 160)
GL = 264


def run(out, seeds):
    import lowload
    from snes_harness import Harness, XPOS, YPOS, XVEL, YVEL, PUCK, PUCKC, SCORE_HOME, GOALIE, o
    from paths import SNES_STATE_TOP, SNES_STATE_BOTTOM, SNES_ROM
    lowload.gentle()
    top = Harness(state=SNES_STATE_TOP, top=True)
    hs = {"top": top, "bottom": Harness(state=SNES_STATE_BOTTOM, top=False, emu=top.e)}
    e = top.e
    print("ROM", SNES_ROM, flush=True)
    with open(out, "w") as fo:
        for si, (x, d) in enumerate((x, d) for x in XS for d in DS):
            clock = 280 - (si * 7) % 40
            for net, h in hs.items():
                sg = 1 if net == "top" else -1
                for aim in range(9):
                    a = aim if net == "top" or aim == 8 else (aim + 4) % 8
                    h.setup(sg * x, sg * (GL - d), settle=90, clock=clock, seed=0x1234567 + si * 101)
                    pre, f = h.shoot(a)
                    if pre is None:
                        continue
                    for s in range(seeds):
                        h.fire(pre, a, (0x9E3779B1 * (si * 97 + aim * 13 + s + 1)) & 0xFFFFFFFF or 1)
                        s0 = e.w(SCORE_HOME)
                        res, held, reb, after = None, 0, None, None
                        prev = (h.sw(XVEL + o(PUCK)), h.sw(YVEL + o(PUCK)))
                        touch_f = None
                        for fr in range(180):
                            h.park(keep_shooter=False)
                            e.run(1)
                            px, py = h.sw(XPOS + o(PUCK)), h.sw(YPOS + o(PUCK))
                            vx, vy = h.sw(XVEL + o(PUCK)), h.sw(YVEL + o(PUCK))
                            gx, gy = h.sw(XPOS + o(GOALIE)), h.sw(YPOS + o(GOALIE))
                            scored = e.w(SCORE_HOME) != s0
                            has = e.w(PUCKC) == o(GOALIE)
                            near = math.hypot(px - gx, py - gy) < 32
                            if reb is None and (has or (near and math.hypot(vx - prev[0], vy - prev[1]) > 1000)):
                                touch_f = fr
                                reb = dict(held=has, out=-sg * vy, side=sg * vx, speed=round(math.hypot(vx, vy)),
                                           px=sg * px, py=GL - sg * py, gx=sg * gx, gy=GL - sg * gy)
                            if scored:
                                res = "goal"
                                break
                            held = held + 1 if has else 0
                            if held >= 20:
                                res = "held"
                                break
                            if reb is not None and touch_f is not None and fr > touch_f and after is None:
                                if sg * vy > 0 and GL - sg * py < 60 and not has:
                                    after = "back toward the goal line"
                            if sg * py < 88 or abs(py) > 300:
                                res = "out of the zone" if sg * py < 88 else "out"
                                break
                            prev = (vx, vy)
                        if res is None:
                            res = "loose"
                        if reb is not None:
                            reb["next"] = res if after is None else (after + (" and in" if res == "goal" else ""))
                        fo.write(json.dumps(dict(net=net, x=x, d=d, aim=aim, seed=s, res=res, reb=reb)) + "\n")
            fo.flush()
            print("spot", si + 1, "of", len(XS) * len(DS), flush=True)
            lowload.breathe()


def report(paths):
    for p in paths:
        R = [json.loads(line) for line in open(p)]
        print(f"== {p}")
        for net in ("top", "bottom"):
            rs = [r for r in R if r["net"] == net]
            c = Counter(r["res"] for r in rs)
            rb = [r["reb"] for r in rs if r["reb"] and not r["reb"]["held"]]
            nxt = Counter(b["next"] for b in rb)
            outs = sorted(b["out"] for b in rb)
            print(f"  {net:6s} {len(rs)} shots: goals {c['goal']} ({c['goal'] / max(len(rs), 1):.1%}), held {c['held']}; "
                  f"rebounds {len(rb)}: speed median {sorted(b['speed'] for b in rb)[len(rb) // 2] if rb else 0}, "
                  f"moving out {sum(o_ > 0 for o_ in outs)}, back goalward {sum(o_ < 0 for o_ in outs)}, sideways "
                  f"{sum(o_ == 0 for o_ in outs)}")
            print(f"         after a rebound: {dict(nxt)}")
    if len(paths) > 1:
        base = {(r["net"], r["x"], r["d"], r["aim"], r["seed"]): r for r in map(json.loads, open(paths[0]))}
        for p in paths[1:]:
            other = {(r["net"], r["x"], r["d"], r["aim"], r["seed"]): r for r in map(json.loads, open(p))}
            for net in ("top", "bottom"):
                ks = [k for k in base if k[0] == net and k in other]
                ch = Counter((base[k]["res"], other[k]["res"]) for k in ks if base[k]["res"] != other[k]["res"])
                print(f"  {p} vs {paths[0]}, {net}: {sum(ch.values())} of {len(ks)} changed: {dict(ch)}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2:])
    else:
        run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
