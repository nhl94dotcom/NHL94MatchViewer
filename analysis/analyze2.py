"""Second pass: facing byte timelines, a controlled-player marker, team stat words, and the spare record slots."""
import struct
import sys
from collections import Counter

cap = sys.argv[1]
FAST = 8 + 0x900 + 0x800
fast = open(cap + r"\fast.bin", "rb").read()
n = len(fast) // FAST
BASE, SIZE, FACING = 0xB04A, 0x80, 0x55  # record 0 base, record size, facing byte offset within a record


def ms(i):
    return struct.unpack_from("<q", fast, i * FAST)[0]


def b_byte(i, addr):
    return fast[i * FAST + 8 + ((addr - 0xB000) ^ 1)]


def b_i16(i, addr):
    return struct.unpack_from("<h", fast, i * FAST + 8 + (addr - 0xB000))[0]


def c_u16(i, addr):
    return struct.unpack_from("<H", fast, i * FAST + 8 + 0x900 + (addr - 0xC400))[0]


def runs(values, min_len):
    """Run-length encodes values, dropping runs shorter than min_len samples and merging neighbours."""
    out = []
    start = 0
    for i in range(1, len(values) + 1):
        if i == len(values) or values[i] != values[start]:
            if i - start >= min_len:
                if out and out[-1][0] == values[start]:
                    out[-1] = (values[start], out[-1][1], i)
                else:
                    out.append((values[start], start, i))
            start = i
    return out


# --- facing: longest stretch per record where the byte steps by +1 or -1 (mod 8) each time, i.e. a steady turn
print("steadiest turns per record (facing byte at record+$55), runs of at least 0.4 s:")
best = []
for k in range(12):
    r = runs([b_byte(i, BASE + SIZE * k + FACING) for i in range(n)], 20)
    for direction in (1, -1):
        length, start = 1, 0
        for j in range(1, len(r) + 1):
            if j < len(r) and (r[j][0] - r[j - 1][0]) % 8 == direction % 8:
                length += 1
            else:
                best.append((length, k, direction, r[start:j]))
                length, start = 1, j
best.sort(key=lambda b: -b[0])
for length, k, direction, seq in best[:4]:
    print(f"  record {k:2d}  {'+1' if direction == 1 else '-1'} per step, {length} steps, {ms(seq[0][1]) / 1000:.1f}s-{ms(seq[-1][2] - 1) / 1000:.1f}s")
    for value, s, e in seq:
        mid = (s + e) // 2
        x = BASE + SIZE * k + 0x1C
        print(f"      facing {value}  {ms(s) / 1000:6.1f}s for {(ms(e - 1) - ms(s)) / 1000:4.1f}s   speed words ({b_i16(mid, x + 12):6d},{b_i16(mid, x + 14):6d})")

# --- a byte that singles out one record among records 0-5 (or 6-11) most of the time: the controlled-player marker
print("\nbytes that single out exactly one skater per team (offset in record: share of samples, how often the chosen one changes):")
for team, ks in (("records 0-5", range(0, 6)), ("records 6-11", range(6, 12))):
    found = []
    for rel in range(SIZE):
        chosen = []
        for i in range(0, n, 2):
            vals = [b_byte(i, BASE + SIZE * k + rel) for k in ks]
            common, count = Counter(vals).most_common(1)[0]
            if count == 5:
                chosen.append(next(k for k, v in zip(ks, vals) if v != common))
        share = len(chosen) / (n / 2)
        switches = sum(1 for a, b in zip(chosen, chosen[1:]) if a != b)
        if share > 0.7:
            found.append((share, rel, switches, Counter(chosen)))
    for share, rel, switches, who in sorted(found, reverse=True)[:6]:
        print(f"  {team}  +${rel:02X}  {share:.0%}  switches={switches}  who={dict(sorted(who.items()))}")

# --- small-valued words in $C400-$CBFF that changed a handful of times (stats, selected-player index, possession)
print("\nwords in $C400-$CBFF that changed 1-40 times and stayed below 200 (address: first -> last, changes, distinct):")
for addr in range(0xC400, 0xCC00, 2):
    vals = [c_u16(i, addr) for i in range(0, n, 2)]
    changes = sum(1 for a, b in zip(vals, vals[1:]) if a != b)
    if 1 <= changes <= 40 and max(vals) < 200:
        print(f"  ${addr:04X}: {vals[0]:3d} -> {vals[-1]:3d}  changes={changes:2d}  distinct={sorted(set(vals))[:14]}")

# --- spare slots: do records 12, 13 and 15 ever change?
print("\nspare record slots:")
for k in (12, 13, 15):
    x = BASE + SIZE * k + 0x1C
    pts = {(b_i16(i, x), b_i16(i, x + 4)) for i in range(0, n, 10)}
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    print(f"  record {k} (${BASE + SIZE * k:04X}): {len(pts)} distinct positions, x {min(xs)}..{max(xs)}, y {min(ys)}..{max(ys)}")
