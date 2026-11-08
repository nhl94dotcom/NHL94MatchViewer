"""Does Genesis Plus GX (our copy of RetroArch 1.17's core) switch the save memory in and out through $A130F1 on a
cartridge bigger than 2 MB? (2026-11-08, for NOSE4Web: a ROM over 2 MB covers $200001, where the save memory is, so
the game must switch it in, as EVO does; NOSE4Web now refuses to grow a Genesis ROM past 2 MB.)

A test ROM built here, no game code: the header declares save memory at $200001-$20FFFF (odd bytes, 'RA' $F8 $20, as
EVO's), the ROM bytes at $200000-$20FFFF are $5A, and the code at $200 does, storing each result in work RAM:
  $FF000A  read $200001 at power-on (no write to $A130F1 yet)
  $FF0000  write 0 to $A130F1 (ROM), read $200001
  $FF0002  write 1 (save memory), write $C3 to $200001, read it back
  $FF0004  write 0, read $200001
  $FF0006  write 1, read $200001
  $FF0008  $AA when done
A 3 MB ROM and a 2 MB one (where $200001 is past the end of the ROM, the usual case) side by side; $5A read = the ROM,
$C3 = the save memory.

python a130f1_test.py"""
import struct
import tempfile
from pathlib import Path

from emu import Emu


def build(size):
    rom = bytearray(b"\xFF" * size)
    struct.pack_into(">II", rom, 0, 0x00FFFE00, 0x00000200)          # stack, start
    for v in range(2, 64):
        struct.pack_into(">I", rom, 4 * v, 0x00000200)
    rom[0x100:0x110] = b"SEGA GENESIS    "
    rom[0x120:0x150] = b"A130F1 TEST".ljust(48)
    struct.pack_into(">II", rom, 0x1A0, 0, size - 1)                  # ROM range
    struct.pack_into(">II", rom, 0x1A8, 0xFF0000, 0xFFFFFF)           # work RAM
    rom[0x1B0:0x1B4] = b"RA\xF8\x20"                                   # save memory: odd bytes, battery
    struct.pack_into(">II", rom, 0x1B4, 0x200001, 0x20FFFF)
    if size > 0x200000:
        rom[0x200000:0x210000] = b"\x5A" * 0x10000
    rd = lambda dst: struct.pack(">HII", 0x13F9, 0x200001, dst)       # move.b ($200001).l,(dst).l
    sw = lambda v: struct.pack(">HHI", 0x13FC, v, 0xA130F1)           # move.b #v,($A130F1).l
    code = (rd(0xFF000A) + sw(0) + rd(0xFF0000) + sw(1) + struct.pack(">HHI", 0x13FC, 0xC3, 0x200001)
            + rd(0xFF0002) + sw(0) + rd(0xFF0004) + sw(1) + rd(0xFF0006)
            + struct.pack(">HHI", 0x13FC, 0xAA, 0xFF0008) + struct.pack(">H", 0x60FE))   # done; bra.s *
    rom[0x200:0x200 + len(code)] = code
    return bytes(rom)


def run(size):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / f"a130f1_{size >> 20}mb.bin"
        p.write_bytes(build(size))
        e = Emu(rom=p)
        e.run(30)
        sram = e.lib.retro_get_memory_size(0)
        r = {k: e.b(0xFF0000 + o) for k, o in (("power-on", 0x0A), ("after 0", 0), ("after 1, wrote C3", 2),
                                               ("after 0 again", 4), ("after 1 again", 6), ("done", 8))}
        return r, sram


def main():
    for size in (0x300000, 0x200000):
        r, sram = run(size)
        what = lambda v: {0x5A: "ROM", 0xC3: "save memory", 0xFF: "open bus / blank"}.get(v, "?")
        print(f"{size >> 20} MB ROM (save memory size the core reports: {sram} bytes)")
        for k, v in r.items():
            print(f"   {k:20s} ${v:02X}  {what(v) if k != 'done' else ('ok' if v == 0xAA else 'code did not finish')}")


if __name__ == "__main__":
    main()
