"""The headless frontend (emu.py) over a copy of the Snes9x core, for the SNES ROM. Work RAM is the core's SYSTEM_RAM
buffer (128 KB, banks $7E-$7F) in the SNES's own little-endian order: the word at $7E:A is ram[A], ram[A + 1]."""
from emu import Emu
from paths import SNES_CORE, SNES_ROM

# libretro joypad ids map one to one onto the SNES pad
SNES_PAD = {"B": 0, "Y": 1, "SELECT": 2, "START": 3, "UP": 4, "DOWN": 5, "LEFT": 6, "RIGHT": 7, "A": 8, "X": 9,
            "L": 10, "R": 11}


class SnesEmu(Emu):
    PAD = SNES_PAD

    def __init__(self, rom=SNES_ROM):
        super().__init__(rom, core=SNES_CORE)

    def b(self, a):
        return self.ram[a & 0x1FFFF]

    def setb(self, a, v):
        self.ram[a & 0x1FFFF] = v & 0xFF

    def w(self, a):
        a &= 0x1FFFF
        return self.ram[a] | self.ram[a + 1] << 8

    def setw(self, a, v):
        a &= 0x1FFFF
        v &= 0xFFFF
        self.ram[a], self.ram[a + 1] = v & 0xFF, v >> 8
