"""Looks for a puck-possession marker. Ground truth: the puck sits on a player and shares that player's speed words."""
import struct
import sys
from collections import Counter

cap = sys.argv[1]
S = 8 + 0x900 + 0x800
fast = open(cap + "/fast.bin", "rb").read()
n = len(fast) // S
BASE, SIZE, PUCK = 0xB04A, 0x80, 14


def byte(i, addr):
    return fast[i * S + 8 + ((addr - 0xB000) ^ 1)]


def i16(i, addr):
    return struct.unpack_from("<h", fast, i * S + 8 + addr - 0xB000)[0]


def u16(i, addr):
    return struct.unpack_from("<H", fast, i * S + 8 + addr - 0xB000)[0]


def c16(i, addr):
    return struct.unpack_from("<H", fast, i * S + 8 + 0x900 + addr - 0xC400)[0]


def carrier(i):
    p = BASE + SIZE * PUCK
    px, py, pvx, pvy = i16(i, p + 0x1C), i16(i, p + 0x20), i16(i, p + 0x28), i16(i, p + 0x2A)
    hits = []
    for k in range(12):
        r = BASE + SIZE * k
        if (i16(i, r + 0x28), i16(i, r + 0x2A)) == (pvx, pvy) and abs(i16(i, r + 0x1C) - px) < 20 and abs(i16(i, r + 0x20) - py) < 20:
            hits.append(k)
    return hits[0] if len(hits) == 1 else None


idx = list(range(0, n, 2))
truth = {i: carrier(i) for i in idx}
held = [i for i in idx if truth[i] is not None]
loose = [i for i in idx if truth[i] is None]
print(f"{len(idx)} samples: puck on a player in {len(held)}, loose or ambiguous in {len(loose)}; by record {dict(sorted(Counter(truth[i] for i in held).items()))}")

print("\npuck-record words that track the carrier (offset: share of 'held' samples where the word names the carrier, encoding):")
for off in range(0, SIZE, 2):
    for label, decode in (("pointer", lambda v: (v - BASE) // SIZE if v >= BASE and (v - BASE) % SIZE == 0 else None), ("index", lambda v: v if v < 12 else None)):
        ok = sum(1 for i in held if decode(u16(i, BASE + SIZE * PUCK + off)) == truth[i])
        if ok > 0.6 * len(held):
            when_loose = Counter(u16(i, BASE + SIZE * PUCK + off) for i in loose).most_common(3)
            print(f"  puck +${off:02X} as {label}: {ok / len(held):.0%}; when loose: {[(hex(v), c) for v, c in when_loose]}")

print("\nglobal words in $C400-$CBFF that track the carrier:")
for addr in range(0xC400, 0xCC00, 2):
    for label, decode in (("pointer", lambda v: (v - BASE) // SIZE if v >= BASE and (v - BASE) % SIZE == 0 else None), ("index", lambda v: v if v < 12 else None)):
        ok = sum(1 for i in held if decode(c16(i, addr)) == truth[i])
        if ok > 0.6 * len(held):
            when_loose = Counter(c16(i, addr) for i in loose).most_common(3)
            print(f"  ${addr:04X} as {label}: {ok / len(held):.0%}; when loose: {[(hex(v), c) for v, c in when_loose]}")

print("\nplayer-record bits set on the carrier and clear on everyone else (offset, bit: set on carrier / set on non-carriers):")
rows = []
for rel in range(SIZE):
    on_c, on_o, tot_c, tot_o = [0] * 8, [0] * 8, 0, 0
    for i in idx[::2]:
        t = truth[i]
        for k in range(12):
            v = byte(i, BASE + SIZE * k + rel)
            if k == t:
                tot_c += 1
                for b in range(8):
                    on_c[b] += (v >> b) & 1
            else:
                tot_o += 1
                for b in range(8):
                    on_o[b] += (v >> b) & 1
    for b in range(8):
        pc, po = on_c[b] / max(1, tot_c), on_o[b] / max(1, tot_o)
        rows.append((pc - po, rel, 1 << b, pc, po))
for diff, rel, bit, pc, po in sorted(rows, reverse=True)[:8]:
    print(f"  +${rel:02X} bit ${bit:02X}: {pc:.0%} / {po:.1%}")
