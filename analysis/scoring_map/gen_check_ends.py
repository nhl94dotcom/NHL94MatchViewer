"""The same body check at both nets, scripted (Genesis NHL '94, 2026-11-19; the recordings: people's C checks connect
more when defending the bottom net, 32.7% of tries against 26.9%, with the same chances and tries; is it the game?).

The scoring-map harness (paths.ROM, the test ROM; its states: period 1 has home defending the bottom net, period 2 the
top), the same period clock at both nets. Pad 1 has the home skater (record 2, the defender); the away carrier (record
7, given the puck) is driven straight at him (his speed set to SPEED toward the defender each frame until they are
within 24 or he falls: pad 2 doesn't take him in these states, and the computer steered him differently in the two);
everyone else but the goalies parked at the far end. In the defending net's frame (the
net at the goal line, "out" toward centre ice; the top net is the bottom one turned half a circle: x and y negated,
and every d-pad direction turned with them), the defender stands at (dx, out) facing out and the carrier starts 80
further out at an angle; the defender holds the direction toward the carrier and presses C (3 frames) a set number of frames in.
The random seed ($D066) is set per trial, the same at both nets
(each net's state would otherwise start every trial from its own fixed seed). Outcome within 90 frames of the press: a check counted (the home team's checks, +$10 of $C6CE, which FallDown adds
to), the carrier down (a fall animation), contact (within 16), or nothing; and the puck lost by the carrier.

python gen_check_ends.py OUT.jsonl   |   python gen_check_ends.py report OUT.jsonl"""
import json
import math
import sys
from collections import Counter

DIRS = {0: ["UP"], 1: ["UP", "RIGHT"], 2: ["RIGHT"], 3: ["DOWN", "RIGHT"], 4: ["DOWN"], 5: ["DOWN", "LEFT"],
        6: ["LEFT"], 7: ["UP", "LEFT"]}
FALL = {0x0D26, 0x0DD8, 0x136A, 0x1776, 0x17E8, 0x185A, 0x18CC, 0x193E, 0x1A00, 0x145C}
D_REC, A_REC = 2, 7
CHECKS = 0xC6CE + 0x10
CONT1, CONT2, PUCKC = 0xC328, 0xC32A, 0xB7AA
SPEED = 8000                      # the carrier's speed (about a skater's), set each frame until within 24


def direction(dx, dy):
    return round(math.degrees(math.atan2(dx, dy)) / 45) % 8


def run(out):
    from harness import Harness, rec, GOALIE
    from paths import STATE_TOP, STATE_BOTTOM
    import lowload
    lowload.gentle()
    # period 1 (STATE_TOP): home attacks the top net, so defends the bottom; period 2: defends the top
    hb = Harness(state=STATE_TOP, top=True)
    ht = Harness(state=STATE_BOTTOM, top=False, emu=hb.e)
    e = hb.e
    nets = {"bottom": (hb, -1), "top": (ht, 1)}

    def put(k, x, y):
        r = rec(k)
        for off, v in ((0, x), (2, 0), (0x14, y), (0x16, 0), (0x28, 0), (0x2A, 0), (0x2C, 0)):
            e.setw(r + off, v & 0xFFFF)

    def park(sg):
        for k in range(12):
            if k in (D_REC, A_REC, 5, 11):
                continue
            put(k, -100 + 18 * k, -sg * 230)        # the far end from the defended net

    with open(out, "w") as fo:
        for net, (h, sg) in nets.items():
            gl = sg * 264                           # the defended goal line; "out" = -sg in y
            for dx in (-40, 0, 40):
                for depth in (70, 110):
                    for ang in (-45, -20, 0, 20, 45):
                        for press in (6, 10, 14, 18, 22):
                            for phase in range(3):
                                e.unserialize(h.base)
                                e.setw(0xC468, 300 - phase)
                                D = (sg * dx, gl - sg * depth)              # half-turn: x negated at the top net
                                ax = dx + 80 * math.sin(math.radians(ang))
                                ao = depth + 80 * math.cos(math.radians(ang))
                                A = (round(sg * ax), round(gl - sg * ao))
                                for _ in range(20 + phase):
                                    park(sg)
                                    put(D_REC, *D)
                                    put(A_REC, *A)
                                    e.setw(PUCKC, A_REC)
                                    e.setw(CONT1, 1)
                                    e.setw(CONT2, 2)
                                    e.run(1)
                                trial = ((dx + 40) // 40) * 1000 + (depth // 10) * 100 + (ang + 45) * 3 + press * 7 + phase
                                e.setl(0xD066, (0x9E3779B1 * (trial + 1)) & 0xFFFFFFFF or 1)   # the same draws at both nets
                                c0 = e.w(CHECKS)
                                res = dict(net=net, dx=dx, depth=depth, ang=ang, press=press, phase=phase)
                                down = contact = False
                                mind = 999.0
                                steer = True
                                for f in range(press + 90):
                                    park(sg)
                                    dxy = (e.sw(rec(A_REC)) - e.sw(rec(D_REC)), e.sw(rec(A_REC) + 0x14) - e.sw(rec(D_REC) + 0x14))
                                    to_a = DIRS[direction(*dxy)]
                                    if steer:                       # the carrier driven straight at the defender
                                        L = math.hypot(*dxy) or 1
                                        e.setw(rec(A_REC) + 0x28, round(-SPEED * dxy[0] / L) & 0xFFFF)
                                        e.setw(rec(A_REC) + 0x2A, round(-SPEED * dxy[1] / L) & 0xFFFF)
                                        if L < 24 or e.w(rec(A_REC) + 0x58) in FALL:
                                            steer = False
                                    hold = to_a + (["C"] if press <= f < press + 3 else [])
                                    e.run(1, hold=hold)
                                    d = math.hypot(*dxy)
                                    mind = min(mind, d)
                                    contact |= d < 16
                                    if e.w(rec(A_REC) + 0x58) in FALL:
                                        down = True
                                    if f > press + 90:
                                        break
                                res.update(check=e.w(CHECKS) - c0, down=down, contact=contact, mind=round(mind, 1),
                                           lost=e.w(PUCKC) != A_REC)
                                fo.write(json.dumps(res) + "\n")
                fo.flush()
            print(net, "done", flush=True)
            lowload.breathe()


def report(path):
    R = [json.loads(line) for line in open(path)]
    for net in ("top", "bottom"):
        rs = [r for r in R if r["net"] == net]
        n = len(rs)
        c = Counter()
        for r in rs:
            c["check counted"] += r["check"] > 0
            c["carrier down"] += r["down"]
            c["contact"] += r["contact"]
            c["puck lost"] += r["lost"]
        print(f"{net:6s} {n} trials: " + ", ".join(f"{k} {v} ({v / n:.1%})" for k, v in c.items()))
    keys = {(r["dx"], r["depth"], r["ang"], r["press"], r["phase"]): r for r in R if r["net"] == "bottom"}
    pairs = [(keys.get((r["dx"], r["depth"], r["ang"], r["press"], r["phase"])), r) for r in R if r["net"] == "top"]
    pairs = [(b, t) for b, t in pairs if b]
    only_b = sum(b["check"] > 0 and not t["check"] > 0 for b, t in pairs)
    only_t = sum(t["check"] > 0 and not b["check"] > 0 for b, t in pairs)
    print(f"paired: a check counted at the bottom net only {only_b}, at the top only {only_t} (of {len(pairs)})")
    for ang in (-45, -20, 0, 20, 45):
        for net in ("top", "bottom"):
            rs = [r for r in R if r["net"] == net and r["ang"] == ang]
            print(f"   angle {ang:+3d} {net:6s}: checks {sum(r['check'] > 0 for r in rs)}/{len(rs)}")


if __name__ == "__main__":
    if sys.argv[1] == "report":
        report(sys.argv[2])
    else:
        run(sys.argv[1])
