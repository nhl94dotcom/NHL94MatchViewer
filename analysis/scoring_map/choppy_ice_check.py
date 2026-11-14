"""NOSE4Web's choppy ice (6847618, both systems), played (2026-11-14): the puck slows up to a quarter more as each
period goes on (L/16 more, L the quarters gone, 0-4, from PerTimeTotal and gameclock), fresh each period; only the
puck; no random numbers drawn.

friction ROM OUT: from a game in play (power-on, START into play, the computer on both sides), a saved state; for each
case (a period, gsp, and a share of it gone, by setting gameclock from PerTimeTotal) the loose puck is put at 12
spots in turn, each with speed (V + 37 k, 0) on the ice (k the run: the SNES build picks its updates by the puck's X fraction, which a
round speed can freeze), and its X speed read each frame for 30 frames (a run touched by
anyone, off the boards, in the air or with Y speed is dropped). Printed per case: the clean runs and the puck's
slowing a frame (its share of the speed lost), against the first case's (period 1, 2% gone).
  Genesis: the puck's record 14 (X +$00, Y +$14, Z +$18, speeds +$28 / +$2A / +$2C, carrier byte +$60 $FF loose),
  gsp $C466, gameclock $C468, PerTimeTotal $C46C. SNES: Xpos / Ypos $0D71 / $0DD3, puckz $0DF9, puckvz $0E01, Xvel /
  Yvel $0EDF / $0EFF, puckc $0AD9, gsp $1630, gameclock $1632, PerTimeTotal $1C82.
same ROM OUT FRAMES: the game from power-on as `friction` starts it, played on, work RAM's hash every 30 frames
  written to OUT/hashes.txt with the clock; run on the original and the build and compare (`compare A B`): with no
  quarter gone the two should be the same frame for frame.
compare A_OUT B_OUT: the first sample where the two differ, and the share of the period gone then.

python choppy_ice_check.py friction|same ROM OUT [FRAMES]
python choppy_ice_check.py compare A_OUT B_OUT"""
import hashlib
import sys
from pathlib import Path

import lowload

CASES = [(0, 0.02), (0, 0.30), (0, 0.55), (0, 0.80), (0, 0.90), (1, 0.02), (1, 0.90), (2, 0.90), (3, 0.02), (3, 0.90)]


class Gen:
    PUCK = 0xB04A + 14 * 0x80
    GSP, CLOCK, TOTAL = 0xC466, 0xC468, 0xC46C
    V = 6000

    def __init__(self, rom, out):
        import gen_1on1_edit_lines as G
        self.r = G.Run(rom, out)
        self.e = self.r.e
        self.r.to_play()

    def step(self, n):
        self.r.step(n)

    def place(self, x, y, v0):
        e, p = self.e, self.PUCK
        for off, v in ((0x00, x), (0x14, y), (0x18, 0), (0x28, v0), (0x2A, 0), (0x2C, 0), (0x5E, 0)):
            e.setw(p + off, v)
        e.setb(p + 0x60, 0xFF)

    def read(self):
        e, p = self.e, self.PUCK
        return e.sw(p + 0x28), e.sw(p + 0x2A), e.w(p + 0x18), e.b(p + 0x60) == 0xFF

    def ram(self):
        return bytes(self.e.ram)


class Snes:
    GSP, CLOCK, TOTAL = 0x1630, 0x1632, 0x1C82
    V = 3000

    def __init__(self, rom, out):
        from snes_ot_goal_check import start
        from snes_60fps_cvc import computer_only
        out.mkdir(parents=True, exist_ok=True)
        self.e, self.m = start(rom, 0, out)
        self.cpu = computer_only
        self.cpu(self.m)
        self.f = 0

    def step(self, n):
        for _ in range(n):
            self.e.run(1)
            self.f += 1
            if self.f % 300 == 0:
                self.cpu(self.m)
            if self.f % 600 == 0:
                lowload.breathe()

    def place(self, x, y, v0):
        m = self.m
        for a, v in ((0x0D71, x), (0x0DD3, y), (0x0DF9, 0), (0x0E01, 0), (0x0EDF, v0), (0x0EFF, 0), (0x0AD9, 0xFFFF)):
            m.setw(a, v & 0xFFFF)

    def read(self):
        m = self.m

        def s(a):
            v = m.w(a)
            return v - 0x10000 if v & 0x8000 else v
        return s(0x0EDF), s(0x0EFF), m.w(0x0DF9), s(0x0AD9) < 0

    def ram(self):
        return bytes(self.e.ram[:0x20000])


def game(rom, out):
    return Gen(rom, out) if rom.lower().endswith((".bin", ".md", ".gen")) else Snes(rom, out)


def w(g, a):
    return (g.e if isinstance(g, Gen) else g.m).w(a)


def setw(g, a, v):
    (g.e if isinstance(g, Gen) else g.m).setw(a, v)


def slowing(g, case_runs=12):
    spots = [(x, y) for x in (-60, 0, 60) for y in (-150, -50, 50, 150)]
    lost, kept = [], 0
    for k in range(60):
        g.place(*spots[k % len(spots)], g.V + 37 * k)      # speeds not all multiples of a power of two
        sp = []
        for _ in range(30):
            g.step(1)
            sp.append(g.read())
        vx = [s[0] for s in sp]
        if all(s[1] == 0 and s[2] == 0 and s[3] for s in sp) and all(0 < b <= a for a, b in zip(vx, vx[1:])) and vx[0] > 0:
            lost.append(1 - (vx[-1] / vx[0]) ** (1 / (len(vx) - 1)))
            kept += 1
        if kept >= case_runs:
            break
    return sum(lost) / len(lost) if lost else None, kept


def friction(rom, out):
    g = game(rom, out)
    st = g.e.serialize()
    base = None
    for gsp, gone in CASES:
        g.e.unserialize(st)
        total = w(g, g.TOTAL)
        setw(g, g.GSP, gsp)
        setw(g, g.CLOCK, max(1, round(total * (1 - gone))))
        s, n = slowing(g)
        if base is None:
            base = s
        rel = f"{s / base:.3f}" if s and base else "-"
        print(f"period {gsp + 1 if gsp < 3 else 'OT'}, {gone:.0%} gone (clock {w(g, g.CLOCK)} of {total}): {n} clean runs, "
              f"slowing a frame {s:.6f}; against the start {rel}", flush=True)


def same(rom, out, frames):
    g = game(rom, out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "hashes.txt").open("w") as fh:
        for k in range(frames // 30):
            g.step(30)
            fh.write(f"{(k + 1) * 30} {w(g, g.GSP)} {w(g, g.CLOCK)} {w(g, g.TOTAL)} {hashlib.md5(g.ram()).hexdigest()}\n")


def compare(a, b):
    A = (Path(a) / "hashes.txt").read_text().split("\n")
    B = (Path(b) / "hashes.txt").read_text().split("\n")
    for x, y in zip(A, B):
        if x != y:
            f, gsp, clock, total, _ = x.split()
            print(f"first difference at frame {f}: period {int(gsp) + 1}, clock {clock} of {total} "
                  f"({1 - int(clock) / int(total):.1%} of the period gone)")
            return
    print(f"the same for all {len(A) - 1} samples")


if __name__ == "__main__":
    lowload.gentle()
    if sys.argv[1] == "compare":
        compare(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "friction":
        friction(sys.argv[2], Path(sys.argv[3]))
    else:
        same(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]))
