"""A small Standard MIDI File reader (no dependencies), for checking NOSE4Web's MIDI exports and imports.

read(path) -> dict(division, tempos [(tick, us per beat)], notes [(start tick, length ticks, channel, note, velocity,
track)], programs [(tick, channel, program, track)], end tick). seconds(mid, tick) converts with the tempo map.

python midi_notes.py FILE   prints each channel's notes, range, programs and note lengths."""
import struct
import sys
from collections import Counter


def _var(b, i):
    v = 0
    while True:
        c = b[i]
        i += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80:
            return v, i


def read(path):
    b = open(path, "rb").read()
    assert b[:4] == b"MThd"
    hl = struct.unpack(">I", b[4:8])[0]
    fmt, ntr, div = struct.unpack(">HHH", b[8:14])
    i = 8 + hl
    notes, programs, tempos, end = [], [], [], 0
    for tr in range(ntr):
        assert b[i:i + 4] == b"MTrk", b[i:i + 4]
        ln = struct.unpack(">I", b[i + 4:i + 8])[0]
        j, stop, t, run, on = i + 8, i + 8 + ln, 0, None, {}
        while j < stop:
            d, j = _var(b, j)
            t += d
            st = b[j]
            if st == 0xFF:
                typ, ln2 = b[j + 1], None
                ln2, k = _var(b, j + 2)
                if typ == 0x51:
                    tempos.append((t, int.from_bytes(b[k:k + 3], "big")))
                j = k + ln2
                continue
            if st in (0xF0, 0xF7):
                ln2, k = _var(b, j + 1)
                j = k + ln2
                continue
            if st & 0x80:
                run = st
                j += 1
            st = run
            cmd, ch = st & 0xF0, st & 15
            n = 1 if cmd in (0xC0, 0xD0) else 2
            data = b[j:j + n]
            j += n
            if cmd == 0x90 and data[1]:
                on.setdefault((ch, data[0]), []).append((t, data[1]))
            elif cmd in (0x80, 0x90):
                lst = on.get((ch, data[0]))
                if lst:
                    s, v = lst.pop(0)
                    notes.append((s, t - s, ch, data[0], v, tr))
            elif cmd == 0xC0:
                programs.append((t, ch, data[0], tr))
        for (ch, n), lst in on.items():
            for s, v in lst:
                notes.append((s, t - s, ch, n, v, tr))
        end = max(end, t)
        i = stop
    return dict(division=div, format=fmt, tempos=sorted(tempos) or [(0, 500000)], notes=sorted(notes),
                programs=programs, end=end)


def seconds(mid, tick):
    s, last_t, us = 0.0, 0, 500000
    for t, u in mid["tempos"]:
        if t >= tick:
            break
        s += (t - last_t) * us / mid["division"] / 1e6
        last_t, us = t, u
    return s + (tick - last_t) * us / mid["division"] / 1e6


def main():
    m = read(sys.argv[1])
    print("division", m["division"], "tempos", [(t, round(60e6 / u, 2)) for t, u in m["tempos"][:4]], "end",
          m["end"], f"({seconds(m, m['end']):.2f} s)")
    print("programs", sorted(set((ch, p) for _, ch, p, _ in m["programs"])))
    for ch in sorted(set(n[2] for n in m["notes"])):
        ns = [n for n in m["notes"] if n[2] == ch]
        print(f"channel {ch}: {len(ns)} notes, range {min(n[3] for n in ns)}-{max(n[3] for n in ns)}, lengths (ticks)"
              f" {Counter(n[1] for n in ns).most_common(4)}, velocities {Counter(n[4] for n in ns).most_common(3)}")


if __name__ == "__main__":
    main()
