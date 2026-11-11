"""The headless frontend (emu.py) over a copy of the Snes9x core, for the SNES ROM. Work RAM is the core's SYSTEM_RAM
buffer (128 KB, banks $7E-$7F) in the SNES's own little-endian order: the word at $7E:A is ram[A], ram[A + 1].

An SA-1 build (header map mode $23; NHL94_SNES_SA1 in paths.py) keeps low RAM $0100-$1FFF and parts of bank $7E in
BW-RAM (the core's SAVE_RAM): b / w / setb / setw route those addresses there (tools/systems/snes.SA1_MOVED, as the
helper reads a live game), so every tool reads and writes the retail addresses on either ROM (2026-11-10)."""
import ctypes
import sys
from pathlib import Path

from emu import Emu
from paths import SNES_CORE, SNES_ROM

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from systems.snes import SA1_MOVED  # noqa: E402

# libretro joypad ids map one to one onto the SNES pad
SNES_PAD = {"B": 0, "Y": 1, "SELECT": 2, "START": 3, "UP": 4, "DOWN": 5, "LEFT": 6, "RIGHT": 7, "A": 8, "X": 9,
            "L": 10, "R": 11}


class SnesEmu(Emu):
    PAD = SNES_PAD

    def __init__(self, rom=SNES_ROM):
        super().__init__(rom, core=SNES_CORE)
        data = Path(rom).read_bytes()
        self.sa1 = len(data) > 0x7FD6 and data[0x7FD5] == 0x23
        self.bw = (ctypes.c_ubyte * self.lib.retro_get_memory_size(0)).from_address(
            self.lib.retro_get_memory_data(0)) if self.sa1 else None

    def at(self, a):
        """(buffer, offset) for work RAM address a (bank $7E/$7F)."""
        a &= 0x1FFFF
        if self.sa1:
            for lo, hi, to in SA1_MOVED:
                if lo <= a < hi:
                    return self.bw, to + a - lo
        return self.ram, a

    def b(self, a):
        buf, o = self.at(a)
        return buf[o]

    def setb(self, a, v):
        buf, o = self.at(a)
        buf[o] = v & 0xFF

    def w(self, a):
        buf, o = self.at(a)
        return buf[o] | buf[o + 1] << 8

    def setw(self, a, v):
        buf, o = self.at(a)
        v &= 0xFFFF
        buf[o], buf[o + 1] = v & 0xFF, v >> 8
