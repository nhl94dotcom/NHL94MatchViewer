"""Longest steady turns (facing byte stepping by one, same sense) in any record, and whether that skater was marked."""
import struct
import sys

cap = sys.argv[1]
rel = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x55
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


chains = []
for k in range(12):
    vals = [b_byte(i, BASE + SIZE * k + rel) for i in range(n)]
    r = []
    start = 0
    for i in range(1, n + 1):
        if i == n or vals[i] != vals[start]:
            if i - start >= 4:
                if r and r[-1][0] == vals[start]:
                    r[-1] = (vals[start], r[-1][1], i)
                else:
                    r.append((vals[start], start, i))
            start = i
    for sense in (1, 7):
        begin = 0
        for j in range(1, len(r) + 1):
            if j == len(r) or (r[j][0] - r[j - 1][0]) % 8 != sense:
                if j - begin >= 6:
                    chains.append((j - begin, k, sense, r[begin:j]))
                begin = j
chains.sort(key=lambda c: c[3][0][1])
print(f"steady turns of 6+ steps, byte +${rel:02X} (record, sense, steps, time, marked share, travelled, values):")
for length, k, sense, seq in chains:
    s, e = seq[0][1], seq[-1][2] - 1
    marked = sum(1 for i in range(s, e + 1) if b_byte(i, BASE + SIZE * k + 0x62) & 8) / (e - s + 1)
    x = BASE + SIZE * k + 0x1C
    print(f"  record {k:2d}  {'+1' if sense == 1 else '-1'}  {length:2d} steps  {ms(s) / 1000:6.1f}-{ms(e) / 1000:6.1f}s  marked {marked:4.0%}  "
          f"({b_i16(s, x)},{b_i16(s, x + 4)})->({b_i16(e, x)},{b_i16(e, x + 4)})  {''.join(str(v) for v, _, _ in seq)}")
