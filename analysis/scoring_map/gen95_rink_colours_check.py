"""NHL '95 (Genesis): which rink colours nothing else on screen uses, for NOSE4Web's per-home-team rink colours
(2026-11-27; NHL '94's answer: line 0 colours 5 and 9, gen_arena_colours_check.py). setupIceRinkPal copies the rink
palette (16 longs at the Rinktilelist header: lines 0-1) into palfadenew ($FFB942); setupice, RestoreGameScreen and
the Create Player screens call it.

Game Setup, penalties on (OptPen $CC5A = 1), into play (pad 1 on the home team, never pressed in play: a press during a
stoppage can end the game to Game Setup); from the opening faceoff (each case from it or a later saved state), every
frame: palfadenew lines 0-1 and, every 2 frames, colour memory lines 0-1 (Genesis Plus GX's state, VRAM_AT): each
change logged with the frame, the pause and horizontal bits (sflags $FFBEF2: sfpz bit 8, sfhor bit 15 of the word)
and the replay bit (sflags2 $FFBEF4 bit 3). At moments (the faceoff; 3,000 frames of period 1 and of period 2 (the other
ends), every 240 frames and every 30 while a penalty is shown; the intermission; a home goal's celebration; the pause
screen, an instant replay and its reverse angle; the end of the game and the three stars): every cell of planes A
and B and the window (from the VDP registers) and every sprite in the link chain, sorted by what its tile is (the
rink: plane B cells on tiles rinkvrcset ($FFAC2A) up to EASNcset ($FFAC32), the centre-ice graphics included; else
the nearest RAM tile base at or below it: fonts, framer, energy bar, crowd, sprites, EA logo, ExtraChars ...), and
the (line, colour) pairs each draws with; only what is on screen (the planes' cells through the scroll table and
the vertical scroll, the window's region, sprites inside the display). For lines 0-1: the colours the rink uses that nothing else does at any
moment. Each scan is grouped by the screen's state: the pause screens (sfpz), horizontal (sfhor: the penalty
referee), replay (sflags2 bit 3), the faceoff close-up (disflags $FFBB7E bit 4), a goal's celebration, between
periods, else vertical play; the colours the rink alone uses in vertical play, and what uses each at other moments.
The verdict is the colour poke's (every 16th scan of play, the first of each penalty, the goal, intermission, pause,
replay and game end): each colour of lines 0-1 set to magenta in a copy of the state and the frame drawn: the pixels
that change are that colour's on screen, split by the pixels plane B draws on that frame (those that change when every
plane B name-table word is put on an all-zero tile); a colour is the rink's alone where all its pixels are.

python gen95_rink_colours_check.py ROM OUT [HOME]"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

import gen95_shootout_check as S
from emu import Emu
from gen95_fight_check import to_setup, ROW
from gen_title_screen_check import gen_word, state, tables

PAL = 0xB942
SFLAGS, SFLAGS2, GSP, CLOCK, OPTPEN, VBINT, DISFLAGS = 0xBEF2, 0xBEF4, 0xC020, 0xC022, 0xCC5A, 0xAC52, 0xBB7E
BASES = {"big font": 0xAC14, "small font": 0xAC16, "energy bar": 0xAC28, "rink": 0xAC2A, "crowd": 0xAC2C,
         "faceoff close-up": 0xAC2E, "framer": 0xAC30, "EA logo": 0xAC32, "sprites": 0xAC36, "ExtraChars (refs)": 0xAC38}
# (the RAM bases setupice / RestoreGameScreen set; the others, the menus' fonts, clock digits, team blocks, keep old values)


def kind(t, bases):
    best = None
    for k, v in bases.items():
        if v <= t and (best is None or v > bases[best]):
            best = k
    return best or "below every base"


def cols(vr, t):
    out = set()
    for i in range(16):
        v = int(vr[(32 * t >> 1) + i])
        out |= {v >> 12 & 15, v >> 8 & 15, v >> 4 & 15, v & 15}
    return out - {0}


def visible(vr, T, vs):
    """The plane cells on screen: (plane, row, col) for the window's region and planes A (outside the window) and B,
    through the scroll table (full screen, per cell or per line, by mode register 3) and the vertical scroll."""
    sw, out = (320 if T["h40"] else 256), set()
    wy, down = T["winy"] & 0x1F, bool(T["winy"] & 0x80)
    wx, right = T["winx"] & 0x1F, bool(T["winx"] & 0x80)
    in_win = lambda cy, cx: (cy >= wy if down else cy < wy) or (cx >= 2 * wx if right else cx < 2 * wx)  # noqa: E731
    mode = T["mode3"] & 3
    for y in range(224):
        hl = 0 if mode == 0 else (y & ~7 if mode == 2 else y)
        for name, k, vv in (("A", 0, vs[0]), ("B", 1, vs[1])):
            hs = int(vr[(T["HS"] >> 1) + 2 * hl + k]) & 0x3FF
            row = ((y + (vv & 0x3FF)) // 8) % T["ph"]
            for x in range(0, sw, 8):
                if name == "A" and in_win(y // 8, x // 8):
                    out.add(("W", y // 8, x // 8))
                    continue
                for xx in (x, x + 7):
                    out.add((name, row, ((xx - hs) // 8) % T["pw"]))
    return out


class Watch:
    def __init__(self, rom, out, home):
        self.e = Emu(rom)
        self.out = out
        self.use = defaultdict(lambda: defaultdict(set))          # moment kind -> (line, colour) -> {users}
        self.log, self.f, self.last_pal, self.last_cram = [], 0, None, None
        self.moments = []
        self.odd = []                               # plane B cells off the rink's tiles
        self.ex = {}                                # a first example of each (group, line / colour, user)
        self.pokes, self.npokes = {}, {}            # group -> 'line,colour' -> pixels drawn by the rink / others
        self.poked = set()
        self.home = home

    def flags(self):
        e = self.e
        return dict(pz=bool(e.w(SFLAGS) & 0x100), hor=bool(e.w(SFLAGS) & 0x8000), replay=bool(e.w(SFLAGS2) & 0x0800),
                    gsp=e.w(GSP), clock=e.w(CLOCK), vb=f"${e.l(VBINT) & 0xFFFFFF:X}")

    def step(self, n=1, hold=()):
        e = self.e
        for _ in range(n):
            e.run(1, hold=list(hold))
            self.f += 1
            pal = tuple(e.w(PAL + 2 * i) for i in range(32))
            if pal != self.last_pal:
                ch = [i for i in range(32) if self.last_pal is None or pal[i] != self.last_pal[i]]
                self.log.append(dict(frame=self.f, what="palfadenew", entries=ch[:32],
                                     values={i: f"{pal[i]:03X}" for i in ch if i in (5, 9) or len(ch) < 6}, **self.flags()))
                self.last_pal = pal
            if self.f % 2 == 0:
                _, cram, _, _ = state(e)
                c = tuple(cram[:32])
                if c != self.last_cram:
                    ch = [i for i in range(32) if self.last_cram is None or c[i] != self.last_cram[i]]
                    self.log.append(dict(frame=self.f, what="CRAM", entries=ch, **self.flags()))
                    self.last_cram = c

    def poke(self, tag, group):
        """What is on screen with each colour of lines 0-1: the colour set to magenta in a copy of the state (colour
        memory, the 9-bit words at VRAM_AT + $10000) and the frame drawn: the pixels that change are that colour's
        on screen, split by the pixels plane B (the rink) draws on that frame (those that change when every plane B
        name-table word is put on an all-zero tile); the rest are plane A's, the window's or sprites'."""
        from gen_score_logo_check import VRAM_AT
        from PIL import Image
        e = self.e
        st = bytes(e.serialize())
        vr, _, reg, _ = state(e)
        T = tables(reg)
        fl = self.flags()
        if fl["replay"]:
            group = "replay"
        elif fl["pz"]:
            group = "pause screens"
        elif fl["hor"]:
            group = "horizontal (penalty)"
        elif e.b(DISFLAGS) & 0x10:
            group = "faceoff close-up"
        zero = next((t for t in range(0x7FF) if not vr[16 * t:16 * t + 16].any()), None)
        if zero is None:
            return

        def frame(entry, hide):
            s2 = bytearray(st)
            if entry is not None:
                o = VRAM_AT + 0x10000 + 2 * entry
                s2[o:o + 2] = (0x1C7).to_bytes(2, "little")         # magenta (BBBGGGRRR)
            if hide:
                for k in range(T["pw"] * T["ph"]):
                    o = VRAM_AT + T["B"] + 2 * k
                    s2[o:o + 2] = zero.to_bytes(2, "little")
            e.unserialize(bytes(s2))
            q = self.out / "_poke.png"
            e.screenshot(q)
            return np.asarray(Image.open(q).convert("RGB"))
        res = self.pokes.setdefault(group, {})
        base = frame(None, False)
        rinkpx = (frame(None, True) != base).any(axis=2)        # the pixels plane B (the rink) draws on this frame
        for ln in (0, 1):
            for c in range(1, 16):
                d_all = (frame(16 * ln + c, False) != base).any(axis=2)
                rink, other = int((d_all & rinkpx).sum()), int((d_all & ~rinkpx).sum())
                if rink or other:
                    d = res.setdefault(f"{ln},{c}", {})
                    for who, px in (("rink", rink), ("other", other)):
                        if px:
                            d[who] = d.get(who, 0) + px
                            d.setdefault(f"{who} at", tag)
        e.unserialize(st)
        self.npokes[group] = self.npokes.get(group, 0) + 1

    def press(self, b, after):
        self.step(6, [b])
        self.step(after)

    def scan(self, tag, group):
        e = self.e
        vr, cram, reg, vs = state(e)
        T = tables(reg)
        bases = {k: e.w(a) for k, a in BASES.items()}
        rink0, rink1 = bases["rink"], bases["EA logo"]
        bases = {k: v for k, v in bases.items() if k == "rink" or v >= rink1}
        fl = self.flags()
        if fl["replay"]:
            group = "replay"
        elif fl["pz"]:
            group = "pause screens"
        elif fl["hor"]:
            group = "horizontal (penalty)"
        elif e.b(DISFLAGS) & 0x10:
            group = "faceoff close-up"
        U = self.use[group]
        for (name, r, c) in visible(vr, T, vs):
            w = T["wwidth"] if name == "W" else T["pw"]
            v = int(vr[(T[name] >> 1) + r * w + c])
            t, ln = v & 0x7FF, v >> 13 & 3
            if t == 0x7FF:                          # the blank cell (its VRAM is the tables')
                continue
            who = "rink" if name == "B" and rink0 <= t < rink1 else f"plane {name}: {kind(t, bases)}"
            if name == "B" and who != "rink" and sum(1 for o in self.odd if o[1] == group) < 60:
                self.odd.append((tag, group, r, c, t, ln))
            for col in cols(vr, t):
                U[(ln, col)].add(who)
                if who != "rink":
                    self.ex.setdefault(f"{group} | {ln},{col} | {who}", [tag, r, c, t])
        sw = 320 if T["h40"] else 256
        link, n = 0, 0
        while n < 80:
            o = (T["SAT"] >> 1) + 4 * link
            y, sl, at, x = int(vr[o]) & 0x3FF, int(vr[o + 1]), int(vr[o + 2]), int(vr[o + 3]) & 0x1FF
            wd, ht = (sl >> 10 & 3) + 1, (sl >> 8 & 3) + 1
            if y + 8 * ht > 128 and y < 128 + 224 and x + 8 * wd > 128 and x < 128 + sw:     # on screen
                for t in range(at & 0x7FF, (at & 0x7FF) + wd * ht):
                    for col in cols(vr, t):
                        U[(at >> 13 & 3, col)].add(f"sprite: {kind(at & 0x7FF, bases)}")
                        self.ex.setdefault(f"{group} | {at >> 13 & 3},{col} | sprite: {kind(at & 0x7FF, bases)}",
                                           [tag, "x", x - 128, "y", y - 128, "tile", at & 0x7FF, "size", wd, ht])
            link = sl & 0x7F
            n += 1
            if not link:
                break
        self.moments.append(dict(frame=self.f, tag=tag, group=group, **fl,
                                 cram01=[f"{gen_word(x):03X}" for x in cram[:32]]))
        if sum(1 for m in self.moments if m["tag"].split()[0] == tag.split()[0]) <= 3:
            e.screenshot(self.out / f"{len(self.moments):03d}_{tag.replace(' ', '_')}.png")


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    home = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    out.mkdir(parents=True, exist_ok=True)
    w = Watch(rom, out, home)
    e = w.e
    to_setup(e)
    e.setb(ROW + 1, home)
    e.setb(ROW + 2, (home + 1) % 26)
    e.setw(OPTPEN, 1)
    e.run(30)
    last = None
    for f in range(60 * 120):                  # START through the screens until the clock runs
        e.run(1, hold=["START"] if f % 240 == 0 else [])
        c = e.w(CLOCK)
        if e.w(GSP) == 0 and last is not None and 0 < c < last:
            break
        last = c
    S0 = e.serialize()
    w.scan("faceoff", "play")

    def play(n, tag):                          # no pad input in play (a press in a stoppage can end the game here)
        for k in range(n // 30):
            w.step(30)
            fl = w.flags()
            if fl["hor"] or fl["pz"] or k % 8 == 7:
                w.scan(f"{tag} {'penalty' if fl['hor'] or fl['pz'] else 'play'}", "play")
            if k % 16 == 15 or ((fl["hor"] or fl["pz"]) and (tag, "pen") not in w.poked):
                w.poke(tag, "play")
                if fl["hor"] or fl["pz"]:
                    w.poked.add((tag, "pen"))
    play(3000, "p1")                           # period 1: penalties as they come
    e.unserialize(S0)
    S.put_goal(e, True)
    for k in range(12):
        w.step(30)
        w.scan(f"goal {k}", "goal")
        if k in (2, 8):
            w.poke(f"goal {k}", "goal")
    e.unserialize(S0)
    w.step(300)
    e.setw(CLOCK, 2)
    for f in range(60 * 30):                   # the intermission; the next period opens on the menu (C: Resume Game)
        w.step(1, ["C"] if e.w(GSP) == 1 and e.w(CLOCK) == 600 and f % 120 < 4 else [])
        fl = w.flags()
        if f % 120 == 60 and (fl["gsp"] == 0 or fl["vb"] != "$7A332" or e.w(CLOCK) >= 598):
            w.scan("intermission", "between periods")
            if f % 600 == 60:
                w.poke("intermission", "between periods")
        if fl["gsp"] == 1 and fl["vb"] == "$7A332" and e.w(CLOCK) < 597:
            break
    S1 = e.serialize()
    play(3000, "p2")                           # period 2: the other ends
    e.unserialize(S0)
    w.step(600)
    w.press("START", 150)
    w.scan("pause", "pause screens")
    w.poke("pause", "pause screens")
    for b, a in (("DOWN", 30), ("C", 300)):
        w.press(b, a)
    w.scan("replay", "play")
    w.poke("replay", "play")
    w.press("START", 60)
    w.press("C", 150)
    w.scan("replay reverse", "play")
    w.step(200)
    w.scan("replay reverse", "play")
    e.unserialize(S1)
    S.put_goal(e, True)                        # a lead, so the game ends rather than going to overtime
    w.step(600)
    e.setw(GSP, 2)
    e.setw(CLOCK, 2)
    for f in range(60 * 40):                   # the end of the game: the three stars (C through its screens)
        w.step(1, ["C"] if f > 600 and f % 240 < 4 else [])
        if f % 240 == 120:
            w.scan("game end", "between periods")
            if f % 960 == 120:
                w.poke("game end", "between periods")
    res = {}
    for group, U in w.use.items():
        res[group] = {f"{ln},{c}": sorted(v) for (ln, c), v in sorted(U.items()) if ln <= 1}
    play = w.use["play"]
    rink_only = {}
    for ln in (0, 1):
        for c in range(1, 16):
            if play.get((ln, c), set()) == {"rink"}:
                rink_only[f"{ln},{c}"] = {g: sorted(U.get((ln, c), set()) - {"rink"}) for g, U in w.use.items()
                                          if g != "play" and U.get((ln, c), set()) - {"rink"}}
    R = dict(rom=Path(rom).name, home=home, pokes=w.pokes, poke_moments=w.npokes, examples=w.ex, plane_b_off_rink=w.odd, rink_only=rink_only, users=res, palette_log=w.log, moments=w.moments)
    (out / "rink_colours.json").write_text(json.dumps(R, indent=1, default=list))
    P = w.pokes.get("play", {})
    order = lambda kv: [int(x) for x in kv[0].split(",")]  # noqa: E731
    print(f"by the colour poke ({w.npokes} moments): lines 0-1 colours on screen in vertical play drawn by the rink "
          "and by nothing else, and where something else draws with them:")
    for k, v in sorted(P.items(), key=order):
        if v.get("rink") and not v.get("other"):
            print(f"  {k}: rink {v['rink']} px; elsewhere: " + (", ".join(f"{g} {d[k]['other']} px ({d[k]['other at']})"
                  for g, d in w.pokes.items() if g != "play" and k in d and d[k].get("other")) or "nothing"))
    print("  shared in vertical play: " + ", ".join(f"{k} (rink {v.get('rink', 0)}, other {v['other']} px, {v['other at']})"
                                                for k, v in sorted(P.items(), key=order) if v.get("other")))
    print("by the cell scan (cells and sprites on screen, also those behind another layer):")
    print("lines 0-1 colours the rink alone uses in vertical play, and what else uses each at other moments:")
    for k, v in rink_only.items():
        print(f"  {k}: {v or 'nothing else at any moment seen'}")
    for ln in (0, 1):
        print(f"line {ln} in vertical play:")
        for c in range(1, 16):
            print(f"  {c:2d}: {', '.join(sorted(play.get((ln, c), set()))) or 'not seen'}")
    print("moments by group:", {g: sum(1 for m in w.moments if m["group"] == g) for g in w.use})
    print("palette changes (palfadenew / CRAM) with the screen's state:")
    for x in w.log:
        print("  ", {k: x[k] for k in ("frame", "what", "pz", "hor", "replay", "gsp", "vb")}, "entries", x["entries"][:8], len(x["entries"]))


if __name__ == "__main__":
    main()
