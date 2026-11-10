"""Energy and skating speed on the Genesis (2026-11-10, for NOSE4Web's "energy from hits only" plan and its drain
option). From the code (logic94 playeracc): the speed level n = floor(floor(legspd / 2) x energy / 4096) (an odd
legspd gets half a step more while the level is under 15), andi #$3F on 4n (so n = 16 wraps to 0), and the top speed
is (n + 20) x 275 (the square root of MaxSpeed's entry); `.sube` takes 33 off 1 call in 128 (the beam counter) and,
while the energy is still at least $C00, gives back endurance / 2, with no cap at $1000.

- `speed ROM OUT`: the pad skater (home record 2) skating straight up the ice from a standstill for 150 frames,
  everyone else parked, the puck away from him, line changes On (OptLine $D058 = 0) and sflags7 ($C2FC) bit 4 clear
  (Auto sets it: every energy reads as full), his energy held at $1000, $AAB (2/3), $555 (1/3) and 0 each frame and
  his working speed (+$69) set to the average skater's and to 30: the highest speed reached (|velocity|, +$28 / +$2A)
  against the code's figure.
- `drain ROM OUT`: the same skater, speed 30 and endurance (+$72) 30, energy $1000 at the start, skating up and down
  the ice for 7200 frames (2 minutes, real; the clock held), on the ROM as given: his energy and top speed each
  second (real). Run on the test ROM and on a copy with `.sube`'s 33 made 0 ($10D42 = 0, the drain-0 case).

python gen_energy_speed_check.py speed ROM OUT | drain ROM OUT | make-drain0 OUT   (a copy of the test ROM)"""
import json
import math
import sys
from pathlib import Path

import harness as H
import lowload
from paths import ROM

OPTLINE, SFLAGS7, CLOCK, TEAM = 0xD058, 0xC2FC, 0xC468, 0xC6CE
ME = 2


def energy_addr(e):
    return TEAM + 0x32 + 2 * e.b(H.rec(ME) + 0x66)


def expected(legspd, en):
    n = ((legspd >> 1) * en) // 4096
    idx = (4 * n) & 0x3F
    top = (idx // 4 + 20) * 275
    if legspd & 1 and idx < 0x3C:
        top = ((idx // 4 + 20) * 275 + (idx // 4 + 21) * 275) / 2     # about: halfway between the squared steps
    return n, top


def prep(h, legspd, endurance=None):
    e = h.e
    e.unserialize(h.base)
    e.setw(OPTLINE, 0)
    e.setw(SFLAGS7, e.w(SFLAGS7) & ~0x1000)
    e.setb(H.rec(ME) + 0x69, legspd)
    if endurance is not None:
        e.setb(H.rec(ME) + 0x72, endurance)


def hold_still(h):
    e = h.e
    h.park(keep_shooter=True)
    e.setb(H.PUCK + 0x60, 0xFF)
    e.setw(H.PUCK, 100)
    e.setw(H.PUCK + 0x14, 0)
    e.setw(CLOCK, 600)


def speed(rom, out):
    h = H.Harness(rom=rom)
    e = h.e
    e.unserialize(h.base)
    sk = sorted(e.b(H.rec(k) + 0x69) for k in range(12) if k not in (5, 11))
    avg = sk[len(sk) // 2] & ~1                              # the median skater's, made even
    res = {"working speeds of the skaters in the state": sk, "average used": avg}
    for legspd in (avg, 30):
        for en in (0x1000, 0xAAB, 0x555, 0):
            prep(h, legspd)
            e.setw(H.rec(ME), 0)
            e.setw(H.rec(ME) + 0x14, -230 * (1 if h.top else -1))
            for off in (0x28, 0x2A, 0x2C):
                e.setw(H.rec(ME) + off, 0)
            top = 0
            for f in range(150):
                hold_still(h)
                e.setw(energy_addr(e), en)
                e.run(1, hold=["UP" if h.top else "DOWN"])
                vx, vy = e.sw(H.rec(ME) + 0x28), e.sw(H.rec(ME) + 0x2A)
                top = max(top, math.hypot(vx, vy))
            n, exp = expected(legspd, en)
            res[f"speed {legspd}, energy {en:#x}"] = {"top reached": round(top), "code: level": n, "code: top": exp}
        lowload.breathe()
    (out / "speed.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


def drain(rom, out, label):
    h = H.Harness(rom=rom)
    e = h.e
    prep(h, 30, 30)
    e.setw(energy_addr(e), 0x1000)
    way, rows, top = "UP", [], 0
    for f in range(7200):
        hold_still(h)
        y = e.sw(H.rec(ME) + 0x14)
        if y > 200:
            way = "DOWN"
        elif y < -200:
            way = "UP"
        e.run(1, hold=[way])
        top = max(top, math.hypot(e.sw(H.rec(ME) + 0x28), e.sw(H.rec(ME) + 0x2A)))
        if f % 60 == 59:
            en = e.w(energy_addr(e))
            rows.append({"s": (f + 1) // 60, "energy": en, "hex": hex(en), "top speed this second": round(top),
                         "code: level, top": expected(30, en)})
            top = 0
        if f % 1800 == 1799:
            lowload.breathe()
    (out / f"drain_{label}.json").write_text(json.dumps(rows, indent=1))
    for r in rows[::10] + [rows[-1]]:
        print(r)


def main():
    what = sys.argv[1]
    if what == "make-drain0":
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        d = bytearray(Path(ROM).read_bytes())
        assert d[0x10D40:0x10D44] == bytes.fromhex("04400021")
        d[0x10D42:0x10D44] = b"\x00\x00"
        (out / "drain0.bin").write_bytes(bytes(d))
        print(out / "drain0.bin")
        return
    rom, out = sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    if what == "speed":
        speed(rom, out)
    else:
        drain(rom, out, Path(rom).stem)


if __name__ == "__main__":
    main()
