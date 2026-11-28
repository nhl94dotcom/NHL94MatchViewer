"""The side-on (horizontal) scoreboard screen's picture, NHL '94 and NHL '95 Genesis (2026-11-27, for NOSE4Web's ads on the
scoreboard screen: export, edit, import as for the rink).

NHL '94: SetHor (scoreboard94.asm) draws IceRinkHorMap with dobitmap (32 x 28 from cell 0,0, d5 = 0: no palette lines
loaded, tiles from rinkvrcset), then USBoard (printscores1's .sbscreen and the penalty-box lines) prints over it with
CC_Font2Pri. The picture is found from SetHor's `movea.l #IceRinkHorMap,a1` / `movea.l #IceRinkHorTiles,a2` pair
($227C x / $247C x + 8); the jim header (+0 the palette, +4 the map: width, height, words), the tiles' count word
(bit 15 clear: raw 4bpp tiles; set: packed) and every long in the ROM equal to the picture's, its tiles' or its map's
address.

Played (penalties on, the computer on both sides) to each place the screen shows: the pause menu (Pausemode_pall),
then play on until sflags $C2EC bit 7 (sfhor) rises: the intermission at a period's end, a penalty's side-on view
otherwise (the instant replay's exit calls SetHor too, back to the same pause screen). At each, from the core's saved state (gen_score_logo_check.VRAM_AT):
- the plane holding the picture and, cell by cell, whether it still names the picture's tile there (else what
  USBoard or the menu put in its place);
- the picture showing: its tiles filled with colour 1, 2 and 3 in turn (a frame each from the same state); pixels that
  differ are the picture's. Then every cell of its plane pointed at the picture's first tile: where that plane can
  show at all (the window, plane A, sprites over it). Per cell: whole, in part, never;
- the colour lines: the (line, colour) pairs the picture's shown pixels use, and those every other cell (other
  planes, the picture plane's other tiles) and sprite on screen use; colour memory each frame for 300 frames: what
  changes while the screen shows;
- the tile sets (rinkvrcset and the sets after it: crowd, faceoff, framer, EASN, team blocks, sprites, ExtraChars):
  what follows the picture's tiles, so the most it may have.
NHL '95 has no IceRinkHor (sfhor only picks the side-on referee's tiles): its static search finds nothing and its pause
screen is shot for the record.

python gen_hor_board_check.py ROM OUT [94|95]
python gen_hor_board_check.py ads ROM OUT   (a picture build's moments, and a control's: ads())
python gen_hor_board_check.py compare CONTROL_OUT BUILD_OUT OUT [EXPECTED.png]   (compare())"""
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

import gen_ot_check as G
from emu import Emu
from gen_score_logo_check import VRAM_AT

SFLAGS, OPTPEN, GSP, CLOCK = 0xC2EC, 0xD056, 0xC466, 0xC468
CHAIN = {"BigFontchars": 0xB010, "smallfontchars": 0xB012, "smallfont2chars": 0xB014, "energybarchars": 0xB016,
         "rinkvrcset": 0xB018, "crowdvrcset": 0xB01A, "faceoffvrcset": 0xB01C, "framercset": 0xB01E,
         "EASNcset": 0xB020, "basetileoffset": 0xB022, "spritechars": 0xB024, "ExtraChars": 0xB026}


def rl(r, a):
    return struct.unpack(">I", r[a:a + 4])[0]


def static(rom):
    r = Path(rom).read_bytes()
    hits = []
    for a in range(0, len(r) - 20, 2):
        if r[a:a + 2] == b"\x22\x7c":
            x = rl(r, a + 2)
            for b in range(a + 6, a + 16, 2):
                if r[b:b + 2] == b"\x24\x7c" and rl(r, b + 2) == x + 8:
                    hits.append((a, x, b))
    if not hits:
        return None
    at, img, at2 = hits[0]
    # ClrHor, just before SetHor, reloads the vertical rink (movea.l #Rinktiles,a2): its count word is the room the
    # side-on picture's tiles have from rinkvrcset (the next set, EASN, follows the vertical rink)
    rink = next(((b, rl(r, b + 2)) for b in range(at - 2, at - 0x100, -2) if r[b:b + 2] == b"\x24\x7c"), None)
    pal, mp = img + rl(r, img), img + rl(r, img + 4)
    w, h = struct.unpack(">HH", r[mp:mp + 4])
    words = list(struct.unpack(f">{w * h}H", r[mp + 4:mp + 4 + 2 * w * h]))
    cnt = struct.unpack(">H", r[img + 8:img + 10])[0]
    refs = {}
    for name, v in (("picture", img), ("tiles", img + 8), ("map", mp), ("palette", pal)):
        refs[name] = [f"${a - 2:X} ({r[a - 2:a].hex()})" for a in range(2, len(r) - 4, 2) if rl(r, a) == v]
    return dict(raw=r, setHor_lea=f"${at:X}", tiles_lea=f"${at2:X}", picture=img,
                vertical_rink=dict(lea=f"${rink[0]:X}", tiles_at=f"${rink[1]:X}",
                                   tiles=struct.unpack(">H", r[rink[1]:rink[1] + 2])[0] & 0x7FFF) if rink else None, map_at=mp, palette_at=pal, w=w, h=h,
                tiles_word=cnt, packed=bool(cnt & 0x8000), tiles=cnt & 0x7FFF, map=words,
                map_max_tile=max(x & 0x7FF for x in words), map_lines=sorted({x >> 13 & 3 for x in words}),
                priority_cells=sum(1 for x in words if x & 0x8000), flipped_cells=sum(1 for x in words if x & 0x1800),
                palette=[struct.unpack(">H", r[pal + 2 * i:pal + 2 * i + 2])[0] for i in range(64)], references=refs)


def gen_word(v9):
    r, g, b = v9 & 7, v9 >> 3 & 7, v9 >> 6 & 7
    return b << 9 | g << 5 | r << 1


class Screen:
    def __init__(self, rom, out, S):
        self.e = Emu(rom)
        self.out = out
        self.S = S
        self.moments = {}

    def state(self):
        st = bytes(self.e.serialize())
        vr = np.frombuffer(st[VRAM_AT:VRAM_AT + 0x10000], dtype="<u2").copy()
        cram = [st[VRAM_AT + 0x10000 + 2 * i] | st[VRAM_AT + 0x10001 + 2 * i] << 8 for i in range(64)]
        reg = list(st[VRAM_AT + 0x10100:VRAM_AT + 0x10120])
        return st, vr, cram, reg

    def poke(self, words):
        """Write VRAM words {word index: value} into the core's state and load it (the state keeps VRAM as
        little-endian words)."""
        st = bytearray(self.e.serialize())
        for i, v in words.items():
            st[VRAM_AT + 2 * i] = v & 0xFF
            st[VRAM_AT + 2 * i + 1] = v >> 8
        self.e.unserialize(bytes(st))

    def shot(self, name):
        p = self.out / f"{name}.png"
        self.e.screenshot(p)
        return np.asarray(Image.open(p).convert("RGB")).astype(int)

    def moment(self, name):
        e, S = self.e, self.S
        st, vr, cram, reg = self.state()
        planes = {"A": (reg[2] & 0x38) << 10, "W": (reg[3] & 0x3E) << 10, "B": (reg[4] & 7) << 13}
        pw = {0: 32, 1: 64, 3: 128}.get(reg[16] & 3, 32)
        base = e.w(CHAIN["rinkvrcset"])
        chain = {k: e.w(a) for k, a in CHAIN.items()}
        ntiles = S["tiles"]
        # the plane holding the picture: the most cells naming map tile + base
        best = None
        for pn, addr in planes.items():
            w = 32 if pn == "W" else pw
            hit = sum(1 for y in range(28) for x in range(32)
                      if (int(vr[(addr >> 1) + y * w + x]) & 0x7FF) == (S["map"][y * 32 + x] & 0x7FF) + base)
            if best is None or hit > best[1]:
                best = (pn, hit, addr, w)
        pn, _, addr, w = best
        cells = [[int(vr[(addr >> 1) + y * w + x]) for x in range(32)] for y in range(28)]
        own = [[(cells[y][x] & 0x7FF) == (S["map"][y * 32 + x] & 0x7FF) + base for x in range(32)] for y in range(28)]
        others = sorted({cells[y][x] & 0x7FF for y in range(28) for x in range(32) if not own[y][x]})
        # the picture's tiles in VRAM against the ROM's (raw tiles): any rewritten while it shows (the clock?)
        changed_tiles = []
        if not S["packed"]:
            rom_tiles = np.frombuffer(S["raw"][S["picture"] + 10:S["picture"] + 10 + 32 * ntiles], dtype=">u2")
            for t in range(ntiles):
                if not (vr[(32 * (base + t) >> 1):(32 * (base + t) >> 1) + 16] == rom_tiles[16 * t:16 * t + 16]).all():
                    changed_tiles.append(t)
        changed_cells = [(y, x) for y in range(28) for x in range(32) if own[y][x] and (S["map"][y * 32 + x] & 0x7FF) in changed_tiles]
        e.screenshot(self.out / f"{name}.png")
        base_img = np.asarray(Image.open(self.out / f"{name}.png").convert("RGB")).astype(int)

        def filled(col):
            pat = ((col << 12) | (col << 8) | (col << 4) | col)
            return pat

        # the picture's own tiles filled, 3 colours
        shots = []
        for col in (1, 2, 3):
            self.e.unserialize(st)
            self.poke({(32 * (base + t) >> 1) + k: filled(col) for t in range(ntiles) for k in range(16)})
            shots.append(self.shot(f"_p{col}"))
        pic = (shots[0] != shots[1]).any(2) | (shots[1] != shots[2]).any(2)
        # every cell of the plane on the picture's first tile (filled), keeping its attribute bits
        shots = []
        for col in (1, 2, 3):
            self.e.unserialize(st)
            d = {(32 * base >> 1) + k: filled(col) for k in range(16)}
            for y in range(28):
                for x in range(32):
                    d[(addr >> 1) + y * w + x] = (cells[y][x] & 0xF800) | base
            self.poke(d)
            shots.append(self.shot(f"_w{col}"))
        plane = (shots[0] != shots[1]).any(2) | (shots[1] != shots[2]).any(2)
        self.e.unserialize(st)
        H, W = pic.shape
        grid_pic = np.zeros((28, 32))
        grid_plane = np.zeros((28, 32))
        for y in range(28):
            for x in range(32):
                if 8 * y < H and 8 * x < W:
                    grid_pic[y, x] = pic[8 * y:8 * y + 8, 8 * x:8 * x + 8].mean()
                    grid_plane[y, x] = plane[8 * y:8 * y + 8, 8 * x:8 * x + 8].mean()
        # colours: the picture's shown pixels, and everything else on screen (by the plain screenshot's tile indexes)
        pairs_pic, pairs_other = set(), set()

        def tile_index(t, px, py, hf, vf):
            if hf:
                px = 7 - px
            if vf:
                py = 7 - py
            v = int(vr[(32 * t >> 1) + py * 2 + px // 4])
            return v >> (12 - 4 * (px % 4)) & 15
        for y in range(28):
            for x in range(32):
                c = cells[y][x]
                line = c >> 13 & 3
                for py in range(8):
                    for px in range(8):
                        if 8 * y + py >= H or 8 * x + px >= W or not plane[8 * y + py, 8 * x + px]:
                            continue
                        i = tile_index(c & 0x7FF, px, py, c >> 11 & 1, c >> 12 & 1)
                        if i:
                            (pairs_pic if own[y][x] else pairs_other).add((line, i))
        for p2, a2 in planes.items():                 # the other planes' cells with any pixel on screen (not under it)
            if a2 == addr:
                continue
            w2 = 32 if p2 == "W" else pw
            for y in range(28):
                for x in range(32):
                    c = int(vr[(a2 >> 1) + y * w2 + x])
                    if p2 == "W" and not (y < (reg[18] & 0x1F) or (reg[18] & 0x80 and y >= (reg[18] & 0x1F))):
                        continue
                    t = c & 0x7FF
                    idx = {tile_index(t, px, py, 0, 0) for px in range(8) for py in range(8)} - {0}
                    if idx and not grid_plane[y, x] == 1:
                        pairs_other |= {(c >> 13 & 3, i) for i in idx}
        sat = ((reg[5] & 0x7F) << 9) >> 1
        spr_lines = set()
        link = 0
        for _ in range(80):
            yv, sl, nm, xv = (int(vr[sat + 4 * link + k]) for k in range(4))
            if 128 <= (yv & 0x3FF) < 352 and 128 <= (xv & 0x1FF) < 128 + W:
                spr_lines.add(nm >> 13 & 3)
            link = sl & 0x7F
            if not link:
                break
        # colour memory for 300 frames
        changes = []
        last = cram
        for f in range(300):
            e.run(1)
            c2 = self.state()[2]
            if c2 != last:
                changes.append(dict(frame=f, entries=[[i // 16, i % 16, f"{gen_word(a):03X}", f"{gen_word(b):03X}"] for i, (a, b) in enumerate(zip(last, c2)) if a != b][:12]))
                last = c2
        self.e.unserialize(st)
        sets = sorted((v, k) for k, v in chain.items())
        after = [(k, v) for v, k in sets if v > base]
        self.moments[name] = dict(plane=pn, plane_addr=f"${addr:X}", rinkvrcset=base, chain=chain,
                                  next_set_after_picture=after[0] if after else None,
                                  cells_naming_picture=sum(map(sum, own)), cells_overwritten=896 - sum(map(sum, own)),
                                  overwritten_rows=sorted({y for y in range(28) for x in range(32) if not own[y][x]}),
                                  overwriting_tiles=others[:40], sfhor=e.b(SFLAGS) >> 7 & 1,
                                  picture_tiles_rewritten=changed_tiles, cells_on_rewritten_tiles=changed_cells,
                                  picture_shows_whole=[[x for x in range(32) if grid_pic[y, x] == 1] for y in range(28)],
                                  plane_hidden=[[x for x in range(32) if grid_plane[y, x] == 0] for y in range(28)],
                                  grid_pic=grid_pic.round(2).tolist(), grid_plane=grid_plane.round(2).tolist(),
                                  own=own, pairs_picture=sorted(pairs_pic), pairs_other=sorted(pairs_other),
                                  sprite_lines=sorted(spr_lines),
                                  cram=[[f"{gen_word(c):03X}" for c in cram[16 * r:16 * r + 16]] for r in range(4)],
                                  cram_changes_300=changes[:20], n_cram_changes=len(changes))
        # the cell map: green the picture shows whole, yellow in part, blue the plane shows but another tile is there
        # (text, logos), red the plane never shows
        img = Image.fromarray(base_img.astype(np.uint8)).resize((W * 2, H * 2), Image.NEAREST)
        ov = Image.new("RGB", img.size)
        px = ov.load()
        for y in range(28):
            for x in range(32):
                gp, gl = grid_pic[y, x], grid_plane[y, x]
                c = (0, 200, 0) if own[y][x] and gp == 1 else (220, 200, 0) if own[y][x] and gp > 0 else \
                    (40, 90, 230) if not own[y][x] and gl > 0 else (220, 0, 0)
                for yy in range(16 * y, min(img.size[1], 16 * y + 16)):
                    for xx in range(16 * x, min(img.size[0], 16 * x + 16)):
                        px[xx, yy] = c
        Image.blend(img, ov, 0.45).save(self.out / f"{name}_cells.png")
        print(name, pn, "picture cells", sum(map(sum, own)), "sfhor", e.b(SFLAGS) >> 7 & 1, flush=True)


def press(e, b, after=60):
    e.run(4, hold=[b])
    e.run(after)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    ver = sys.argv[3] if len(sys.argv) > 3 else ("95" if "95" in Path(rom).name else "94")
    out.mkdir(parents=True, exist_ok=True)
    S = static(rom)
    if S is None or ver == "95":
        e = Emu(rom)
        e.run(1500)
        for _ in range(3):
            press(e, "START", 300)
        e.screenshot(out / "setup_or_menu.png")
        (out / "hor_board.json").write_text(json.dumps(dict(rom=Path(rom).name, ver=ver, static=S and {k: v for k, v in S.items() if k not in ("map", "raw")},
                                                            note="no SetHor picture pair found")))
        print("no side-on picture:", S is None)
        return
    sc = Screen(rom, out, S)
    e = sc.e
    G.to_setup(e, out)
    e.setw(OPTPEN, 0)                                  # penalties on
    G.into_play(e)
    e.run(120)
    base = e.serialize()
    # the pause menu
    press(e, "START", 150)
    sc.moment("pause_menu")
    e.unserialize(base)
    # play on (the computer on both sides) until sflags bit 7 (sfhor) rises: at a period's end the intermission
    # (the clock at 0, or the period just changed), otherwise a penalty's side-on view; through up to 3 periods,
    # START pressed at the intermission's screens to go on
    got, last_change, g, hor = {}, -10000, e.w(GSP), 0
    for f in range(80000):
        h = e.b(SFLAGS) >> 7 & 1
        press_now = h and "intermission" in got and f % 200 == 0
        e.run(1, hold=["START"] if press_now else [])
        if e.w(GSP) != g:
            g, last_change = e.w(GSP), f
        h2 = e.b(SFLAGS) >> 7 & 1
        if h2 and not hor:
            kind = "intermission" if e.w(CLOCK) == 0 or f - last_change < 900 else "penalty_side_on"
            if kind not in got:
                e.run(90)
                got[kind] = f
                sc.moment(kind)
                if kind == "penalty_side_on":
                    e.run(240)
                    if e.b(SFLAGS) & 0x80:
                        sc.moment("penalty_side_on_later")
        hor = h2
        if len(got) == 2 or e.w(GSP) >= 3:
            break
    if "penalty_side_on" not in got:
        # none came up: one is called, as faceoff_fix_test does: a PenBuf ($C3A4) entry (hooking $1E, the puck
        # carrier puckc $B7AA), gmode's penalty bits clear; the side-on view follows when the call's delay runs out
        e.unserialize(base)
        for tries in range(40):
            e.run(30)
            k = e.w(0xB7AA)
            if 0 <= k < 12 and not e.b(SFLAGS) & 0x80:
                e.setw(0xC3A4, 0x1E << 8 | k)
                e.setw(0xC3A6, 0)
                e.setw(0xC2EA, e.w(0xC2EA) & ~0x0D00)
                for f in range(1500):
                    e.run(1)
                    if e.b(SFLAGS) & 0x80:
                        e.run(90)
                        got["penalty_side_on (called)"] = f
                        sc.moment("penalty_side_on")
                        e.run(240)
                        if e.b(SFLAGS) & 0x80:
                            sc.moment("penalty_side_on_later")
                        break
                break
    R = dict(rom=Path(rom).name, ver=ver, found=got,
             static={k: (f"${v:X}" if isinstance(v, int) and k in ("picture", "map_at", "palette_at") else v)
                     for k, v in S.items() if k not in ("map", "palette", "raw")},
             picture_palette=[[f"{S['palette'][16 * r + c]:03X}" for c in range(16)] for r in range(4)],
             moments=sc.moments)
    (out / "hor_board.json").write_text(json.dumps(R, indent=1, default=list))


def ads(rom, out):
    """For a side-on picture build (NHL '94): the same moments on a ROM, each saved (screenshot; video memory, colour
    memory, registers): the pause menu and play 300 frames after it (ClrHor's reload), a penalty's side-on view (called
    as main does) and play after it, the intermission (the clock set to 0:03) and period 2. A build is compared with a
    control (the base with the build's changes outside the picture: its checksum call NOPed), so both play alike."""
    out.mkdir(parents=True, exist_ok=True)
    e = Emu(rom)
    G.to_setup(e, out)
    e.setw(OPTPEN, 0)
    G.into_play(e)
    e.run(120)
    got = []

    def snap(tag):
        st = bytes(e.serialize())
        np.savez_compressed(out / f"dump_{tag}.npz", vram=np.frombuffer(st[VRAM_AT:VRAM_AT + 0x10000], dtype="<u2"),
                            cram=np.frombuffer(st[VRAM_AT + 0x10000:VRAM_AT + 0x10080], dtype="<u2"),
                            reg=np.frombuffer(st[VRAM_AT + 0x10100:VRAM_AT + 0x10120], dtype=np.uint8),
                            sfhor=e.b(SFLAGS) >> 7 & 1, rinkvrcset=e.w(CHAIN["rinkvrcset"]))
        e.screenshot(out / f"{tag}.png")
        got.append(tag)

    base = e.serialize()
    press(e, "START", 150)
    snap("pause_menu")
    press(e, "START", 60)
    e.run(300)
    snap("play_after_pause")
    e.unserialize(base)                                      # a penalty called, as main does
    for _ in range(40):
        e.run(30)
        k = e.w(0xB7AA)
        if 0 <= k < 12 and not e.b(SFLAGS) & 0x80:
            e.setw(0xC3A4, 0x1E << 8 | k)
            e.setw(0xC3A6, 0)
            e.setw(0xC2EA, e.w(0xC2EA) & ~0x0D00)
            for f in range(1500):
                e.run(1)
                if e.b(SFLAGS) & 0x80:
                    e.run(90)
                    snap("penalty_side_on")
                    for _ in range(3000):
                        e.run(1)
                        if not e.b(SFLAGS) & 0x80:
                            break
                    e.run(300)
                    snap("play_after_penalty")
                    break
            break
    e.unserialize(base)                                      # the intermission, then period 2
    e.setw(CLOCK, 3)
    g0, inter, c_last = e.w(GSP), False, None
    for f in range(15000):
        hor = e.b(SFLAGS) >> 7 & 1
        e.run(1, hold=["START"] if inter and hor and f % 200 == 0 else [])
        if not inter and e.b(SFLAGS) & 0x80 and (e.w(CLOCK) == 0 or e.w(GSP) != g0):
            e.run(90)
            snap("intermission")
            inter = True
        if inter and e.w(GSP) != g0 and not e.b(SFLAGS) & 0x80 and f % 60 == 0:
            c = e.w(CLOCK)
            if c_last is not None and 0 < c < c_last:          # period 2's clock running
                e.run(300)
                snap("period2")
                break
            c_last = c
    (out / "ads.json").write_text(json.dumps(dict(rom=Path(rom).name, moments=got)))
    print(Path(rom).name, got, flush=True)


def layers(dmp):
    """Planes B, A and the window (32 x 28 cells from the top left, no scroll: the side-on screen) drawn from a dump's
    video and colour memory, colour 0 left black; RGB in steps of 36 (a Genesis level)."""
    vr, cram, reg = dmp["vram"], dmp["cram"], dmp["reg"]
    pw = {0: 32, 1: 64, 3: 128}.get(int(reg[16]) & 3, 32)
    rgb = np.array([[(int(c) & 7) * 36, (int(c) >> 3 & 7) * 36, (int(c) >> 6 & 7) * 36] for c in cram])
    out = {}
    for name, addr, w in (("B", (int(reg[4]) & 7) << 13, pw), ("A", (int(reg[2]) & 0x38) << 10, pw),
                          ("W", (int(reg[3]) & 0x3E) << 10, 32)):
        img = np.zeros((224, 256, 3), int)
        for y in range(28):
            for x in range(32):
                c = int(vr[(addr >> 1) + y * w + x])
                t, line, hf, vf = c & 0x7FF, c >> 13 & 3, c >> 11 & 1, c >> 12 & 1
                words = vr[(32 * t >> 1):(32 * t >> 1) + 16].astype(int)
                px = np.array([[w_ >> (12 - 4 * k) & 15 for w_ in words[2 * r:2 * r + 2] for k in range(4)] for r in range(8)])
                if hf:
                    px = px[:, ::-1]
                if vf:
                    px = px[::-1]
                col = rgb[16 * line + px]
                col[px == 0] = 0
                img[8 * y:8 * y + 8, 8 * x:8 * x + 8] = col
        out[name] = img
    return out


def compare(base, build, out, panel=(64, 144, 192, 168), expected=None):
    """A side-on picture build's `ads` run against the control's: each side-on moment's screen pixel for pixel outside
    the panel (x0, y0, x1, y1), the panel against the editor's expected picture (Genesis levels: 255 / 7 a step there,
    the core's 252 / 7), and in play after each (ClrHor's reload) the vertical rink's tiles (0 to the rink's count) and
    the screen as the control's."""
    out.mkdir(parents=True, exist_ok=True)
    res = []

    def check(name, ok, detail=""):
        res.append(("PASS" if ok else "FAIL", name, detail))
    x0, y0, x1, y1 = panel
    ex = np.asarray(Image.open(expected).convert("RGB")).astype(int) if expected else None
    tags = json.loads((base / "ads.json").read_text())["moments"]
    tb = json.loads((build / "ads.json").read_text())["moments"]
    check("the same moments reached", tags == tb, f"{tags} / {tb}")
    rink_tiles = 454                       # ClrHor's vertical rink (Rinktiles $56062, count $1C6)
    for tag in tags:
        if tag not in tb:
            continue
        a = np.asarray(Image.open(base / f"{tag}.png").convert("RGB")).astype(int)
        b = np.asarray(Image.open(build / f"{tag}.png").convert("RGB")).astype(int)
        d = (a != b).any(2)
        da, db = np.load(base / f"dump_{tag}.npz"), np.load(build / f"dump_{tag}.npz")
        if int(da["sfhor"]):
            # the picture's plane (B) and the text planes (A, window) drawn from each run's own video and colour
            # memory, sprites left out (the two games part a little: the build unpacks fewer tiles); cell by cell
            pa, pb = layers(da), layers(db)
            for name in ("B", "A", "W"):
                cells = sorted({(y // 8, x // 8) for y, x in zip(*np.nonzero((pa[name] != pb[name]).any(2)))})
                inside = [c for c in cells if y0 // 8 <= c[0] < y1 // 8 and x0 // 8 <= c[1] < x1 // 8]
                if name == "B":
                    # cells where both runs name tiles past the vertical rink's room (USBoard's text over the picture:
                    # the clock, a penalty's number) are the game's state, not the picture
                    regB = lambda dd: ((int(dd["reg"][4]) & 7) << 13 >> 1, {0: 32, 1: 64, 3: 128}.get(int(dd["reg"][16]) & 3, 32))  # noqa: E731
                    (aa, wa), (ab, wb) = regB(da), regB(db)
                    text = [c for c in cells if (int(da["vram"][aa + c[0] * wa + c[1]]) & 0x7FF) >= rink_tiles
                            and (int(db["vram"][ab + c[0] * wb + c[1]]) & 0x7FF) >= rink_tiles]
                    pic = [c for c in cells if c not in inside and c not in text]
                    check(f"{tag}: plane B (the picture) as the control's outside the panel's cells", not pic, str(pic[:8]))
                    if text:
                        res.append(("INFO", f"{tag}: plane B text cells differing (USBoard's clock / penalty lines: the games part a little)", str(text[:8])))
                    check(f"{tag}: the panel's cells differ (the ad is there)", bool(inside), f"{len(inside)} cells")
                else:
                    check(f"{tag}: plane {name} (text, blocks, boxes) as the control's", not cells, str(cells[:8]))
            vis = d.copy()
            vis[y0:y1, x0:x1] = False
            res.append(("INFO", f"{tag}: screenshot pixels differing outside the panel (sprites: the games part a little)",
                        f"{int(vis.sum())} px"))
            if ex is not None:
                same = (np.rint(ex[y0:y1, x0:x1] * 7 / 255) == np.rint(pb["B"][y0:y1, x0:x1] / 36)).all(2)
                check(f"{tag}: plane B's panel is the expected picture (Genesis levels)", bool(same.all()), f"{100 * same.mean():.2f}% of pixels")
                shown = (np.rint(ex[y0:y1, x0:x1] * 7 / 255) == np.rint(b[y0:y1, x0:x1] * 7 / 252)).all(2)
                res.append(("INFO", f"{tag}: on screen, the panel's pixels as expected (sprites may cover some)", f"{100 * shown.mean():.2f}%"))
        else:
            n = 16 * rink_tiles
            same = bool((da["vram"][:n] == db["vram"][:n]).all())
            check(f"{tag}: the vertical rink's {rink_tiles} tiles as the control's (ClrHor's reload)", same,
                  f"{int((da['vram'][:n] != db['vram'][:n]).reshape(-1, 16).any(1).sum())} tiles differ")
            res.append(("INFO", f"{tag}: screenshot pixels differing (the games part a little)", f"{int(d.sum())} px"))
        Image.fromarray(np.concatenate([a, b], 1).astype(np.uint8)).save(out / f"{tag}_control_build.png")
    lines = [f"{a}  {b}" + (f"  [{c}]" if c and a != "PASS" else "") for a, b, c in res]
    (out / "compare.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if sys.argv[1] == "ads":
        ads(sys.argv[2], Path(sys.argv[3]))
    elif sys.argv[1] == "compare":
        compare(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), expected=sys.argv[5] if len(sys.argv) > 5 else None)
    else:
        main()
