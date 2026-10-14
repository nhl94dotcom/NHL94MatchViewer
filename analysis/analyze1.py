"""First pass over an NHL '94 RAM capture: clock/score timeline, pointer-like globals, and a search for the facing field."""
import math
import struct
import sys
from collections import Counter, defaultdict

cap = sys.argv[1]
FAST = 8 + 0x900 + 0x800
fast = open(cap + r"\fast.bin", "rb").read()
full = open(cap + r"\full.bin", "rb").read()
n = len(fast) // FAST


def u16(buf, off):
    return struct.unpack_from("<H", buf, off)[0]


def i16(buf, off):
    return struct.unpack_from("<h", buf, off)[0]


def sample(i):
    """Returns (ms, block at $B000, block at $C400) for fast sample i."""
    base = i * FAST
    return struct.unpack_from("<q", fast, base)[0], base + 8, base + 8 + 0x900


def b_word(i, addr, signed=True):
    off = sample(i)[1] + (addr - 0xB000)
    return i16(fast, off) if signed else u16(fast, off)


def b_byte(i, addr):
    return fast[sample(i)[1] + ((addr - 0xB000) ^ 1)]


def c_word(i, addr):
    return u16(fast, sample(i)[2] + (addr - 0xC400))


print(f"{n} fast samples")

# --- clock and stats timeline: print whenever a watched stat word changes
watch = {"p1score C6DA": 0xC6DA, "p2score CA3E": 0xCA3E, "p1shots C6CC": 0xC6CC, "p2shots CA30": 0xCA30,
         "C466": 0xC466}
prev = None
print("\nstat changes (ms, clock $C468, values):")
for i in range(n):
    cur = tuple(c_word(i, a) for a in watch.values())
    if cur != prev:
        print(f"  {sample(i)[0]:7d} ms  clock {c_word(i, 0xC468):4d}  " + "  ".join(f"{k}={v}" for k, v in zip(watch, cur)))
        prev = cur
print(f"clock: start {c_word(0, 0xC468)}, end {c_word(n - 1, 0xC468)}")

# --- words in the full snapshots that always hold a player/puck record address (or zero) and change
FULL = 8 + 0x10000
nf = len(full) // FULL
record_x = {0xB066 + 0x80 * k for k in range(16)}
print("\nwords that look like pointers into the object records (offset: distinct values, changes):")
for off in range(0, 0x10000, 2):
    vals = [u16(full, s * FULL + 8 + off) for s in range(nf)]
    distinct = set(vals)
    if len(distinct) < 2:
        continue
    for delta in range(-0x66, 0x1A, 2):  # allow the record's true base to sit before or after its X field
        shifted = {v - delta for v in distinct if v != 0}
        if shifted and shifted <= record_x:
            changes = sum(1 for a, b in zip(vals, vals[1:]) if a != b)
            print(f"  ${off:04X} (X{delta:+d}): {sorted(hex(v) for v in distinct)}  changes={changes}")
            break

# --- facing search: a small-valued byte in each record whose value predicts the direction of travel
print("\nfacing candidates (relative byte offset from record X; score 1.0 = value fully determines travel direction):")
skaters = [k for k in range(12) if k not in (5, 11)]
results = []
for rel in range(-0x26, 0x5A):
    sums = defaultdict(lambda: [0.0, 0.0, 0])
    for k in skaters:
        x_addr = 0xB066 + 0x80 * k
        for i in range(0, n, 3):
            vx, vy = b_word(i, x_addr + 12), b_word(i, x_addr + 14)
            if vx * vx + vy * vy < 3000 * 3000:
                continue
            ang = math.atan2(vy, vx)
            s = sums[b_byte(i, x_addr + rel)]
            s[0] += math.cos(ang)
            s[1] += math.sin(ang)
            s[2] += 1
    total = sum(s[2] for s in sums.values())
    if not (4 <= len(sums) <= 40) or total == 0:
        continue
    score = sum(math.hypot(s[0], s[1]) for s in sums.values()) / total
    results.append((score, rel, sums))
results.sort(key=lambda r: -r[0])
for score, rel, sums in results[:8]:
    mapping = ", ".join(f"{v}:{math.degrees(math.atan2(s[1], s[0])):.0f}deg(n={s[2]})" for v, s in sorted(sums.items()))
    print(f"  rel {rel:+4d}  score {score:.3f}  values={len(sums)}  {mapping}")
