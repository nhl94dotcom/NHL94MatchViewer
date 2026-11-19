"""NHL '95 goalie frames drawn from the ROM with their HotList points (2026-11-19). NHL '95 keeps its sprites like NHL '94
(found through the same code, `movea.l #SprTbl,a2 / adda.l 4(a2),a2`, at $79DCC): SprTbl $CA56A, the frame table at
SprTbl + its second long ($1318F4: word n and n + 1 bound frame n's pieces), tile t at SprTbl + 10 + 32t. Each piece is a
VDP sprite entry, not NHL '94's layout: y, a size byte (low nibble: width and height in cells; HIGH NIBBLE: the tile
number's bits 11-14), the pattern word (palette, flips, tile bits 0-10), x. HotList at $137B66 (x, y bytes), placed as
GetHot does for a goalie (y negated: a screen offset (x, y)): ROM red, a second ROM's blue. ZOOM=1: the ready, glove
and stick frames facing down (4, 3) beside facing up (0, 1).
python gen95_goalie_frames.py ROM [ROM2] OUT.png"""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import extract_sprites as X
from PIL import Image, ImageDraw
rom = Path(sys.argv[1]).read_bytes()
other = Path(sys.argv[2]).read_bytes() if len(sys.argv) > 3 else None
out = sys.argv[-1]
SPR = 0xCA56A
X.TILES = SPR + 10
X.FRAME_TABLE = SPR + struct.unpack_from(">I", rom, SPR + 4)[0]
HOT = 0x137B66
X.SLOT[3] = 3
X.TILES = SPR + 10          # tile n at SprTbl + 10 + 32n (the size byte's high nibble gives n's bits 11-14)
def pieces(r, n):
    """'95's pieces are VDP sprite entries: y, size byte (and link), pattern word, x. Returned in '94's layout
    (x, y, tile, attr with size bits 0-3 as w-1 << 2 | h-1, palette 13-14, flips 11-12)."""
    ft = X.FRAME_TABLE
    s, e = ft + struct.unpack_from(">H", r, ft + 2 * n)[0], ft + struct.unpack_from(">H", r, ft + 2 * n + 2)[0]
    out = []
    for p in range(s, e, 8):
        y, sz, pat, x = struct.unpack_from(">hHHh", r, p)
        size = (sz >> 8) & 0x0F
        out.append((x, y, ((sz >> 12) << 11) | (pat & 0x7FF), (pat & 0x7800) | size))
    return out
X.pieces = pieces
rows = [("ready", 606), ("glove l", 614), ("glove r", 622), ("stick l", 630), ("stick r", 638)]
import os
if os.environ.get("ZOOM"):
    grid = [[(f"{k} f{f}", b + f) for f in (4, 0, 3, 1)] for k, b in rows]
else:
    grid = [[(f"{k} f{f}", b + f) for f in range(8)] for k, b in rows]
    grid += [[(f"crouch {904 + 3 * s + j}", 904 + 3 * s + j) for s in range(6)] for j in range(3)]
S, CW, CH = 4, 64, 64
SZ = 4 if os.environ.get('ZOOM') else 2
img = Image.new("RGB", (8 * CW * S // 2 * 1 + 40, len(grid) * CH * S // 2 + 40), (235, 242, 246))
img = Image.new("RGB", (len(grid[0]) * CW * SZ + 20, len(grid) * CH * SZ + 20), (235, 242, 246))
d = ImageDraw.Draw(img)
S = SZ
for r_, row in enumerate(grid):
    for c, (lab, fr) in enumerate(row):
        ox, oy = 10 + c * CW * S + CW, 10 + r_ * CH * S + int(CH * 1.35)
        try:
            left, top, canvas = X.compose(rom, fr)
        except Exception as ex:
            d.text((ox - 50, oy - 40), f"{fr}: {ex}"[:30], fill=(200, 0, 0)); continue
        for y, line in enumerate(canvas):
            for x, (slot, v) in enumerate(line):
                if v:
                    g = 30 + 13 * v
                    d.rectangle([ox + (left + x) * S, oy + (top + y) * S, ox + (left + x + 1) * S - 1, oy + (top + y + 1) * S - 1], fill=(g, g, g))
        d.line([ox - 3, oy, ox + 3, oy], fill=(0, 160, 0)); d.line([ox, oy - 3, ox, oy + 3], fill=(0, 160, 0))
        for r2, col in ((rom, (230, 0, 0)), (other, (0, 70, 255))):
            if r2 is None:
                continue
            hx, hy = struct.unpack_from(">bb", r2, HOT + 2 * fr)
            px, py = ox + hx * S, oy + hy * S
            d.ellipse([px - 4, py - 4, px + 4, py + 4], outline=col, width=2)
        hx, hy = struct.unpack_from(">bb", rom, HOT + 2 * fr)
        d.text((ox - CW + 4, oy - int(CH * 1.3)), f"{fr} {lab} ({hx},{hy})", fill=(0, 0, 0))
img.save(out)
print("saved", out)
