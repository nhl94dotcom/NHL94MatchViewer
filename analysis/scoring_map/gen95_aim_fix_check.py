"""The bottom-net shot aim fix in NHL '95 played (2026-11-19; NOSE4Web's shotScatterFix for NHL '95: doshot's
`lsr.w #1,d0` at $84D40 a nop; NHL '94's version: gen_aim_fix_check.py).

Wrist shots launched by the game itself, on the ROM given (the live states of gen95_updown.py: period 1 at the top net,
period 2 at the bottom; the pad's skater shooting, everyone else parked, the away goalie in net). At each net the
shooter settles with the puck at each spot of a grid (net coordinates: x across, d out from the goal line; the bottom
net turned half a circle), the period clock the same at both nets for a spot; then each of the 9 aims (the d-pad held
through the release), the release frame replayed with SEEDS seeds ($CC6A set just before it), and the shot played
out: goal (either score), saved (the goalie holds it 20 frames, or it turns back), else where it first crossed the
goal line (|x| <= 24 on target: post / crossbar or a late save; beyond: wide). One line per shot.

python gen95_aim_fix_check.py ROM OUT.jsonl [SEEDS]   |   python gen_aim_fix_check.py report BASE.jsonl FIX.jsonl"""
import json
import sys

from emu import Emu
from gen95_updown import H95, STATES, rec, PUCK, GOALIE, PUCKC, SEED, SCORES

XS = (-90, -45, 0, 45, 90)
DS = (40, 70, 100, 130, 160)
DIRPAD = {0: ["UP"], 1: ["UP", "RIGHT"], 2: ["RIGHT"], 3: ["DOWN", "RIGHT"], 4: ["DOWN"], 5: ["DOWN", "LEFT"],
          6: ["LEFT"], 7: ["UP", "LEFT"], 8: []}


def main():
    import lowload
    rom, out = sys.argv[1], sys.argv[2]
    seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    lowload.gentle()
    e = Emu(rom)
    hs = {"top": H95(e, STATES / "live_p1.state", True), "bottom": H95(e, STATES / "live_p2.state", False)}
    p = rec(PUCK)
    with open(out, "w") as fo:
        for si, (x, d) in enumerate((x, d) for x in XS for d in DS):
            clock = 590 - (si * 7) % 40
            for net, h in hs.items():
                sg = 1 if net == "top" else -1
                h.setup(sg * x, sg * (264 - d), clock, settle=90)
                settled = e.serialize()
                for aim in range(9):
                    e.unserialize(settled)
                    # the release frame found with the aim held; it is then replayed from the frame before
                    pre = None
                    for f in range(90):
                        st = e.serialize()
                        h.park()
                        e.run(1, hold=(["C"] if f < 3 else []) + DIRPAD[aim])
                        if e.w(PUCKC) & 0xFF00:
                            pre = st
                            break
                    if pre is None:
                        continue
                    for s in range(seeds):
                        e.unserialize(pre)
                        e.setl(SEED, (0x9E3779B1 * (si * 97 + aim * 13 + s + 1)) & 0xFFFFFFFF or 1)
                        h.park()
                        e.run(1, hold=DIRPAD[aim])
                        v = (e.sw(p + 0x28), e.sw(p + 0x2A), e.sw(p + 0x2C))
                        s0 = tuple(e.w(a) for a in SCORES)
                        res, cross, held, away = None, None, 0, 0
                        prev = (e.sw(p), e.sw(p + 0x14))
                        for fr in range(150):
                            h.park(keep=False)
                            e.run(1)
                            px, py = e.sw(p), e.sw(p + 0x14)
                            if tuple(e.w(a) for a in SCORES) != s0:
                                res = "goal"
                                break
                            if cross is None and prev[1] * sg < 264 <= py * sg and py != prev[1]:
                                cross = prev[0] + (px - prev[0]) * (264 * sg - prev[1]) / (py - prev[1])
                            prev = (px, py)
                            held = held + 1 if e.w(PUCKC) == GOALIE else 0
                            away = away + 1 if e.sw(p + 0x2A) * sg < 0 else 0
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


if __name__ == "__main__":
    main()
