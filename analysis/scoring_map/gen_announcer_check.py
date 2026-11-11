"""NOSE4Web's announcer picture on the Genesis matchup screen, against the original (2026-11-10, for NOSE4Web 2e0aedb:
nhl94_announcer.bin, a test picture in Ron Barr's place). Both ROMs are taken to the matchup screen the same way
(gen_ronbarr_check's presses) and compared from the core's video memory (gen_score_logo_check.VRAM_AT): every plane A
and plane B cell outside Ron Barr's area (cells (1,1) on, the original map's size), the tile data each of those cells and
every sprite on screen shows (so the hot / cold icons whose tiles come after the picture's), the colour memory line by
line, and the sprite list. The ROM side: where ScoutingReport's movea points, the block's header (palette and map
offsets, the tiles' count word and its bit 15), the map's size and the tiles and palette lines its cells use. The
picture's cells are cropped from each screenshot (picture_<rom>.png, 4x) to see its way round and colours.

python gen_announcer_check.py ORIGINAL NEW OUT"""
import struct
import sys
from pathlib import Path

from PIL import Image

import menu_shots as M
from gen_ronbarr_check import rom_side
from gen_setup_screen import state, vword, tile_pixels

PRESSES = "w900 START w120 START w120 w60"


def capture(rom, out, tag):
    info = rom_side(Path(rom).read_bytes())
    e = M.emulator(rom)
    M.play(e, PRESSES, out)
    e.run(4, hold=["START"])
    e.run(200)
    shot = out / f"matchup_{tag}.png"
    e.screenshot(shot)
    st, vr, cram, reg = state(e)
    # the matchup pages after the first (the page turns every $10E frames): 1-6 are the players, with the hot / cold icon
    # (HotColdIcon, at row $19) under a hot or cold one; a screenshot of each, and the video memory of the last
    pages = []
    for k in range(1, 8):
        e.run(270)
        pages.append(out / f"page{k}_{tag}.png")
        e.screenshot(pages[-1])
    vr_late = state(e)[1]
    return info, shot, vr, cram, reg, pages, vr_late


def planes(reg):
    size = reg[16]
    width = (32, 64, 32, 128)[size & 3]
    return (("plane A", (reg[2] & 0x38) << 10), ("plane B", (reg[4] & 7) << 13)), width, (reg[5] & 0x7F) << 9


def sprite_list(vr, sat):
    out, k, seen = [], 0, set()
    while k not in seen and len(seen) < 80:
        seen.add(k)
        w4 = [vword(vr, sat + 8 * k + 2 * j) for j in range(4)]
        sz, link = w4[1] >> 8, w4[1] & 0x7F
        x, y = (w4[3] & 0x1FF) - 128, (w4[0] & 0x3FF) - 128
        if -32 < x < 320 and -32 < y < 224:
            out.append((x, y, sz, w4[2]))
        if not link:
            break
        k = link
    return out


def tile_bytes(vr, t):
    return bytes(vr[32 * t:32 * t + 32])


def main():
    orig, new, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    A = capture(orig, out, "original")
    B = capture(new, out, "new")
    for tag, (info, *_ ) in (("original", A), ("new", B)):
        rom = Path(orig if tag == "original" else new).read_bytes()
        cnt = struct.unpack(">H", rom[info["at"] + 8:info["at"] + 10])[0]
        print(f"{tag}: ScoutingReport's movea at ${info['code']:X} -> block ${info['at']:X}; palette +${info['pal_off']:X}, map "
              f"+${info['map_off']:X}; word after the header ${cnt:04X} (bit 15 {'set: packed' if cnt & 0x8000 else 'clear: unpacked'}); "
              f"map {info['map_w']} x {info['map_h']}; tiles {info['tiles_distinct']} distinct, numbered to {info['tiles_max'] - 1}; "
              f"palette lines in the map {info['lines_in_map']}")
    (ia, sa, va, ca, ra, pga, vla), (ib, sb, vb, cb, rb, pgb, vlb) = A, B
    (pa, width, sat_a), (_, _, sat_b) = planes(ra), planes(rb)
    if ra[:19] != rb[:19]:
        print("video registers differ:", [(i, ra[i], rb[i]) for i in range(19) if ra[i] != rb[i]])
    mw, mh = ia["map_w"], ia["map_h"]
    inside = lambda name, x, y: name == "plane A" and 1 <= x < 1 + mw and 1 <= y < 1 + mh
    # cells outside the picture: the same map word, and the same tile data behind it
    word_diff, data_diff, tiles_outside = [], [], set()
    for name, base in pa:
        for y in range(28):
            for x in range(40):
                if inside(name, x, y):
                    continue
                wa, wb = vword(va, base + 2 * (y * width + x)), vword(vb, base + 2 * (y * width + x))
                if wa != wb:
                    word_diff.append((name, x, y, f"{wa:04x}", f"{wb:04x}"))
                    continue
                t = wa & 0x7FF
                tiles_outside.add(t)
                if tile_bytes(va, t) != tile_bytes(vb, t):
                    data_diff.append((name, x, y, t))
    print(f"cells outside the picture ({mw} x {mh} from (1,1) on plane A): {2 * 40 * 28 - mw * mh} compared; map words differing: "
          f"{len(word_diff)} {word_diff[:12]}; same word but different tile data: {len(data_diff)} {data_diff[:12]}")
    # the picture's own cells
    pic_a = sorted({vword(va, pa[0][1] + 2 * (y * width + x)) & 0x7FF for y in range(1, 1 + mh) for x in range(1, 1 + mw)})
    pic_b = sorted({vword(vb, pa[0][1] + 2 * (y * width + x)) & 0x7FF for y in range(1, 1 + mh) for x in range(1, 1 + mw)})
    lines_b = sorted({vword(vb, pa[0][1] + 2 * (y * width + x)) >> 13 & 3 for y in range(1, 1 + mh) for x in range(1, 1 + mw)})
    print(f"picture cells: original tiles {pic_a[0]}-{pic_a[-1]} ({len(pic_a)} distinct); new {pic_b[0]}-{pic_b[-1]} "
          f"({len(pic_b)} distinct), palette lines {lines_b}; picture tiles also used outside it: "
          f"{sorted(set(pic_b) & tiles_outside)[:12] or 'none'}")
    # sprites (the hot / cold icons and anything else): same list, same tile data
    spa, spb = sprite_list(va, sat_a), sprite_list(vb, sat_b)
    print(f"sprites on screen: original {len(spa)}, new {len(spb)}; lists the same: {spa == spb}")
    bad = []
    for (x, y, sz, attr) in spb:
        n = (((sz >> 2) & 3) + 1) * ((sz & 3) + 1)
        t0 = attr & 0x7FF
        for t in range(t0, t0 + n):
            if tile_bytes(va, t) != tile_bytes(vb, t):
                bad.append((x, y, t))
    print(f"  sprite tiles: {sum((((s[2] >> 2) & 3) + 1) * ((s[2] & 3) + 1) for s in spb)} shown, different from the original: {bad[:12] or 'none'}"
          f"; tile numbers {sorted({s[3] & 0x7FF for s in spb})}")
    # tile memory after the picture's tiles (the hot / cold icons in the original sit there)
    top = max(pic_a[-1], pic_b[-1]) + 1
    after = [t for t in range(top, top + 96) if tile_bytes(va, t) != tile_bytes(vb, t)]
    print(f"tiles {top}-{top + 95} (after the picture's): different from the original: {after[:20] or 'none'}")
    # the hot / cold icons: loaded straight after the picture's tiles (hoticonchars, coldiconchars = d4 after dobitmap), so
    # they move with the picture's tile count; their data at the new place against the original's
    na, nb = pic_a[-1] + 1, pic_b[-1] + 1
    same = 0
    for k in range(96):
        if tile_bytes(vla, na + k) == tile_bytes(vlb, nb + k):
            same += 1
        else:
            break
    print(f"tiles after the picture: original from {na}, new from {nb}; the first {same} are the same data in both (the hot and cold icons' tiles)")
    # every matchup page, outside the picture, pixel for pixel
    for k, (a, b) in enumerate(zip(pga, pgb), 1):
        ia_, ib_ = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
        sx, sy = ia_.width / 320, ia_.height / 224
        d = sum(ia_.getpixel((x, y)) != ib_.getpixel((x, y)) for y in range(ia_.height) for x in range(ia_.width)
                if not (8 * sx <= x < 8 * (1 + mw) * sx and 8 * sy <= y < 8 * (1 + mh) * sy))
        icon = sum(ia_.getpixel((x, y)) != (0, 0, 0) for y in range(int(200 * sy), int(224 * sy)) for x in range(ia_.width)) if False else None
        print(f"matchup page {k}: screenshot pixels outside the picture that differ: {d}")
    # colours
    words = lambda c: [c[2 * i] | c[2 * i + 1] << 8 for i in range(64)]
    wa, wb = words(ca), words(cb)
    for line in range(4):
        d = [(i, f"{wa[16 * line + i]:03x}", f"{wb[16 * line + i]:03x}") for i in range(16) if wa[16 * line + i] != wb[16 * line + i]]
        print(f"colour line {line}: {'same' if not d else d}")
    # the picture cropped from each screenshot
    for tag, shot in (("original", sa), ("new", sb)):
        im = Image.open(shot).convert("RGB")
        sx, sy = im.width / 320, im.height / 224
        box = (int(8 * sx), int(8 * sy), int(8 * (1 + mw) * sx), int(8 * (1 + mh) * sy))
        crop = im.crop(box)
        crop.resize((crop.width * 4, crop.height * 4), Image.NEAREST).save(out / f"picture_{tag}.png")
        if tag == "new":
            w, h = crop.size
            pick = lambda fx, fy: crop.getpixel((int(w * fx), int(h * fy)))
            print("new picture, sampled colours (RGB): top-left", pick(0.3, 0.25), "top-right", pick(0.7, 0.25),
                  "bottom-left", pick(0.3, 0.75), "bottom-right", pick(0.7, 0.75), "middle", pick(0.5, 0.5))
    # the rest of the screen, picture area blanked, pixel for pixel
    ima, imb = Image.open(sa).convert("RGB"), Image.open(sb).convert("RGB")
    sx, sy = ima.width / 320, ima.height / 224
    diff = 0
    for y in range(ima.height):
        for x in range(ima.width):
            if 8 * sx <= x < 8 * (1 + mw) * sx and 8 * sy <= y < 8 * (1 + mh) * sy:
                continue
            diff += ima.getpixel((x, y)) != imb.getpixel((x, y))
    print(f"screenshot pixels outside the picture that differ: {diff}")


if __name__ == "__main__":
    main()
