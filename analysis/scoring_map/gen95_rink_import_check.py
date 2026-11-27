"""The NHL '95 (Genesis) rink for an import (2026-11-27, for NOSE4Web's rink import on NHL '95, as on NHL '94:
gen_rink_import_check.py): how many tiles the rink may have, the centre-ice logo's tiles, kept rows or cells, the
reverse-angle rink, the priority bits.

From the ROM: Rinktilelist ($C4A7C: palette offset, map offset, then the tiles' count word, $1D4 = 468, and the
plain tiles; the map 48 x 85 at $C8586) and RevRinkTilelist ($16060E: a bare map, 48 x 85, no tiles of its own);
for each map the tiles its cells name, the cells with the priority bit, the cells naming the last 24 tiles (where
LoadHomeTeamGfx puts the home team's centre-ice graphics: d4 - $18), and every ROM long holding the two addresses
(the instructions to repoint).

Played (Boston at home against the next team; the computer on both sides): from the opening faceoff, the VRAM
character bases (rinkvrcset, EASNcset, energybarchars, animchars, spritechars, framerchars, smallfontchars,
ExtraChars, ReplayIconChars) and the VDP's planes; then every 30 frames the core's video memory (Genesis Plus GX's
state, gen_score_logo_check.VRAM_AT): the highest non-zero tile below plane B ($C000 = tile $600) and the tile ranges
that change; plane B's 32 ring rows against the map row each holds (rows from Vpos as updatescroll queues them:
the cells' words, priority bits, any cell the game changed), the map rows ever shown; the rink tiles 0-467 against
the opening faceoff's. Moments: play, Instant Replay and its reverse angle (sflags4 bit 4: plane B against
RevRinkTilelist), the pause menu's other screens (RestoreGameScreen), the end of period 1 (intermission screens) and
the start of period 2. Screenshots at each.

python gen95_rink_import_check.py ROM OUT
python gen95_rink_import_check.py teams ROM OUT HOME   (the centre-ice logo's tiles for one home team)
python gen95_rink_import_check.py compare RETAIL_OUT BUILD_OUT OUT   (a rink import build against retail: compare())"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

from emu import Emu
from gen_score_logo_check import VRAM_AT
import gen95_rink_logo_check as RL

RINK, REV = 0xC4A7C, 0x16060E
VARS = {"rinkvrcset": 0xAC2A, "EASNcset": 0xAC32, "energybarchars": 0xAC28, "animchars": 0xAC2C,
        "spritechars": 0xAC36, "framerchars": 0xDC30, "smallfontchars": 0xAC16, "ExtraChars": 0xAC38,
        "ReplayIconChars": 0xAC3A}
VPOS, HPOS, SFLAGS4, GSP, CLOCK, HOMETEAM = 0xB932, 0xB936, 0xBEFA, 0xC020, 0xC022, 0xBF54
SFLAGS, SFLAGS2, FACEOFFVRC = 0xBEF2, 0xBEF4, 0xAC2E     # sflags bit 0 paused (sfpz), 7 horizontal (sfhor); sflags2
                                                          # bit 3 a replay (sf2replay)


def maps(rom):
    p, m = struct.unpack(">II", rom[RINK:RINK + 8])
    count = struct.unpack(">H", rom[RINK + 8:RINK + 10])[0]
    w, h = struct.unpack(">HH", rom[RINK + m:RINK + m + 4])
    rink = list(struct.unpack(f">{w * h}H", rom[RINK + m + 4:RINK + m + 4 + 2 * w * h]))
    rw, rh = struct.unpack(">HH", rom[REV:REV + 4])
    rev = list(struct.unpack(f">{rw * rh}H", rom[REV + 4:REV + 4 + 2 * rw * rh]))
    return dict(count=count, w=w, h=h, pal_at=RINK + p, map_at=RINK + m, rink=rink, rev=rev, rw=rw, rh=rh)


def describe(words, w, count):
    tiles = sorted({x & 0x7FF for x in words})
    pri = [(i // w, i % w) for i, x in enumerate(words) if x & 0x8000]
    logo = [(i // w, i % w, (x & 0x7FF) - (count - 24)) for i, x in enumerate(words) if count - 24 <= (x & 0x7FF) < count]

    def box(cells):
        if not cells:
            return None
        rs, cs = [c[0] for c in cells], [c[1] for c in cells]
        return dict(n=len(cells), rows=[min(rs), max(rs)], cols=[min(cs), max(cs)])
    rows = {}
    for r, c in pri:
        rows.setdefault(r, []).append(c)
    return dict(tiles_named=len(tiles), highest=tiles[-1], unused=[t for t in range(count) if t not in set(tiles)],
                priority=box(pri), priority_rows={r: [min(cs), max(cs), len(cs)] for r, cs in sorted(rows.items())},
                logo=box(logo), logo_cells=logo, palettes=sorted({x >> 13 & 3 for x in words}))


def refs(rom, values):
    out = {}
    for v in values:
        k = v.to_bytes(4, "big")
        out[f"${v:X}"] = [f"${i - 2:X} ({rom[i - 2:i].hex()})" for i in range(2, len(rom) - 4) if rom[i:i + 4] == k]
    return out


def vram(e, with_display=False):
    st = bytes(e.serialize())
    vr = np.frombuffer(st[VRAM_AT:VRAM_AT + 0x10000], dtype="<u2").copy()
    lit = any(st[VRAM_AT + 0x10000:VRAM_AT + 0x10080])                        # colour memory not all black
    return (vr, bool(st[VRAM_AT + 0x10101] & 0x40) and lit) if with_display else vr   # register 1 bit 6: display on


class Watch:
    def __init__(self, e, M, out):
        self.e, self.M, self.out = e, M, out
        self.ref = None
        self.hi = 0
        self.rows_seen = {"rink": set(), "rev": set()}
        self.cell_diffs = []
        self.tile_diffs = []
        self.log = []
        self.n = 0
        self.views = {}
        self.play_vb = None
        self.flags = set()
        self.hi_at = None
        self.after = []                         # (what, the tiles from the rink's end to plane B) at each check

    def check(self, what):
        e, M = self.e, self.M
        vr, shown = vram(e, True)
        tiles = vr[:0xC000 >> 1].reshape(-1, 16)
        nz = np.nonzero(tiles.any(axis=1))[0]
        if int(nz[-1]) > self.hi:
            self.hi = int(nz[-1])
            self.hi_at = (what, {k: e.w(a) for k, a in VARS.items()}, e.w(FACEOFFVRC))
        vb = e.l(0xAC52) & 0xFFFFFF                  # VBint: the play handler (VBlank) while the rink is up
        if self.play_vb is None:
            self.play_vb = vb
        replay = bool(e.b(SFLAGS2) & 8)
        # disflags bit 2 (dfng): graphics loading; another vblank handler: another screen
        view = ("display off" if not shown or e.w(0xBB7E) & 4 else "other screen" if vb != self.play_vb else
                "horizontal" if e.b(SFLAGS) & 0x80 else "replay" if replay else
                "paused" if e.b(SFLAGS) & 1 else "vertical")
        self.flags.add((what, view, f"{vb:X}", e.b(SFLAGS), e.b(SFLAGS2), e.b(SFLAGS4)))
        self.views[view] = self.views.get(view, 0) + 1
        if view not in ("vertical", "replay"):       # the pause scoreboard and other screens load their own tiles
            return
        self.after.append((what, tiles[M["count"]:0x600].copy()))
        if self.ref is None:
            self.ref = tiles[:M["count"]].copy()
        d = np.nonzero((tiles[:M["count"]] != self.ref).any(axis=1))[0]
        if len(d):
            self.tile_diffs.append((what, bool(e.b(SFLAGS2) & 8), [int(d[0]), int(d[-1]), len(d)], e.b(SFLAGS), e.w(GSP), e.w(CLOCK)))
            if len(self.tile_diffs) <= 4:
                e.screenshot(self.out / f"tile_diff_{len(self.tile_diffs)}.png")
        rev = bool(e.b(SFLAGS4) & 0x10)
        words, key = (M["rev"], "rev") if rev else (M["rink"], "rink")
        # updatescroll: d1 = (Vpos + 16) / 8; the ring holds map rows 30 - d1 to 61 - d1, map row r in ring row r & 31
        top = 0x1E - ((e.sw(VPOS) + 16) >> 3)
        bad = 0
        for k in range(32):
            row = top + k
            if not 0 <= row < M["h"]:
                continue
            ring = row & 0x1F
            plane = vr[(0xC000 >> 1) + 64 * ring:(0xC000 >> 1) + 64 * ring + M["w"]]
            want = words[row * M["w"]:(row + 1) * M["w"]]
            if list(map(int, plane)) == want:
                self.rows_seen[key].add(row)
            elif k in range(2, 29):                  # rows on screen (the ring's edges may be mid-update)
                bad += 1
                diff = [c for c in range(M["w"]) if int(plane[c]) != want[c]]
                self.cell_diffs.append((what, key, row, len(diff), [(c, f"{int(plane[c]):04X}", f"{want[c]:04X}") for c in diff[:3]]))
        self.log.append(dict(what=what, rev=rev, vpos=e.sw(VPOS), rows_bad=bad,
                             vars={k: e.w(a) for k, a in VARS.items()}))
        self.n += 1


def main():
    rom_path, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rom = rom_path.read_bytes()
    M = maps(rom)
    R = dict(rom=rom_path.name, count=M["count"], map=[M["w"], M["h"]], pal_at=f"${M['pal_at']:X}", map_at=f"${M['map_at']:X}",
             rink=describe(M["rink"], M["w"], M["count"]), rev=describe(M["rev"], M["rw"], M["count"]),
             rev_cells_differ=sum(a != b for a, b in zip(M["rink"], M["rev"])),
             references=refs(rom, [RINK, RINK + 8, REV]))
    e = RL.opening(str(rom_path), 1, 2)
    if e is None:
        raise SystemExit("no opening faceoff")
    st = bytes(e.serialize())
    reg = list(st[VRAM_AT + 0x10100:VRAM_AT + 0x10120])
    R["vdp"] = dict(planeA=f"${(reg[2] & 0x38) << 10:X}", window=f"${(reg[3] & 0x3E) << 10:X}", planeB=f"${(reg[4] & 7) << 13:X}",
                    sprites=f"${(reg[5] & 0x7F) << 9:X}", hscroll=f"${(reg[13] & 0x3F) << 10:X}", size=f"{reg[16]:02X}")
    R["chars_at_faceoff"] = {k: e.w(a) for k, a in VARS.items()}
    W = Watch(e, M, out)
    W.check("faceoff")
    e.screenshot(out / "faceoff.png")
    vmin, vmax = e.sw(VPOS), e.sw(VPOS)

    def play(n, what, shots=0):
        nonlocal vmin, vmax
        for k in range(n // 30):
            e.run(30)
            vmin, vmax = min(vmin, e.sw(VPOS)), max(vmax, e.sw(VPOS))
            W.check(what)
            if shots and k % shots == 0:
                e.screenshot(out / f"{what}_{k:03d}.png")
    play(3600, "play", shots=20)
    # Instant Replay, its reverse angle (as gen95_rink_logo_check --replay)
    for b, w in (("START", 120), ("DOWN", 30), ("C", 300)):
        e.run(6, hold=[b])
        e.run(w)
    W.check("replay")
    e.run(6, hold=["START"])
    e.run(60)
    e.run(6, hold=["C"])
    e.run(120)
    W.check("reverse angle")
    e.screenshot(out / "reverse_0.png")
    e.run(6, hold=["C"])
    for k in range(10):
        e.run(40)
        W.check("reverse angle")
        if k % 3 == 0:
            e.screenshot(out / f"reverse_{k + 1}.png")
    for k in range(8):                                # back out to play
        e.run(6, hold=["START"])
        e.run(90)
        if not e.b(SFLAGS4) & 0x10 and k > 2:
            break
    play(600, "after replay")
    # pause screens: START, each item a few steps down, A/C into it, out
    for item in range(1, 6):
        e.run(6, hold=["START"])
        e.run(90)
        for _ in range(item):
            e.run(6, hold=["DOWN"])
            e.run(20)
        e.run(6, hold=["C"])
        e.run(200)
        e.screenshot(out / f"pause_item{item}.png")
        for _ in range(4):
            e.run(6, hold=["START"])
            e.run(120)
        play(300, f"after pause item {item}")
    # the end of period 1 and the start of period 2
    e.setw(CLOCK, 3)
    p0 = e.w(GSP)
    for f in range(9000):
        e.run(1, hold=["START"] if f % 240 == 0 else [])
        if f % 30 == 0:
            W.check("period end / intermission" if e.w(GSP) == p0 else "period 2")
        if f % 600 == 0:
            e.screenshot(out / f"intermission_{f:04d}.png")
        if e.w(GSP) != p0 and f % 30 == 0 and e.w(CLOCK) < 590:
            break
    play(1800, "period 2", shots=20)
    R["vpos_range"] = [vmin, vmax]
    R["rows_seen"] = {k: [min(v), max(v), len(v)] if v else None for k, v in W.rows_seen.items()}
    R["rows_never_seen"] = {k: [r for r in range(M["h"]) if r not in v] for k, v in W.rows_seen.items()}
    R["highest_nonzero_tile_below_planeB"] = f"${W.hi:X} ({W.hi})"
    R["rink_tile_changes"] = W.tile_diffs[:40]
    R["plane_cells_unlike_map"] = W.cell_diffs[:40]
    R["checks"] = W.n
    R["views"] = W.views
    R["flags_seen"] = sorted(W.flags)
    R["highest_at"] = W.hi_at
    R["vram_D000_DBFF_nonzero_words"] = int(np.count_nonzero(vram(e)[0xD000 >> 1:0xDC00 >> 1]))
    R["chars_seen"] = sorted({json.dumps(x["vars"], sort_keys=True) for x in W.log})
    (out / "rink95.json").write_text(json.dumps(R, indent=1, default=list))
    np.savez_compressed(out / "after_tiles.npz", tiles=np.array([t for _, t in W.after]),
                        labels=np.array([w for w, _ in W.after]))
    print(json.dumps({k: R[k] for k in ("count", "map", "vdp", "chars_at_faceoff", "highest_nonzero_tile_below_planeB",
                                        "vpos_range", "rows_seen", "rev_cells_differ", "references")}, indent=1))
    for k in ("rink", "rev"):
        print(k, {x: R[k][x] for x in ("tiles_named", "highest", "priority", "logo", "palettes")}, "unused", len(R[k]["unused"]))


def teams(rom_path, out, home):
    """`teams`: the opening faceoff with HOME at home: the centre-ice logo's tiles (the rink's last 24) in VRAM and
    a screenshot (one team a process: the core is a single DLL)."""
    out.mkdir(parents=True, exist_ok=True)
    M = maps(Path(rom_path).read_bytes())
    e = RL.opening(rom_path, home, 1 if home != 1 else 2)
    if e is None:
        raise SystemExit("no opening faceoff")
    e.run(60)
    tiles = vram(e)[:0xC000 >> 1].reshape(-1, 16)
    np.save(out / f"logo_{home:02d}.npy", tiles[M["count"] - 24:M["count"]])
    e.screenshot(out / f"logo_{home:02d}.png")


def compare(ret, new, out):
    """A rink import build's runs against retail's (main and teams on each, the same presses; the retail side a scratch
    copy with the build's checksum changes, so both power on alike and play the same frames): pass / fail lines.
    Plane B as the build's own maps in every check (normal and reverse); the tiles from the rink's end to plane B (EASN,
    energy bar, crowd, sprites, framer, fonts, the faceoff close-up and the other ExtraChars) as retail's check by
    check; the centre-ice logo's 24 tiles as retail's for each home team run; the screenshots: the pixels that differ
    from retail's, as 8 x 8 cells grouped into boxes (only the edited squares may differ, and nothing in the reverse
    angle or off the rink)."""
    from PIL import Image
    A, B = (json.loads((d / "rink95.json").read_text()) for d in (ret, new))
    res = []

    def check(name, ok, detail=""):
        res.append(("PASS" if ok else "FAIL", name, detail))
    check("tile count as retail", A["count"] == B["count"], str(B["count"]))
    # (retail itself has a few: the check catches period 2's start while the screen is being rebuilt)
    key = lambda x: [y[:4] for y in x]  # noqa: E731
    check("plane B as the build's own maps in every check, or where retail's is not its own too",
          key(B["plane_cells_unlike_map"]) == key(A["plane_cells_unlike_map"]),
          str(B["plane_cells_unlike_map"][:3]))
    check("reverse angle seen", "rev" in B["rows_seen"] and bool(B["rows_seen"]["rev"]), str(B["rows_seen"]))
    check("rink tiles changed only where retail's did", B["rink_tile_changes"] == A["rink_tile_changes"], str(B["rink_tile_changes"][:2]))
    check("priority cells as retail (both maps)", A["rink"]["priority"] == B["rink"]["priority"] and A["rev"]["priority"] == B["rev"]["priority"])
    ta, tb = (np.load(d / "after_tiles.npz") for d in (ret, new))
    same_n = len(ta["tiles"]) == len(tb["tiles"])
    bad = [i for i in range(min(len(ta["tiles"]), len(tb["tiles"]))) if not (ta["tiles"][i] == tb["tiles"][i]).all()]
    check(f"tiles after the rink as retail's, check by check ({len(tb['tiles'])} checks)", same_n and not bad,
          f"differ at {[str(tb['labels'][i]) for i in bad[:5]]}")
    logos = sorted(p.name for p in ret.glob("logo_*.npy") if (new / p.name).exists())
    lbad = [n for n in logos if not (np.load(ret / n) == np.load(new / n)).all()]
    check(f"centre-ice logo tiles as retail's ({len(logos)} home teams)", logos and not lbad, str(lbad))
    shots = sorted(p.name for p in ret.glob("*.png") if (new / p.name).exists())
    rows = []
    for n in shots:
        a = np.asarray(Image.open(ret / n).convert("RGB")).astype(int)
        b = np.asarray(Image.open(new / n).convert("RGB")).astype(int)
        if a.shape != b.shape:                                # a different screen mode (H32 / H40): not the same moment
            rows.append((n, -1, [("size", a.shape[1], b.shape[1])]))
            continue
        d = (a != b).any(axis=2)
        cells = {(int(y) // 8, int(x) // 8) for y, x in zip(*np.nonzero(d))}
        boxes = []                                            # 8 x 8 cells joined into boxes (4-neighbours)
        left = set(cells)
        while left:
            stack, comp = [left.pop()], []
            while stack:
                c = stack.pop()
                comp.append(c)
                for nb in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
                    if nb in left:
                        left.remove(nb)
                        stack.append(nb)
            ys, xs = [c[0] for c in comp], [c[1] for c in comp]
            boxes.append((8 * (max(xs) - min(xs) + 1), 8 * (max(ys) - min(ys) + 1), 8 * min(xs), 8 * min(ys)))
        rows.append((n, int(d.sum()), boxes))
    out.mkdir(parents=True, exist_ok=True)
    (out / "screens.json").write_text(json.dumps(rows, indent=1))
    rev_bad = [r for r in rows if r[0].startswith("reverse") and r[1]]
    other_bad = [r for r in rows if r[1] > 0 and not r[0].startswith("reverse") and any(w > 40 or h > 24 for w, h, _, _ in r[2])]
    sized = [r for r in rows if r[1] < 0]
    check("every screenshot pair the same screen mode", not sized, str(sized[:4]))
    check(f"reverse-angle screenshots identical to retail's ({sum(r[0].startswith('reverse') for r in rows)})", not rev_bad, str(rev_bad[:2]))
    check("other screenshots differ only in patch-sized boxes (up to 40 x 24: a 32 x 16 square off the 8-pixel grid)",
          not other_bad, str(other_bad[:2]))
    lines = [f"{a}  {b}" + (f"  [{c}]" if c and a == "FAIL" else "") for a, b, c in res]
    lines.append("screens that differ: " + ", ".join(f"{n} {px} px {[(w, h) for w, h, _, _ in bx]}" for n, px, bx in rows if px > 0))
    (out / "compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    elif sys.argv[1] == "teams":
        teams(sys.argv[2], Path(sys.argv[3]), int(sys.argv[4]))
    else:
        main()
