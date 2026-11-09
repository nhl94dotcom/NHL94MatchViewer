"""The Genesis Game Setup screen's video memory (2026-11-09, for NOSE4Web's custom setup background question). On a
ROM (retail: nhl94.bin), power-on to Game Setup, a few seconds for the team blocks and logos; then from the core's
saved state (gen_score_logo_check.VRAM_AT: VRAM, colour memory, VDP registers):
- the tile ranges setoptions hands out from d4 (the RAM bases framercset ... logobox2chars; the background's tiles
  run from the setup font's end to vispicchars), the highest tile anything uses, and the planes, window, sprite
  table and scroll table (VDP registers 2, 3, 4, 5, 13);
- for each piece (by tile range), the (palette line, colour) pairs its cells and sprites draw with;
- the palette lines GameSetUpMap's data holds (lines 0, 2, 3: dobitmap's d5 = $D) against colour memory now;
- screenshots: the screen as it is, with the background's tiles blanked (all colour 0), and with them filled with
  colour 1, and the share of the screen whose pixels the background's tiles decide.
A player card is then waited for (setupcardflags bit 0: the byte at $D42E, the word's high byte) and the same done again.

python gen_setup_screen.py ROM OUT"""
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

from emu import Emu
from gen_score_logo_check import VRAM_AT

VARS = {"teambitmapchars": None, "framercset": 0xB01E, "smallfontchars": 0xB012, "setupfontchars": 0xBF52,
        "vispicchars": 0xD432, "setupmenuchars": 0xD426, "homepicchars": 0xD430, "logobox1chars": 0xD436,
        "logobox2chars": 0xD438}
CARDFLAGS = 0xD42E
GAMESETUPMAP = 0x4B7A0


def state(e):
    st = bytearray(e.serialize())
    vr = st[VRAM_AT:VRAM_AT + 0x10000]
    cram = st[VRAM_AT + 0x10000:VRAM_AT + 0x10080]
    reg = st[VRAM_AT + 0x10100:VRAM_AT + 0x10120]
    return st, vr, cram, reg


def vword(vr, a):
    a &= 0xFFFF
    return vr[a] | vr[a + 1] << 8          # the state keeps VRAM as little-endian words


def tile_pixels(vr, t):
    """Colour indexes of tile t's 64 pixels (big-endian nibbles within each word; the state's words are swapped)."""
    out = []
    for r in range(8):
        for w in range(2):
            v = vword(vr, 32 * t + 4 * r + 2 * w)
            out += [(v >> 12) & 15, (v >> 8) & 15, (v >> 4) & 15, v & 15]
    return out


def layout(e, rom, out, tag):
    st, vr, cram, reg = state(e)
    base = {k: e.w(a) for k, a in VARS.items() if a}
    # teambitmapchars: LoadSetupTiles starts at 2; the remapped copy starts where the plain one ended
    pieces = []
    order = [("team banners (TeamBitmaps, plain)", 2, None), ("team banners (remapped)", None, "framercset"),
             ("frame (SetupFramerMap)", "framercset", "smallfontchars"),
             ("small font", "smallfontchars", "setupfontchars"),
             ("setup font (PrintFont2Map)", "setupfontchars", None),
             ("background (GameSetUpMap)", None, "vispicchars"),
             ("visitors' picture space (36)", "vispicchars", None),
             ("top strip (GameSetUpMap2)", None, "setupmenuchars"),
             ("menu box (SetupMenuMap)", "setupmenuchars", "homepicchars"),
             ("home picture space (36)", "homepicchars", "logobox1chars"),
             ("logo box 1", "logobox1chars", "logobox2chars"),
             ("logo box 2", "logobox2chars", None)]
    # the unknown boundaries: the team banners' two copies are the same size; the background is 240 tiles
    # (GameSetUpMap's tile count, read from its data below); the strip starts 36 after vispicchars
    data = Path(rom).read_bytes()
    pal_off, map_off = struct.unpack(">II", data[GAMESETUPMAP:GAMESETUPMAP + 8])
    span = (base["framercset"] - 2) // 2
    b = {"tb2": 2 + span, "bg0": None, "strip0": base["vispicchars"] + 0x24,
         "lb2end": base["logobox2chars"] + (base["logobox2chars"] - base["logobox1chars"])}
    # the background's first tile: the lowest tile number its map uses (map words + d4)
    mw, mh = struct.unpack(">HH", data[GAMESETUPMAP + map_off:GAMESETUPMAP + map_off + 4])
    words = struct.unpack(f">{mw * mh}H", data[GAMESETUPMAP + map_off + 4:GAMESETUPMAP + map_off + 4 + 2 * mw * mh])
    tiles_in_map = max(w & 0x7FF for w in words) + 1
    b["bg0"] = base["vispicchars"] - tiles_in_map
    ranges = [("team banners (TeamBitmaps, plain)", 2, b["tb2"]),
              ("team banners (remapped)", b["tb2"], base["framercset"]),
              ("frame (SetupFramerMap)", base["framercset"], base["smallfontchars"]),
              ("small font", base["smallfontchars"], base["setupfontchars"]),
              ("setup font (PrintFont2Map)", base["setupfontchars"], b["bg0"]),
              ("background (GameSetUpMap)", b["bg0"], base["vispicchars"]),
              ("visitors' picture space", base["vispicchars"], b["strip0"]),
              ("top strip (GameSetUpMap2)", b["strip0"], base["setupmenuchars"]),
              ("menu box (SetupMenuMap)", base["setupmenuchars"], base["homepicchars"]),
              ("home picture space", base["homepicchars"], base["logobox1chars"]),
              ("logo box 1", base["logobox1chars"], base["logobox2chars"]),
              ("logo box 2", base["logobox2chars"], b["lb2end"])]
    piece_of = {}
    for name, lo, hi in ranges:
        for t in range(lo, hi):
            piece_of[t] = name
    planeA, window, planeB = (reg[2] & 0x38) << 10, (reg[3] & 0x3E) << 10, (reg[4] & 7) << 13
    sat, hscroll = (reg[5] & 0x7F) << 9, (reg[13] & 0x3F) << 10
    size = reg[16]
    width, height = (32, 64, 32, 128)[size & 3], (32, 64, 32, 128)[(size >> 4) & 3]
    used = defaultdict(set)              # piece -> {(line, colour)}
    cells = defaultdict(lambda: defaultdict(int))
    hi_used = 0
    for pname, pbase, w, h in (("plane A", planeA, width, height), ("plane B", planeB, width, height),
                               ("window", window, 64 if reg[12] & 1 else 32, 32)):
        for i in range(w * h):
            v = vword(vr, pbase + 2 * i)
            t, line = v & 0x7FF, (v >> 13) & 3
            if t == 0x7FF or t == 0:
                continue
            hi_used = max(hi_used, t)
            piece = piece_of.get(t, f"other tile {t:#x}")
            cells[pname][piece] += 1
            for c in set(tile_pixels(vr, t)):
                if c:
                    used[piece].add((line, c))
    k, seen, sprites = 0, 0, []
    while seen < 80:
        a = sat + 8 * k
        w = [vword(vr, a + 2 * j) for j in range(4)]
        sz, link = w[1] >> 8, w[1] & 0x7F
        t0, line = w[2] & 0x7FF, (w[2] >> 13) & 3
        n = (((sz >> 2) & 3) + 1) * ((sz & 3) + 1)
        if w[0] or w[3]:
            sprites.append((t0, n, line, (w[3] & 0x1FF) - 128, (w[0] & 0x3FF) - 128))
            for t in range(t0, t0 + n):
                hi_used = max(hi_used, t)
                piece = "sprite: " + piece_of.get(t, f"tile {t:#x}")
                for c in set(tile_pixels(vr, t)):
                    if c:
                        used[piece].add((line, c))
        seen += 1
        if link == 0:
            break
        k = link
    nonzero = [t for t in range(2048) if any(vr[32 * t:32 * t + 32])]
    rgb = lambda v: f"{v:03x}"
    cramw = [cram[2 * i] | cram[2 * i + 1] << 8 for i in range(64)]
    palrom = [struct.unpack(">H", data[GAMESETUPMAP + pal_off + 2 * i:GAMESETUPMAP + pal_off + 2 * i + 2])[0]
              for i in range(64)]
    res = {"bases": {k: hex(v) for k, v in base.items()}, "background first tile": hex(b["bg0"]),
           "background tiles (map)": tiles_in_map, "end of d4 tiles": hex(b["lb2end"]),
           "highest tile drawn": hex(hi_used), "highest non-zero tile": hex(nonzero[-1]) if nonzero else None,
           "non-zero tiles above end": [hex(t) for t in nonzero if t >= b["lb2end"]][:20],
           "plane A": hex(planeA), "plane B": hex(planeB), "window": hex(window), "sprite table": hex(sat),
           "hscroll": hex(hscroll), "reg11 (scroll modes)": hex(reg[11]), "backdrop (reg 7)": hex(reg[7]), "plane size": f"{width}x{height}", "reg12": hex(reg[12]),
           "window regs 17/18": (hex(reg[17]), hex(reg[18])),
           "cells by plane and piece": {p: dict(v) for p, v in cells.items()},
           "colours used (line, index)": {p: sorted(v) for p, v in sorted(used.items())},
           "sprites": sprites,
           "colour memory now": [" ".join(rgb(v) for v in cramw[16 * l:16 * l + 16]) for l in range(4)],
           "GameSetUpMap palette data": [" ".join(rgb(v) for v in palrom[16 * l:16 * l + 16]) for l in range(4)]}
    (out / f"{tag}.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ("sprites",)}, indent=1), flush=True)
    # screenshots: as is, background tiles blanked, background tiles filled with colour 1
    e.screenshot(out / f"{tag}_as_is.png")
    shots = {}
    for name, fill in (("blank", 0), ("fill1", 0x1111)):
        st2 = bytearray(st)
        for t in range(b["bg0"], base["vispicchars"]):
            for j in range(16):
                a = VRAM_AT + 32 * t + 2 * j
                st2[a], st2[a + 1] = fill & 0xFF, fill >> 8
        e.unserialize(bytes(st2))
        e.run(1)
        e.screenshot(out / f"{tag}_{name}.png")
        shots[name] = out / f"{tag}_{name}.png"
    e.unserialize(bytes(st))
    try:
        from PIL import Image, ImageChops
        a = Image.open(shots["blank"]).convert("RGB")
        c = Image.open(shots["fill1"]).convert("RGB")
        diff = ImageChops.difference(a, c).convert("L").point(lambda v: 255 if v else 0)
        share = sum(1 for v in diff.getdata() if v) / (a.width * a.height)
        diff.save(out / f"{tag}_background_shows.png")
        print(f"{tag}: the background's tiles decide {share:.1%} of the screen's pixels ({a.width}x{a.height})",
              flush=True)
    except ImportError:
        pass


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    e.run(900)
    e.run(4, hold=["START"])
    e.run(120)
    e.run(4, hold=["START"])
    e.run(150)
    layout(e, rom, out, "setup")
    e.run(250)                            # the first player card is up by then (setup + 400 frames)
    layout(e, rom, out, "card")

if __name__ == "__main__":
    main()
