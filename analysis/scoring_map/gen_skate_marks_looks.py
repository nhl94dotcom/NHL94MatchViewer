"""How NOSE4Web's Genesis skate marks could look stronger (2026-11-14: the user found them hard to see, CDL Season 12's
lighter ice most of all): mock-ups from one moment of play, the plane and colours edited in a copy of the state.

A computer game on the marks build (5-minute periods, the pads let go) played to CLOCK seconds left in period 1, a
state saved at a moment the camera is still. Then each look is the same state with only video memory or colour
memory changed (our own headless core: nothing of the user's), one frame run, a screenshot:
  as_is        the build as it is: $8E / $F4 (the rink's own one-pixel streaks, palette 0 colour 2)
  colour       palette 0 colour 2 darkened (the rink's own streaks with it: what else uses colour 2 is listed)
  long         each mark the rink's long streak tile $A4 / $A5 (15-16 pixels) instead
  medium       the 6-pixel streak $FB
  double       twice as many marks (each mark's neighbour cell along its diagonal marked too)
  long_double  long and double together
Also printed: palette 0's colours, the ice colour and the streak colour, and their contrast.

python gen_skate_marks_looks.py ROM OUT [CLOCK]"""
import struct
import sys
from pathlib import Path

import gen_ot_check as G
import gen_skate_marks_check as K
import lowload
from emu import Emu

VRAM_AT = K.VRAM_AT
CRAM_AT = VRAM_AT + 0x10000
PLANE_B = K.PLANE_B


def colours(st):
    """Palette line 0 as (r, g, b) 0-7 each, from Genesis Plus GX's colour memory (9-bit words, BBBGGGRRR)."""
    out = []
    for i in range(16):
        w = st[CRAM_AT + 2 * i] | st[CRAM_AT + 2 * i + 1] << 8
        out.append(((w >> 0) & 7, (w >> 3) & 7, (w >> 6) & 7))
    return out


def set_colour(st, line, i, rgb):
    r, g, b = rgb
    w = r | g << 3 | b << 6
    st[CRAM_AT + 32 * line + 2 * i] = w & 0xFF
    st[CRAM_AT + 32 * line + 2 * i + 1] = w >> 8


def word(st, r, c):
    a = VRAM_AT + PLANE_B + 2 * (r * 64 + c)
    return st[a] | st[a + 1] << 8


def put(st, r, c, v):
    a = VRAM_AT + PLANE_B + 2 * (r * 64 + c)
    st[a], st[a + 1] = v & 0xFF, v >> 8


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    clock = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    rmap = K.rom_map(Path(rom).read_bytes())
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(0xD050, 0)
    if not G.into_play(e):
        print("never reached play")
        return
    for f in range(60 * 60 * 10):
        if f % 60 == 0:
            e.setw(K.CONT1, 0)
            e.setw(K.CONT2, 0)
            for k in range(12):
                e.setb(K.BASE + K.SZ * k + 0x62, e.b(K.BASE + K.SZ * k + 0x62) & ~8)
        e.run(1)
        if e.w(K.GSP) == 0 and e.w(K.CLOCK) <= clock and e.b(K.SCREEN) == 0:
            break
    print(f"period {e.w(K.GSP) + 1} clock {e.w(K.CLOCK)} marks {e.w(K.COUNT)}", flush=True)
    base = bytearray(e.serialize())
    pal = colours(base)
    print("palette 0 (r, g, b 0-7):", pal)
    print(f"ice (colour 0) {pal[0]}, streak (colour 2) {pal[2]}")
    # the marks on the plane: cells whose tile is a mark tile and isn't the ROM map's there
    pl = K.plane(e)
    rows = {}
    for pr, words in enumerate(pl):
        best = max(range(K.H), key=lambda r: sum(1 for c in range(K.W) if (words[c] & 0x7FF) == (rmap[r * K.W + c] & 0x7FF)))
        if sum(1 for c in range(K.W) if (words[c] & 0x7FF) == (rmap[best * K.W + c] & 0x7FF)) >= K.W * 0.7:
            rows[pr] = best
    marks = [(pr, c) for pr, r in rows.items() for c in range(K.W)
             if (pl[pr][c] & 0x7FF) in K.MARK_TILES and (pl[pr][c] & 0x7FF) != (rmap[r * K.W + c] & 0x7FF)]
    plain = {(pr, c) for pr, r in rows.items() for c in range(K.W) if (rmap[r * K.W + c] & 0x7FF) == 0x8F}
    print(f"{len(marks)} marks on the plane; tiles {sorted(set(hex(pl[pr][c]) for pr, c in marks))}")

    def shot(name, st):
        e.unserialize(bytes(st))
        e.screenshot(out / f"{name}.png")

    shot("as_is", base)
    st = bytearray(base)                                  # darker streak colour
    r, g, b = pal[2]
    set_colour(st, 0, 2, (max(0, r - 3), max(0, g - 2), max(0, b - 1)))
    shot("colour", st)
    for name, tiles in (("long", (0xA4, 0xA5)), ("medium", (0xFB, 0xFB))):
        st = bytearray(base)
        for k, (pr, c) in enumerate(marks):
            v = pl[pr][c]
            put(st, pr, c, (v & ~0x7FF) | tiles[k % 2])
        shot(name, st)
    for name, tile in (("double", None), ("long_double", (0xA4, 0xA5))):
        st = bytearray(base)
        for k, (pr, c) in enumerate(marks):
            v = pl[pr][c]
            flip = v & 0x0800
            nb = (pr + 1, c - 1) if not flip else (pr + 1, c + 1)   # the next cell along the diagonal
            new = v if tile is None else (v & ~0x7FF) | tile[k % 2]
            put(st, pr, c, new)
            if nb in plain and 0 <= nb[1] < K.W:
                put(st, nb[0] % 32, nb[1], new)
        shot(name, st)
    print("written:", sorted(p.name for p in out.glob("*.png")))


if __name__ == "__main__":
    main()
