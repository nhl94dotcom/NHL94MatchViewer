"""NOSE4Web's crowd-bonus option (bug 21), played in the game (Genesis, 2026-11-08, the user approved running the
patched ROMs). SetSflags8Bit1 ($FEF66) always sets sflags8 bit 1, which every crowd-bonus test reads before the real
flag (sflags7 bit 6, the meter past its record), so the +2 Agility / +2 Speed is always on. The option nops the
branch, so the bonus follows the meter.

The home centre on pad 1, standing at centre ice with everyone else parked, skates right for 90 frames (nothing else
pressed) with the meter held loud (CurCrowdMeter $C30E above CrowdRecord $C310) or quiet (below), each frame: his top
speed, and how often sflags8 bit 1 and sflags7 bit 6 were on.

python crowd_test.py ROM [ROM ...]"""
import math
import sys

from blind_ring_test import park, SHOOTER
from bot import rec, PUCKC
from bot_scenario import live_state
from emu import Emu

CUR, RECORD, SFLAGS7, SFLAGS8 = 0xC30E, 0xC310, 0xC2FC, 0xC2FE


def run(e, base, loud):
    e.unserialize(base)
    e.setw(0xC468, 250)
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(SHOOTER) + 0x62, e.b(rec(SHOOTER) + 0x62) | 8)
    e.setw(0xC320, SHOOTER)
    e.setw(rec(SHOOTER), 0)
    e.setw(rec(SHOOTER) + 0x14, 0)
    for off in (0x28, 0x2A, 0x2C):
        e.setw(rec(SHOOTER) + off, 0)
    e.setw(PUCKC, 0xFF00 | 11)
    e.setw(rec(14), (-100) & 0xFFFF)
    e.setw(rec(14) + 0x14, 200)
    top, b8, b7 = 0, 0, 0
    for f in range(90):
        e.setw(CUR, 0x7FFF if loud else 0)
        e.setw(RECORD, 0 if loud else 0x7FFF)
        park(e)
        e.run(1, hold=["RIGHT"])
        top = max(top, math.hypot(e.sw(rec(SHOOTER) + 0x28), e.sw(rec(SHOOTER) + 0x2A)))
        b8 += bool(e.w(SFLAGS8) & 0x0200)
        b7 += bool(e.w(SFLAGS7) & 0x4000)
    return round(top), b8, b7


def main():
    for rom in sys.argv[1:]:
        e = Emu(rom)
        base = live_state(e, 0)
        for loud in (True, False):
            top, b8, b7 = run(e, base, loud)
            print(f"{rom.split('/')[-1]}: meter {'loud' if loud else 'quiet'}: top speed {top}; sflags8 bit 1 on {b8} of 90 "
                  f"frames, sflags7 bit 6 on {b7}")


if __name__ == "__main__":
    main()
