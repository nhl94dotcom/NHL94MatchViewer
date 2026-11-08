"""Which piece is in front where a team's big logo overlaps itself, in the SNES game (2026-11-08, for NOSE4Web, which
draws later pieces over earlier ones; Hartford's has 192 overlapping pixels).

The big logos (matchups, Game Setup and stats screens, player cards) are sprites: DrawSprite writes a logo's pieces
into the sprite table in list order (sprcount + 4 each), and the game never rotates sprite priority (OAMADDH is only
ever cleared), so the first piece has the lowest sprite number and is drawn in front. To see it: the matchups' first
page with the team as the visitors (its logo at 12, 12 in sprite palette 2), the shown sprite table (OAMShowBuf),
the sprite tiles from VRAM (OBSEL 3: tiles at word $6000, 8x8 / 16x16) and the colours from colourbuf; the logo is
drawn again offline with the earlier pieces in front and with the later ones in front, and each is compared with the
game's own screen pixel for pixel.

python snes_logo_overlap.py ROM OUT [VISITOR_LEFT_PRESSES]   (default 1: Hartford, from Los Angeles)"""
import ctypes as C
import sys
from pathlib import Path

from PIL import Image

import menu_shots as M


def rgb(w):
    return tuple((w >> s & 31) * 255 // 31 for s in (0, 5, 10))


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    left = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    out.mkdir(parents=True, exist_ok=True)
    e = M.emulator(rom)
    vram = bytes  # filled below
    M.play(e, f"w1500 START w240 START w240 DOWN DOWN LEFT*{left} w60 START w240 START w200", out)
    e.screenshot(out / "game.png")
    vram = bytes((C.c_ubyte * 65536).from_address(e.lib.retro_get_memory_data(3)))
    ram = e.ram
    buf = e.w(0x07AC)
    oam = bytes(ram[buf:buf + 0x220])
    pal = [rgb(ram[0x17500 + 2 * (128 + 16 * 2 + i)] | ram[0x17500 + 2 * (128 + 16 * 2 + i) + 1] << 8) for i in range(16)]
    pieces = []
    for n in range(128):
        x, y, t, a = oam[4 * n], oam[4 * n + 1], oam[4 * n + 2], oam[4 * n + 3]
        hi = oam[512 + n // 4] >> (2 * (n % 4)) & 3
        x |= (hi & 1) << 8
        if x >= 256:
            x -= 512
        p = a >> 1 & 7
        if p != 2 or not (0 <= x < 80 and 0 <= y < 80):
            continue
        pieces.append(dict(n=n, x=x, y=y, tile=t | (a & 1) << 8, h=bool(a & 0x40), v=bool(a & 0x80), size=16 if hi & 2 else 8))

    def tile_px(t, px, py):
        base = (0x6000 + t * 16) * 2
        d = vram[base:base + 32]
        b = 7 - px
        return (d[2 * py] >> b & 1) | (d[2 * py + 1] >> b & 1) << 1 | (d[16 + 2 * py] >> b & 1) << 2 | (d[17 + 2 * py] >> b & 1) << 3

    def piece_px(pc, sx, sy):
        s = pc["size"]
        if pc["h"]:
            sx = s - 1 - sx
        if pc["v"]:
            sy = s - 1 - sy
        t = pc["tile"] + (sx // 8) + 16 * (sy // 8)
        return tile_px(t, sx % 8, sy % 8)

    def render(order):
        img = {}
        for pc in order:                                  # later in this list = drawn on top
            for sy in range(pc["size"]):
                for sx in range(pc["size"]):
                    c = piece_px(pc, sx, sy)
                    if c:
                        img[(pc["x"] + sx, pc["y"] + sy)] = c
        return img

    front_first = render(list(reversed(pieces)))          # the game's rule: the first piece in front
    front_last = render(pieces)                           # later pieces over earlier ones
    game = Image.open(out / "game.png").convert("RGB")
    cover = {}
    for pc in pieces:
        for sy in range(pc["size"]):
            for sx in range(pc["size"]):
                c = piece_px(pc, sx, sy)
                if c:
                    cover.setdefault((pc["x"] + sx, pc["y"] + sy), []).append(c)
    over = sum(1 for v in cover.values() if len(v) > 1)
    clash = sum(1 for v in cover.values() if len(v) > 1 and len(set(v)) > 1)
    differ = [k for k in front_first if front_first[k] != front_last.get(k)]
    for name, img in (("earlier_in_front", front_first), ("later_in_front", front_last)):
        near = lambda a, b: all(abs(i - j) <= 8 for i, j in zip(a, b))     # the core's RGB565 rounds a little
        miss = sum(1 for (x, y), c in img.items() if 0 <= x < 256 and 0 <= y < 224 and not near(game.getpixel((x, y)), pal[c]))
        pic = Image.new("RGB", (80, 80), (0, 0, 0))
        for (x, y), c in img.items():
            if 0 <= x < 80 and 0 <= y < 80:
                pic.putpixel((x, y), pal[c])
        pic.resize((320, 320), Image.NEAREST).save(out / f"{name}.png")
        print(f"{name}: {len(img)} pixels drawn, {miss} differ from the game's screen")
    game.crop((0, 0, 80, 80)).resize((320, 320), Image.NEAREST).save(out / "game_logo.png")
    print(f"{len(pieces)} pieces (sprite numbers {[p['n'] for p in pieces]}); {over} pixels where two or more pieces "
          f"have colour ({clash} of them with different colours in the pieces); the two orders differ in {len(differ)}")


if __name__ == "__main__":
    main()
