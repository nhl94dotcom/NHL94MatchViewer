"""The Genesis matchup screen's Ron Barr picture, measured (2026-11-10, for NOSE4Web's "replace Ron Barr with your own
picture"). From the ROM: RonBarrMap (found by ScoutingReport's `movea.l #RonBarrMap,a0` / ... / `move.w (a1),d2`):
its palette and map offsets, the packed tiles' size, the palette's lines, the map's size, the tiles and palette bits its
cells use. In the game (retail nhl94.bin, the matchup screen after Game Setup): video memory from the core's state
(gen_score_logo_check.VRAM_AT): the cells ScoutingReport drew from it (cell (1,1) on, the map's size), the colours
its tiles use on each line, the colour memory, and every other cell and sprite on the screen by palette line, with
the colours it uses, and any that use Ron Barr's tiles.

python gen_ronbarr_check.py ROM OUT"""
import re
import struct
import sys
from collections import defaultdict
from pathlib import Path

import menu_shots as M
from gen_setup_screen import state, vword, tile_pixels


def rom_side(data):
    # ScoutingReport's: the bitmap drawn with its own size (move.w (a1),d2 / move.w mapheight(a1),d3) on colour lines 2-3
    # (moveq #$C,d5); other screens load bitmaps with the same opening (2026-11-10: the first match was a 40 x 28 one)
    m = re.search(rb"\x20\x7C(.{4})\x22\x48\x24\x48\xD1\xDA\xD3\xDA\x42\x40\x42\x41\x34\x11\x36\x29\x00\x02\x7A\x0C", data, re.S)
    at = struct.unpack(">I", m.group(1))[0]
    pal_off, map_off = struct.unpack(">II", data[at:at + 8])
    mw, mh = struct.unpack(">HH", data[at + map_off:at + map_off + 4])
    words = struct.unpack(f">{mw * mh}H", data[at + map_off + 4:at + map_off + 4 + 2 * mw * mh])
    tiles = sorted({w & 0x7FF for w in words})
    pal = [struct.unpack(">16H", data[at + pal_off + 32 * k:at + pal_off + 32 * k + 32]) for k in range(4)]
    return dict(code=m.start(), at=at, pal_off=pal_off, map_off=map_off, packed=pal_off - 8 if pal_off < map_off else
                map_off - 8, map_w=mw, map_h=mh, map_bytes=4 + 2 * mw * mh, tiles_max=max(tiles) + 1,
                tiles_distinct=len(tiles), lines_in_map=sorted({(w >> 13) & 3 for w in words}),
                flags=sorted({w >> 11 & 0x1F for w in words}), pal=pal, words=words)


def screen(e, out, info):
    st, vr, cram, reg = state(e)
    planeA, planeB = (reg[2] & 0x38) << 10, (reg[4] & 7) << 13
    window = (reg[3] & 0x3E) << 10
    sat = (reg[5] & 0x7F) << 9
    size = reg[16]
    width, height = (32, 64, 32, 128)[size & 3], (32, 64, 32, 128)[(size >> 4) & 3]
    cramw = [cram[2 * i] | cram[2 * i + 1] << 8 for i in range(64)]
    res = dict(cram=[[f"{c:03x}" for c in cramw[16 * k:16 * k + 16]] for k in range(4)])
    ron_tiles, ron_cells = set(), []
    users = defaultdict(lambda: defaultdict(set))        # line -> where -> colours
    for pname, pbase, w, h in (("plane A", planeA, width, height), ("plane B", planeB, width, height)):
        for y in range(28):
            for x in range(40):
                v = vword(vr, pbase + 2 * (y * w + x))
                t, line = v & 0x7FF, (v >> 13) & 3
                cols = {c for c in tile_pixels(vr, t) if c}
                inside = 1 <= x < 1 + info["map_w"] and 1 <= y < 1 + info["map_h"]
                if pname == "plane A" and inside:
                    ron_tiles.add(t)
                    ron_cells.append((x, y, t, line))
                    users[line]["Ron Barr"] |= cols
                elif t and cols:
                    where = ("top" if y < 9 else "middle" if y < 18 else "bottom") + (" left" if x < 13 else " right" if x >= 27 else " centre")
                    users[line][f"{pname} {where}"] |= cols
    sprites = []
    k, seen = 0, set()
    while k not in seen and len(seen) < 80:
        seen.add(k)
        a = sat + 8 * k
        w4 = [vword(vr, a + 2 * j) for j in range(4)]
        sz, link = w4[1] >> 8, w4[1] & 0x7F
        t0, line = w4[2] & 0x7FF, (w4[2] >> 13) & 3
        n = (((sz >> 2) & 3) + 1) * ((sz & 3) + 1)
        x, y = (w4[3] & 0x1FF) - 128, (w4[0] & 0x3FF) - 128
        if -32 < x < 320 and -32 < y < 224:
            cols = set()
            for t in range(t0, t0 + n):
                cols |= {c for c in tile_pixels(vr, t) if c}
            sprites.append(dict(x=x, y=y, tile=t0, n=n, line=line, colours=sorted(cols), ron=bool(set(range(t0, t0 + n)) & ron_tiles)))
            users[line][f"sprite at ({x}, {y})"] |= cols
        if not link:
            break
        k = link
    res["ron_tiles"] = [min(ron_tiles), max(ron_tiles), len(ron_tiles)] if ron_tiles else None
    res["ron_lines"] = sorted({c[3] for c in ron_cells})
    res["users"] = {line: {k: sorted(v) for k, v in d.items()} for line, d in users.items()}
    res["sprites"] = sprites
    # other cells that show one of Ron Barr's tiles
    res["ron_tiles_elsewhere"] = []
    for pname, pbase in (("plane A", planeA), ("plane B", planeB)):
        for y in range(28):
            for x in range(40):
                t = vword(vr, pbase + 2 * (y * width + x)) & 0x7FF
                inside = pname == "plane A" and 1 <= x < 1 + info["map_w"] and 1 <= y < 1 + info["map_h"]
                if t in ron_tiles and not inside and t:
                    res["ron_tiles_elsewhere"].append((pname, x, y, t))
    return res


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    info = rom_side(Path(rom).read_bytes())
    print(f"RonBarrMap at ${info['at']:X} (ScoutingReport's movea at ${info['code']:X}): palette at +${info['pal_off']:X}, map at "
          f"+${info['map_off']:X}; packed tiles {info['packed']} bytes (from +8); map {info['map_w']} x {info['map_h']} cells "
          f"({info['map_bytes']} bytes); tiles used {info['tiles_distinct']} distinct, numbered to {info['tiles_max'] - 1}; "
          f"palette lines in the map words {info['lines_in_map']}, flag bits {info['flags']}")
    for k, line in enumerate(info["pal"]):
        print(f"  palette data line {k}: {' '.join(f'{c:03x}' for c in line)}")
    e = M.emulator(rom)
    M.play(e, "w900 START w120 START w120 w60", out)
    e.run(4, hold=["START"])
    e.run(200)
    e.screenshot(out / "matchup.png")
    res = screen(e, out, info)
    print("on screen: Ron Barr's cells", res["ron_tiles"], "(first tile, last, count) on palette lines", res["ron_lines"])
    print("colour memory:")
    for k, line in enumerate(res["cram"]):
        print(f"  line {k}: {' '.join(line)}")
    for line in sorted(res["users"]):
        print(f"line {line} colours used by:")
        for where, cols in sorted(res["users"][line].items()):
            print(f"    {where}: {cols}")
    print("Ron Barr's tiles elsewhere:", res["ron_tiles_elsewhere"][:20] or "none")
    print("sprites:", [(s["x"], s["y"], s["line"], s["n"]) for s in res["sprites"]])


if __name__ == "__main__":
    main()
