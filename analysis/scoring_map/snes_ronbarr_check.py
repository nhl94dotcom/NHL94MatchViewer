"""The SNES scouting (matchup) screen's Ron Barr picture, measured (2026-11-10, for NOSE4Web's "replace Ron Barr with
your own picture"). LoadScoutingScreen (NHL94SNES): BG1 map at 0, BG2 map at $400 words, BG2 tiles at $1000 words,
BG1 tiles at $2000; SetupScreenPalette to colours 0-$1F, RonBarrPalette's first 16 to $20 (row 2), MenuBackPalette to
$30; RonBarrTiles unpacked and sent after MenuBackTiles (backchars); RonBarrMap unpacked, its non-empty words plus
backchars, charofs2 and palette 2 into textmap2 (BG2). From the ROM: the three pieces' packed sizes and the unpacked
sizes their headers give (Decompress: format word, then the size). In the game (the retail ROM, the matchup screen
after Game Setup): which of the 32 x 28 cells are the picture (BG2 cells on Ron Barr's tiles) and which the frame and
text (BG1, and BG2 cells the map leaves empty); Ron Barr's tile range and the rest of BG2's tile room; the colours
each part uses, by colour row.

python snes_ronbarr_check.py ROM OUT"""
import ctypes
import struct
import sys
from collections import defaultdict
from pathlib import Path

import menu_shots as M

BACKCHARS, CHAROFS2, COLOURBUF = 0x35B4, 0x35AC, 0x17500


def vram(e):
    n = e.lib.retro_get_memory_size(3)
    return bytes((ctypes.c_ubyte * n).from_address(e.lib.retro_get_memory_data(3)))


def tile_colours(vr, base_words, t):
    """Colour indexes a 4-bit-a-pixel tile uses (planes 0/1 then 2/3, 8 rows)."""
    a = 2 * base_words + 32 * t
    cols = set()
    for r in range(8):
        p0, p1, p2, p3 = vr[a + 2 * r], vr[a + 2 * r + 1], vr[a + 16 + 2 * r], vr[a + 16 + 2 * r + 1]
        for b in range(8):
            cols.add(((p0 >> b) & 1) | (((p1 >> b) & 1) << 1) | (((p2 >> b) & 1) << 2) | (((p3 >> b) & 1) << 3))
    return cols


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    e = M.emulator(rom)
    M.play(e, "w1500 START w240 START w240 w60 START w240", out)
    e.run(4, hold=["START"])
    e.run(200)
    e.screenshot(out / "matchup.png")
    vr = vram(e)
    back, ofs2 = e.w(BACKCHARS), e.w(CHAROFS2)
    print(f"backchars {back} (the first BG2 tile after MenuBackTiles), charofs2 {ofs2}; video memory {len(vr)} bytes")
    cols = [e.w(COLOURBUF + 2 * i) for i in range(128)]
    for row in range(4):
        print(f"  colour row {row}: {' '.join(f'{c:04x}' for c in cols[16 * row:16 * row + 16])}")
    bg = {"BG1": (0x0000, 0x2000), "BG2": (0x0400, 0x1000)}            # map base, tile base (words)
    cells = {}
    for name, (mapw, tilew) in bg.items():
        cells[name] = [[struct.unpack_from("<H", vr, 2 * mapw + 2 * (32 * y + x))[0] for x in range(32)] for y in range(28)]
    ron = [(x, y) for y in range(28) for x in range(32) if cells["BG2"][y][x] & 0x3FF >= back and (cells["BG2"][y][x] >> 10) & 7 == 2]
    ron_tiles = sorted({cells["BG2"][y][x] & 0x3FF for x, y in ron})
    if ron:
        xs, ys = [x for x, _ in ron], [y for _, y in ron]
        print(f"Ron Barr: {len(ron)} BG2 cells, columns {min(xs)}-{max(xs)}, rows {min(ys)}-{max(ys)}, tiles {ron_tiles[0]}-{ron_tiles[-1]} "
              f"({len(ron_tiles)} distinct), palette 2")
        print("  rows of the 32 x 28 map with picture cells (column ranges):")
        for y in range(28):
            row = [x for x, yy in ron if yy == y]
            if row:
                print(f"    row {y:2d}: columns {min(row)}-{max(row)} ({len(row)} cells)")
    # the rest of BG2's tiles, and the room after Ron Barr's (BG2's tiles end where BG1's begin: $2000 words)
    other_bg2 = sorted({w & 0x3FF for row in cells["BG2"] for w in row} - set(ron_tiles))
    room_end = (0x2000 - 0x1000) // 16
    top = ron_tiles[-1] + 1 if ron_tiles else back
    print(f"BG2 tile room: tiles 0-{room_end - 1} ({room_end}); MenuBackTiles 0-{back - 1}; Ron Barr {back}-{top - 1}; "
          f"{room_end - top} tiles free after them; other BG2 tiles on screen: {other_bg2[:12]}{'...' if len(other_bg2) > 12 else ''}")
    # colours each part uses
    use = defaultdict(lambda: defaultdict(set))
    for name, (mapw, tilew) in bg.items():
        for y in range(28):
            for x in range(32):
                w = cells[name][y][x]
                t, pal = w & 0x3FF, (w >> 10) & 7
                c = {k for k in tile_colours(vr, tilew, t) if k}
                if not c:
                    continue
                part = "Ron Barr" if name == "BG2" and (x, y) in set(ron) else f"{name} " + (
                    "left" if x < 11 else "right" if x >= 21 else "centre") + (" top" if y < 10 else " bottom" if y >= 19 else " middle")
                use[pal][part] |= c
    for pal in sorted(use):
        print(f"colour row {pal} used by:")
        for part, c in sorted(use[pal].items()):
            print(f"    {part}: {sorted(c)}")


if __name__ == "__main__":
    main()
