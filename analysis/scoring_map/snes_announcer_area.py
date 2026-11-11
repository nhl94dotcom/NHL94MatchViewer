"""The SNES scouting (matchup) screen over time, for NOSE4Web's "a new picture in Ron Barr's place" (2026-11-10): which of
the 32 x 28 cells Ron Barr's picture covers (BG2 cells on his tiles, palette 2: snes_ronbarr_check), and which cells
anything else uses while the screen runs (the text types out and the matchups page by themselves): BG1 cells with a
visible pixel (the text, the matchup names and ratings), BG2 cells that aren't the picture and aren't the plain
menu background (the frames and boxes), and sprites. Sampled every 30 frames for 60 s (real), from 180 frames into the
screen (before that it is still fading in, and the video memory holds some of the last screen). The largest rectangle inside the bottom-right area that nothing but the picture and the plain background ever
uses, and the rectangles a picture of Ron Barr's own extent would cross. Screenshots now and then (shot_<frame>.png).

python snes_announcer_area.py ROM OUT"""
import ctypes
import struct
import sys
from collections import Counter
from pathlib import Path

import menu_shots as M
from snes_ronbarr_check import vram, tile_colours, BACKCHARS

BG = {"BG1": (0x0000, 0x2000), "BG2": (0x0400, 0x1000)}   # map base, tile base (words): LoadScoutingScreen


def cells(vr, name):
    mapw, tilew = BG[name]
    return [[struct.unpack_from("<H", vr, 2 * mapw + 2 * (32 * y + x))[0] for x in range(32)] for y in range(28)]


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    e = M.emulator(rom)
    M.play(e, "w1500 START w240 START w240 w60 START w240", out)
    e.run(4, hold=["START"])
    back = None
    picture, bg1, bg2_other, bg2_words = set(), Counter(), Counter(), Counter()
    samples = 0
    for k in range(126):
        e.run(30)
        if k < 6:
            continue        # the first 180 frames: still fading in, the video memory partly the last screen's
        vr = vram(e)
        back = e.w(BACKCHARS)
        c1, c2 = cells(vr, "BG1"), cells(vr, "BG2")
        samples += 1
        for y in range(28):
            for x in range(32):
                w1, w2 = c1[y][x], c2[y][x]
                if {c for c in tile_colours(vr, BG["BG1"][1], w1 & 0x3FF) if c}:
                    bg1[(x, y)] += 1
                t2, pal2 = w2 & 0x3FF, (w2 >> 10) & 7
                if t2 >= back and pal2 == 2:
                    picture.add((x, y))
                elif t2 >= back:
                    bg2_other[(x, y)] += 1
                bg2_words[(x, y, w2 & 0x3FF if t2 < back else -1)] += 1
        if k in (6, 10, 20, 40, 80, 125):
            e.screenshot(out / f"shot_{30 * (k + 1)}.png")
    print(f"{samples} samples, every 30 frames; backchars {back}")
    xs, ys = [x for x, _ in picture], [y for _, y in picture]
    print(f"Ron Barr's cells: {len(picture)}, columns {min(xs)}-{max(xs)}, rows {min(ys)}-{max(ys)}")
    # what the background tiles (below backchars) are in the bottom-right: the menu background repeats, a frame doesn't
    print("BG1 cells ever drawn in rows 12-27 (row: columns):")
    for y in range(12, 28):
        row = sorted(x for (x, yy) in bg1 if yy == y)
        if row:
            print(f"  row {y:2d}: {row}")
    print("BG2 cells on tiles after the menu background other than the picture:", sorted(bg2_other)[:40] or "none")
    # BG2 cells below backchars inside the picture's box: which tiles (the frame, if any, is among them)
    box = [(x, y) for y in range(min(ys), max(ys) + 1) for x in range(min(xs), max(xs) + 1)]
    plain = Counter()
    for (x, y, t), n in bg2_words.items():
        if (x, y) in box and t >= 0:
            plain[t] += 1
    print("BG2 tiles (menu background / frame) in the picture's box, cells x samples:", plain.most_common(12))
    # the largest rectangle in rows 12-27 x columns 0-31 with no BG1 drawing ever
    free = [[(x, y) not in bg1 for x in range(32)] for y in range(28)]
    best = (0, None)
    for y0 in range(12, 28):
        for y1 in range(y0, 28):
            for x0 in range(32):
                for x1 in range(x0, 32):
                    if all(free[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)):
                        a = (y1 - y0 + 1) * (x1 - x0 + 1)
                        if a > best[0]:
                            best = (a, (x0, y0, x1, y1))
                    else:
                        break
    a, (x0, y0, x1, y1) = best
    print(f"largest rectangle in rows 12-27 that BG1 never draws in: columns {x0}-{x1}, rows {y0}-{y1} ({x1 - x0 + 1} x {y1 - y0 + 1} = {a} cells)")
    # within the picture's own columns and rows
    best = (0, None)
    for y0 in range(min(ys), max(ys) + 1):
        for y1 in range(y0, max(ys) + 1):
            for x0 in range(min(xs), max(xs) + 1):
                for x1 in range(x0, max(xs) + 1):
                    if all(free[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)):
                        a = (y1 - y0 + 1) * (x1 - x0 + 1)
                        if a > best[0]:
                            best = (a, (x0, y0, x1, y1))
                    else:
                        break
    a, (x0, y0, x1, y1) = best
    print(f"largest such rectangle inside Ron Barr's box (columns {min(xs)}-{max(xs)}, rows {min(ys)}-{max(ys)}): columns {x0}-{x1}, "
          f"rows {y0}-{y1} ({x1 - x0 + 1} x {y1 - y0 + 1} = {a} cells)")


if __name__ == "__main__":
    main()
