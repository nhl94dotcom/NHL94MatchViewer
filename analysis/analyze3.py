"""Facing timeline of whichever skater in records 0-5 the +$62 byte singles out (the controlled-player candidate)."""
import struct
import sys
from collections import Counter

cap = sys.argv[1]
t_end = float(sys.argv[2]) if len(sys.argv) > 2 else 100.0
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


marker_values = Counter()
timeline = []  # (sample, record or None, facing)
for i in range(n):
    vals = [b_byte(i, BASE + SIZE * k + 0x62) for k in range(6)]
    common, count = Counter(vals).most_common(1)[0]
    if count == 5:
        k = next(k for k, v in enumerate(vals) if v != common)
        marker_values[(common, vals[k])] += 1
        timeline.append((i, k, b_byte(i, BASE + SIZE * k + 0x55)))
    else:
        timeline.append((i, None, None))
print("marker byte (usual value, marked value) counts:", dict(marker_values.most_common(6)))

print(f"\nmarked skater's facing, runs of 0.25 s or longer, first {t_end:.0f} s:")
print("   start   dur  record facing   position      speed words")
start = 0
for j in range(1, len(timeline) + 1):
    if j == len(timeline) or timeline[j][1:] != timeline[start][1:]:
        i0, k, facing = timeline[start]
        if j - start >= 12 and ms(i0) / 1000 <= t_end:
            if k is None:
                print(f"  {ms(i0) / 1000:6.1f} {(ms(timeline[j - 1][0]) - ms(i0)) / 1000:5.1f}    (no single marked skater)")
            else:
                mid = timeline[(start + j) // 2][0]
                x = BASE + SIZE * k + 0x1C
                print(f"  {ms(i0) / 1000:6.1f} {(ms(timeline[j - 1][0]) - ms(i0)) / 1000:5.1f}    {k}      {facing}     ({b_i16(mid, x):4d},{b_i16(mid, x + 4):4d})  ({b_i16(mid, x + 12):6d},{b_i16(mid, x + 14):6d})")
        start = j
