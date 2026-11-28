"""The SNES side-on scoreboard screen's rink (2026-11-27, for NOSE4Web's "ads on the side-on scoreboard": the
rink map's rows 85-112 as a picture to edit; retail and the SA-1 / 2 MB builds).

SetHor (from Pausemode, chkprogress (a penalty), PeriodOver, ExitStatsScreen, ReplayMode, SaveRegsStartHL2) blanks
the screen, sets sfhormode, Hscroll 0 and Vscroll -1 and runs SetHor_rink: MapPartToVRAM copies rinkmapbuf rows
85-112 (28 rows), columns 0-31 into BG2's map at $400 and columns 16-47 into $800, then USBoard prints the
scoreboard (BG1, the text map). ReplayMode pastes rows 85-92, columns 32-39 (the replay icon) into BG1 with charofs
-256. DrawHorTeams (setvideo) draws the team blocks and sends their palette rows.

From a game in play (Snes9x, headless), the side-on screen at each moment it shows: the pause scoreboard (START,
then the pause menu's cursor on each item, a stats screen and back through ExitStatsScreen), a penalty if one comes
up while the game plays on, the end of period 1 and the intermission. At each:
- BG2's map words ($400-$BFF) matched against rinkmapbuf rows 85-112 (which map rows and columns are where);
- the scroll (BG2HScroll $07DA, BG2VScroll $07DC as the game keeps them) and sfhormode;
- BG1's cells that draw something (the scoreboard, text, team blocks) and their palettes; colour memory rows 6 and 7
  (DrawHorTeams) against play's;
- which BG2 cells show: every BG2 map word of one half ($400 or $800) pointed at a spare tile (named by neither layer
  at that moment) filled with colour 1, then colour 2, on a palette where those two differ, the cells' priority bits
  kept, one frame each from the same state; the screen pixels that differ belong to that half's cells (placed by a
  single cell poked the same way). Each BG2 map cell: shown whole, in part (text, blocks or sprites over it) or not
  at all, and the rink map's row and column it holds.
Then from rinkmapbuf: the tiles rows 85-112 name, which of them rows 0-84 also name (the play rink), the crowd's
animated tiles (1-65), tiles 256 and up (the replay icon must keep those), and the icon's cells.

Outputs: hor.json, screenshots of each moment, cells.png (the rink rows 85-112 x columns 0-47 over the scoreboard:
green shown whole at every moment seen, yellow in part or at some, red never, grey not on screen).

python snes_hor_board_check.py ROM OUT"""
import ctypes as C
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

from snes_rink_import_check import Snes, W, H, CROWD, CLOCK, GSP, SFLAGS, PSITEM, HOMETEAM, VISTEAM, is_sa1

SFHOR, BG2H, BG2V, BG1H, BG1V = 0x15DA, 0x07DA, 0x07DC, 0x07D6, 0x07D8
ROW0 = 85
ICON = [(r, c) for r in range(85, 93) for c in range(32, 40)]


def solid(colour):
    return bytes([0xFF if colour >> (k % 2) & 1 else 0 for k in range(16)] +
                 [0xFF if colour >> (2 + k % 2) & 1 else 0 for k in range(16)])


class Hor:
    def __init__(self, rom, out):
        self.s = Snes(rom)
        self.out = out
        self.moments = []
        self.shown = defaultdict(list)          # (vram half, map row, map col) -> [share of pixels showing, ...]

    def shot(self):
        p = self.out / "_poke.png"
        self.s.e.screenshot(p)
        return np.asarray(Image.open(p).convert("RGB")).astype(int)

    def spare_tile(self, vr):
        named1 = {int(v) & 0x3FF for v in vr[0x0000:0x0400]}
        named2 = {int(v) & 0x3FF for v in vr[0x0400:0x0C00]}
        for t in range(1023, 300, -1):           # BG2 tile t is BG1 tile t - 256 (BG2 tiles from $1000, BG1's $2000)
            if t not in named2 and (t - 256) not in named1:
                return t
        return None

    def poke(self, cells, colour, t, pal, vr):
        for i, b in enumerate(solid(colour)):
            self.s.vr[2 * (0x1000 + 16 * t) + i] = b
        for a in cells:
            v = int(vr[a]) & 0x2000 | pal << 10 | t
            self.s.vr[2 * a], self.s.vr[2 * a + 1] = v & 0xFF, v >> 8

    def diff(self, cells, t, pal, vr, raw):
        shots = []
        for col in (1, 2):
            self.poke(cells, col, t, pal, vr)
            shots.append(self.shot())
            self.s.load(raw)
        return (shots[0] != shots[1]).any(axis=2)

    def place(self, half, vr, raw, t, pal):
        """Where one cell of this half shows: (row, col, screen x, screen y) for the first of a few cells that shows,
        or None (the half isn't on screen)."""
        base = 0x400 if half == "L" else 0x800
        for r, c in ((5, 5), (5, 20), (20, 5), (20, 20), (12, 12), (2, 28)):
            d = self.diff([base + 32 * r + c], t, pal, vr, raw)
            ys, xs = np.nonzero(d)
            if len(ys):
                return r, c, int(xs.min()) if xs.max() - xs.min() < 8 else int(xs.max()) - 7, int(ys.max()) - 7
        return None

    def sample(self, what, poke=True):
        s, e = self.s, self.s.e
        vr = s.words()
        m = s.rmap()
        cg = s.cgram()
        raw = s.raw()
        rows = {}
        for v in range(32):
            for half, base, c0, n in (("L", 0x400, 0, 32), ("R", 0x800, 16, 32)):
                words = [int(x) for x in vr[base + 32 * v:base + 32 * v + n]]
                hit = next((r for r in range(H) if m[r * W + c0:r * W + c0 + n] == words), None)
                if hit is not None:
                    rows[f"{half}{v}"] = hit
        bg1 = [(i // 32, i % 32, int(v) >> 10 & 7) for i, v in enumerate(vr[0:0x400])
               if (int(v) & 0x3FF) and vr[0x2000 + 16 * (int(v) & 0x3FF):0x2000 + 16 * (int(v) & 0x3FF) + 16].any()]
        M = dict(what=what, sfhor=e.w(SFHOR), paused=bool(e.w(SFLAGS) & 1), bg2_scroll=[e.w(BG2H), e.w(BG2V)],
                 bg1_scroll=[e.w(BG1H), e.w(BG1V)], vram_rows=rows, bg1_cells=len(bg1),
                 bg1_rows=sorted({r for r, _, _ in bg1}), bg1_palettes=sorted({p for _, _, p in bg1}),
                 cgram_6_7=[f"{c:04X}" for c in cg[96:128]], psitem=e.w(PSITEM))
        M["board_shown"] = rows.get("L0") == ROW0          # BG2 holds rows 85-112 from its top row
        if poke and M["board_shown"]:
            t = self.spare_tile(vr)
            pal = next((p for p in range(8) if cg[16 * p + 1] != cg[16 * p + 2]), 0)
            vis = {}
            for half, base in (("L", 0x400), ("R", 0x800)):
                d = self.diff(list(range(base, base + 0x400)), t, pal, vr, raw)
                M[f"pixels_{half}"] = int(d.sum())
                at = self.place(half, vr, raw, t, pal) if d.any() else None
                M[f"placed_{half}"] = at
                if at is None:
                    continue
                r0, c0, x0, y0 = at
                for row in range(32):
                    for col in range(32):
                        x = x0 + 8 * (col - c0)
                        y = (y0 + 8 * (row - r0)) % 256
                        if y > 248:
                            y -= 256
                        if not (-7 <= x <= 255 and -7 <= y <= 223):
                            continue
                        box = d[max(0, y):max(0, y + 8), max(0, x):max(0, x + 8)]
                        if not box.size:
                            continue
                        share = float(box.mean())
                        vis[(half, row, col)] = share
                        self.shown[(half, row, col)].append(share)
            M["cells_shown_whole"] = sum(1 for v in vis.values() if v == 1)
            M["cells_shown_part"] = sum(1 for v in vis.values() if 0 < v < 1)
        e.screenshot(self.out / f"{len(self.moments):02d}_{what.replace(' ', '_')}.png")
        self.moments.append(M)
        return M


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    h = Hor(rom, out)
    s, e = h.s, h.s.e
    s.to_setup()
    n = 32 if is_sa1(rom) and Path(rom).stat().st_size > 0x180000 else 28
    e.setw(HOMETEAM, 1)
    e.setw(VISTEAM, 2 % n)
    e.run(30)
    if not s.into_play():
        raise SystemExit("not into play")
    m0 = s.rmap()
    e.run(600)
    play_cg = s.cgram()
    # the pause scoreboard, then the menu's cursor on each item
    s.press("START", 60)
    h.sample("pause 60")
    e.run(180)
    h.sample("pause 240")
    seen = set()
    for k in range(16):
        it = e.w(PSITEM)
        if it in seen:
            break
        seen.add(it)
        h.sample(f"cursor item {it}", poke=k % 3 == 0)
        s.press("DOWN", 30)
    for _ in range(20):                                   # back to the first item
        if e.w(PSITEM) == 0:
            break
        s.press("UP", 20)
    # a stats screen (Game Stats, item 2) and back through ExitStatsScreen
    for _ in range(20):
        if e.w(PSITEM) == 2:
            break
        s.press("DOWN", 20)
    s.press("A", 300)
    h.sample("stats screen", poke=False)

    def board():
        return [int(x) for x in s.words()[0x400:0x420]] == s.rmap()[ROW0 * W:ROW0 * W + 32]
    for k in range(10):
        s.press("START" if k % 2 == 0 else "A", 200)
        if e.w(SFLAGS) & 1 and not e.w(SFLAGS) & 0x0800 and board():
            break
    h.sample("after stats (ExitStatsScreen)")
    s.press("START", 120)                                 # resume
    # play on; a penalty's side-on view (chkprogress) if one comes up
    pen = 0
    for f in range(6000):
        e.run(1)
        if f % 20 == 0 and pen < 4 and e.w(SFHOR) and not e.w(SFLAGS) & 1 and board():
            h.sample(f"penalty {pen}", poke=pen < 2)
            pen += 1
    # the end of period 1 and the intermission
    e.setw(CLOCK, 3)
    p0 = e.w(GSP)
    k = 0
    for f in range(7000):
        e.run(1, hold=["START"] if f > 2400 and f % 300 == 0 else [])
        if f % 150 == 0 and k < 12 and e.w(SFHOR) and board():
            h.sample(f"period end {f}", poke=k % 3 == 0)
            k += 1
        if e.w(GSP) != p0 and not e.w(SFHOR) and f > 2500:
            break
    # from rinkmapbuf: the tiles rows 85-112 name
    rows_hb = m0[ROW0 * W:]
    play = m0[:ROW0 * W]
    t_hb = {v & 0x3FF for v in rows_hb}
    t_play = {v & 0x3FF for v in play}
    icon = [m0[r * W + c] for r, c in ICON]
    R = dict(rom=Path(rom).name, moments=h.moments,
             tiles_rows_85_112=len(t_hb), shared_with_play_rink=sorted(t_hb & t_play),
             crowd_tiles_in_rows_85_112=sorted(t_hb & set(CROWD)),
             crowd_cells_in_rows_85_112=[(ROW0 + i // W, i % W) for i, v in enumerate(rows_hb) if (v & 0x3FF) in CROWD],
             tiles_256_up_outside_icon=sorted({v & 0x3FF for i, v in enumerate(rows_hb)
                                               if (v & 0x3FF) >= 256 and (ROW0 + i // W, i % W) not in ICON}),
             icon_tiles=[min(v & 0x3FF for v in icon), max(v & 0x3FF for v in icon), len({v & 0x3FF for v in icon})],
             icon_tiles_also_elsewhere=sorted({v & 0x3FF for v in icon} & ({v & 0x3FF for i, v in enumerate(rows_hb)
                                              if (ROW0 + i // W, i % W) not in ICON} | t_play)),
             palettes_rows_85_112={p: sum(1 for v in rows_hb if v >> 10 & 7 == p) for p in range(8)},
             priority_cells_rows_85_112=sum(1 for v in rows_hb if v & 0x2000),
             cgram_6_7_play=[f"{c:04X}" for c in play_cg[96:128]])
    # each rink cell (rows 85-112, columns 0-47): via the half and VRAM row that held it
    grid = {}
    for (half, row, col), shares in h.shown.items():           # (recorded only while the board shows)
        rr, cc = ROW0 + row, col + (16 if half == "R" else 0)
        if row >= 28:
            continue
        g = grid.setdefault((rr, cc), [])
        g.extend(shares)
    cls = {}
    for (rr, cc), sh in grid.items():
        cls[(rr, cc)] = "whole" if min(sh) == 1 else "never" if max(sh) == 0 else "part"
    R["rows"] = {rr: "".join({"whole": ".", "part": "+", "never": "#"}.get(cls.get((rr, cc)), " ") for cc in range(W))
                 for rr in range(ROW0, H)}
    (out / "hor.json").write_text(json.dumps(R, indent=1, default=str))
    # the cell map over the first scoreboard screenshot: each shown cell where its half placed it then
    first = next((M for M in h.moments if M["what"] == "pause 240"), None)
    shot = next(iter(sorted(out.glob("*pause_240*.png"))), None)
    if first and shot:
        img = Image.open(shot).convert("RGB").resize((512, 448), Image.NEAREST)
        ov = Image.new("RGB", img.size, (90, 90, 90))
        px = ov.load()
        for half in ("L", "R"):
            at = first.get(f"placed_{half}")
            if not at:
                continue
            r0, c0, x0, y0 = at
            for (hh, row, col), sh in h.shown.items():
                if hh != half:
                    continue
                x, y = x0 + 8 * (col - c0), (y0 + 8 * (row - r0)) % 256
                if y > 248:
                    y -= 256
                if not (0 <= x < 256 and -7 <= y < 224):
                    continue
                c = (0, 200, 0) if min(sh) == 1 else (220, 0, 0) if max(sh) == 0 else (220, 200, 0)
                for yy in range(2 * max(0, y), 2 * min(224, y + 8)):
                    for xx in range(2 * x, 2 * min(256, x + 8)):
                        px[xx, yy] = c
        Image.blend(img, ov, 0.45).save(out / "cells.png")
    print(json.dumps({k: v for k, v in R.items() if k not in ("moments",)}, indent=1, default=str))
    for M in h.moments:
        print({k: M.get(k) for k in ("what", "sfhor", "bg2_scroll", "pixels_L", "pixels_R", "cells_shown_whole",
                                       "cells_shown_part", "bg1_rows", "bg1_palettes")}, sorted(set(M["vram_rows"].values()))[:3])


if __name__ == "__main__":
    main()
