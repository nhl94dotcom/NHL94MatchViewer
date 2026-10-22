"""doshot's launch, ported exactly (Genesis input94.asm doshot, .notperf, .perf; video94 randomd0, Sroot), with the 68000's
integer rules: muls.w / mulu.w on the low words, divs.w / divu.w leaving the destination unchanged on overflow.

launch(inputs, draws) -> (vx, vy, vz) for given random draws; outcomes(inputs) -> the full list of (probability,
(perfect, sx, sy, sz)) the shot can take; rng helpers replay the game's generator from a seed."""
from fractions import Fraction

SHOTSETS = [(0, 0xC), (0x10, 0xC), (0x10, 6), (0x10, 0), (0, 0), (-0x10, 0), (-0x10, 6), (-0x10, 0xC), (0, 6)]


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def s32(v):
    v &= 0xFFFFFFFF
    return v - 0x100000000 if v & 0x80000000 else v


def muls_w(a, b):
    return s16(a) * s16(b)


def mulu_w(a, b):
    return (a & 0xFFFF) * (b & 0xFFFF)


def divs_w(dst32, src):
    """68000 divs.w: dst (32 bits) / src (16 bits signed); quotient in the low word, remainder in the high word; on
    overflow the destination is unchanged."""
    d, s = s32(dst32), s16(src)
    q = abs(d) // abs(s)
    if (d < 0) != (s < 0):
        q = -q
    r = d - q * s
    if q < -32768 or q > 32767:
        return dst32 & 0xFFFFFFFF
    return ((r & 0xFFFF) << 16) | (q & 0xFFFF)


def divu_w(dst32, src):
    d, s = dst32 & 0xFFFFFFFF, src & 0xFFFF
    q, r = d // s, d % s
    if q > 0xFFFF:
        return d
    return (r << 16) | q


def sroot(v):
    """Sroot: integer square root as the game takes it (floor). Checked against the game in tests."""
    import math
    return math.isqrt(v)


# --- the random generator (randomd0)
M = 0xBB40E62D


def lcg(seed):
    return (seed * M + 1) & 0xFFFFFFFF


def draw(seed, rng):
    """(new seed, value) for randomd0(range)."""
    s = lcg(seed)
    v = ((s >> 8) & 0xFFFF) * (rng & 0xFFFF) >> 16
    return s, v


def launch(inp, perfect, sx=0, sy=0, sz=0):
    """inp: dict px, py (puck at doshot), top (shooting at the top net), dir (passdir 0-8), pout (passspeed after
    the power scaling), sha (working Shot Accuracy), vz0 (puckvz before the shot, kept when the height offset is 0).
    perfect: no scatter; else sx, sy, sz the scatter draws already centred (randomd0s results and the z draw)."""
    gy = 0x108 if inp["top"] else -0x108
    ox, oz = SHOTSETS[inp["dir"]]
    dx = s16(ox - inp["px"])
    dy = s16(gy - inp["py"])
    z = oz
    d3 = sroot(dx * dx + dy * dy) or 1
    if not perfect:
        dx = s16(dx + sx)
        dy = s16(dy + sy)
        z = s16(z + sz)
    pout = inp["pout"]
    d2 = muls_w(pout, 0x44)
    d2 = muls_w(d2, dx)
    vx = s16(divs_w(d2, d3))
    d2 = muls_w(pout, 0x44)
    d2 = muls_w(d2, dy)
    vy = s16(divs_w(d2, d3))
    neg = vy < 0
    if inp["top"] and neg:
        vy = 0x3810
    elif not inp["top"] and not neg:
        vy = s16(0xC7F0)
    if z & 0xFFFF == 0:
        return vx, vy, inp.get("vz0", 0)
    d1 = mulu_w(z, pout)
    d1 = mulu_w(d1, 0x44)
    d1 = divu_w(d1, d3) & 0xFFFF
    t = mulu_w(d3, 0xB33)
    t = divu_w(t, pout) & 0xFFFF
    t = (t + d1) & 0xFFFF
    if t > 0x1800:
        t = 0x1800
    vz = s16(t)
    if topshelf(inp):
        vz = puckvzadj(inp["py"], vy, vz)
    return vx, vy, vz


PAD_STACKS = (0x250, 0x2A2)


def topshelf(inp):
    """prepshot's in-close top-shelf flag: the opposing goalie in a pad stack (or none on the ice, not handled here),
    a high aim (passdir 0, 1 or 7) and the puck 216+ toward the goal; never for one-timers."""
    py = inp["py"] if inp["top"] else -inp["py"]
    return inp.get("gspa") in PAD_STACKS and inp["dir"] in (0, 1, 7) and s16(py) >= 0xD8


def puckvzadj(py, vy, vz):
    """onetimer94 puckvzadj: the height speed from the frames to the goal line (NTSC)."""
    d = abs(s16(py))
    d = abs(d - 0x108)
    if vy & 0xFFFF == 0:
        return vz
    v = abs(s16(vy))
    q = divu_w(d << 16, v) & 0xFFFF
    f = divu_w(q, 0x11) & 0xFFFF
    if f == 0:
        f = 1
    d1 = divu_w(0xA0000, (f * 0x11) & 0xFFFF)
    d2 = 0x33 * f
    if d2 >= 0x7FFF:
        d2 = 0x7FFF
    lo = ((d1 & 0xFFFF) + d2) & 0xFFFF
    if lo & 0x8000:
        lo = 0x7FFF
    return s16(lo)


def scatter_ranges(inp):
    """The scatter's ranges: adj (x: randomd0s(adj) = -adj .. adj-1), yadj (y: -yadj .. yadj-1), zr (z: 0 .. zr-1),
    and d3, from .notperf."""
    gy = 0x108 if inp["top"] else -0x108
    ox, _ = SHOTSETS[inp["dir"]]
    dx = s16(ox - inp["px"])
    dy = s16(gy - inp["py"])
    d3 = sroot(dx * dx + dy * dy) or 1
    lo = ((inp["pout"] >> 4) & 0xFF) - ((inp["sha"] >> 1) & 0xFF)
    lo = (lo + 0x10) & 0xFF
    d0 = ((inp["pout"] >> 4) & 0xFF00) | lo
    adj = (mulu_w(d0, d3) & 0xFFFF) >> 6            # mulu.w then lsr.w #6 on the low word
    if d3 <= 0xFA:
        adj >>= 1
    if adj >= 0x88:
        adj = 0x88
    ycap = min(adj, 0x3C)
    yadj = ycap >> 1 if dy < 0 else ycap
    return adj, yadj, ycap >> 1, d3


def perfect_chance(inp, within=True):
    """(sha + 1) / (sha + 16) within 200 of the aim point, else 0 (highlight / pulled goalie / shootout not
    handled here)."""
    _, _, _, d3 = scatter_ranges(inp)
    if d3 > 0xC8:
        return Fraction(0)
    n = 0x10 + inp["sha"]
    return Fraction(n - 15, n)


def replay(inp, seed):
    """The launch the game makes from the seed at doshot's start (no other random call inside doshot before the
    perfect roll: shotdiradj and makepde use none)."""
    adj, yadj, zr, d3 = scatter_ranges(inp)
    if d3 <= 0xC8:
        seed, v = draw(seed, 0x10 + inp["sha"])
        if v > 0xE:
            return launch(inp, True), seed
    seed, v = draw(seed, 2 * adj)
    sx = v - adj
    seed, v = draw(seed, 2 * yadj)
    sy = v - yadj
    seed, v = draw(seed, zr)
    return launch(inp, False, s16(sx), s16(sy), v), seed
