"""The Genesis line-change box against the score box's corner, and the palettes and sprite priority in play (2026-11-08,
for NOSE4Web's Genesis score logos; gen_score_logo_check.py has the whole-game watch).

nhl94.bin with line changes On (manual: the lower box appears for the team whose box is at the bottom, sflags3 bit 0)
and pad 1 on the home team: in periods 1 and 2 (the ends switch), A while pad 1's team has the puck opens the line-change
box; the text map's cells at columns $16-$1E, rows $15-$1C are read while it is up and after a line is chosen (B), with
screenshots. In play: the palette lines (palfadenew $BD28, and the video chip's colour memory from the saved state)
and how many of the sprites in the sprite table have the priority bit.

python gen_lc_box_check.py ROM OUT"""
import sys
from pathlib import Path

import menu_shots as M
from gen_score_logo_check import Watch, VRAM_AT, VMAP1, MAP1COL, PAL, VSPR, PUCK, CLOCK, GSP


def cells(g):
    vr, _ = g.vram()
    m1, sh = g.w(VMAP1), g.w(MAP1COL)
    return [[g.cell(vr, m1, c, r, sh) for c in range(0x16, 0x1F)] for r in range(0x15, 0x1D)]


def show(rows):
    return "\n".join(f"   row ${0x15 + i:02X}: " + " ".join(f"{v:04x}" for v in row) for i, row in enumerate(rows))


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    g = Watch(rom, out)
    e = g.e
    M.play(e, "w900 START w120 START w120 DOWN*7 RIGHT DOWN RIGHT RIGHT w60 S:setup", out)
    for _ in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    g.step(120)
    print("palfadenew in play:")
    for k in range(4):
        print(f"   line {k}: " + " ".join(f"{g.w(PAL + 32 * k + 2 * i):04x}" for i in range(16)))
    st = e.serialize()
    cram = st[VRAM_AT + 0x10000:VRAM_AT + 0x10080]
    print("colour memory (Genesis Plus GX's 9-bit form):")
    for k in range(4):
        print(f"   line {k}: " + " ".join(f"{cram[32 * k + 2 * i] | cram[32 * k + 2 * i + 1] << 8:03x}" for i in range(16)))
    vr, _ = g.vram()
    sat, k, seen, pri, n = g.w(VSPR), 0, 0, 0, 0
    while seen < 80:
        a = (sat + 8 * k) & 0xFFFF
        attr = vr[a + 4] | vr[a + 5] << 8
        link = (vr[a + 2] | vr[a + 3] << 8) & 0x7F
        n += 1
        pri += bool(attr & 0x8000)
        seen += 1
        if link == 0:
            break
        k = link
    print(f"sprites in the table: {n}, with the priority bit: {pri}")
    for per in (0, 1):
        g.wait_play()
        opened = False
        for _ in range(3000):
            k = g.b(PUCK + 0x61)
            if g.b(PUCK + 0x60) == 0 and k < 6 and g.b(0xB04A + k * 0x80 + 0x62) & 8:
                g.step(60, hold=["A"])                 # held: aholdtimer counts down before SetLCmode
                g.step(20)
                opened = True
                break
            g.step(1)
        g.step(20)
        print(f"period {per + 1}: A pressed with the puck: {opened}; lower box flag {g.state()['lower_lc']}")
        e.screenshot(out / f"lc_{per + 1}_open.png")
        print(show(cells(g)))
        g.press("B", 60)
        e.screenshot(out / f"lc_{per + 1}_closed.png")
        print("   after B:")
        print(show(cells(g)))
        if per == 0:
            e.setw(CLOCK, 5)
            for _ in range(400):
                g.step(30)
                if g.w(GSP) == 1 and g.in_play():
                    break
                if not g.in_play():
                    g.press("C", 60)                     # the intermission's menu: Resume Game
                    g.press("START", 60)


if __name__ == "__main__":
    main()
