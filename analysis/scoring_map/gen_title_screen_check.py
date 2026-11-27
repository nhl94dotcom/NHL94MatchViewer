"""The Genesis title screen's video memory, NHL '94 and NHL '95 (2026-11-27, for NOSE4Web's title picture editor:
TitleScreenImg replaced by a copy in free room; which tiles, planes, palette rows and lines it may use).

From power-on, frame by frame, while TitleScreen runs (VBint = VBlank_TitleScreen; its address from the
`move.l #imm,(VBint).l` before the first `movea.l #TitleScreenImg,a0`, the instruction NOSE4Web's pointer is in:
NHL '94 $FF10C, NHL '95 $A1374, the operand 2 bytes on), from the core's saved state (gen_score_logo_check.VRAM_AT):
- the VDP registers (planes A / B, window, sprite table, scroll table, the window's split WINX / WINY, the scroll mode)
  each time they change;
- every tile index any plane cell (window, A, B: the whole name tables) or sprite names, and the highest tile whose
  VRAM is not all zero; the tiles each piece took (the picture, then the images after it, by the d4 each dobitmap
  passes on: TempWord1 / smallfontchars, and each image's own map), and the free run up to the first table;
- sprites: Sattsize when set, and the sprite table's visible entries (the link chain from entry 0);
- the colour memory: every distinct state and its first frame, and for each piece (by tile range) the (row, colour)
  pairs its cells draw with (the credits text: the small font);
- the line scroll table: for each screen line whether planes A / B are scrolled from 0 there during the slide-in, and
  which rows show the window (the window cells over the picture's rows);
- screenshots every 20 frames for the first 400, then every 300.
Then START (the title ends) and Game Setup is waited out until the demo starts and ends (does the title come back:
Opening2, not Opening), then a soft reset (retro_reset) back to the title: the title's VRAM, colours and screen against
the first time.

python gen_title_screen_check.py ROM OUT [94|95]"""
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from emu import Emu
from gen_score_logo_check import VRAM_AT

GAME = {"94": dict(ptr=(0xFF10C, 0xFF13E), VBint=0xB03A, Vcount=0xB03E, TempWord1=0xBF12, smallfontchars=0xB012,
                   Sattsize=0xC2E8, palfadenew=0xBD28, Vscroll=0xBD20),
        "95": dict(ptr=(0xA1374, 0xA13A6), VBint=0xAC52, Vcount=0xAC56, TempWord1=0xBB10, smallfontchars=0xAC16,
                   Sattsize=0xBEEE, palfadenew=0xB942, Vscroll=0xB93A)}


def rl(rom, a):
    return struct.unpack(">I", rom[a:a + 4])[0]


def rw(rom, a):
    return struct.unpack(">H", rom[a:a + 2])[0]


def title_layout(rom, g):
    """The handler's address and every image TitleScreen draws (movea.l #imm,a0 = $207C imm), in order."""
    p = g["ptr"][0]
    vb = next(rl(rom, a + 2) for a in range(p, p - 0x200, -2) if rw(rom, a) == 0x23FC)
    imgs = []
    a = p
    while a < p + 0x200 and len(imgs) < 6:
        if rw(rom, a) == 0x207C:
            imgs.append((a + 2, rl(rom, a + 2)))
        a += 2
    seen, out = set(), []
    for at, img in imgs:
        if img in seen:
            continue
        seen.add(img)
        if img + 8 > len(rom) or rl(rom, img) > 0x20000 or rl(rom, img + 4) > 0x20000:
            continue                                  # not a picture (the sound driver's program on NHL '95)
        pal, mp = img + rl(rom, img), img + rl(rom, img + 4)
        wd, ht = rw(rom, mp), rw(rom, mp + 2)
        if not (0 < wd <= 64 and 0 < ht <= 32):
            continue
        words = [rw(rom, mp + 4 + 2 * i) for i in range(wd * ht)]
        out.append(dict(ptr_at=f"${at:X}", img=f"${img:X}", w=wd, h=ht, maxtile=max(x & 0x7FF for x in words),
                        pal=[rw(rom, pal + 2 * i) for i in range(64)]))
    return vb, out


def state(e):
    st = bytes(e.serialize())
    vr = np.frombuffer(st[VRAM_AT:VRAM_AT + 0x10000], dtype="<u2")        # VRAM words (the state's little-endian)
    cram = [st[VRAM_AT + 0x10000 + 2 * i] | st[VRAM_AT + 0x10001 + 2 * i] << 8 for i in range(64)]
    reg = list(st[VRAM_AT + 0x10100:VRAM_AT + 0x10120])
    vs = [st[VRAM_AT + 0x10080 + 2 * i] | st[VRAM_AT + 0x10081 + 2 * i] << 8 for i in range(2)]
    return vr, cram, reg, vs


def gen_word(v9):
    r, g, b = v9 & 7, v9 >> 3 & 7, v9 >> 6 & 7
    return b << 9 | g << 5 | r << 1


def tables(reg):
    h40 = reg[12] & 0x81 == 0x81
    sz = {0: 32, 1: 64, 3: 128}
    pw, ph = sz.get(reg[16] & 3, 32), sz.get(reg[16] >> 4 & 3, 32)
    return dict(A=(reg[2] & 0x38) << 10, W=(reg[3] & (0x3C if h40 else 0x3E)) << 10, B=(reg[4] & 7) << 13,
                SAT=(reg[5] & (0x7E if h40 else 0x7F)) << 9, HS=(reg[13] & 0x3F) << 10, pw=pw, ph=ph, h40=h40,
                winx=reg[17], winy=reg[18], mode3=reg[11], wwidth=64 if h40 else 32)


def cells(vr, base, w, h):
    return [int(vr[(base >> 1) + i]) for i in range(w * h)]


def tile_cols(vr, t):
    out = set()
    for i in range(16):
        v = int(vr[(32 * t >> 1) + i])
        out |= {v >> 12 & 15, v >> 8 & 15, v >> 4 & 15, v & 15}
    return out


def sprites(vr, sat):
    out, link, n = [], 0, 0
    while n < 80:
        o = (sat >> 1) + 4 * link
        y, sl, nm, x = (int(vr[o + k]) for k in range(4))
        out.append(dict(i=link, y=y & 0x3FF, x=x & 0x1FF, size=sl >> 8 & 15, tile=nm & 0x7FF, pal=nm >> 13 & 3))
        link = sl & 0x7F
        n += 1
        if link == 0:
            break
    return out


def main():
    rom_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    ver = sys.argv[3] if len(sys.argv) > 3 else ("95" if "95" in rom_path.name else "94")
    g = GAME[ver]
    out.mkdir(parents=True, exist_ok=True)
    rom = rom_path.read_bytes()
    vb, imgs = title_layout(rom, g)
    e = Emu(str(rom_path))
    R = dict(rom=rom_path.name, ver=ver, handler=f"${vb:X}", images=imgs, regs=[], cram=[], sprites=[])
    plane_tiles = defaultdict(set)
    hiwritten = 0
    lastreg = None
    lastcram = None
    vsmax = [0, 0]                  # the largest vertical scroll of planes A and B seen
    hs_moving = defaultdict(set)    # screen line -> {"A", "B"} scrolled away from 0 at some frame
    f = 0
    started = None
    first = None
    vc0 = tw = 0
    for f in range(4000):
        e.run(1)
        if (e.l(g["VBint"]) & 0xFFFFFF) != vb:
            if started is not None:
                break
            continue
        if started is None:
            started, vc0, tw = f, e.w(g["Vcount"]), 0
        if "d4" not in R:                  # TitleScreen keeps the picture's end (d4) in TempWord1 while it sets up
            tw = e.w(g["TempWord1"]) or tw
        if "d4" not in R and e.w(g["Vcount"]) != vc0:      # the first frame with interrupts on: set up
            R["setup_done"] = f
            R["d4"] = dict(picture_end=tw, smallfontchars=e.w(g["smallfontchars"]))
        vr, cram, reg, vs = state(e)
        vsmax = [max(a, b & 0x3FF) for a, b in zip(vsmax, vs)]
        T = tables(reg)
        if reg[:24] != lastreg:
            R["regs"].append(dict(frame=f, **{k: (f"${v:X}" if isinstance(v, int) and k not in ("pw", "ph", "winx", "winy", "mode3", "wwidth") else v) for k, v in T.items()}, raw=[f"{x:02X}" for x in reg[:24]]))
            lastreg = reg[:24]
        if cram != lastcram:
            R["cram"].append(dict(frame=f, rows=[[f"{gen_word(c):03X}" for c in cram[16 * r:16 * r + 16]] for r in range(4)]))
            lastcram = cram
        st = e.w(g["Sattsize"])
        sp = sprites(vr, T["SAT"])
        vis = [s for s in sp if 128 <= s["y"] < 128 + 224 + 32 and s["x"] > 0]
        if st or vis:
            R["sprites"].append(dict(frame=f, Sattsize=st, visible=vis[:8]))
        for name in ("A", "B", "W"):
            w, h = (T["wwidth"], 32) if name == "W" else (T["pw"], T["ph"])
            for i, c in enumerate(cells(vr, T[name], w, h)):
                plane_tiles[name].add(c & 0x7FF)
        nz = np.nonzero(vr[:0xA000 >> 1])[0]
        if len(nz):
            hiwritten = max(hiwritten, int(nz[-1]) * 2)
        # line scroll (mode3 & 3 == 3: a long a line, A then B)
        if T["mode3"] & 3 == 3:
            hs = vr[T["HS"] >> 1:(T["HS"] >> 1) + 448]
            for ln in range(224):
                if hs[2 * ln] & 0x3FF:
                    hs_moving[ln].add("A")
                if hs[2 * ln + 1] & 0x3FF:
                    hs_moving[ln].add("B")
        k = f - started
        if k == 300:
            first = (vr.copy(), cram, reg)
            e.screenshot(out / "first_300.png")
        if (k < 400 and k % 20 == 0) or k % 300 == 0:
            e.screenshot(out / f"title_{k:04d}.png")
        if k == 2500:
            break
    R["title_from"], R["title_to"] = started, f
    R["vscroll_max"] = dict(A=vsmax[0], B=vsmax[1])
    vr, cram, reg, _ = state(e)
    T = tables(reg)
    # pieces by tile range: the picture from 0 to the d4 it handed on, each image after it from where the last ended
    # (its map's highest tile + 1; the last one up to the small font, whose start smallfontchars keeps)
    font = R["d4"]["smallfontchars"]
    names = ["picture (TitleScreenImg)"] + [f"image at {im['img']}" for im in imgs[1:]]
    pieces, d4 = [], 0
    for i, im in enumerate(imgs):
        end = R["d4"]["picture_end"] if i == 0 else font if i == len(imgs) - 1 else d4 + im["maxtile"] + 1
        pieces.append((names[i], d4, end - 1))
        d4 = end
    pieces.append(("small font (credits)", font, None))
    R["pieces_guess"] = pieces
    # colours each piece draws with: every cell of every plane, by its tile's range
    pairs = defaultdict(set)
    where = defaultdict(lambda: defaultdict(set))
    for name in ("W", "A", "B"):
        w, h = (T["wwidth"], 32) if name == "W" else (T["pw"], T["ph"])
        for i, c in enumerate(cells(vr, T[name], w, h)):
            t, pal = c & 0x7FF, c >> 13 & 3
            cols = tile_cols(vr, t) - {0}
            if not cols:
                continue
            piece = next((p[0] for p in reversed(pieces) if t >= p[1]), "?")
            for col in cols:
                pairs[piece].add((pal, col))
            where[piece][name].add((i // w, i % w))
    R["piece_colours"] = {k: sorted(v) for k, v in pairs.items()}
    R["piece_cells"] = {k: {n: dict(rows=[min(r for r, _ in v), max(r for r, _ in v)], cols=[min(c for _, c in v), max(c for _, c in v)], n=len(v)) for n, v in d.items()} for k, d in where.items()}
    R["plane_tiles_max"] = {k: max(v - {0x7FF}) if v - {0x7FF} else None for k, v in plane_tiles.items()}
    R["highest_nonzero_vram_below_A000"] = f"${hiwritten:X} (tile ${hiwritten // 32:X})"
    R["hscroll_lines"] = {"A": [ln for ln in range(224) if "A" in hs_moving[ln]], "B": [ln for ln in range(224) if "B" in hs_moving[ln]]}
    # After the title: START, Game Setup left alone until the demo (no press for $5460 frames), on NHL '94 until it
    # has played 600 frames ($FFF7 = 0), then A (EndDemoOnPress: ExitToOpening, Opening2); the title's handler
    # watched all the way
    after, seen, k = [], 0, 0
    e.run(4, hold=["START"])
    e.run(60)

    def watch(n, until=None):
        nonlocal k, seen
        run0 = 0
        for _ in range(n):
            e.run(1)
            k += 1
            h = e.l(g["VBint"]) & 0xFFFFFF
            if not after or after[-1][1] != h:
                after.append((k, h))
            seen += h == vb
            if until:
                run0 = run0 + 1 if until() else 0
                if run0 == 600:
                    return True
        return False
    played = watch(0x5460 + 12000, (lambda: e.b(0xFFF7) == 0) if ver == "94" else None)
    e.screenshot(out / "demo.png")
    e.run(4, hold=["A"])
    watch(1500)
    e.screenshot(out / "after_demo.png")
    R["after_title"] = dict(handlers=[(k, f"${h:X}") for k, h in after], demo_in_play=played, title_handler_seen=seen)
    # A soft reset (the console's reset button): the title again, compared with the first time at the same frame
    e.lib.retro_reset()
    k0 = None
    for f2 in range(4000):
        e.run(1)
        if (e.l(g["VBint"]) & 0xFFFFFF) == vb:
            k0 = f2 if k0 is None else k0
            if f2 - k0 == 300:
                vr2, cram2, reg2, _ = state(e)
                e.screenshot(out / "reset_300.png")
                a, b = np.asarray(Image.open(out / "first_300.png")), np.asarray(Image.open(out / "reset_300.png"))
                R["reset"] = dict(title_after=k0, vram_words_differ=int((vr2 != first[0]).sum()),
                                  vram_tiles_differ=sorted({int(i) // 16 for i in np.nonzero(vr2[:0xA000 >> 1] != first[0][:0xA000 >> 1])[0]})[:20],
                                  cram_same=cram2 == first[1], regs_same=reg2[:19] == first[2][:19],
                                  pixels_differ=int((a != b).any(axis=2).sum()))
                break
    (out / "title.json").write_text(json.dumps(R, indent=1, default=list))
    np.save(out / "title_vram.npy", vr)
    print(json.dumps({k: R[k] for k in ("handler", "d4", "title_from", "title_to", "pieces_guess", "plane_tiles_max", "highest_nonzero_vram_below_A000", "vscroll_max", "after_title", "reset")}, default=list))


if __name__ == "__main__":
    main()
