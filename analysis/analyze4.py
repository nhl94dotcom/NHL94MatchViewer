"""Bit-level search for a one-skater-per-team marker, then the facing timeline of the skater a chosen marker selects."""
import struct
import sys

cap = sys.argv[1]
FAST = 8 + 0x900 + 0x800
fast = open(cap + r"\fast.bin", "rb").read()
n = len(fast) // FAST
BASE, SIZE = 0xB04A, 0x80


def ms(i):
    return struct.unpack_from("<q", fast, i * FAST)[0]


def b_byte(i, addr):
    return fast[i * FAST + 8 + ((addr - 0xB000) ^ 1)]


def b_i16(i, addr):
    return struct.unpack_from("<h", fast, i * FAST + 8 + (addr - 0xB000))[0]


def selected(i, ks, rel, bit):
    hit = [k for k in ks if b_byte(i, BASE + SIZE * k + rel) & bit]
    return hit[0] if len(hit) == 1 else None


if len(sys.argv) == 2:
    print("bits set on exactly one of a team's six records (team, offset, bit: share of samples, switches, per-record counts):")
    for name, ks in (("0-5", range(0, 6)), ("6-11", range(6, 12))):
        rows = []
        for rel in range(SIZE):
            for bit in (1, 2, 4, 8, 16, 32, 64, 128):
                seq = [selected(i, ks, rel, bit) for i in range(0, n, 4)]
                picks = [s for s in seq if s is not None]
                if len(picks) < 0.5 * len(seq) or len(set(picks)) < 3:
                    continue
                switches = sum(1 for a, b in zip(picks, picks[1:]) if a != b)
                rows.append((len(picks) / len(seq), rel, bit, switches, {k: picks.count(k) for k in ks}))
        for share, rel, bit, switches, who in sorted(rows, reverse=True)[:8]:
            print(f"  {name:5s} +${rel:02X} bit ${bit:02X}: {share:.0%}  switches={switches}  {who}")
else:
    lo, rel, bit, t0, t1 = int(sys.argv[2]), int(sys.argv[3], 16), int(sys.argv[4], 16), float(sys.argv[5]), float(sys.argv[6])
    ks = range(lo, lo + 6)
    line = [(i, selected(i, ks, rel, bit)) for i in range(n)]
    line = [(i, k, None if k is None else b_byte(i, BASE + SIZE * k + 0x55)) for i, k in line]
    print("   start   dur  record facing   position      speed words")
    start = 0
    for j in range(1, len(line) + 1):
        if j == len(line) or line[j][1:] != line[start][1:]:
            i0, k, facing = line[start]
            if j - start >= 12 and t0 <= ms(i0) / 1000 <= t1 and k is not None:
                mid = line[(start + j) // 2][0]
                x = BASE + SIZE * k + 0x1C
                print(f"  {ms(i0) / 1000:6.1f} {(ms(line[j - 1][0]) - ms(i0)) / 1000:5.1f}    {k:2d}     {facing}     ({b_i16(mid, x):4d},{b_i16(mid, x + 4):4d})  ({b_i16(mid, x + 12):6d},{b_i16(mid, x + 14):6d})")
            start = j
