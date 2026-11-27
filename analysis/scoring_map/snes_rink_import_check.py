"""The SNES rink for an import (2026-11-27, for NOSE4Web's rink import on the SNES, as on NHL '94 Genesis:
gen_rink_import_check.py; retail and the SA-1 / 2 MB builds): how many tiles the rink may have, the cells
BuildRinkMap overwrites, the rows the game reads from, the palette rows that are the teams'.

setupice (mode 1; BG2's map at VRAM word $400 (64 x 32), BG2's tiles from $1000, BG1's from $2000, sprites $6000)
unpacks IceRinkTiles to BG2 tile 0 on and sets centericechars to their count; LoadCenterIce puts the home team's
centre-ice tiles there (CenterIceTable) and faceoffvrcset after them; then FaceOffTiles, RinkLogoTiles (EASNcset),
RefTilesHor (refcharshor), RefTiles (refchars), a blank tile, the small font, the framer, the big font, the score
tiles and TeamBlocksTiles (ExtraChars after them), each where the one before ended. BuildRinkMap unpacks IceRinkMap
to rinkmapbuf ($7F:C800, 48 x 113 words after a 6-byte header) and pastes the logo's map (+ centericechars,
palette 5) around word $10B6.

`teams`: for each home team (HomeTeam $1C98 set on Game Setup, the next team visiting), into play: those character
bases, the logo's cells in rinkmapbuf (cells naming tiles centericechars to faceoffvrcset - 1), the colour memory
(CGDATA in the state's PPU block, big-endian, at +64), a screenshot of centre ice.

`play` (the first team, or HOME): a game watched every 30 frames: video memory (Snes9x memory 3): the highest non-zero
word below $6000, the BG1 / BG2 tiles the maps name (BG2 $1000 + 16 t, BG1 $2000 + 16 t) and where they lie among the
sets, each BG2 video row (map columns 0-31 at $400 + 32 v, 32-47 at $800 + 32 v) matched to the rinkmapbuf row it
holds; rinkmapbuf against the first sample (cells the game changes); the rink's and logo's tiles against the first
sample's in play (the crowd's tiles 1-65 apart: showcrowd rewrites them from CrowdTiles). Moments: play, the pause scoreboard (SetHor:
rows 85-112), the instant replay (its icon from rows 85-92, columns 32-39), each pause item, the end of period 1, the
intermission and period 2.

python snes_rink_import_check.py ROM OUT [teams|play] [HOME]"""
import ctypes as C
import json
import struct
import sys
from pathlib import Path

import numpy as np

import menu_shots as M

HOMETEAM, VISTEAM, GSP, CLOCK, SFLAGS, PSITEM, VPOS = 0x1C98, 0x1C9A, 0x1630, 0x1632, 0x15D8, 0x0D15, 0x0D37
MAP, W, H = 0x1C800 + 6, 48, 113
CROWD = range(1, 66)          # BG2 tiles showcrowd rewrites from CrowdTiles (CrowdAnimTable's VRAM tiles: groups .1-.21)
CHARS = {"centericechars": 0x35B8, "faceoffvrcset": 0x35BA, "EASNcset": 0x35B0, "refcharshor": 0x35C8,
         "refchars": 0x35CA, "blankchar": 0x35D0, "smallfontchars": 0x35B6, "framercset": 0x35BC,
         "BigFontchars": 0x35AE, "scorechars": 0x35CE, "ExtraChars": 0x35C2, "charofs": 0x35AA}


def is_sa1(rom):
    d = Path(rom).read_bytes()
    return len(d) > 0x7FD6 and d[0x7FD5] == 0x23


class Snes:
    def __init__(self, rom):
        self.rom = rom
        self.e = M.emulator(rom)
        self.vr = (C.c_ubyte * self.e.lib.retro_get_memory_size(3)).from_address(self.e.lib.retro_get_memory_data(3))

    def words(self):
        return np.frombuffer(bytes(self.vr), dtype="<u2").copy()

    def raw(self):
        n = self.e.lib.retro_serialize_size()
        buf = (C.c_ubyte * n)()
        self.e.lib.retro_serialize(buf, n)
        return bytes(buf)

    def load(self, raw):
        self.e.lib.retro_unserialize(C.cast(C.create_string_buffer(raw, len(raw)), C.c_void_p), len(raw))

    def cgram(self):
        r = self.raw()
        i = r.index(b"PPU:")
        return [struct.unpack_from(">H", r, i + 11 + 64 + 2 * k)[0] for k in range(256)]

    def rmap(self):
        return [self.e.w(MAP + 2 * i) for i in range(W * H)]

    def chars(self):
        return {k: self.e.w(a) for k, a in CHARS.items()}

    def press(self, b, after=40):
        self.e.run(4, hold=[b])
        self.e.run(after)

    def to_setup(self):
        M.play(self.e, "w1800 START w240 w120" if is_sa1(self.rom) else "w1500 START w240 START w240 w120", Path("."))

    def into_play(self):
        """From Game Setup: START (the controller screen), START (the matchups), START until the clock runs."""
        e = self.e
        self.press("START", 240)
        self.press("START", 400)
        for _ in range(30):
            c = e.w(CLOCK)
            e.run(240)
            if e.w(CLOCK) != c and not e.w(SFLAGS) & 1:
                return True
            self.press("START", 60)
        return False


def logo_cells(m, ch):
    lo, hi = ch["centericechars"], ch["faceoffvrcset"]
    cells = [(i // W, i % W) for i, v in enumerate(m) if lo <= (v & 0x3FF) < hi]
    if not cells:
        return None
    rs, cs = [r for r, _ in cells], [c for _, c in cells]
    return dict(n=len(cells), rows=[min(rs), max(rs)], cols=[min(cs), max(cs)],
                palettes=sorted({m[r * W + c] >> 10 & 7 for r, c in cells}), tiles=hi - lo)


def teams(rom, out):
    s = Snes(rom)
    s.to_setup()
    base = s.raw()
    n = 32 if is_sa1(rom) and Path(rom).stat().st_size > 0x180000 else 28
    res = []
    for t in range(n):
        s.load(base)
        s.e.setw(HOMETEAM, t)
        s.e.setw(VISTEAM, (t + 1) % n)
        s.e.run(30)
        ok = s.into_play()
        ch = s.chars()
        m = s.rmap()
        cg = s.cgram()
        row = dict(team=t, home=s.e.w(HOMETEAM), vis=s.e.w(VISTEAM), in_play=ok, chars=ch, logo=logo_cells(m, ch),
                   cgram_rows=[[f"{c:04X}" for c in cg[16 * r:16 * r + 16]] for r in range(16)])
        res.append(row)
        s.e.screenshot(out / f"team{t:02d}.png")
        print(t, ok, ch["centericechars"], ch["faceoffvrcset"], ch["ExtraChars"], row["logo"], flush=True)
    rows_vary = sorted({r for a in res for b in res for r in range(16) if a["cgram_rows"][r] != b["cgram_rows"][r]})
    sizes = [r["chars"]["faceoffvrcset"] - r["chars"]["centericechars"] for r in res]
    summary = dict(rom=Path(rom).name, teams=n, rink_tiles=sorted({r["chars"]["centericechars"] for r in res}),
                   logo_tiles=[min(sizes), max(sizes)], logo_max_team=sizes.index(max(sizes)),
                   ExtraChars=[min(r["chars"]["ExtraChars"] for r in res), max(r["chars"]["ExtraChars"] for r in res)],
                   logo_box=[min(r["logo"]["rows"][0] for r in res if r["logo"]), max(r["logo"]["rows"][1] for r in res if r["logo"]),
                             min(r["logo"]["cols"][0] for r in res if r["logo"]), max(r["logo"]["cols"][1] for r in res if r["logo"])],
                   colour_rows_that_change_with_teams=rows_vary)
    (out / "teams.json").write_text(json.dumps(dict(summary=summary, teams=res), indent=1))
    print(json.dumps(summary, indent=1))


def play(rom, out, home):
    s = Snes(rom)
    e = s.e
    s.to_setup()
    n = 32 if is_sa1(rom) and Path(rom).stat().st_size > 0x180000 else 28
    e.setw(HOMETEAM, home)
    e.setw(VISTEAM, (home + 1) % n)
    e.run(30)
    if not s.into_play():
        raise SystemExit("not into play")
    ch0 = s.chars()
    m0 = s.rmap()
    R = dict(rom=Path(rom).name, home=home, chars=ch0, logo=logo_cells(m0, ch0))
    play_rows = m0[:85 * W]
    used = {v & 0x3FF for v in play_rows}
    R["map"] = dict(tiles_named_rows_0_84=len(used), highest=max(used),
                    unused_below_rink_end=[t for t in range(ch0["centericechars"]) if t not in {v & 0x3FF for v in m0}],
                    crowd_cells=len([v for v in play_rows if (v & 0x3FF) in CROWD]),
                    crowd_rows=sorted({i // W for i, v in enumerate(play_rows) if (v & 0x3FF) in CROWD}),
                    priority_cells=len([v for v in play_rows if v & 0x2000]),
                    priority_rows=sorted({i // W for i, v in enumerate(play_rows) if v & 0x2000}),
                    palettes={p: len([v for v in play_rows if v >> 10 & 7 == p]) for p in range(8)},
                    rows_85_112_tiles=len({v & 0x3FF for v in m0[85 * W:]}))
    hi = [0, None]
    hi_by = {}
    pal_use = {}
    rink_ref = None
    rink_lost = []
    crowd_seen = set()
    refs = {"BG1": {}, "BG2": {}}
    rows_seen, map_changes, log = set(), [], []

    def check(what):
        nonlocal rink_ref
        vr = s.words()
        nz = np.nonzero(vr[:0x6000])[0]
        if len(nz) and int(nz[-1]) > hi[0]:
            hi[0], hi[1] = int(nz[-1]), what
        cat = what.split(" ")[0] if not what.startswith("pause item") else what
        if len(nz):
            hi_by[cat] = max(hi_by.get(cat, 0), int(nz[-1]))
        rink = vr[0x1000:0x1000 + 16 * ch0["faceoffvrcset"]].reshape(-1, 16)   # the rink's and the logo's tiles
        if rink_ref is None:
            rink_ref = rink.copy()
        elif what.split(" ")[0] in ("play", "period") and not e.w(SFLAGS) & 1:
            d = np.nonzero((rink != rink_ref).any(axis=1))[0]
            crowd_seen.update(int(x) for x in d if x in CROWD)
            d = [int(x) for x in d if x not in CROWD]
            if d:
                rink_lost.append((what, len(d), d[:12]))
        for name, mbase, tbase in (("BG1", 0x0000, 0x2000), ("BG2", 0x0400, 0x1000)):
            for v in vr[mbase:mbase + 0x800 if name == "BG2" else mbase + 0x400]:
                t = int(v) & 0x3FF
                a = tbase + 16 * t
                if vr[a:a + 16].any():
                    refs[name].setdefault(t, set()).add(what.split(" ")[0])
                    if what.split(" ")[0] in ("play", "period"):
                        pal_use.setdefault((name, int(v) >> 10 & 7), set()).add(t)
        m = s.rmap()
        rows = {tuple(m[r * W:(r + 1) * W]): r for r in range(H)}
        shown = []
        for v in range(32):
            words = tuple(int(x) for x in vr[0x400 + 32 * v:0x400 + 32 * v + 32]) + tuple(int(x) for x in vr[0x800 + 32 * v:0x800 + 32 * v + 16])
            if words in rows:
                shown.append(rows[words])
        if not e.w(SFLAGS) & 1:
            rows_seen.update(shown)
        d = [i for i, (a, b) in enumerate(zip(m, m0)) if a != b]
        if d:
            map_changes.append((what, len(d), [(i // W, i % W) for i in d[:4]]))
        log.append(dict(what=what, paused=bool(e.w(SFLAGS) & 1), hor=None, rows_shown=len(shown)))

    for k in range(120):                                      # 3,600 frames of play
        e.run(30)
        check("play")
        if k % 30 == 0:
            e.screenshot(out / f"play_{k:03d}.png")
    s.press("START", 120)                                     # the pause scoreboard (SetHor)
    check("scoreboard")
    e.screenshot(out / "scoreboard.png")
    vr = s.words()
    m = s.rmap()
    left = [int(x) for x in vr[0x400:0x400 + 32]]
    R["scoreboard_row0_is_map_row"] = next((r for r in range(H) if m[r * W:r * W + 32] == left), None)
    for item in range(1, 14):                                 # each pause item, in and out
        for _ in range(40):
            if e.w(PSITEM) == item:
                break
            s.press("DOWN", 20)
        s.press("A", 300)
        check(f"pause item {item}")
        e.screenshot(out / f"pause_item{item:02d}.png")
        if item == 1:                                         # the instant replay: its icon
            for b in ("LEFT", "RIGHT"):
                e.run(120, hold=[b])
            check("replay")
            e.screenshot(out / "replay.png")
        for kk in range(10):
            s.press("START" if kk % 2 == 0 else "A", 200)
            if e.w(SFLAGS) & 1 and not e.w(SFLAGS) & 0x0800:
                break
        check(f"after item {item}")
    s.press("START", 120)                                     # back to play
    for k in range(20):
        e.run(30)
        check("play again")
    e.setw(CLOCK, 3)                                          # the end of period 1, the intermission, period 2
    p0 = e.w(GSP)
    for f in range(9000):
        e.run(1, hold=["START"] if f % 240 == 0 and f > 300 else [])
        if f % 30 == 0:
            check("intermission" if e.w(GSP) == p0 else "period 2")
        if f % 900 == 0:
            e.screenshot(out / f"intermission_{f:04d}.png")
        if e.w(GSP) != p0 and f % 30 == 0 and e.w(CLOCK) < 290 and not e.w(SFLAGS) & 1:
            break
    for k in range(60):
        e.run(30)
        check("period 2")
    ch = s.chars()

    def where(name, t):
        a = (0x2000 if name == "BG1" else 0x1000) + 16 * t
        t2 = (a - 0x1000) // 16                               # as a BG2 tile number (the sets' numbering)
        sets = sorted(((v, k) for k, v in ch.items() if k != "charofs"), reverse=True)
        return next((k for v, k in sets if t2 >= v), "rink (IceRinkTiles)")
    R["highest_nonzero_below_6000"] = [f"${hi[0]:04X}", hi[1]]
    R["bg_refs_by_set"] = {name: {} for name in refs}
    for name, d in refs.items():
        for t, whats in d.items():
            k = where(name, t)
            x = R["bg_refs_by_set"][name].setdefault(k, [10 ** 6, -1, set()])
            x[0], x[1] = min(x[0], t), max(x[1], t)
            x[2] |= whats
    R["bg2_highest_tile_named"] = max(refs["BG2"])
    R["highest_nonzero_by_moment"] = {k: f"${v:04X}" for k, v in hi_by.items()}
    R["rink_tiles_changed_in_play"] = rink_lost[:10]
    R["rink_tiles_ever_changed"] = sorted({t for x in rink_lost for t in x[2]})
    R["crowd_tiles_seen_changing"] = [min(crowd_seen), max(crowd_seen), len(crowd_seen)] if crowd_seen else None
    R["palettes_in_play"] = {f"{n} palette {p}": sorted({where(n, t) for t in ts}) for (n, p), ts in sorted(pal_use.items())}
    R["bg1_highest_vram_named"] = f"${0x2000 + 16 * max(refs['BG1']) + 15:04X}"
    R["map_rows_shown_in_play"] = [min(rows_seen), max(rows_seen), len(rows_seen)] if rows_seen else None
    R["map_rows_never_shown_in_play"] = [r for r in range(H) if r not in rows_seen]
    R["map_changes"] = map_changes[:20]
    R["chars_end"] = ch
    (out / "play.json").write_text(json.dumps(R, indent=1, default=lambda x: sorted(x) if isinstance(x, set) else str(x)))
    print(json.dumps({k: v for k, v in R.items() if k != "map_rows_never_shown_in_play"}, indent=1,
                     default=lambda x: sorted(x) if isinstance(x, set) else str(x)))
    print("never shown in play:", R["map_rows_never_shown_in_play"])


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[3] if len(sys.argv) > 3 else "teams"
    if mode == "teams":
        teams(rom, out)
    else:
        play(rom, out, int(sys.argv[4]) if len(sys.argv) > 4 else 11)


if __name__ == "__main__":
    main()
