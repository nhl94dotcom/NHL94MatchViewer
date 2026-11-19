"""Goalie frames 407-430 (ready, glove a, glove b for each facing) drawn from the ROM with their HotList hot spots (the stick blade, and where a held puck sits): ROM_A red, ROM_B blue. python goalie_hot_frames.py ROM_A ROM_B OUT.png"""
import struct, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import extract_sprites as X
from PIL import Image, ImageDraw
R = Path(sys.argv[1]).read_bytes()
B = Path(sys.argv[2]).read_bytes()
S, W, H = 5, 48, 56
img = Image.new("RGB", (3 * W * S, 8 * H * S), (230, 240, 245))
d = ImageDraw.Draw(img)
for fr in range(407, 431):
    dr, j = (fr - 407) // 3, (fr - 407) % 3
    left, top, canvas = X.compose(R, fr)
    ox, oy = j * W * S + 24 * S, dr * H * S + 34 * S          # the anchor on the sheet
    for y, row in enumerate(canvas):
        for x, (slot, v) in enumerate(row):
            if v:
                g = 40 + 12 * v
                d.rectangle([ox + (left + x) * S, oy + (top + y) * S, ox + (left + x + 1) * S - 1, oy + (top + y + 1) * S - 1], fill=(g, g, g))
    for rom, col, r in ((R, (220, 0, 0), 4), (B, (0, 60, 255), 2)):
        hx, hy = struct.unpack_from(">bb", rom, 0xA44C8 + 2 * fr)
        px, py = ox + hx * S + S // 2, oy + hy * S + S // 2
        d.ellipse([px - r * 2, py - r * 2, px + r * 2, py + r * 2], outline=col, width=3)
    d.text((j * W * S + 4, dr * H * S + 4), f"{fr} dir {dr} {['ready', 'glove a', 'glove b'][j]}", fill=(0, 0, 0))
img.save(sys.argv[3])
print("left/top sample", X.compose(R, 407)[:2])
