"""Finds controller-state bytes in a full-RAM capture (ram.bin) by looking for bits that pulse a handful of times."""
import struct
import sys

path = sys.argv[1] + "/ram.bin"
REC = 8 + 0x10000
data = open(path, "rb").read()
n = len(data) // REC
ms = [struct.unpack_from("<q", data, i * REC)[0] for i in range(n)]

# Pass 1: how often each byte changes. Compare 256-byte chunks first; most of RAM is static.
changes = [0] * 0x10000
for i in range(1, n):
    a, b = (i - 1) * REC + 8, i * REC + 8
    for c in range(0, 0x10000, 256):
        if data[a + c:a + c + 256] != data[b + c:b + c + 256]:
            for j in range(c, c + 256):
                if data[a + j] != data[b + j]:
                    changes[j] += 1
candidates = [j for j in range(0x10000) if 8 <= changes[j] <= 400]
print(f"{n} samples over {ms[-1] / 1000:.0f} s; {len(candidates)} bytes changed 8-400 times")


def pulses(host, bit):
    """(start ms, duration ms) for each stretch where the bit is set."""
    out, start = [], None
    for i in range(n):
        on = data[i * REC + 8 + host] & bit
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append((ms[start], ms[i] - ms[start]))
            start = None
    if start is not None:
        out.append((ms[start], ms[n - 1] - ms[start]))
    return out


# Pass 2: bytes where at least three different bits were each tapped 4-8 times (a tap = set for under 0.7 s).
found = []
for host in candidates:
    per_bit = {bit: pulses(host, bit) for bit in (1, 2, 4, 8, 16, 32, 64, 128)}
    tapped = [bit for bit, p in per_bit.items() if 4 <= sum(1 for _, d in p if d < 700) <= 8 and len(p) <= 12]
    if len(tapped) >= 3:
        found.append((host, per_bit))
print(f"{len(found)} bytes have three or more tapped bits")
for host, per_bit in found[:12]:
    print(f"\n${host ^ 1:04X} ({changes[host]} changes)")
    for bit, p in sorted(per_bit.items()):
        if p:
            print(f"   bit ${bit:02X}: " + ", ".join(f"{s / 1000:.1f}s/{d}ms" for s, d in p[:14]) + (" ..." if len(p) > 14 else ""))
