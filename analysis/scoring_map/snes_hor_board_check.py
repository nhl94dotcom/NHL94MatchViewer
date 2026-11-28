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

python snes_hor_board_check.py ROM OUT
python snes_hor_board_check.py ads ROM OUT   (a side-on board build's moments, and the base's: ads())
python snes_hor_board_check.py compare BASE_OUT BUILD_OUT OUT [EXPECTED.png]   (compare())"""
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


def ads(rom, out):
    """For a side-on board build: the moments saved (snes_rink_import_check.dump: video and colour memory,
    rinkmapbuf, character bases; and a screenshot): the opening faceoff, the pause scoreboard, the instant replay (the
    icon), play after it, a penalty's side-on view (penalties set on: retail's menu leaves them Off; up to 20,000
    frames of play) and the intermission; the crowd's tiles 1-65 watched for 300 frames on each board. Home team 1."""
    from snes_rink_import_check import dump
    out.mkdir(parents=True, exist_ok=True)
    s = Snes(rom)
    e = s.e
    s.to_setup()
    n = 32 if is_sa1(rom) and Path(rom).stat().st_size > 0x180000 else 28
    e.setw(HOMETEAM, 1)
    e.setw(VISTEAM, 2 % n)
    e.setw(0x34C4, 2)                                     # Penalties On, No Offside (snes_60fps_cvc.OPTPEN)
    e.run(30)
    if not s.into_play():
        raise SystemExit("not into play")
    got = {}

    def snap(tag):
        dump(s, out, tag)
        e.screenshot(out / f"{tag}.png")
        got[tag] = True

    def board():
        return [int(x) for x in s.words()[0x400:0x420]] == s.rmap()[ROW0 * W:ROW0 * W + 32]

    def crowd_watch(tag):
        """The crowd's tiles 1-65 for 300 frames while the board shows: which are rewritten (showcrowd)."""
        ref = s.words()[0x1000:0x1000 + 16 * 66].reshape(-1, 16).copy()
        changed, n = set(), 0
        for _ in range(30):
            e.run(10)
            if not (e.w(SFHOR) and board()):          # only samples with the board up count
                continue
            n += 1
            now = s.words()[0x1000:0x1000 + 16 * 66].reshape(-1, 16)
            changed |= {int(t) for t in np.nonzero((now != ref).any(1))[0]}
        got[f"{tag}_crowd_tiles_changed"] = sorted(changed)
        got[f"{tag}_crowd_samples"] = n
    snap("faceoff")
    e.run(300)
    s.press("START", 180)
    snap("pause")
    raw = s.raw()
    crowd_watch("pause")
    s.load(raw)
    for _ in range(40):                                   # the instant replay (item 1): its icon on BG1
        if e.w(PSITEM) == 1:
            break
        s.press("DOWN", 20)
    s.press("A", 300)
    snap("replay")
    for k in range(10):
        s.press("START" if k % 2 == 0 else "A", 200)
        if e.w(SFLAGS) & 1 and not e.w(SFLAGS) & 0x0800 and board():
            break
    s.press("START", 120)
    e.run(300)
    snap("play")
    in_play = s.raw()
    for f in range(20000):                                # a penalty's side-on view
        e.run(1)
        if f % 10 == 0 and e.w(SFHOR) and not e.w(SFLAGS) & 1 and board():
            e.run(60)
            if not (e.w(SFHOR) and board()):
                continue
            snap("penalty")
            crowd_watch("penalty")
            got["penalty_frame"] = f
            break
    s.load(in_play)                                       # the end of period 1 from play: the intermission's board
    e.setw(CLOCK, 3)
    p0 = e.w(GSP)
    for f in range(12000):
        e.run(1)
        if f % 30 == 0 and e.w(SFHOR) and board() and (e.w(CLOCK) == 0 or e.w(GSP) != p0):
            e.run(60)
            snap("intermission")
            crowd_watch("intermission")
            break
    (out / "ads.json").write_text(json.dumps(dict(rom=Path(rom).name, got=got)))
    print(Path(rom).name, got, flush=True)


def compare(base, build, out, expected=None, panel=((93, 96), (2, 30))):
    """A side-on board build's `ads` run against the base ROM's, each drawn from its own data (the two games need not
    stay in step): rinkmapbuf cell by cell (only the panel's cells, rows 93-95 columns 2-29, may differ; the replay icon,
    the crowd's cells, the logo and rows 0-84 drawn as the base; the palette and priority bits as the base); the sets after
    the rink by content; at each board moment BG2's 32 x 28 (only the panel's cells may differ; BG1 noted); the panel
    against the editor's expected picture of rows 85-112 (SNES levels); the replay icon (BG1); the crowd's tiles
    animating on the penalty's board; the highest video memory below the sprites."""
    from snes_rink_import_check import render, cells_differ
    out.mkdir(parents=True, exist_ok=True)
    res = []

    def check(name, ok, detail=""):
        res.append(("PASS" if ok else "FAIL", name, detail))
    (r0, r1), (c0, c1) = panel
    pan = {(r, c) for r in range(r0, r1) for c in range(c0, c1)}
    L = lambda d, tag: np.load(d / f"dump_{tag}.npz")  # noqa: E731
    ga, gb = (json.loads((d / "ads.json").read_text())["got"] for d in (base, build))
    fa, fb = L(base, "faceoff"), L(build, "faceoff")
    ca, cb = json.loads(str(fa["chars"])), json.loads(str(fb["chars"]))
    grow = cb["centericechars"] - ca["centericechars"]
    check(f"rink tiles {ca['centericechars']} -> {cb['centericechars']} (+{grow}); every set after it {grow} later",
          all(cb[k] - ca[k] == grow for k in ca if k not in ("charofs", "centericechars")))
    sa, sb = fa["vram"], fb["vram"]
    for k in ("centericechars", "faceoffvrcset", "EASNcset", "refcharshor", "refchars", "smallfontchars", "framercset",
              "BigFontchars", "scorechars"):
        nxt = sorted(v for kk, v in ca.items() if kk != "charofs" and v > ca[k])
        m = (nxt[0] if nxt else ca[k] + 16) - ca[k]
        a, b = sa[0x1000 + 16 * ca[k]:0x1000 + 16 * (ca[k] + m)], sb[0x1000 + 16 * cb[k]:0x1000 + 16 * (cb[k] + m)]
        check(f"set {k} ({m} tiles, from {ca[k]} now {cb[k]}) unchanged", len(a) == len(b) and bool((a == b).all()))
    ra, rb = fa["rmap"], fb["rmap"]
    ia = render(fa["vram"], fa["cgram"], ra, W, H, 0x1000)
    ib = render(fb["vram"], fb["cgram"], rb, W, H, 0x1000)
    diff = cells_differ(ia, ib, W, H, ra, rb)
    check(f"rinkmapbuf: only the panel's cells differ ({len(diff)} cells differ)", set(diff) <= pan,
          str(sorted(set(diff) - pan)[:8]))
    check("rows 0-84 (the play rink) drawn as the base", not [c for c in diff if c[0] < 85])
    check("the replay icon's cells (rows 85-92, columns 32-39) drawn as the base and on tiles 256 and up",
          not [c for c in diff if c in set(ICON)] and min(int(rb[r * W + c]) & 0x3FF for r, c in ICON) >= 256)
    crowd = {(i // W, i % W) for i in range(W * H) if int(ra[i]) & 0x3FF in CROWD}
    check(f"the crowd's {len(crowd)} cells still name tiles 1-65 (the same words as the base)",
          all(int(ra[r * W + c]) == int(rb[r * W + c]) for r, c in crowd))
    bits = [(i // W, i % W) for i in range(W * H) if (int(ra[i]) & 0x3C00) != (int(rb[i]) & 0x3C00) and (i // W, i % W) not in pan]
    check("palette and priority bits as the base outside the panel", not bits, str(bits[:8]))
    if expected:
        ex = np.asarray(Image.open(expected).convert("RGB")).astype(np.int64)
        part = ib[8 * ROW0:8 * H, 0:8 * min(W, ex.shape[1] // 8)]
        h_, w_ = min(part.shape[0], ex.shape[0]), min(part.shape[1], ex.shape[1])
        a, e_ = part[:h_, :w_], ex[:h_, :w_]
        opaque = (a >= 0).all(axis=2)
        lv = lambda x: np.rint(x * 31 / 255)  # noqa: E731
        bad = opaque & (np.abs(lv(a) - lv(e_)) > 1).any(axis=2)
        pb_ = np.zeros_like(bad)
        pb_[8 * (r0 - ROW0):8 * (r1 - ROW0), 8 * c0:8 * c1] = True
        team = np.zeros_like(bad)                     # cells on palettes 2 / 3 (the teams', set at run time)
        for i in range(ROW0 * W, H * W):
            if int(rb[i]) >> 10 & 7 in (2, 3) and i % W < w_ // 8:
                y, x = divmod(i - ROW0 * W, W)
                team[8 * y:8 * y + 8, 8 * x:8 * x + 8] = True
        check("rows 85-112 as the expected picture (the panel)", not (bad & pb_).any(), f"{int((bad & pb_).sum())} px in the panel")
        check("rows 85-112 as the expected picture (outside the panel, team-coloured cells aside)", not (bad & ~pb_ & ~team).any(),
              f"{int((bad & ~pb_ & ~team).sum())} px")
    for tag in ("pause", "penalty", "intermission"):
        if tag not in ga or tag not in gb:
            check(f"{tag}: reached on both", False, f"base {tag in ga}, build {tag in gb}")
            continue
        da, db = L(base, tag), L(build, tag)
        ea, eb = da["vram"][0x400:0x400 + 32 * 28], db["vram"][0x400:0x400 + 32 * 28]
        A = render(da["vram"], da["cgram"], ea, 32, 28, 0x1000)
        B = render(db["vram"], db["cgram"], eb, 32, 28, 0x1000)
        d = cells_differ(A, B, 32, 28, ea, eb)
        span = {(r - ROW0, c) for r, c in pan}
        check(f"{tag}: BG2 (the board) as the base but the panel's cells", set(d) <= span, str(sorted(set(d) - span)[:8]))
        check(f"{tag}: the panel's cells differ (the ad is there)", bool(set(d) & span), f"{len(set(d) & span)} cells")
        # BG1's text: its tiles sit past the rink (BG1 tile t is BG2 tile t + 256), so they move with the rink's growth
        sh = lambda v: (int(v) & ~0x3FF) | ((int(v) & 0x3FF) + (grow if (int(v) & 0x3FF) + 256 >= ca["centericechars"] else 0)) & 0x3FF  # noqa: E731
        b1 = [(i // 32, i % 32) for i, (x, y) in enumerate(zip(da["bg1"], db["bg1"])) if sh(x) != int(y)]
        res.append(("INFO", f"{tag}: BG1 (scoreboard text) cells differing, the tiles' shift allowed for (the clock, a penalty's player: the games part)",
                    f"{len(b1)} {b1[:6]}"))
        Image.fromarray(np.clip(np.concatenate([A, B], axis=1), 0, 255).astype(np.uint8)).save(out / f"{tag}_board_base_build.png")
        sa_, sb_ = (np.asarray(Image.open(d_ / f"{tag}.png").convert("RGB")) for d_ in (base, build))
        Image.fromarray(np.concatenate([sa_, sb_], 1)).save(out / f"{tag}_screens_base_build.png")
    da, db = L(base, "replay"), L(build, "replay")
    idx = [y * 32 + x for y in range(2, 10) for x in range(2, 10)]
    A = render(da["vram"], da["cgram"], da["vram"][0:0x400][idx], 8, 8, 0x2000)
    B = render(db["vram"], db["cgram"], db["vram"][0:0x400][idx], 8, 8, 0x2000)
    d = cells_differ(A, B, 8, 8)
    check("the replay icon (BG1, 8 x 8) drawn as the base", not d, str(d[:8]))
    pa_, pb2 = L(base, "play"), L(build, "play")
    pr_a = render(pa_["vram"], pa_["cgram"], pa_["rmap"], W, 85, 0x1000)
    pr_b = render(pb2["vram"], pb2["cgram"], pb2["rmap"], W, 85, 0x1000)
    dp = cells_differ(pr_a, pr_b, W, 85, pa_["rmap"], pb2["rmap"])
    check("in play after the replay: rows 0-84 drawn as the base", not dp, str(dp[:8]))
    for tag in ("pause", "penalty", "intermission"):
        na, nb = (len(g.get(f"{tag}_crowd_tiles_changed") or []) for g in (ga, gb))
        sa2, sb2 = (g.get(f"{tag}_crowd_samples") for g in (ga, gb))
        check(f"{tag}: the crowd's tiles 1-65 animate on the board as on the base (base {na} tiles rewritten in {sa2} samples "
              f"with the board up, build {nb} in {sb2}; bursts: a fail only if the base animates and the build not)", nb > 0 or na == 0)
    lines = [f"{a}  {b}" + (f"  [{c}]" if c and a != "PASS" else "") for a, b, c in res]
    (out / "compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1] == "ads":
        ads(sys.argv[2], Path(sys.argv[3]))
    elif sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 else None)
    else:
        main()
