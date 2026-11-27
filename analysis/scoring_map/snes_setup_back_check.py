"""The SNES Game Setup screen's background picture (SetupBackTiles / SetupBackMap / SetupBackPalette), for NOSE4Web's
setup background editor (2026-11-27): what video memory, palette rows and screen cells a new picture can use.

SetupScreen (setoptions calls it with setupvis + $21) puts BG2's map at VRAM $0400 (words), BG2's characters at $1000
and BG1's at $2000, sprites at $6000: MenuBackTiles from $1000 (backchars of them), then SetupBackTiles straight
after, its map entries + backchars, palette 2 (a zero entry keeps MenuBack's cell, palette 3).

Power-on to Game Setup (retail: START twice; the SA-1 builds: once), then a walk of the screen: idle, the cursor down
every line and back, each choice stepped on each line (the teams too: logos, banners and photos reloaded), Left and
Right held. At each step, from the core:
- video memory (Snes9x's memory 3) and colour memory (CGDATA in the state's PPU block, big-endian words, at
  PPU + 64); BG1 and BG2's maps (32 x 28 shown);
- for $1000-$3FFF: the words that are ever non-zero or ever change, and the tiles BG1 / BG2 cells name there (BG2
  tile t at $1000 + 16t, BG1 tile t at $2000 + 16t): who owns $22C0-$2FFF (and $3000 on);
- the colour rows: every change of each row from the first sample, and the rows the maps' cells name;
- the picture's cells that show: the picture's tiles (BG2 cells on palette 2 from backchars) filled with colour 1,
  then colour 2, a frame each from the same state; the screen pixels that differ are where the picture shows. Then
  the same with every BG2 cell pointed at that tile: the cells of the 32 x 28 grid where BG2 shows whole at every
  step, in part or at some steps, or never (BG1 text, the logo boxes, sprites over them: picture_cells.png);
- the brightening band (MenuScreenHDMA: window 1 x $40-$BF on lines $10-$2F, colour math adds the fixed colour to
  BG2 there): the colours on screen in the band against the same colour outside it.

python snes_setup_back_check.py ROM OUT
python snes_setup_back_check.py compare RETAIL_OUT BUILD_OUT OUT   (a picture build's run against retail's: compare())"""
import ctypes as C
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

import menu_shots as M

BACKCHARS = 0x35B4


def is_sa1(rom):
    d = Path(rom).read_bytes()
    return len(d) > 0x7FD6 and d[0x7FD5] == 0x23


class Screen:
    def __init__(self, rom, out):
        self.e = M.emulator(rom)
        self.out = out
        self.vram = (C.c_ubyte * self.e.lib.retro_get_memory_size(3)).from_address(self.e.lib.retro_get_memory_data(3))
        self.ever_nz = np.zeros(0x8000, bool)
        self.changed = np.zeros(0x8000, bool)
        self.first = None
        self.refs = {"BG1": defaultdict(set), "BG2": defaultdict(set)}    # tile -> {palette}
        self.cg_first = None
        self.cg_changes = defaultdict(set)          # row -> {(colour, value)} differing from the first sample
        self.visible = np.zeros((28, 32), int)      # samples in which each cell showed the picture
        self.bg2_seen = np.zeros((28, 32), int)     # ... BG2 whole, whatever it holds (every BG2 cell poked)
        self.bg2_any = np.zeros((28, 32), int)      # ... BG2 in at least one pixel
        self.grids = []                             # (step, the share of each cell's pixels where BG2 shows)
        self.samples = 0
        self.pic_samples = 0
        self.band = []
        self.log = []

    def raw(self):
        n = self.e.lib.retro_serialize_size()
        buf = (C.c_ubyte * n)()
        self.e.lib.retro_serialize(buf, n)
        return bytes(buf)

    def ppu(self, raw):
        i = raw.index(b"PPU:")
        n = int(raw[i + 4:i + 10])
        return raw[i + 11:i + 11 + n]

    def cgram(self, raw=None):
        p = self.ppu(raw or self.raw())
        return [struct.unpack_from(">H", p, 64 + 2 * i)[0] for i in range(256)]

    def words(self):
        return np.frombuffer(bytes(self.vram), dtype="<u2").copy()

    def maps(self, vr):
        return {"BG1": vr[0x0000:0x0000 + 32 * 28], "BG2": vr[0x0400:0x0400 + 32 * 28]}

    def sample(self, what, picture=True):
        vr = self.words()
        self.samples += 1
        self.ever_nz |= vr != 0
        if self.first is None:
            self.first = vr.copy()
        self.changed |= vr != self.first
        mp = self.maps(vr)
        for name, cells in mp.items():
            for c in cells:
                self.refs[name][int(c) & 0x3FF].add(int(c) >> 10 & 7)
        cg = self.cgram()
        if self.cg_first is None:
            self.cg_first = cg
        for i, (a, b) in enumerate(zip(cg, self.cg_first)):
            if a != b:
                self.cg_changes[i // 16].add((i % 16, f"{a:04X}"))
        back = self.e.w(BACKCHARS)
        self.log.append(dict(n=self.samples, what=what, backchars=back, smallfontchars=self.e.w(0x35B6),
                             nextfreechar=self.e.w(0x35C4), picchars=self.e.w(0x35D2)))
        if picture:
            self.picture_cells(vr, back, cg, what)

    def picture_cells(self, vr, back, cg, what):
        """The picture's tiles filled with colour 1, then 2 (a frame each, from the same state): where they differ."""
        bg2 = self.maps(vr)["BG2"]
        tiles = sorted({int(c) & 0x3FF for c in bg2 if (int(c) >> 10 & 7) == 2 and (int(c) & 0x3FF) >= back})
        if not tiles:
            return
        st = self.raw()

        def poked(whole):
            shots = []
            for col in (1, 2):
                pat = bytes([0xFF if col >> (k % 2) & 1 else 0 for k in range(16)] + [0xFF if col >> (2 + k % 2) & 1 else 0 for k in range(16)])
                for t in tiles:
                    a = 2 * (0x1000 + 16 * t)
                    for i, b in enumerate(pat):
                        self.vram[a + i] = b
                if whole:                       # every BG2 cell on the picture's first tile, palette 2
                    for i in range(1024):
                        v = int(vr[0x0400 + i]) & 0xE000 | 0x0800 | tiles[0]
                        self.vram[2 * (0x0400 + i)], self.vram[2 * (0x0400 + i) + 1] = v & 0xFF, v >> 8
                p = self.out / f"_poke{col}.png"
                self.e.screenshot(p)
                shots.append(np.asarray(Image.open(p).convert("RGB")).astype(int))
                self.e.lib.retro_unserialize(C.cast(C.create_string_buffer(st, len(st)), C.c_void_p), len(st))
            return shots[0], (shots[0] != shots[1]).any(axis=2)

        _, diff = poked(False)
        a, diff_all = poked(True)
        h = diff.shape[0]
        self.pic_samples += 1
        for y in range(28):
            for x in range(32):
                box = (slice(max(0, 8 * y - 1), min(h, 8 * y + 7)), slice(8 * x, 8 * x + 8))   # BG2's vertical scroll is -1
                self.visible[y, x] += bool(diff[box].any())
                self.bg2_seen[y, x] += bool(diff_all[box].all())
                self.bg2_any[y, x] += bool(diff_all[box].any())
        frac = np.zeros((28, 32))
        for y in range(28):
            for x in range(32):
                frac[y, x] = diff_all[max(0, 8 * y - 1):min(h, 8 * y + 7), 8 * x:8 * x + 8].mean()
        self.grids.append((what, frac))
        # the brightening band: colour 1 of palette 2 inside (x $40-$BF, lines $10-$2F) against outside
        rgb = lambda v: ((v & 31) << 3, (v >> 5 & 31) << 3, (v >> 10 & 31) << 3)   # noqa: E731
        lines = {}
        for ln in range(0x08, 0x38):           # every BG2 cell colour 1: the colour on screen line by line, in the band's
            row = a[ln, 0x40:0xC0][diff_all[ln, 0x40:0xC0]]        # columns where BG2 shows
            if len(row):
                lines[ln] = sorted({tuple(int(v) for v in p) for p in row})[:2]
        outside = a[0x60:, :][diff_all[0x60:, :]]
        self.band.append(dict(what=what, colour1=rgb(cg[33]), by_line=lines,
                              outside=sorted({tuple(int(v) for v in p) for p in outside})[:2],
                              picture_pixels_in_band=int(diff[0x10:0x30, 0x40:0xC0].sum())))

    def press(self, b, after=40):
        self.e.run(4, hold=[b])
        self.e.run(after)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    s = Screen(rom, out)
    e = s.e
    M.play(e, "w1800 START w240 w120" if is_sa1(rom) else "w1500 START w240 START w240 w120", out)
    e.screenshot(out / "setup.png")
    for k in range(10):                         # idle
        e.run(30)
        s.sample(f"idle {k}", picture=k % 3 == 0)
    for line in range(10):                      # each line: its choices stepped and back (Play Mode stays Regular
        for k in range(6):                      # Season, so the photos show), then down
            s.press("RIGHT", 50)
            s.sample(f"line {line} right {k}", picture=k in (0, 2, 5))
            if k == 1:
                e.screenshot(out / f"line_{line:02d}.png")
        for k in range(6):
            s.press("LEFT", 50)
            s.sample(f"line {line} left {k}", picture=False)
        if line:
            e.run(120, hold=["RIGHT"])
            s.sample(f"line {line} right held")
        s.press("DOWN", 50)
        s.sample(f"line {line} down")
    for k in range(40):                         # left alone (the demo countdown is $12C0 frames)
        e.run(90)
        s.sample(f"idle long {k}", picture=k % 4 == 0)
    for k in range(14):
        s.press("UP", 30)
        s.sample(f"up {k}", picture=False)
    for k in range(20):
        e.run(60)
        s.sample(f"idle end {k}", picture=k % 5 == 0)
    e.screenshot(out / "setup_end.png")
    # owners of $1000-$3FFF: the tiles the maps name
    own = {}
    for name, base in (("BG1", 0x2000), ("BG2", 0x1000)):
        for t, pals in s.refs[name].items():
            for a in range(base + 16 * t, base + 16 * t + 16):
                if 0x1000 <= a < 0x4000:
                    own.setdefault(a, set()).add(f"{name} tile {t} pal {sorted(pals)}")

    def runs(mask, lo, hi):
        out_, start = [], None
        for a in range(lo, hi + 1):
            on = a < hi and mask[a]
            if on and start is None:
                start = a
            elif not on and start is not None:
                out_.append(f"${start:04X}-${a - 1:04X}")
                start = None
        return out_
    back = s.log[0]["backchars"]
    pic = sorted(t for t, p in s.refs["BG2"].items() if 2 in p and t >= back)
    R = dict(rom=Path(rom).name, sa1=is_sa1(rom), backchars=back, picture_tiles=[pic[0], pic[-1], len(pic)] if pic else None,
             picture_vram=f"${0x1000 + 16 * back:04X}-${0x1000 + 16 * (pic[-1] + 1) - 1:04X}" if pic else None,
             samples=s.samples, picture_samples=s.pic_samples,
             nonzero_22C0_2FFF=runs(s.ever_nz, 0x22C0, 0x3000), changed_1000_3FFF=runs(s.changed, 0x1000, 0x4000),
             nonzero_3000_3FFF=runs(s.ever_nz, 0x3000, 0x4000),
             named_in_22C0_2FFF=sorted({o for a in range(0x22C0, 0x3000) for o in own.get(a, ())}),
             named_1680_22BF_not_picture=sorted({o for a in range(0x1000 + 16 * back, 0x22C0) for o in own.get(a, ()) if "BG2" not in o or "pal [2]" not in o}),
             named_1680_2FFF_not_picture=sorted({o for a in range(0x1000 + 16 * back, 0x3000) for o in own.get(a, ()) if "BG2" not in o}),
             bg1_tiles=[min(s.refs["BG1"]), max(s.refs["BG1"])], bg2_tiles=[min(s.refs["BG2"]), max(s.refs["BG2"])],
             map_palettes={n: sorted({p for v in s.refs[n].values() for p in v}) for n in s.refs},
             colour_rows_changed={r: sorted(v) for r, v in sorted(s.cg_changes.items())},
             colours_first=[[f"{c:04X}" for c in s.cg_first[16 * r:16 * r + 16]] for r in range(8)],
             never_shows=[[x for x in range(32) if s.visible[y, x] == 0] for y in range(28)],
             bg2_never_seen=[[x for x in range(32) if s.bg2_any[y, x] == 0] for y in range(28)],
             bg2_always_whole=[[x for x in range(32) if s.bg2_seen[y, x] == s.pic_samples] for y in range(28)],
             always_shows=[[x for x in range(32) if s.visible[y, x] == s.pic_samples] for y in range(28)],
             band=s.band[:3] + s.band[-2:], log=s.log)
    (out / "setup_back.json").write_text(json.dumps(R, indent=1, default=list))
    # The screen at rest (Regular Season, the idle steps: a team or mode change redraws the top for a few frames,
    # other modes hide the photos): each cell's share of pixels where BG2 shows, the least and the most
    reg = [g for w, g in s.grids if w.startswith("idle")]
    lo, hi = np.min(reg, axis=0), np.max(reg, axis=0)
    R["regular_season"] = dict(steps=len(reg),
                               hidden_always=[[x for x in range(32) if hi[y, x] == 0] for y in range(28)],
                               shown_whole_always=[[x for x in range(32) if lo[y, x] == 1] for y in range(28)],
                               least_share=[[round(float(v), 2) for v in row] for row in lo])
    (out / "setup_back.json").write_text(json.dumps(R, indent=1, default=list))
    np.save(out / "vram_first.npy", s.first)
    # a picture of the grid (at rest): green = BG2 shows whole at every step, yellow = in part (text, edges) or
    # at some steps only, red = never a pixel
    img = Image.open(out / "setup.png").convert("RGB").resize((512, 448), Image.NEAREST)
    ov = Image.new("RGB", img.size)
    px = ov.load()
    for y in range(28):
        for x in range(32):
            c = (0, 200, 0) if lo[y, x] == 1 else (220, 0, 0) if hi[y, x] == 0 else (220, 200, 0)
            for yy in range(16 * y, 16 * y + 16):
                for xx in range(16 * x, 16 * x + 16):
                    px[xx, yy] = c
    Image.blend(img, ov, 0.45).save(out / "picture_cells.png")
    print(json.dumps({k: v for k, v in R.items() if k not in ("log", "never_shows", "always_shows", "band", "regular_season", "bg2_never_seen", "bg2_always_whole", "colours_first", "colour_rows_changed", "nonzero_22C0_2FFF", "nonzero_3000_3FFF", "changed_1000_3FFF")}, indent=1, default=list))


def compare(ret, new, out):
    """A setup background build's run against retail's (both made by main, the same ROM family): pass / fail lines
    for what must stay as it was, and the screens side by side. The picture may use BG2 tiles from backchars + 1 up to
    512 ($1680-$2FFF) and colour row 2; everything else on the screen is checked against retail: MenuBack's tiles,
    BG1's map and tiles at the first sample (the photos left out: they change with the teams), the colour rows but 2,
    which rows change while the screen runs, the brightening band, and the cells the picture can't show in."""
    A, B = (json.loads((d / "setup_back.json").read_text()) for d in (ret, new))
    va, vb = (np.load(d / "vram_first.npy") for d in (ret, new))
    res = []

    def check(name, ok, detail=""):
        res.append(("PASS" if ok else "FAIL", name, detail))
    back = A["backchars"]
    check("backchars as retail", B["backchars"] == back, str(B["backchars"]))
    pt = B["picture_tiles"] or [0, 0, 0]
    check("picture tiles within backchars + 1 .. 512 ($1680-$2FFF)", pt[0] > back and pt[1] <= 512, f"{pt} {B['picture_vram']}")
    check("nothing but BG2 (the picture) names $1680-$2FFF", not B.get("named_1680_2FFF_not_picture"), str(B.get("named_1680_2FFF_not_picture")))
    check("MenuBack's tiles (BG2 0-103) unchanged", bool((va[0x1000:0x1000 + 16 * back] == vb[0x1000:0x1000 + 16 * back]).all()))
    check("BG1's map unchanged (first sample)", bool((va[0:32 * 28] == vb[0:32 * 28]).all()))
    pic0 = 0x2000 + 16 * A["log"][0]["picchars"]
    same = va[0x3000:pic0] == vb[0x3000:pic0]
    check(f"BG1's tiles $3000-${pic0 - 1:04X} unchanged (the photos from ${pic0:04X} left out)", bool(same.all()),
          f"{int((~same).sum())} words differ")
    # the picture's cells name tiles past backchars (on palette 2, or 3 / 4 when the map word carries palette bits:
    # SetupScreen adds $0800); a cell naming a MenuBack tile must be retail's own
    pic = lambda v: (int(v) & 0x3FF) > back  # noqa: E731
    pairs = list(zip(va[0x400:0x400 + 32 * 28], vb[0x400:0x400 + 32 * 28]))
    off = [i for i, (x, y) in enumerate(pairs) if not pic(x) and not pic(y) and x != y]
    freed = [i for i, (x, y) in enumerate(pairs) if pic(x) and not pic(y)]     # retail's picture there, MenuBack now
    check(f"BG2 cells left to MenuBack as retail's ({len(freed)} cells retail's picture covered left to MenuBack too)", not off,
          ", ".join(f"row {i // 32} col {i % 32}" for i in off[:8]))
    pals = sorted({int(y) >> 10 & 7 for y in vb[0x400:0x400 + 32 * 28] if pic(y)})
    check("the picture's cells on palettes 2-4 only (rows 3 and 4 are MenuBack's, fixed on this screen)", set(pals) <= {2, 3, 4}, str(pals))
    for r in (0, 1, 3, 4, 5, 6, 7):
        check(f"colour row {r} as retail (first sample)", A["colours_first"][r] == B["colours_first"][r], " ".join(B["colours_first"][r]))
    rows = lambda R: sorted(R["colour_rows_changed"])  # noqa: E731
    check("the same colour rows change while the screen runs (rows 2-4 never)", rows(A) == rows(B) and not {"2", "3", "4"} & set(rows(B)), str(rows(B)))
    def lift(R):           # the colour added in the band, line by line (against the same colour outside it; 255 clips)
        b0 = R["band"][0]
        o = b0["outside"][0]
        k = next(k for k in (1, 0, 2) if o[k] < 100)    # a channel low enough not to clip, green first
        return {ln: v[0][k] - o[k] for ln, v in b0["by_line"].items()}
    check("brightening band: the same lift line by line", lift(A) == lift(B), str(sorted(set(lift(B).values()))))
    ha, hb = A["regular_season"]["hidden_always"], B["regular_season"]["hidden_always"]
    check("the cells never showing BG2 as retail", ha == hb, str([(y, r) for y, r in enumerate(hb) if r != ha[y]]))
    out.mkdir(parents=True, exist_ok=True)
    shots = ["setup.png"] + sorted(p.name for p in ret.glob("line_*.png")) + ["setup_end.png", "picture_cells.png"]
    shots = [x for x in shots if (ret / x).exists() and (new / x).exists()]
    sheet = Image.new("RGB", (2 * 512, 448 * len(shots)))
    for i, x in enumerate(shots):
        for j, d in enumerate((ret, new)):
            sheet.paste(Image.open(d / x).convert("RGB").resize((512, 448), Image.NEAREST), (512 * j, 448 * i))
    sheet.save(out / "setup_compare.png")
    lines = [f"{a}  {b}" + (f"  [{c}]" if c and a == "FAIL" else "") for a, b, c in res]
    (out / "setup_compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    else:
        main()
