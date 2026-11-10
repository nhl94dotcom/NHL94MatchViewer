"""NOSE4Web's Game Setup backgrounds against retail (Genesis, 2026-11-09; the picture's address at $F823C), from
gen_setup_screen.py's output folders (its states, screenshots and background masks, logos up "setup" and a player card
up "card"):
- clean: every pixel the background doesn't decide (retail's mask) compared with retail's: any difference is a mark on
  the cards, logos, banners, menu or lettering; and whether the masks are the same;
- bars (a colour test ROM): each background pixel's (palette line, colour) from video memory against the screenshot
  and the ROM's palette words (GameSetUpMap's palette data, 0BGR);
- grid: the 40 x 28 cells whose background never shows in either state (retail's masks), each marked by what covers it
  there: '#' a fixed piece (the top strip, the logo box frame) or a team banner (no banner tile of any team has a
  colour-0 pixel: checked), '+' a logo's or a player photo's pixels (another team or player may leave gaps), '.' the
  background shows.

python gen_setup_compare.py RETAIL_DIR [clean DIR ...] [bars DIR COLOUR_ROM] [grid]"""
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

import gen_setup_screen as S
from gen_score_logo_check import VRAM_AT

TAGS = ("setup", "card")


def load(d, tag):
    st = (d / f"{tag}.state").read_bytes()
    return (st[VRAM_AT:VRAM_AT + 0x10000], st[VRAM_AT + 0x10100:VRAM_AT + 0x10120],
            Image.open(d / f"{tag}_as_is.png").convert("RGB"), Image.open(d / f"{tag}_background_shows.png").convert("L"),
            json.loads((d / f"{tag}.json").read_text()))


def clean(retail, d):
    for tag in TAGS:
        _, _, ra, rm, _ = load(retail, tag)
        _, _, pa, pm, _ = load(d, tag)
        masks = sum(1 for x in range(320) for y in range(224) if (rm.getpixel((x, y)) > 0) != (pm.getpixel((x, y)) > 0))
        bad = sum(1 for x in range(320) for y in range(224) if not rm.getpixel((x, y)) and ra.getpixel((x, y)) != pa.getpixel((x, y)))
        print(f"{d.name} {tag}: masks differ at {masks} px; pixels outside the background differing from retail: {bad}")


def bars(d, rom):
    data = Path(rom).read_bytes()
    g = struct.unpack(">I", data[S.GAMESETUPMAP_PTR:S.GAMESETUPMAP_PTR + 4])[0]
    pal = g + struct.unpack(">I", data[g:g + 4])[0]
    palw = [struct.unpack(">H", data[pal + 2 * i:pal + 2 * i + 2])[0] for i in range(64)]
    for tag in TAGS:
        vr, reg, shot, mask, _ = load(d, tag)
        plane_b = (reg[4] & 7) << 13
        seen = defaultdict(lambda: defaultdict(int))
        for cy in range(28):
            for cx in range(40):
                v = S.vword(vr, plane_b + 2 * (64 * cy + cx))
                line, px = (v >> 13) & 3, S.tile_pixels(vr, v & 0x7FF)
                for r in range(8):
                    for c in range(8):
                        idx = px[(7 - r if v & 0x1000 else r) * 8 + (7 - c if v & 0x800 else c)]
                        x, y = cx * 8 + c, cy * 8 + r
                        if mask.getpixel((x, y)):
                            seen[(0, 0) if idx == 0 else (line, idx)][shot.getpixel((x, y))] += 1
        bad = []
        for k, cols in seen.items():
            w = palw[16 * k[0] + k[1]]
            got = max(cols, key=cols.get)
            if tuple(round(c / 34) for c in got) != ((w >> 1) & 7, (w >> 5) & 7, (w >> 9) & 7) or len(cols) > 1:
                bad.append(k)
        print(f"{tag}: {len(seen)} (line, colour) pairs shown (the backdrop included), "
              f"{len({max(c, key=c.get) for c in seen.values()})} distinct colours; not as the ROM's palette: {bad}")
        print("   ", sorted(seen))


def grid(retail):
    hidden, team = {}, defaultdict(bool)
    for tag in TAGS:
        vr, reg, _, mask, j = load(retail, tag)
        b = {k: int(v, 16) for k, v in j["bases"].items()}
        plane_a = (reg[2] & 0x38) << 10
        pics = [(b["vispicchars"], b["vispicchars"] + 0x24), (b["homepicchars"], b["logobox1chars"])]
        for cy in range(28):
            for cx in range(40):
                shows = any(mask.getpixel((cx * 8 + c, cy * 8 + r)) for r in range(8) for c in range(8))
                hidden[(cx, cy)] = hidden.get((cx, cy), True) and not shows
                t = S.vword(vr, plane_a + 2 * (64 * cy + cx)) & 0x7FF
                team[(cx, cy)] |= any(lo <= t < hi for lo, hi in pics)
    rows = ["".join(("+" if team[(cx, cy)] else "#") if hidden[(cx, cy)] else "." for cx in range(40)) for cy in range(28)]
    print(f"never shows: {sum(hidden.values())} cells ({sum(1 for k in hidden if hidden[k] and not team[k])} '#', "
          f"{sum(1 for k in hidden if hidden[k] and team[k])} '+')")
    print("\n".join(rows))


def main():
    retail = Path(sys.argv[1])
    args = sys.argv[2:]
    while args:
        what = args.pop(0)
        if what == "clean":
            while args and args[0] not in ("bars", "grid"):
                clean(retail, Path(args.pop(0)))
        elif what == "bars":
            bars(Path(args.pop(0)), args.pop(0))
        elif what == "grid":
            grid(retail)


if __name__ == "__main__":
    main()
