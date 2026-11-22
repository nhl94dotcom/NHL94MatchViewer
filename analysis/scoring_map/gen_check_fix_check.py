"""NOSE4Web's checkFix ("Everyone checks as the computer", nhl94_checkFix.bin: the `asl.w #1,d0` at $13D70, E340, a
NOP) played (2026-11-21). CCStart starts a check's knockdown sum at 120, doubled to 240 for a person's checker, then
takes away the checker's weight and adds the target's in one byte: a person's check wraps (the weight bug), and
pressing B after C hands the checker to the computer before contact (120: the CB check). With the NOP everyone uses
120 (GENESIS_MECHANICS 7.2's predictions for a person at equal impact: light into heavy 100% -> 18%, equal 10% ->
30%, heavy into light 13% -> 90%).

gen_check_ends.py's scripted check at the bottom net (the scoring-map harness, period 1's state): the pad-1 home
skater (record 2) faces the away carrier (record 7, driven at him) and presses C a set number of frames in; with CB, B
4 frames after C. The two players' weights (+$67, nibble x 8) set each trial: light 40 / heavy 80 / equal 60 / 60.
Run once on the test ROM and once on a copy with the same NOP (`build` makes it); the same trials and seeds.

python gen_check_fix_check.py build OUT.bin          (the test ROM with $13D70 E340 -> 4E71)
python gen_check_fix_check.py run OUT.jsonl          (NHL94_SMAP_ROM picks the ROM)
python gen_check_fix_check.py report A.jsonl B.jsonl"""
import json
import math
import sys
from collections import Counter

from gen_check_ends import CHECKS, CONT1, CONT2, D_REC, A_REC, DIRS, FALL, PUCKC, SPEED, direction

PAIRS = {"light into heavy": (40, 80), "equal": (60, 60), "heavy into light": (80, 40)}


def build(out):
    from paths import ROM
    b = bytearray(open(ROM, "rb").read())
    assert b[0x13D70:0x13D72] == bytes.fromhex("e340"), b[0x13D6C:0x13D76].hex()
    b[0x13D70:0x13D72] = bytes.fromhex("4e71")
    open(out, "wb").write(b)
    print("written", out)


def run(out):
    from harness import Harness, rec
    from paths import STATE_TOP
    import lowload
    lowload.gentle()
    h = Harness(state=STATE_TOP, top=True)
    e = h.e
    sg = -1
    gl = sg * 264

    def put(k, x, y):
        r = rec(k)
        for off, v in ((0, x), (2, 0), (0x14, y), (0x16, 0), (0x28, 0), (0x2A, 0), (0x2C, 0)):
            e.setw(r + off, v & 0xFFFF)

    def park():
        for k in range(12):
            if k in (D_REC, A_REC, 5, 11):
                continue
            put(k, -100 + 18 * k, -sg * 230)

    with open(out, "w") as fo:
        for pair, (wc, wt) in PAIRS.items():
            for mode in ("C", "CB"):
                for depth in (70, 110):
                    for ang in (-20, 0, 20):
                        for press in (6, 10, 14, 18):
                            for phase in range(4):
                                e.unserialize(h.base)
                                e.setw(0xC468, 300 - phase)
                                D = (0, gl - sg * depth)
                                ax = 80 * math.sin(math.radians(ang))
                                ao = depth + 80 * math.cos(math.radians(ang))
                                A = (round(sg * ax), round(gl - sg * ao))
                                for _ in range(20 + phase):
                                    park()
                                    put(D_REC, *D)
                                    put(A_REC, *A)
                                    e.setw(PUCKC, A_REC)
                                    e.setw(CONT1, 1)
                                    e.setw(CONT2, 2)
                                    e.run(1)
                                e.setb(rec(D_REC) + 0x67, wc)
                                e.setb(rec(A_REC) + 0x67, wt)
                                trial = (depth // 10) * 100 + (ang + 45) * 3 + press * 7 + phase
                                e.setl(0xD066, (0x9E3779B1 * (trial + 1)) & 0xFFFFFFFF or 1)
                                c0 = e.w(CHECKS)
                                down = contact = False
                                steer = True
                                for f in range(press + 90):
                                    park()
                                    dxy = (e.sw(rec(A_REC)) - e.sw(rec(D_REC)),
                                           e.sw(rec(A_REC) + 0x14) - e.sw(rec(D_REC) + 0x14))
                                    to_a = DIRS[direction(*dxy)]
                                    if steer:
                                        L = math.hypot(*dxy) or 1
                                        e.setw(rec(A_REC) + 0x28, round(-SPEED * dxy[0] / L) & 0xFFFF)
                                        e.setw(rec(A_REC) + 0x2A, round(-SPEED * dxy[1] / L) & 0xFFFF)
                                        if L < 24 or e.w(rec(A_REC) + 0x58) in FALL:
                                            steer = False
                                    hold = list(to_a)
                                    if press <= f < press + 3:
                                        hold.append("C")
                                    if mode == "CB" and press + 4 <= f < press + 7:
                                        hold.append("B")
                                    e.run(1, hold=hold)
                                    contact |= math.hypot(*dxy) < 16
                                    if e.w(rec(A_REC) + 0x58) in FALL:
                                        down = True
                                fo.write(json.dumps(dict(pair=pair, mode=mode, depth=depth, ang=ang, press=press,
                                                         phase=phase, check=e.w(CHECKS) - c0, down=down,
                                                         contact=contact, weights=[e.b(rec(D_REC) + 0x67),
                                                                                    e.b(rec(A_REC) + 0x67)])) + "\n")
                fo.flush()
                print(pair, "done", flush=True)
                lowload.breathe()


def report(paths):
    for p in paths:
        R = [json.loads(x) for x in open(p) if x.strip()]
        print(f"== {p}: {len(R)} trials")
        for pair in PAIRS:
            for mode in ("C", "CB"):
                S = [r for r in R if r["pair"] == pair and r["mode"] == mode and r["contact"]]
                d = sum(r["down"] for r in S)
                c = sum(r["check"] > 0 for r in S)
                print(f"  {pair:17s} {mode:2s}: contact {len(S):3d}, carrier down {d:3d} ({d / max(len(S), 1):.0%}), "
                      f"check counted {c}")


def main():
    if sys.argv[1] == "build":
        build(sys.argv[2])
    elif sys.argv[1] == "run":
        run(sys.argv[2])
    else:
        report(sys.argv[2:])


if __name__ == "__main__":
    main()
