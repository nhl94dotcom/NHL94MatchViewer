"""How often each SNES penalty roll is reached, original engine against McMarkis's SA-1 build (2026-11-08, for NOSE4Web:
the SA-1 build at 30 frames a second calls more Roughing and Interference; more contact, or a different roll?).

The rolls (NHL94SNES disassembly): checkagr (random below (20 - aggress) x 16, doubled for a player on a pad, halved
near the puck; a penalty when the result is small) from four places: checkcheck's Charging roll (a burst check that
doesn't knock the man down) and Roughing roll (one that does), holdcheck's Hooking / Holding roll, Bcheck's Tripping
roll; and checkint's own Interference roll (a skater and a goalie colliding: randoma8(20 - aggress) < 2). In a scratch
copy, each of those five `jsl` goes instead to a stub in free ROM ($9B:D000, ROM $DD000, unused in both) that calls the real
routine and adds 1 to its own word, and, after the
real routine returns, to a second word when the roll came up a penalty (checkagr's d0 = 0, Bcheck's under 5, Interference's
result under 2; the caller may still not call it: highlights, or a goalie flag), and to a third and fourth when it came up
during highlights (gmode $15D4 bit gmhl: the callers call nothing) or in the side view (sfhormode $15DA: AddPenalty2
queues nothing), so play is otherwise unchanged. The counters: work RAM $7F:FF00 on the original, BW-RAM $40:FF00 on the SA-1 build (its game
code may run on the SA-1, which can't reach work RAM). The SA-1 build is also run at 30 frames a second
(snes_60fps_cvc.make_30). Games as snes_60fps_cvc (seeded, computer against computer, 5-minute periods), with the
penalties called by number.

python snes_penalty_rolls.py ROM GAMES OUT.jsonl"""
import json
import re
import sys
from pathlib import Path

import lowload
import snes_60fps_cvc as C

ROLLS = ["charging", "roughing", "hook_hold", "tripping", "interference"]
STUB_AT = 0xDD000


def snes_addr(o):
    return ((0x80 + o // 0x8000) << 16) | (0x8000 + o % 0x8000)


def patch(rom, out):
    f = bytearray(Path(rom).read_bytes())
    h = len(f) % 0x8000                                   # a copier header
    r = f[h:]
    sa1 = r[0x7FD5] == 0x23
    agr = r.find(bytes.fromhex("a9140038fd43140a0a0a0a"))
    if agr < 0:
        agr = r.find(bytes.fromhex("a9140038fd43740a0a0a0a"))
    a = snes_addr(agr)
    sites = [m.start() for m in re.finditer(re.escape(bytes([0x22, a & 0xFF, (a >> 8) & 0xFF, a >> 16])), r)]
    tails = [r[s + 4:s + 9].hex() for s in sites]
    assert tails == ["a5a5c90100", "a5a5c90100", "a5a5c90100", "a5a5c90500"], tails      # charging, roughing, hold, trip
    assert r[sites[2] + 11:sites[2] + 14].hex() == "a92800"
    ci = [m.start() + 7 for m in re.finditer(re.escape(bytes.fromhex("a9140038fd")), r) if r[m.start() + 7] == 0x22]
    assert len(ci) == 1
    sites.append(ci[0])
    assert r[STUB_AT:STUB_AT + 0x200] == b"\xff" * 0x200
    counter = 0x40FF00 if sa1 else 0x7FFF00
    for k, s in enumerate(sites):
        target = int.from_bytes(r[s + 1:s + 4], "little")
        reach, zero = (counter + 2 * k).to_bytes(3, "little"), (counter + 0x20 + 2 * k).to_bytes(3, "little")
        inter = k == len(sites) - 1
        test = bytes([0xA3, 0x01, 0xC9, 0x02, 0x00]) if inter else bytes([0xA5, 0xA5, 0xC9, 5 if k == 3 else 1, 0x00])
        hl = (counter + 0x40 + 2 * k).to_bytes(3, "little")
        hor = (counter + 0x60 + 2 * k).to_bytes(3, "little")
        low = 0x406000 if sa1 else 0x7E0000                                  # where the build keeps low RAM
        gmode, sfhormode = (low + 0x15D4).to_bytes(3, "little"), (low + 0x15DA).to_bytes(3, "little")
        inc = lambda c: bytes([0xAF]) + c + bytes([0x1A, 0x8F]) + c        # 9 bytes
        tail = (inc(zero)
                + bytes([0xAF]) + gmode + bytes([0x29, 0x10, 0x00, 0xF0, 0x09]) + inc(hl)      # highlights (gmhl)
                + bytes([0xAF]) + sfhormode + bytes([0xF0, 0x09]) + inc(hor))                  # the side view
        stub = (bytes([0x22]) + target.to_bytes(3, "little") + bytes([0x08, 0xC2, 0x20, 0x48])
                + inc(reach) + test + bytes([0xB0, len(tail)]) + tail + bytes([0x68, 0x28, 0x6B]))
        assert len(stub) <= 96
        at = STUB_AT + 96 * k
        r[at:at + len(stub)] = stub
        r[s + 1:s + 4] = snes_addr(at).to_bytes(3, "little")
    f[h:] = r
    Path(out).write_bytes(f)
    if sa1:
        C.make_30(out, out)
    return sa1, counter


def main():
    rom, games, out = sys.argv[1], int(sys.argv[2]), Path(sys.argv[3])
    lowload.gentle()
    scratch = out.with_suffix(".rolls" + Path(rom).suffix)
    sa1, counter = patch(rom, scratch)

    def counters(e, m):
        if sa1:
            buf, o = m.bw, counter & 0xFFFF
        else:
            buf, o = e.ram, 0x10000 + (counter & 0xFFFF)
        word = lambda k: buf[o + 2 * k] | buf[o + 2 * k + 1] << 8
        spare = [word(j + q) for j in (0, 16, 32, 48) for q in range(len(ROLLS), 16)]
        return dict(rolls=dict(zip(ROLLS, [word(k) for k in range(len(ROLLS))])),
                    hits=dict(zip(ROLLS, [word(16 + k) for k in range(len(ROLLS))])),
                    hits_highlight=dict(zip(ROLLS, [word(32 + k) for k in range(len(ROLLS))])),
                    hits_side_view=dict(zip(ROLLS, [word(48 + k) for k in range(len(ROLLS))])), spare_nonzero=sum(1 for v in spare if v))

    done = {json.loads(line)["seed"] for line in out.read_text().splitlines()} if out.exists() else set()
    for n in range(games):
        if n in done:
            continue
        r = C.game(str(scratch), n, extra=counters)
        r["seed"] = n
        with out.open("a") as fh:
            fh.write(json.dumps(r) + "\n")
        print(json.dumps(r), flush=True)


if __name__ == "__main__":
    main()
