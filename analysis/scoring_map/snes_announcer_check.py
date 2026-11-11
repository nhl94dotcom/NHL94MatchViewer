"""NOSE4Web's SNES announcer picture against the original (2026-11-11, for 8f5a975: NHL94_announcer.smc,
nhl94_2026_announcer.sfc). The new picture goes in the rectangle nothing else on the scouting screen covers (columns
23-31, rows 12-27: snes_announcer_area.py) in up to 15 colours of row 2. Both ROMs are taken to the scouting screen the
same way (snes_announcer_area's presses) and sampled every 30 frames from 180 frames in (the fade-in) for 30 s (real):
the BG2 cells on picture tiles (at or above backchars, palette 2) inside and outside the rectangle, the picture's
tiles and their room (BG2's tiles end at 256, where BG1's begin), the colours each row holds and which rows the rest of
the screen uses, BG1 (the text and the box) against the original, and the screenshots outside the rectangle pixel for
pixel at the first sample (later ones differ by the text, which follows the random hot / cold rolls). The picture is
cropped from a screenshot (picture_<tag>.png, 4x).

python snes_announcer_check.py ORIGINAL NEW OUT"""
import struct
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

import menu_shots as M
from snes_ronbarr_check import vram, tile_colours, BACKCHARS, COLOURBUF
from snes_announcer_area import cells, BG

RECT = (23, 12, 31, 27)          # columns, rows (inclusive)
inside = lambda x, y: RECT[0] <= x <= RECT[2] and RECT[1] <= y <= RECT[3]


def run(rom, out, tag):
    e = M.emulator(rom)
    M.play(e, "w1500 START w240 START w240 w60 START w240", out)
    e.run(4, hold=["START"])
    e.run(180)
    samples = []
    for k in range(60):
        e.run(30)
        vr = vram(e)
        samples.append(dict(vr=vr, back=e.w(BACKCHARS), cols=[e.w(COLOURBUF + 2 * i) for i in range(128)],
                            c1=cells(vr, "BG1"), c2=cells(vr, "BG2")))
        if k in (0, 59):
            e.screenshot(out / f"shot{k}_{tag}.png")
    return samples


def picture_cells(s):
    return [(x, y, s["c2"][y][x]) for y in range(28) for x in range(32)
            if s["c2"][y][x] & 0x3FF >= s["back"] and (s["c2"][y][x] >> 10) & 7 == 2]


def main():
    orig, new, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    A, B = run(orig, out, "original"), run(new, out, "new")
    a, b = A[0], B[0]
    print(f"backchars: original {a['back']}, new {b['back']}")
    for tag, S in (("original", A), ("new", B)):
        pc = picture_cells(S[0])
        xs, ys = [x for x, _, _ in pc], [y for _, y, _ in pc]
        tiles = sorted({w & 0x3FF for _, _, w in pc})
        outside = [(x, y) for x, y, _ in pc if not inside(x, y)]
        flips = Counter((w >> 14) & 3 for _, _, w in pc)
        print(f"{tag}: picture cells {len(pc)}, columns {min(xs)}-{max(xs)}, rows {min(ys)}-{max(ys)}; tiles {tiles[0]}-{tiles[-1]} "
              f"({len(tiles)} distinct, room to 255: {255 - tiles[-1]} left); outside the rectangle: {len(outside)} {outside[:10]}; "
              f"flip bits {dict(flips)}")
        changes = sum(picture_cells(s) != pc for s in S[1:])
        print(f"  samples where the picture's cells changed: {changes} of {len(S) - 1}")
    # the rectangle on the new ROM: every cell a picture cell?
    pc = {(x, y) for x, y, _ in picture_cells(b)}
    missing = [(x, y) for y in range(RECT[1], RECT[3] + 1) for x in range(RECT[0], RECT[2] + 1) if (x, y) not in pc]
    print(f"new: rectangle cells not on the picture: {len(missing)} {missing[:12]}")
    # BG2 outside the rectangle: the original's Ron Barr cells now?
    ron = {(x, y) for x, y, _ in picture_cells(a)}
    left = Counter()
    for (x, y) in ron:
        if not inside(x, y):
            w = b["c2"][y][x]
            left["menu background" if w & 0x3FF < b["back"] else f"tile {w & 0x3FF} palette {(w >> 10) & 7}"] += 1
    print(f"new: Ron Barr's old cells outside the rectangle ({sum(left.values())}) now show: {dict(left)}")
    other2 = [(x, y) for y in range(28) for x in range(32) if (x, y) not in ron and not inside(x, y) and a["c2"][y][x] != b["c2"][y][x]]
    print(f"new: other BG2 cells outside the rectangle that differ from the original: {len(other2)} {other2[:10]}")
    # menu background tiles the same?
    bt = [t for t in range(a["back"]) if a["vr"][2 * BG["BG2"][1] + 32 * t:2 * BG["BG2"][1] + 32 * t + 32]
          != b["vr"][2 * BG["BG2"][1] + 32 * t:2 * BG["BG2"][1] + 32 * t + 32]]
    print(f"menu background tiles (0-{a['back'] - 1}) differing: {bt[:12] or 'none'}")
    # BG1 against the original at the first sample: map words and tile data
    d1 = [(x, y) for y in range(28) for x in range(32) if a["c1"][y][x] != b["c1"][y][x]]
    t1 = sorted({a["c1"][y][x] & 0x3FF for y in range(28) for x in range(32)})
    dd = [t for t in t1 if a["vr"][2 * BG["BG1"][1] + 32 * t:2 * BG["BG1"][1] + 32 * t + 32]
          != b["vr"][2 * BG["BG1"][1] + 32 * t:2 * BG["BG1"][1] + 32 * t + 32]]
    print(f"BG1 at the first sample: map words differing {len(d1)} {d1[:10]}; tiles shown with different data {dd[:10] or 'none'}")
    bg1_in = Counter()
    for S in (A, B):
        for s in S:
            for y in range(RECT[1], RECT[3] + 1):
                for x in range(RECT[0], RECT[2] + 1):
                    if {c for c in tile_colours(s["vr"], BG["BG1"][1], s["c1"][y][x] & 0x3FF) if c}:
                        bg1_in[(x, y)] += 1
    print(f"BG1 drawing inside the rectangle, any sample of either ROM: {dict(bg1_in) or 'none'}")
    # colours
    for row in range(8):
        ca, cb = a["cols"][16 * row:16 * row + 16], b["cols"][16 * row:16 * row + 16]
        d = [(i, f"{ca[i]:04x}", f"{cb[i]:04x}") for i in range(16) if ca[i] != cb[i]]
        print(f"colour row {row}: {'same' if not d else d}")
    used = Counter()
    for y in range(28):
        for x in range(32):
            for name in ("BG1", "BG2"):
                w = b["c1" if name == "BG1" else "c2"][y][x]
                if (w >> 10) & 7 == 2 and {c for c in tile_colours(b["vr"], BG[name][1], w & 0x3FF) if c}:
                    used[(name, "picture" if (x, y) in pc and name == "BG2" else "other")] += 1
    print(f"new: cells drawn in colour row 2: {dict(used)}")
    # screenshots
    for k in (0, 59):
        ia, ib = Image.open(out / f"shot{k}_original.png").convert("RGB"), Image.open(out / f"shot{k}_new.png").convert("RGB")
        sx, sy = ia.width / 256, ia.height / 224
        box = (int(8 * RECT[0] * sx), int(8 * RECT[1] * sy), int(8 * (RECT[2] + 1) * sx), int(8 * (RECT[3] + 1) * sy))
        diff = [(x, y) for y in range(ia.height) for x in range(ia.width)
                if not (box[0] <= x < box[2] and box[1] <= y < box[3]) and ia.getpixel((x, y)) != ib.getpixel((x, y))]
        ron_px = sum(1 for (x, y) in diff if (int(x / sx) // 8, int(y / sy) // 8) in ron)
        print(f"screenshot {k}: pixels outside the rectangle that differ {len(diff)} (on Ron Barr's old cells: {ron_px})")
        if k == 0:
            for tag, im in (("original", ia), ("new", ib)):
                crop = im.crop(box)
                crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST).save(out / f"picture_{tag}.png")


if __name__ == "__main__":
    main()
