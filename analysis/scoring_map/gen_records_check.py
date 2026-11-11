"""Saved records across a reset (2026-11-11, for NOSE4Web: chaos's fighting patch makes a 3 MB ROM, where the save
memory has to be switched in through $A130F1). The computer against itself with User Records on (OptUserRec $D054 =
0), 5-minute periods: UpdateRecords writes the team and player records to save memory at the intermission after the
game, with its checksum (MakeSRAMChecksum). The save memory (libretro memory 0) is read before the game, after it, and
after the core is reset (retro_reset) and the game booted again to Game Setup: at power-on the game checks the
checksum and formats the save memory if it doesn't match, so the records surviving the reset means they were written
and read back where the game looks for them.

python gen_records_check.py ROM OUT [--names]"""
import ctypes
import hashlib
import sys
from pathlib import Path

import gen_ot_check as G
import lowload
from emu import Emu

OPTUSER, OPTPEN, PERLEN, CONT1, CONT2, GSP, CLOCK, SCREEN = 0xD054, 0xD056, 0xD050, 0xC328, 0xC32A, 0xC466, 0xC468, 0xFFF7
BASE, SZ = 0xB04A, 0x80


def sram(e):
    n = e.lib.retro_get_memory_size(0)
    p = e.lib.retro_get_memory_data(0)
    return bytes((ctypes.c_ubyte * n).from_address(p)) if n and p else b""


def summary(b):
    used = [i for i, v in enumerate(b) if v not in (0x00, 0xFF)]
    return f"{len(b)} bytes, {len(used)} not 00/FF, md5 {hashlib.md5(b).hexdigest()[:10]}"


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    e = Emu(rom)
    G.to_setup(e, out)
    s0 = sram(e)
    print("save memory at Game Setup, first boot:", summary(s0))
    e.setw(OPTUSER, 0)
    e.setw(OPTPEN, 2)
    e.setw(PERLEN, 0)
    if "--names" in sys.argv:
        # a ROM starting at "Two - Head to Head" (CDL) asks the people for names with User Records on; Players set to
        # One - Home, one name: B to edit, the
        # d-pad to a letter, C to select it, START when done (an empty name isn't taken)
        def p(btn, w=40):
            e.run(4, hold=[btn])
            e.run(w)
        e.setw(0xD04A, 0)                       # Players (OptNOP): One - Home, so one name is asked for
        p("START", 120)
        p("B", 60)
        p("RIGHT")
        p("C")
        p("START", 120)
        e.screenshot(out / "after_names.png")
    if not G.into_play(e):
        print("never reached play")
        return
    frame, still, last, ended = 0, 0, None, None
    while frame < 60 * 60 * 45:
        if frame % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            c = e.w(CLOCK)
            still = still + 1 if c == last else 0
            last = c
            if frame % 3600 == 0:
                lowload.breathe()
        e.run(4, hold=["START"] if still >= 8 and frame % 60 < 4 else [])     # any waiting screen (a pause menu opened closes on the next)
        frame += 4
        if ended is None and e.w(GSP) >= 3:
            ended = frame
        # the game over (back to the first period's number: the next game's setup) or 5 minutes past period 3
        # (overtime included): the records are written at the intermission after it
        if ended is not None and (e.w(GSP) == 0 or frame - ended > 10 * 60 * 60):
            e.run(600)
            break
    s1 = sram(e)
    e.screenshot(out / "after_game.png")
    print(f"after the game (periods {e.w(GSP)}, score {e.w(0xC6DA)}-{e.w(0xCA3E)}):", summary(s1),
          "| changed bytes:", sum(a != b for a, b in zip(s0, s1)))
    e.lib.retro_reset()
    G.to_setup(e, out)
    s2 = sram(e)
    print("after a reset and a boot to Game Setup:", summary(s2), "| same as after the game:", s1 == s2,
          "| changed bytes:", sum(a != b for a, b in zip(s1, s2)))


if __name__ == "__main__":
    main()
