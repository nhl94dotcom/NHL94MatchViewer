"""The Genesis rink background drawn from the ROM (2026-11-14; the video reader's reference picture).

Rinktilelist (a .map.jim at $5605A on retail nhl94.bin; the routine setupice loads its tiles from VRAM char 0, so the
map's tile numbers are the jim's own): +0 long the palette's offset (two lines of 16 colours, 9-bit BGR words), +4 long
the map's offset (word columns, word rows, then the map words: bit 15 priority, 14-13 palette line, 12 vertical flip,
11 horizontal flip, 10-0 tile), +8 word the tile count (bit 15 clear: not packed), then 32-byte tiles (4 bits a pixel).
The centre-ice logo is a sprite (addframe2), not part of this picture. Colour 0 of line 0 is the backdrop.

render(rom) -> (H, W, 3) uint8, one pixel per screen pixel, 384 x 904 for retail.

python analysis/vision/rink_render.py ROM OUT.png"""
import struct
import sys
from pathlib import Path

import numpy as np

RINKTILELIST = 0x5605A
LEVELS = np.array([0, 33, 66, 99, 140, 173, 206, 239], np.uint8)     # the 3-bit levels in RetroArch's recordings
                                                                     # (Genesis Plus GX; measured, 2026-11-14)


def colour(w):
    return LEVELS[(w >> 1) & 7], LEVELS[(w >> 5) & 7], LEVELS[(w >> 9) & 7]


def find_rink(rom):
    """The Rinktilelist address: retail's, or found by its shape (a palette 128 bytes before a 48 x 113 map)."""
    def ok(a):
        try:
            p, m = struct.unpack(">II", rom[a:a + 8])
            return m - p == 0x80 and struct.unpack(">HH", rom[a + m:a + m + 4]) == (48, 113)
        except struct.error:
            return False
    if ok(RINKTILELIST):
        return RINKTILELIST
    for a in range(0, len(rom) - 16, 2):
        if ok(a):
            return a
    raise ValueError("no rink map found")


def render(rom, a=None):
    a = find_rink(rom) if a is None else a
    p, m = struct.unpack(">II", rom[a:a + 8])
    pal = [colour(w) for w in struct.unpack(">64H", rom[a + p:a + p + 128])]
    n = struct.unpack(">H", rom[a + 8:a + 10])[0]
    assert not n & 0x8000, "packed rink tiles"
    raw = np.frombuffer(rom[a + 10:a + 10 + 32 * n], np.uint8).reshape(n, 8, 4)
    tiles = np.stack([raw >> 4, raw & 15], axis=-1).reshape(n, 8, 8)       # pixel indices
    cols, rows = struct.unpack(">HH", rom[a + m:a + m + 4])
    words = struct.unpack(f">{cols * rows}H", rom[a + m + 4:a + m + 4 + 2 * cols * rows])
    pal = np.array(pal, np.uint8)
    img = np.zeros((rows * 8, cols * 8, 3), np.uint8)
    for i, w in enumerate(words):
        t = w & 0x7FF
        px = tiles[t] if t < n else np.zeros((8, 8), np.uint8)
        if w & 0x800:
            px = px[:, ::-1]
        if w & 0x1000:
            px = px[::-1]
        line = (w >> 13) & 3
        y, x = divmod(i, cols)
        img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = pal[line * 16 + px]
    return img


if __name__ == "__main__":
    rom = Path(sys.argv[1]).read_bytes()
    img = render(rom)
    from PIL import Image
    Image.fromarray(img).save(sys.argv[2])
    print(img.shape, sys.argv[2])
