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

python snes_rink_import_check.py ROM OUT [teams|play|goal] [HOME]
python snes_rink_import_check.py ROM OUT logos HOME ...
python snes_rink_import_check.py compare BASE_OUT BUILD_OUT OUT [EXPECTED.png]   (a rink build against the base: compare())
python snes_rink_import_check.py compare-goal BASE_OUT BUILD_OUT OUT   (the forced goal's dumps: compare_goal())"""
import ctypes as C
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

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


def dump(s, out, tag):
    """The video memory, colour memory, rinkmapbuf and character bases now, for `compare`."""
    np.savez_compressed(out / f"dump_{tag}.npz", vram=s.words(), cgram=np.array(s.cgram(), dtype=np.uint16),
                        rmap=np.array(s.rmap(), dtype=np.uint16), chars=json.dumps(s.chars()),
                        bg1=s.words()[0x0000:0x0400], score=np.array([s.e.w(0x178E), s.e.w(0x1790)]))


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

    dump(s, out, "faceoff")                                   # the opening faceoff, just dropped
    goals = list(s.e.w(a) for a in (0x178E, 0x1790))
    for k in range(120):                                      # 3,600 frames of play
        e.run(30)
        check("play")
        if k % 30 == 0:
            e.screenshot(out / f"play_{k:03d}.png")
        g = [s.e.w(a) for a in (0x178E, 0x1790)]
        if g != goals:                                        # a goal: its moment and the next faceoff
            goals = g
            dump(s, out, f"goal_{k:03d}")
            e.screenshot(out / f"goal_{k:03d}.png")
    s.press("START", 120)                                     # the pause scoreboard (SetHor)
    check("scoreboard")
    e.screenshot(out / "scoreboard.png")
    dump(s, out, "scoreboard")
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
            dump(s, out, "replay")
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


def tiles4(vr, tbase, n=1024):
    """Every 4bpp tile from word tbase as an (n, 8, 8) array of colour numbers."""
    w = vr[tbase:tbase + 16 * n].reshape(n, 16).astype(np.int64)
    lo, hi = w[:, :8], w[:, 8:]
    out = np.zeros((n, 8, 8), np.int64)
    for x in range(8):
        b = 7 - x
        out[:, :, x] = (lo >> b & 1) | (lo >> (b + 8) & 1) << 1 | (hi >> b & 1) << 2 | (hi >> (b + 8) & 1) << 3
    return out


def render(vr, cg, entries, w, h, tbase, charofs=0):
    """Map entries (w x h) drawn with the tiles from tbase and the colour memory: RGB, colour 0 left as -1."""
    T = tiles4(vr, tbase)
    rgb = np.array([[(int(c) & 31) << 3, (int(c) >> 5 & 31) << 3, (int(c) >> 10 & 31) << 3] for c in cg], dtype=np.int64)
    img = np.full((8 * h, 8 * w, 3), -1, np.int64)
    for i, e in enumerate(entries[:w * h]):
        e = int(e)
        t = ((e & 0x3FF) + charofs) & 0x3FF
        p = T[t]
        if e & 0x4000:
            p = p[:, ::-1]
        if e & 0x8000:
            p = p[::-1]
        col = rgb[16 * (e >> 10 & 7) + p]
        col[p == 0] = -1
        y, x = divmod(i, w)
        img[8 * y:8 * y + 8, 8 * x:8 * x + 8] = col
    return img


def cells_differ(a, b, w, h, ea=None, eb=None):
    """Cells whose pixels differ; with the two maps' entries, cells naming the crowd's tiles (1-65, animated, caught
    at a different frame in each run) are compared by their map words instead."""
    d = (a != b).any(axis=2)
    out = []
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if ea is not None and (int(ea[i]) & 0x3FF in CROWD or int(eb[i]) & 0x3FF in CROWD):
                if int(ea[i]) != int(eb[i]) and (int(ea[i]) & 0x3FF in CROWD) != (int(eb[i]) & 0x3FF in CROWD):
                    out.append((y, x))
                continue
            if d[8 * y:8 * y + 8, 8 * x:8 * x + 8].any():
                out.append((y, x))
    return out


def compare(base, build, out, expected=None):
    """A rink build's dumps against the base ROM's (both made by `play` and `logos`): the rink drawn from each ROM's
    own rinkmapbuf, tiles and colours (so the two games need not stay in step), cell by cell; the palette, priority and
    flip bits; the sets after the rink by content (each starts as many tiles later as the rink grew); the pause
    scoreboard's rink (BG2 from its map at that moment) and the replay icon (BG1, cells 2-9 of rows 2-9); the crowd's
    tiles changing; the highest video memory used; and, given the editor's expected picture (rows 0-84), the build's
    rink against it outside the logo and the team-coloured cells."""
    out.mkdir(parents=True, exist_ok=True)
    res = []

    def check(name, ok, detail=""):
        res.append(("PASS" if ok else "FAIL", name, detail))
    L = lambda d, tag: np.load(d / f"dump_{tag}.npz")  # noqa: E731
    fa, fb = L(base, "faceoff"), L(build, "faceoff")
    ca, cb = json.loads(str(fa["chars"])), json.loads(str(fb["chars"]))
    grow = cb["centericechars"] - ca["centericechars"]
    check(f"rink tiles {ca['centericechars']} -> {cb['centericechars']} (+{grow}); every set after it {grow} later",
          all(cb[k] - ca[k] == grow for k in ca if k not in ("charofs", "centericechars")),
          str({k: cb[k] - ca[k] for k in ca if k != "charofs"}))
    ra, rb = fa["rmap"], fb["rmap"]
    ia = render(fa["vram"], fa["cgram"], ra, W, H, 0x1000)
    ib = render(fb["vram"], fb["cgram"], rb, W, H, 0x1000)
    diff = cells_differ(ia, ib, W, H, ra, rb)
    bits = [i for i in range(W * H) if (int(ra[i]) & 0x3C00) != (int(rb[i]) & 0x3C00)]
    check("every cell's palette and priority bits as the base", not bits, str([(i // W, i % W) for i in bits[:8]]))
    flips = [(i // W, i % W) for i in range(W * H) if (int(ra[i]) ^ int(rb[i])) & 0xC000]
    check(f"flip bits as the base outside the edited cells ({len(flips)} edited cells reuse squares flipped)",
          set(flips) <= set(diff), str(sorted(set(flips) - set(diff))[:8]))
    kept = [c for c in diff if c[0] >= 85]
    check("rows 85-112 (the scoreboard's rink, the replay icon) drawn as the base", not kept, str(kept[:8]))
    logo = {(r, c) for r in range(43, 49) for c in range(20, 28)}
    crowd = {(i // W, i % W) for i in range(85 * W) if int(ra[i]) & 0x3FF in CROWD}
    check("the logo's cells drawn as the base", not [c for c in diff if c in logo])
    check("the crowd's cells drawn as the base (tiles 1-65 at this moment)", not [c for c in diff if c in crowd],
          str([c for c in diff if c in crowd][:8]))
    R = dict(cells_differing=len(diff), rows=sorted({r for r, _ in diff}), cells=diff)
    sa, sb = fa["vram"], fb["vram"]
    for k in ("centericechars", "faceoffvrcset", "EASNcset", "refcharshor", "refchars", "smallfontchars", "framercset",
              "BigFontchars", "scorechars"):
        nxt = sorted(v for kk, v in ca.items() if kk != "charofs" and v > ca[k])
        n = (nxt[0] if nxt else ca[k] + 16) - ca[k]
        a = sa[0x1000 + 16 * ca[k]:0x1000 + 16 * (ca[k] + n)]
        b = sb[0x1000 + 16 * cb[k]:0x1000 + 16 * (cb[k] + n)]
        check(f"set {k} ({n} tiles, from {ca[k]} now {cb[k]}) unchanged", len(a) == len(b) and bool((a == b).all()))
    if expected:
        ex = np.asarray(Image.open(expected).convert("RGB")).astype(np.int64)
        lv = lambda x: np.rint(x * 31 / 255)  # noqa: E731
        team = {(i // W, i % W) for i in range(85 * W) if int(rb[i]) >> 10 & 7 in (2, 3)}
        bad = []
        for y in range(85):
            for x in range(W):
                if (y, x) in logo or (y, x) in team:
                    continue
                a = ib[8 * y:8 * y + 8, 8 * x:8 * x + 8]
                e = ex[8 * y:8 * y + 8, 8 * x:8 * x + 8]
                opaque = (a >= 0).all(axis=2)
                if (np.abs(lv(a[opaque]) - lv(e[opaque])) > 1).any():
                    bad.append((y, x))
        exp_cells = [(y, x) for y in range(85) for x in range(W) if (y, x) not in logo and (y, x) not in team
                     and (np.abs(lv(np.where(ia[8 * y:8 * y + 8, 8 * x:8 * x + 8] >= 0, ia[8 * y:8 * y + 8, 8 * x:8 * x + 8], 0)) - lv(ex[8 * y:8 * y + 8, 8 * x:8 * x + 8]))[(ia[8 * y:8 * y + 8, 8 * x:8 * x + 8] >= 0).all(axis=2)] > 1).any()]
        check("the build's rink is the expected picture (outside the logo and the team-coloured cells)", not bad, str(bad[:8]))
        check("the cells that differ from the base are the ones the expected picture changes", sorted(set(diff) - logo - team) == exp_cells,
              f"build {len(set(diff) - logo - team)}, expected {len(exp_cells)}")
        R["expected_cells"] = len(exp_cells)
    for tag, mbase, tbase, region in (("scoreboard", 0x400, 0x1000, None), ("replay", 0x0000, 0x2000, (2, 10, 2, 10))):
        try:
            da, db = L(base, tag), L(build, tag)
        except FileNotFoundError:
            check(f"{tag}: dumped in both", False)
            continue
        ea, eb = da["vram"][mbase:mbase + 32 * 32], db["vram"][mbase:mbase + 32 * 32]
        if region:
            y0, y1, x0, x1 = region
            idx = [y * 32 + x for y in range(y0, y1) for x in range(x0, x1)]
            ea, eb = ea[idx], eb[idx]
            w, h = x1 - x0, y1 - y0
            oa, ob = json.loads(str(da["chars"]))["charofs"], json.loads(str(db["chars"]))["charofs"]
        else:
            w, h, oa, ob = 32, 28, 0, 0
            ea, eb = ea[:32 * 28], eb[:32 * 28]
        A = render(da["vram"], da["cgram"], ea, w, h, tbase)
        B = render(db["vram"], db["cgram"], eb, w, h, tbase)
        d = cells_differ(A, B, w, h, ea, eb) if not region else cells_differ(A, B, w, h)
        check(f"{tag}: drawn as the base ({w} x {h} cells; the crowd's by map word)", not d, str(d[:8]))
        Image.fromarray(np.clip(np.concatenate([A, B], axis=1), 0, 255).astype(np.uint8)).save(out / f"{tag}_base_build.png")
    for name, d in (("base", base), ("build", build)):
        P = json.loads((d / "play.json").read_text())
        R[f"{name}_highest"] = P["highest_nonzero_below_6000"]
        R[f"{name}_crowd"] = P["crowd_tiles_seen_changing"]
        R[f"{name}_rink_tiles_changed_in_play"] = P["rink_tiles_ever_changed"]
        R[f"{name}_map_changes"] = len(P["map_changes"])
    check("the crowd animates (tiles 1-65 rewritten in play)", bool(R["build_crowd"]), str(R["build_crowd"]))
    check("no other rink tile changes in play", not R["build_rink_tiles_changed_in_play"], str(R["build_rink_tiles_changed_in_play"][:8]))
    hi = int(R["build_highest"][0][1:], 16)
    check(f"video memory below the sprites ($6000): highest used {R['build_highest'][0]} ({R['build_highest'][1]}), "
          f"{(0x6000 - 1 - hi) // 16} tiles to spare", hi < 0x6000)
    teams_ = sorted({p.name[5:-4] for p in build.glob("dump_team*.npz")} & {p.name[5:-4] for p in base.glob("dump_team*.npz")})
    for t in teams_:
        da, db = L(base, t), L(build, t)
        A = render(da["vram"], da["cgram"], da["rmap"], W, H, 0x1000)
        B = render(db["vram"], db["cgram"], db["rmap"], W, H, 0x1000)
        d = cells_differ(A, B, W, H, da["rmap"], db["rmap"])
        c1, c2 = json.loads(str(da["chars"])), json.loads(str(db["chars"]))
        n = c1["faceoffvrcset"] - c1["centericechars"]
        lg = (da["vram"][0x1000 + 16 * c1["centericechars"]:0x1000 + 16 * c1["faceoffvrcset"]] ==
              db["vram"][0x1000 + 16 * c2["centericechars"]:0x1000 + 16 * c2["faceoffvrcset"]]).all()
        check(f"home team {t[4:]}: logo ({n} tiles) and its cells as the base; other differing cells only the edit's",
              bool(lg) and not [c for c in d if c in logo] and set(d) <= set(diff), f"{len(d)} cells; logo tiles same {bool(lg)}")
    Image.fromarray(np.clip(np.concatenate([ia, ib], axis=1), 0, 255).astype(np.uint8)).save(out / "rink_base_build.png")
    lines = [f"{a}  {b}" + (f"  [{c}]" if c and a == "FAIL" else "") for a, b, c in res]
    (out / "compare.txt").write_text("\n".join(lines) + "\n")
    (out / "compare.json").write_text(json.dumps(R, indent=1, default=str))
    print("\n".join(lines))


XPOS, YPOS, XFRAC, YFRAC, XVEL, YVEL, ZPOS = 0x0D55, 0x0DB7, 0x0D77, 0x0DD9, 0x0EC3, 0x0EE3, 0x0DF9
POSITION, PFGOAL, PUCKC, CARRIER2, GOALS, PUCK = 0x0F43, 0x14C3, 0x0AD9, 0x0AE7, 0x178E, 14


def forced_goal(rom, out, home):
    """`goal`: a home goal forced (snes_organ_resume_check.goal_song's way: the away goalie moved aside, the puck sent
    into the net the home team attacks) 240 frames into play; then every frame through the goal display until the
    faceoff after it and 600 frames of play: the highest video memory word below $6000 (and when), the character
    bases, dumps at the goal + 30, + 120, + 300 frames, at the highest moment and at the faceoff after."""
    s = Snes(rom)
    e = s.e
    s.to_setup()
    n = 32 if is_sa1(rom) and Path(rom).stat().st_size > 0x180000 else 28
    e.setw(HOMETEAM, home)
    e.setw(VISTEAM, (home + 1) % n)
    e.run(30)
    if not s.into_play():
        raise SystemExit("not into play")
    e.run(240)
    hk = next(k for k in range(6) if e.w(POSITION + 2 * k) not in (0, 0xFFFF))
    up = 1 if e.w(PFGOAL + 2 * hk) else -1
    gk = next(k for k in range(6, 12) if e.w(POSITION + 2 * k) == 0)
    g0 = e.w(GOALS)

    def put(k, x, y, vx=0, vy=0):
        for a, v in ((XPOS, x), (YPOS, y), (XFRAC, 0), (YFRAC, 0), (XVEL, vx), (YVEL, vy)):
            e.setw(a + 2 * k, v & 0xFFFF)
    t_goal = None
    for f in range(600):
        if f < (1 if is_sa1(rom) else 60) and e.w(GOALS) == g0:
            put(gk, 90, 240 * up)
            put(PUCK, 0, 240 * up, 0, 0x2000 * up)
            e.setw(ZPOS + 2 * PUCK, 0)
            e.setw(PUCKC, 0xFFFF)
            e.setw(CARRIER2, 0xFFFF)
        e.run(1)
        if e.w(GOALS) != g0:
            t_goal = f
            break
    R = dict(rom=Path(rom).name, home=home, goal=t_goal is not None, goals=[g0, e.w(GOALS)], up=up)
    if t_goal is None:
        (out / "goal.json").write_text(json.dumps(R, indent=1))
        raise SystemExit("no goal")
    hi, hi_f, faceoff, trace = 0, None, None, []
    for f in range(4000):
        e.run(1)
        vr = s.words()
        nz = np.nonzero(vr[:0x6000])[0]
        top = int(nz[-1]) if len(nz) else 0
        if top > hi:
            hi, hi_f = top, f
            dump(s, out, "goal_peak")
        if f in (30, 120, 300):
            dump(s, out, f"goal_{f:03d}")
            e.screenshot(out / f"goal_{f:03d}.png")
        if f % 30 == 0:
            trace.append(dict(f=f, top=f"${top:04X}", clock=e.w(CLOCK), stopped=e.w(0x15D6), chars=s.chars()))
        if faceoff is None and f > 120 and e.w(0x15D6) == 0 and e.w(CLOCK) != trace[-1]["clock"]:
            faceoff = f                                    # the clock running again: the faceoff after the goal
            dump(s, out, "goal_faceoff")
            e.screenshot(out / "goal_faceoff.png")
        if faceoff is not None and f - faceoff >= 600:
            break
    R.update(highest=f"${hi:04X}", highest_frame_after_goal=hi_f, margin_tiles=(0x6000 - 1 - hi) // 16,
             faceoff_after=faceoff, chars_at_end=s.chars(), trace=trace)
    (out / "goal.json").write_text(json.dumps(R, indent=1))
    print(json.dumps({k: v for k, v in R.items() if k != "trace"}, indent=1))


def compare_goal(base, build, out):
    """`compare-goal`: the forced goal's dumps against the base's: the tiles past ExtraChars at each moment (any set
    the goal display loads, by content: the build's start as many tiles later as the rink grew), every set's start,
    the rink drawn at the faceoff after, and the highest video memory with its margin below $6000."""
    out.mkdir(parents=True, exist_ok=True)
    res = []

    def check(name, ok, detail=""):
        res.append(("PASS" if ok else "FAIL", name, detail))
    A, B = (json.loads((d / "goal.json").read_text()) for d in (base, build))
    check("a home goal scored in both", A["goal"] and B["goal"], f"{A['goals']} / {B['goals']}")
    L = lambda d, tag: np.load(d / f"dump_{tag}.npz")  # noqa: E731
    for tag in ("goal_030", "goal_120", "goal_300", "goal_peak", "goal_faceoff"):
        try:
            da, db = L(base, tag), L(build, tag)
        except FileNotFoundError:
            check(f"{tag}: dumped in both", False)
            continue
        ca, cb = json.loads(str(da["chars"])), json.loads(str(db["chars"]))
        grow = cb["centericechars"] - ca["centericechars"]
        moved = {k: cb[k] - ca[k] for k in ca if k not in ("charofs", "centericechars")}
        check(f"{tag}: every set after the rink {grow} later", all(v == grow for v in moved.values()), str(moved))
        va, vb = da["vram"], db["vram"]

        def named(v, c):            # tiles past ExtraChars that BG1 (+256) or BG2 cells name, as offsets from it
            t = {int(x) & 0x3FF for x in v[0x400:0xC00]} | {(int(x) & 0x3FF) + 256 for x in v[0:0x400]}
            return sorted(k - c["ExtraChars"] for k in t if k >= c["ExtraChars"] and k < 0x500)
        oa, ob = named(va, ca), named(vb, cb)
        same = oa == ob and all((va[0x1000 + 16 * (ca["ExtraChars"] + k):][:16] == vb[0x1000 + 16 * (cb["ExtraChars"] + k):][:16]).all() for k in oa)
        stale = int(np.count_nonzero(va[0x1000 + 16 * (ca["ExtraChars"] + (max(oa) + 1 if oa else 0)):0x6000]))
        check(f"{tag}: the tiles past ExtraChars the maps name ({len(oa)} / {len(ob)}) the same content"
              f" (the base's {stale} words past them that nothing names left aside)", same, f"{oa[:12]} / {ob[:12]}")
        sets_ok = all((va[0x1000 + 16 * ca[k]:0x1000 + 16 * ca[k] + 16 * 4] == vb[0x1000 + 16 * cb[k]:0x1000 + 16 * cb[k] + 16 * 4]).all()
                      for k in ("faceoffvrcset", "EASNcset", "refcharshor", "refchars", "smallfontchars", "BigFontchars", "scorechars"))
        check(f"{tag}: each set's first tiles the same content", sets_ok)
        if tag == "goal_faceoff":
            ia = render(va, da["cgram"], da["rmap"], W, H, 0x1000)
            ib = render(vb, db["cgram"], db["rmap"], W, H, 0x1000)
            d = cells_differ(ia, ib, W, H, da["rmap"], db["rmap"])
            check("the faceoff after the goal: the rink as the base but the edit's cells", True, f"{len(d)} cells differ")
            res[-1] = (res[-1][0], res[-1][1] + f" ({len(d)} cells differ, rows {sorted({r for r, _ in d})[:12]})", "")
    hb = int(B["highest"][1:], 16)
    check(f"highest video memory through the goal display {A['highest']} (base) / {B['highest']} (build): "
          f"{(0x6000 - 1 - hb) // 16} tiles below the sprites", hb < 0x6000)
    lines = [f"{a}  {b}" + (f"  [{c}]" if c and a == "FAIL" else "") for a, b, c in res]
    (out / "compare_goal.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def team_dumps(rom, out, homes):
    """`logos`: for each home team given, Game Setup to the opening faceoff: a dump and a screenshot."""
    s = Snes(rom)
    s.to_setup()
    base = s.raw()
    n = 32 if is_sa1(rom) and Path(rom).stat().st_size > 0x180000 else 28
    for t in homes:
        s.load(base)
        s.e.setw(HOMETEAM, t)
        s.e.setw(VISTEAM, (t + 1) % n)
        s.e.run(30)
        ok = s.into_play()
        dump(s, out, f"team{t:02d}")
        s.e.screenshot(out / f"team{t:02d}.png")
        print(t, ok, s.chars()["centericechars"], s.chars()["faceoffvrcset"], flush=True)


def main():
    if sys.argv[1] == "compare-goal":
        compare_goal(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
        return
    if sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5] if len(sys.argv) > 5 else None)
        return
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[3] if len(sys.argv) > 3 else "teams"
    if mode == "goal":
        forced_goal(rom, out, int(sys.argv[4]) if len(sys.argv) > 4 else 11)
    elif mode == "logos":
        team_dumps(rom, out, [int(t) for t in sys.argv[4:]])
    elif mode == "teams":
        teams(rom, out)
    else:
        play(rom, out, int(sys.argv[4]) if len(sys.argv) > 4 else 11)


if __name__ == "__main__":
    main()
