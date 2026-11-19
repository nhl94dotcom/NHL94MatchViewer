"""The bottom-net shot aim fix played (2026-11-19; NOSE4Web's shotScatterFix: doshot's `lsr.w #1,d0`, which halves the
depth scatter when the aim's dy < 0, i.e. at the bottom net, made a nop; retail $C492, the test ROM $C48E).

Wrist shots taken by the game itself (harness.shoot: the doshot frame not taken over), on the ROM paths.ROM points at
(NHL94_SMAP_ROM: the test ROM, or a copy with the nop). At each net (live.state top, live_p2.state bottom), the shooter
settles with the puck at each spot of a grid (net coordinates: x across, d out from the goal line; the bottom net
turned half a circle), the period clock the same at both nets for a spot; then each of the 9 aims (0-8), and for each
the doshot frame replayed with SEEDS game seeds ($D066 set just before it, the aim held), the shot played out with
everyone else kept away: goal (the score), saved (the goalie held it 20 frames, or it turned back), else where it first
crossed the goal line (|x| <= 24 on target: post / crossbar or a late save; beyond: wide). One line per shot.

python gen_aim_fix_check.py OUT.jsonl [SEEDS]
python gen_aim_fix_check.py report BASE.jsonl FIX.jsonl"""
import json
import sys
from collections import Counter
from pathlib import Path

XS = (-90, -45, 0, 45, 90)
DS = (40, 70, 100, 130, 160)
SEED = 0xD066


def run(out, seeds):
    import harness as H
    from harness import Harness, DIRPAD, PUCK, PUCKC, SCORE_HOME, GOALIE, rec
    from paths import STATE_TOP, STATE_BOTTOM, ROM
    import lowload
    lowload.gentle()
    top_h = Harness(state=STATE_TOP, top=True)
    hs = {"top": top_h, "bottom": Harness(state=STATE_BOTTOM, top=False, emu=top_h.e)}
    e = top_h.e
    print("ROM", ROM, flush=True)
    with open(out, "w") as fo:
        for si, (x, d) in enumerate((x, d) for x in XS for d in DS):
            clock = 590 - (si * 7) % 40
            for net, h in hs.items():
                sg = 1 if net == "top" else -1
                h.setup(sg * x, sg * (264 - d), settle=90, clock=clock)
                settled = e.serialize()
                for aim in range(9):
                    e.unserialize(settled)
                    pre, f = h.shoot(aim)
                    if pre is None:
                        continue
                    for s in range(seeds):
                        e.unserialize(pre)
                        e.setl(SEED, (0x9E3779B1 * (si * 97 + aim * 13 + s + 1)) & 0xFFFFFFFF or 1)
                        h.park()
                        e.run(1, hold=DIRPAD[aim])
                        v = (e.sw(PUCK + 0x28), e.sw(PUCK + 0x2A), e.sw(PUCK + 0x2C))
                        s0, res, cross, held, away = e.w(SCORE_HOME), None, None, 0, 0
                        prev = (e.sw(PUCK), e.sw(PUCK + 0x14))
                        for fr in range(150):
                            h.park(keep_shooter=False)
                            e.run(1)
                            px, py = e.sw(PUCK), e.sw(PUCK + 0x14)
                            if e.w(SCORE_HOME) != s0:
                                res = "goal"
                                break
                            if cross is None and (prev[1] * sg < 264 <= py * sg) and py != prev[1]:
                                cross = prev[0] + (px - prev[0]) * (264 * sg - prev[1]) / (py - prev[1])
                            prev = (px, py)
                            held = held + 1 if e.w(PUCKC) == GOALIE else 0
                            away = away + 1 if e.sw(PUCK + 0x2A) * sg < 0 else 0
                            if held >= 20 or (away >= 4 and cross is None):
                                res = "saved"
                                break
                            if py * sg > 290:
                                break
                        if res is None:
                            res = "saved" if cross is None else ("on target" if abs(cross) <= 24 else "wide")
                        fo.write(json.dumps(dict(net=net, x=x, d=d, aim=aim, seed=s, res=res, v=v,
                                                 cross=None if cross is None else round(sg * cross, 1))) + "\n")
            fo.flush()
            print("spot", si + 1, "of", len(XS) * len(DS), flush=True)
            lowload.breathe()


def report(a, b):
    A = {(r["net"], r["x"], r["d"], r["aim"], r["seed"]): r for r in map(json.loads, open(a))}
    B = {(r["net"], r["x"], r["d"], r["aim"], r["seed"]): r for r in map(json.loads, open(b))}
    for net in ("top", "bottom"):
        keys = [k for k in A if k[0] == net and k in B]
        same_v = sum(A[k]["v"] == B[k]["v"] for k in keys)
        ca, cb = Counter(A[k]["res"] for k in keys), Counter(B[k]["res"] for k in keys)
        print(f"{net}: {len(keys)} shots; launch identical {same_v}; results changed "
              f"{sum(A[k]['res'] != B[k]['res'] for k in keys)}")
        for res in ("goal", "saved", "on target", "wide"):
            print(f"   {res:9s} base {ca[res]:5d} ({ca[res] / len(keys):5.1%})   fix {cb[res]:5d} ({cb[res] / len(keys):5.1%})")
        moved = Counter((A[k]["res"], B[k]["res"]) for k in keys if A[k]["res"] != B[k]["res"])
        print("   changes", dict(moved))


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2], sys.argv[3])
    else:
        run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 4)
