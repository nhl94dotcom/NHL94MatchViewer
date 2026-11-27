"""SNES: which rink colours nothing else on screen uses, for NOSE4Web's per-home-team rink colours (2026-11-27; NHL
'94 Genesis: line 0 colours 5 and 9, gen_arena_colours_check.py). setupice copies RinkPalette (128 colours) into
palbuffer ($7E35F4) twice: rows 0-7 (the backgrounds) and rows 8-15 (the sprites); setplayercolors then writes the
uniforms over rows 2 / 3 and 12 / 13 and the player markers over row 10 and sends all 256 colours. The rink is BG2
(map word $0400, tiles from word $1000), the text layer BG1 (map word 0, tiles from word $2000), mode 1.

A computer game on the ROM (snes_momentum_blocks_check.boot: regular season, penalties on, the computer on both
sides; any build, SA-1 too), every frame: palbuffer rows 0-15 and, every 2 frames, colour memory (CGDATA in the
state's PPU block at +64, big-endian words): each change logged with the frame, sflags ($15D8: bit 0 paused, $0800
replay) and sfhormode ($15DA: the horizontal scoreboard). Every 30 frames of play and at moments (a pause into each
pause item, the instant replay, the end of a period and the intermission, the next periods at the other ends): every
cell of BG1 and BG2 on screen (each layer's map, tile base and scroll from the PPU block: BG n at +14 + 11n, map base,
H / V offset, tile size, tile base, map size) and every sprite on screen (OAM found in the PPU block by the game's
OAM buffer, OAMShowBuf $07AC), sorted by what its tile is (the rink: BG2 tiles below faceoffvrcset ($7E35BA): the
rink's own and the centre-ice logo; else the nearest of the tile bases setupice sets: faceoff, EA logo, referees,
fonts, framer, score tiles, ExtraChars), and the (row, colour) pairs each draws with. Grouped by the screen's state
(play, paused: the pause menu and the stats screens, which send their own colours and go back to palbuffer's after,
replay, horizontal, between periods); the colours of rows 0-7 the rink alone uses in play, and what uses each
elsewhere; rows 8-15 (the sprites' copy) listed apart. The verdict is the colour poke's (every 10th play scan and at the pause menu,
the replay and the period ends): each colour of rows 0-7 set to magenta in a copy of the state and the frame drawn:
the pixels that change are that colour's on screen, split by the pixels the rink draws on that frame (those that change
when BG2 is hidden: every map entry on an all-zero tile); a colour is the rink's alone where all its pixels are.

python snes_rink_colours_check.py ROM OUT"""
import ctypes as C
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

import snes_momentum_blocks_check as B

PALBUF, SFLAGS, SFHOR, GSP, CLOCK, PSITEM, OAMSHOW = 0x35F4, 0x15D8, 0x15DA, 0x1630, 0x1632, 0x0D15, 0x07AC
BASES = {"centre ice / faceoff": 0x35BA, "EA logo": 0x35B0, "referees (horizontal)": 0x35C8, "referees": 0x35CA,
         "blank": 0x35D0, "small font": 0x35B6, "framer": 0x35BC, "big font": 0x35AE, "score tiles": 0x35CE,
         "ExtraChars": 0x35C2}


def kind(t, bases):
    best = None
    for k, v in bases.items():
        if v <= t and (best is None or v > bases[best]):
            best = k
    return best or "below every base"


def tile_cols(vr, base_w, t):
    a = 2 * base_w + 32 * t
    if a + 32 > len(vr):
        return set()
    cols = set()
    for r in range(8):
        p0, p1, p2, p3 = vr[a + 2 * r], vr[a + 2 * r + 1], vr[a + 16 + 2 * r], vr[a + 17 + 2 * r]
        for b in range(8):
            cols.add((p0 >> b & 1) | (p1 >> b & 1) << 1 | (p2 >> b & 1) << 2 | (p3 >> b & 1) << 3)
    return cols - {0}


class Watch:
    def __init__(self, e, m, out):
        self.e, self.m, self.out = e, m, out
        self.vram = (C.c_ubyte * e.lib.retro_get_memory_size(3)).from_address(e.lib.retro_get_memory_data(3))
        self.use = defaultdict(lambda: defaultdict(set))
        self.ex, self.log, self.moments = {}, [], []
        self.f, self.last_pal, self.last_cg, self.oam_at = 0, None, None, None
        self.pokes, self.npokes = {}, {}            # group -> 'row,colour' -> pixels drawn by the rink / others

    def ppu(self):
        n = self.e.lib.retro_serialize_size()
        buf = (C.c_ubyte * n)()
        self.e.lib.retro_serialize(buf, n)
        raw = bytes(buf)
        i = raw.index(b"PPU:")
        return raw[i + 11:i + 11 + int(raw[i + 4:i + 10])]

    def flags(self):
        m = self.m
        s = m.w(SFLAGS)
        return dict(paused=bool(s & 1), replay=bool(s & 0x0800), hor=m.w(SFHOR) != 0, gsp=m.w(GSP), clock=m.w(CLOCK))

    def step(self, n=1, hold=()):
        e, m = self.e, self.m
        for _ in range(n):
            e.run(1, hold=list(hold))
            self.f += 1
            pal = tuple(m.w(PALBUF + 2 * i) for i in range(256))
            if pal != self.last_pal:
                ch = [i for i in range(256) if self.last_pal is None or pal[i] != self.last_pal[i]]
                self.log.append(dict(frame=self.f, what="palbuffer", rows=sorted({i // 16 for i in ch}), n=len(ch), **self.flags()))
                self.last_pal = pal
            if self.f % 2 == 0:
                p = self.ppu()
                cg = p[64:64 + 512]
                if cg != self.last_cg:
                    ch = [i for i in range(256) if self.last_cg is None or cg[2 * i:2 * i + 2] != self.last_cg[2 * i:2 * i + 2]]
                    self.log.append(dict(frame=self.f, what="CGRAM", rows=sorted({i // 16 for i in ch}), n=len(ch), **self.flags()))
                    self.last_cg = cg

    def press(self, b, after=40):
        self.step(4, [b])
        self.step(after)

    def group(self):
        fl = self.flags()
        return "replay" if fl["replay"] else "paused" if fl["paused"] else "horizontal" if fl["hor"] else "play"

    def scan(self, tag):
        m, e = self.m, self.e
        p = self.ppu()
        vr = bytes(self.vram)
        bg = []
        for n in range(4):
            o = 14 + 11 * n
            sc, ho, vo = struct.unpack_from(">HHH", p, o)
            size8, nb, scs = p[o + 6], struct.unpack_from(">H", p, o + 7)[0], struct.unpack_from(">H", p, o + 9)[0]
            bg.append(dict(sc=sc, h=ho & 0x3FF, v=vo & 0x3FF, nb=nb, scs=scs, big=size8))
        mode = p[58]
        cg = [struct.unpack_from(">H", p, 64 + 2 * i)[0] for i in range(256)]
        group = self.group()
        if group == "play" and tag.startswith("period end"):
            group = "between periods"
        U = self.use[group]
        bases = {k: m.w(a) for k, a in BASES.items()}
        rink_end = bases["centre ice / faceoff"]
        for n, name in ((0, "BG1"), (1, "BG2")):
            L = bg[n]
            wide, tall = L["scs"] in (1, 3), L["scs"] in (2, 3)
            seen = set()
            for y in range(224):
                row = ((y + L["v"] + 1) // 8) % (64 if tall else 32)
                for x in list(range(0, 256, 8)) + [255]:
                    col = ((x + L["h"]) // 8) % (64 if wide else 32)
                    seen.add((row, col))
            for row, col in seen:
                a = L["sc"] + (row % 32) * 32 + (col % 32) + (0x400 if col >= 32 else 0) + ((0x800 if wide else 0x400) if row >= 32 else 0)
                v = vr[2 * a] | vr[2 * a + 1] << 8
                t, pal = v & 0x3FF, v >> 10 & 7
                if name == "BG2":
                    who = "rink" if t < rink_end else f"BG2: {kind(t, bases)}"
                else:
                    who = f"BG1: {kind(t + (L['nb'] - 0x1000) // 16, bases)}"
                for c in tile_cols(vr, L["nb"], t):
                    U[(pal, c)].add(who)
                    if who != "rink":
                        self.ex.setdefault(f"{group} | {pal},{c} | {who}", [tag, row, col, t])
        # sprites: OAM, found once by the game's buffer
        if self.oam_at is None:
            ptr = m.w(OAMSHOW)
            want = bytes(e.ram[ptr + i] for i in range(32)) if not m.sa1 else None
            if want:
                k = p.find(want, 576)
                self.oam_at = k if k > 0 else -1
        if self.oam_at and self.oam_at > 0:
            o = self.oam_at
            obsel_base = 0x6000
            for i in range(128):
                x, y, nm, at = p[o + 4 * i], p[o + 4 * i + 1], p[o + 4 * i + 2], p[o + 4 * i + 3]
                hi = p[o + 512 + i // 4] >> (2 * (i % 4)) & 3
                x |= (hi & 1) << 8
                big = hi >> 1 & 1
                sz = 2 if big else 1
                if x >= 256 and x < 512 - 8 * sz or y >= 224 and y < 256 - 8 * sz:
                    continue
                t0 = nm | (at & 1) << 8
                pal = 8 + (at >> 1 & 7)
                for ty in range(sz):
                    for tx in range(sz):
                        t = (t0 + tx + 16 * ty) & 0x1FF
                        for c in tile_cols(vr, obsel_base, t):
                            U[(pal, c)].add("sprite")
        self.moments.append(dict(frame=self.f, tag=tag, group=group, mode=mode, bg=bg[:2], **self.flags(),
                                 cg0_7=[f"{x:04X}" for x in cg[:128]]))
        if sum(1 for x in self.moments if x["tag"] == tag) <= 2:
            e.screenshot(self.out / f"{len(self.moments):03d}_{tag.replace(' ', '_')}.png")

    def play(self, frames, tag):
        for k in range(frames // 30):
            self.step(30)
            self.scan(tag)
            if k % 10 == 5:
                self.poke(tag)

    def poke(self, tag):
        """What is on screen with each colour of rows 0-7: the colour set to magenta in a copy of the state, the frame
        drawn as it is: the pixels that change are that colour's. Which of them the rink draws: the pixels that change
        when BG2 is hidden (every map entry on an all-zero tile) in the unpoked frame; the rest are another layer's."""
        e = self.e
        n = e.lib.retro_serialize_size()
        buf = (C.c_ubyte * n)()
        e.lib.retro_serialize(buf, n)
        st = bytes(buf)
        i = st.index(b"PPU:") + 11
        vr = bytes(self.vram)
        p = st[i:i + 2652]
        group = self.group()
        if group == "play" and tag.startswith("period end"):
            group = "between periods"
        lay = {}
        for k, name in ((0, "BG1"), (1, "BG2")):
            o = 14 + 11 * k
            sc, nb, scs = struct.unpack_from(">H", p, o)[0], struct.unpack_from(">H", p, o + 7)[0], struct.unpack_from(">H", p, o + 9)[0]
            zero = next((t for t in range(1024) if not any(vr[2 * nb + 32 * t:2 * nb + 32 * t + 32])), None)
            lay[name] = (sc, 0x1000 if scs == 3 else 0x800 if scs in (1, 2) else 0x400, zero)

        def frame(cg_entry, hide):
            s2 = bytearray(st)
            if cg_entry is not None:
                o = i + 64 + 2 * cg_entry
                s2[o:o + 2] = (0x7C1F).to_bytes(2, "big")
            e.lib.retro_unserialize(C.cast(C.create_string_buffer(bytes(s2), len(s2)), C.c_void_p), len(s2))
            if hide:
                sc, words, zero = lay["BG2"]
                for a in range(sc, sc + words):
                    self.vram[2 * a], self.vram[2 * a + 1] = zero & 0xFF, zero >> 8
            q = self.out / "_poke.png"
            e.screenshot(q)
            from PIL import Image
            import numpy as np
            return np.asarray(Image.open(q).convert("RGB"))
        if lay["BG2"][2] is None:
            return
        res = self.pokes.setdefault(group, {})
        base = frame(None, False)
        rinkpx = (frame(None, True) != base).any(axis=2)        # the pixels the rink draws on this frame
        for r in range(8):
            for c in range(1, 16):
                d = (frame(16 * r + c, False) != base).any(axis=2)
                for who, px in (("rink", int((d & rinkpx).sum())), ("other", int((d & ~rinkpx).sum()))):
                    if px:
                        x = res.setdefault(f"{r},{c}", {})
                        x[who] = x.get(who, 0) + px
                        x.setdefault(f"{who} at", tag)
        e.lib.retro_unserialize(C.cast(C.create_string_buffer(st, len(st)), C.c_void_p), len(st))
        self.npokes[group] = self.npokes.get(group, 0) + 1

    def pause_item(self, item):
        m = self.m
        self.press("START", 90)
        self.scan(f"pause menu")
        self.poke("pause menu")
        for _ in range(40):
            if m.w(PSITEM) == item:
                break
            self.press("DOWN")
        self.press("A", 300)
        self.scan(f"pause item {item}")
        if item == 1:
            for k in range(4):
                self.step(100)
                self.scan("replay")
                if k == 1:
                    self.poke("replay")
        for k in range(10):
            self.press("START" if k % 2 == 0 else "A", 240)
            if m.w(SFLAGS) & 1 and not m.w(SFLAGS) & 0x0800:
                break
        for _ in range(40):
            if m.w(PSITEM) == 0:
                break
            self.press("UP")
        self.press("START", 240)
        self.scan(f"after item {item}")


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    e, m = B.boot(rom, 0)
    w = Watch(e, m, out)
    w.scan("start")
    w.play(3000, "p1")
    for item in (1, 2, 3, 4):                  # the replay, then the first stats screens
        w.pause_item(item)
        w.play(300, "p1 after pause")
    for per in range(2):                       # to the end of the period, the break, the next period (other ends)
        m.setw(CLOCK, 2)
        first = None
        for k in range(160):
            fl = w.flags()
            w.step(30, ["START"] if k % 4 == 3 and (fl["paused"] or fl["hor"] or fl["gsp"] == per) else [])
            if k % 6 == 0:
                w.scan(f"period end {per}")
            if k % 12 == 3:
                w.poke(f"period end {per}")
            fl = w.flags()
            if fl["gsp"] == per + 1:
                first = fl["clock"] if first is None else first
                if not fl["paused"] and not fl["hor"] and fl["clock"] < first:
                    break
        w.play(2400, f"p{per + 2}")
    U = w.use
    res = {g: {f"{r},{c}": sorted(v) for (r, c), v in sorted(u.items())} for g, u in U.items()}
    play = U["play"]
    rink_rows = sorted({r for (r, c), v in play.items() if "rink" in v})
    lines = [f"{Path(rom).name}: rink (BG2) rows in play {rink_rows}"]
    rink_only = {}
    for r in range(8):
        for c in range(1, 16):
            v = play.get((r, c), set())
            if v == {"rink"}:
                rink_only[f"{r},{c}"] = {g: sorted(u.get((r, c), set()) - {"rink"}) for g, u in U.items()
                                         if g != "play" and u.get((r, c), set()) - {"rink"}}
    P = w.pokes.get("play", {})
    poke_only = {k: {g: d[k] for g, d in w.pokes.items() if g != "play" and k in d and d[k].get("other")}
                 for k, v in P.items() if v.get("rink") and not v.get("other")}
    lines.append(f"by the colour poke ({w.npokes} moments): rows 0-7 colours on screen in play drawn by the rink and by "
                 "nothing else, and where something else draws with them:")
    lines += [f"  {k}: {v or 'nothing else at any moment'}" for k, v in sorted(poke_only.items(), key=lambda kv: [int(x) for x in kv[0].split(',')])]
    lines.append("  shared in play: " + ", ".join(f"{k} (rink {v.get('rink', 0)} px, other {v['other']} px)" for k, v in
                                               sorted(P.items(), key=lambda kv: [int(x) for x in kv[0].split(',')]) if v.get("other")))
    lines.append("by the map scan (cells and tiles; it also counts cells hidden behind the other layer):")
    lines.append("rows 0-7 colours the rink alone uses in play, and what else uses each at other moments:")
    lines += [f"  {k}: {v or 'nothing else at any moment seen'}" for k, v in rink_only.items()]
    for r in range(8):
        lines.append(f"row {r} in play: " + "; ".join(f"{c}: {'/'.join(sorted(play.get((r, c), set()))) or '-'}" for c in range(1, 16)))
    lines.append("sprite rows (8-15) in play: " + ", ".join(f"{r}: {sorted(c for (rr, c) in play if rr == r)}" for r in range(8, 16)))
    lines.append(f"moments by group: { {g: sum(1 for x in w.moments if x['group'] == g) for g in U} }")
    lines.append("palette writes (palbuffer / CGRAM) and the screen's state:")
    lines += [f"  {x}" for x in w.log]
    R = dict(rom=Path(rom).name, rink_rows=rink_rows, rink_only=rink_only, users=res, examples=w.ex, palette_log=w.log,
             moments=w.moments, oam_at=w.oam_at, pokes=w.pokes, poke_moments=w.npokes)
    (out / "rink_colours.json").write_text(json.dumps(R, indent=1, default=list))
    (out / "summary.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))


if __name__ == "__main__":
    main()
