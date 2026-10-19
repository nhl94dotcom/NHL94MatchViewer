"""Super-fast passes (Genesis; 2026-10-19, the user: now and then a person's pass comes out far faster than any
other). passtoa0 (input94.asm) aims a targeted pass at where the receiver's stick will be: it solves for the time t
(1/8 s steps, 1-24) when a puck at the passer's pass speed meets him if he keeps skating, then sets the puck's velocity
to cover that distance in t: v = distance x 65536 / (120 t), per axis. The solve is in 16-bit words, so this replays it
exactly (word wraps, signed multiplies of low words, the division's quotient word) on every targeted pass in the
recordings, from the sample before the pass, and compares the answer with what the puck did.
python analysis/fast_pass_study.py [capture folders]"""
import math
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "tools")
from export_match import Capture  # noqa: E402

BASE, SIZE, PUCK = 0xB04A, 0x80, 14
PASSSPEED, PASSPLAYER = 0xBEDE, 0xBEE0
HOTLIST = 0xA44C8
ROM = (Path.home() / "RetroArch-1.17-Win64/ROMs/Genesis/nhl94.bin").read_bytes()


def w16(v):
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def w32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v


def rec(k, off):
    return BASE + SIZE * k + off


def sroot(d0):
    """video94 sroot on an unsigned long (a negative long is a huge one)."""
    d0 &= 0xFFFFFFFF
    return int(math.isqrt(d0)) & 0xFFFF


def solve(dx, dy, rvx, rvy, passspeed):
    """passtoa0's arithmetic: returns (t, vx, vy) as the game computes them (vx / vy None on a division overflow)."""
    d5 = w16(passspeed >> 2)
    d2, d3 = w16(dx >> 2), w16(dy >> 2)
    vx = w16((w16(rvx) * 0xF0) >> 16)
    vy = w16((w16(rvy) * 0xF0) >> 16)
    j = w16(2 * w16(w16(d2 * vx) + w16(d3 * vy)))
    k = w32(vx * vx + vy * vy - d5 * d5)
    a2 = w32(d2 * d2 + d3 * d3)
    prod = w32(w16(a2) * w16(k) * 4)
    disc = w32(j * j - prod)
    root = sroot(disc)
    d5w = w16(k) >> 2
    if d5w == 0:
        d5w = 1
    d0 = root
    t = 0
    for _ in range(2):   # dbpl d3 with d3 = 1: at most two tries, the second with the root negated
        num = w16(w16(d0) - j)
        q = int(num / d5w)  # divs truncates toward zero
        if abs(q) > 32767:
            q = num  # overflow: d2 unchanged (its low word)
        t = w16(q)
        d0 = -d0
        if t >= 0:
            break
    if t == 0:
        t = 1
    if (t & 0xFFFF) > 24:
        t = 24
    out = []
    for disp_base, v in ((dx, vx), (dy, vy)):
        disp = w16(w16(disp_base) + (w32(v * t) >> 1))
        num = disp * 65536 + (0xFFFF if (w32(v * t) >> 1) < 0 else 0)
        q = int(num / (t * 120))
        out.append(None if abs(q) > 32767 else q)
    return t, out[0], out[1]


def main():
    folders = sys.argv[1:] or [str(p) for p in sorted((Path.home() / "Documents/NHL94 Viewer/captures").glob("2026-10-1[78]_2*"))]
    rows, agree = [], Counter()
    for folder in folders:
        cap = Capture(Path(folder))
        if cap.system.NAME != "genesis":
            continue
        for i in range(2, cap.count):
            k = cap.word(i, PASSPLAYER)
            if k >= 12 or cap.word(i - 1, PASSPLAYER) < 12:
                continue
            q = i - 1   # the state before the pass
            passer = cap.byte(q, rec(PUCK, 0x61))
            px, py = w16(cap.word(q, rec(PUCK, 0))), w16(cap.word(q, rec(PUCK, 0x14)))
            fr = cap.word(q, rec(k, 6))
            if not 0 < fr < 900:
                continue
            hx, hy = struct.unpack_from(">bb", ROM, HOTLIST + 2 * fr)
            if not cap.byte(q, rec(k, 0x76)) & 1:
                hx = -hx
            x, y = w16(cap.word(q, rec(k, 0))), w16(cap.word(q, rec(k, 0x14)))
            dx, dy = x + hx - px, y - hy - py
            rvx, rvy = w16(cap.word(q, rec(k, 0x28))), w16(cap.word(q, rec(k, 0x2A)))
            ps = cap.word(i, PASSSPEED)
            t, vx, vy = solve(dx, dy, rvx, rvy, ps)
            avx, avy = w16(cap.word(i, rec(PUCK, 0x28))), w16(cap.word(i, rec(PUCK, 0x2A)))
            actual = math.hypot(avx, avy)
            pred = math.hypot(vx or 0, vy or 0)
            agree["within 10%" if pred and abs(pred - actual) <= 0.1 * actual else "off"] += 1
            human = bool(cap.byte(q, rec(passer, 0x62)) & 0x08) if passer < 12 else None
            rows.append((round(actual), round(pred), t, round(math.hypot(dx, dy)), round(math.hypot(rvx, rvy)),
                         ps, human, Path(folder).name, i, passer, k))
    print("targeted passes:", len(rows), dict(agree))
    rows.sort(reverse=True)
    sp = sorted(r[0] for r in rows)
    print("actual speed: median", sp[len(sp) // 2], " 95th", sp[int(.95 * len(sp))], " max", sp[-1])
    print("fastest (actual, predicted, t in 1/8 s, distance to his stick, receiver speed, passspeed, person, game, sample, passer, receiver):")
    for r in rows[:20]:
        print("  ", r)
    print("by t:", sorted(Counter(r[2] for r in rows).items()))


if __name__ == "__main__":
    main()
