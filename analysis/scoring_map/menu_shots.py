"""Screenshots of the game's own screens from power-on, for checking ROM edits that show outside play (2026-11-08, for
NOSE4Web's player photo and score logo editing): boot a ROM in a copy of the core, follow a script of button presses
and waits, save a screenshot at each `s`. The same script on the original and the edited ROM gives pictures to
compare, frame for frame (the boot is the same every time: no input before the script's).

Script tokens (space separated): a button name (Genesis A B C START UP DOWN LEFT RIGHT; SNES B Y A X L R SELECT START
...) is held 4 frames then released 20; NAME*k k times; wN waits N frames; s saves OUT/NN.png; S:NAME saves OUT/NAME.png;
h:BUTTON:N holds a button N frames; u:ADDR:VALUE:BUTTON presses the button (4 frames held, 26 waited) until the RAM word at
ADDR (hex; SNES work RAM bank $7E, Genesis $FFxxxx) is VALUE, up to 40 presses (a menu's cursor: presses can be lost).

python menu_shots.py ROM OUT "w600 s START w60 s ..."   (the system by the ROM's extension: .bin Genesis, else SNES)"""
import sys
from pathlib import Path


def emulator(rom):
    if rom.lower().endswith((".bin", ".md", ".gen")):
        from emu import Emu
        return Emu(rom)
    from snes_emu import SnesEmu
    e = SnesEmu(rom)
    data = Path(rom).read_bytes()
    if len(data) > 0x7FD6 and data[0x7FD5] == 0x23:      # SA-1: low RAM in BW-RAM (faceoff_fix_test.Snes.MOVED)
        import ctypes as C
        from faceoff_fix_test import Snes
        bw = (C.c_ubyte * e.lib.retro_get_memory_size(0)).from_address(e.lib.retro_get_memory_data(0))
        plain = e.w

        def w(a):
            for lo, hi, to in Snes.MOVED:
                if lo <= a < hi:
                    o = to + a - lo
                    return bw[o] | bw[o + 1] << 8
            return plain(a)
        e.w = w
    return e


def play(e, script, out):
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    for tok in script.split():
        if tok == "s" or tok.startswith("S:"):
            name = f"{n:02d}" if tok == "s" else tok[2:]
            e.screenshot(out / f"{name}.png")
            n += 1
        elif tok.startswith("w"):
            e.run(int(tok[1:]))
        elif tok.startswith("u:"):
            _, addr, val, b = tok.split(":")
            for _ in range(40):
                if e.w(int(addr, 16)) == int(val):
                    break
                e.run(4, hold=[b])
                e.run(26)
            else:
                print("never reached", tok)
        elif tok.startswith("h:"):
            _, b, k = tok.split(":")
            e.run(int(k), hold=[b])
        else:
            b, _, k = tok.partition("*")
            for _ in range(int(k or 1)):
                e.run(4, hold=[b])
                e.run(20)


if __name__ == "__main__":
    rom, out, script = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    play(emulator(rom), script, out)
