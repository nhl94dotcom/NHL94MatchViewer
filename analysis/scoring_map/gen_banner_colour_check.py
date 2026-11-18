"""NOSE4Web's in-game banner colours (Genesis, 2026-11-18): a team's missing stripe colour put into the arena's line 1
colour 11 ($59924's line 1: the word at $5995A, retail $020 dark green), the test ROM San Jose's top stripe teal
$0AA0 with its in-game banner (the TeamBlocks set: setupTeamBlocksMap, PutTeamBlock, PlayoffScreen_doteam) lettered SJ.

The same route on two ROMs (an original and the build), San Jose against New Jersey (Opt1team / Opt2team set at Game
Setup), each screen screenshotted and, from its saved state, the pixels drawn with colour memory entry 27 (line 1
colour 11) found exactly: that entry set to a marker colour in the state and the frame drawn again, every pixel that
changes uses it. So on each screen: where the slot shows (its pixels' bounding boxes and a mask image), and its value
there (the colour memory's 9-bit form and as a Genesis word).
Screens: Game Setup; each screen before the opening faceoff (START pressed through them); play; the pause screen and
each pause item (C on items 1-8); the horizontal rink of a penalty (the computer on both sides, the visitors held at
Aggression 38 until one); the screens of the first intermission (START through them); the playoff tree (New Playoffs:
OptPlayMode 1, START from Game Setup, San Jose put in Buffalo's place in potree $FFCEF4); the boot screens (the EA logo).

python gen_banner_colour_check.py ORIGINAL BUILD OUT        (OUT/<orig|build>/NAME.png, NAME_slot.png, report.json)"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import gen_ot_check as G
import lowload
from emu import Emu
from gen_score_logo_check import VRAM_AT

OPT1, OPT2, OPTPEN, PERLEN, PLAYMODE = 0xD04C, 0xD04E, 0xD056, 0xD050, 0xD048
SCREEN, SFLAGS, MENUITEM, CLOCK, GSP, CONT1, CONT2 = 0xFFF7, 0xC2EC, 0xCF20, 0xC468, 0xC466, 0xC328, 0xC32A
BASE, SZ = 0xB04A, 0x80
PUCK, OPTLINE = 0xB04A + 14 * 0x80, 0xD058
SJ, NJ = 19, 12
POTREE = 0xCEF4                  # potree: the 16 teams of the playoff tree, bytes (found in RAM: retail's bracket)
ENTRY = 27                       # colour memory entry: line 1, colour 11
CRAM = VRAM_AT + 0x10000         # Genesis Plus GX's colour memory in its state: 64 words, 9-bit form (BBBGGGRRR)
MARK = 0x1C7                     # magenta in the 9-bit form


def grab(e):
    e.want_frame = True
    e.lib.retro_run()
    e.want_frame = False
    data, w, h, pitch = e.frame
    if getattr(e, "pixfmt", 0) == 2:
        img = Image.frombuffer("RGB", (w, h), data, "raw", "BGR;16", pitch, 1)
    else:
        img = Image.frombuffer("RGBX", (w, h), data, "raw", "BGRX", pitch, 1).convert("RGB")
    return np.array(img)


def nine_to_word(v):
    r, g, b = v & 7, (v >> 3) & 7, (v >> 6) & 7
    return f"${b << 9 | g << 5 | r << 1:04X}"


def boxes(mask):
    """Bounding boxes of the mask's 8-way connected parts (x0, y0, x1, y1, pixels), largest first."""
    lab = np.zeros(mask.shape, np.int32)
    out = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]:
            continue
        n = len(out) + 1
        stack, pts = [(y0, x0)], []
        lab[y0, x0] = n
        while stack:
            y, x = stack.pop()
            pts.append((y, x))
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[yy, xx] and not lab[yy, xx]:
                        lab[yy, xx] = n
                        stack.append((yy, xx))
        p = np.array(pts)
        out.append((int(p[:, 1].min()), int(p[:, 0].min()), int(p[:, 1].max()), int(p[:, 0].max()), len(p)))
    return sorted(out, key=lambda b: -b[4])


class Route:
    def __init__(self, rom, out):
        self.e = Emu(rom)
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.report = {}

    def press(self, b, after=26):
        self.e.run(4, hold=[b])
        self.e.run(after)

    def capture(self, name):
        """The screen and the pixels drawn with entry ENTRY (the state left as it was)."""
        e = self.e
        st = e.serialize()
        a = grab(e)
        e.unserialize(st)
        val = st[CRAM + 2 * ENTRY] | st[CRAM + 2 * ENTRY + 1] << 8
        line1 = [st[CRAM + 32 + 2 * i] | st[CRAM + 33 + 2 * i] << 8 for i in range(16)]
        mark = bytearray(st)
        mv = MARK if val != MARK else 0x038
        mark[CRAM + 2 * ENTRY], mark[CRAM + 2 * ENTRY + 1] = mv & 0xFF, mv >> 8
        e.unserialize(bytes(mark))
        b = grab(e)
        e.unserialize(st)
        mask = np.any(a != b, axis=2)
        Image.fromarray(a).save(self.out / f"{name}.png")
        over = a.copy()
        over[mask] = (255, 0, 255)
        Image.fromarray(over).save(self.out / f"{name}_slot.png")
        self.report[name] = dict(entry=nine_to_word(val), line1=[nine_to_word(v) for v in line1],
                                 pixels=int(mask.sum()), boxes=boxes(mask)[:12])
        return a, mask

    def save(self):
        (self.out / "report.json").write_text(json.dumps(self.report, indent=1))


def game_route(rom, out):
    r = Route(rom, out)
    e = r.e
    for f in (150, 300, 450, 600, 750):                    # the boot screens (EA logo and on)
        e.run(150 if f > 150 else 150)
        r.capture(f"boot_{f}")
    e.run(900 - 750)
    e.run(4, hold=["START"]); e.run(120)
    e.run(4, hold=["START"]); e.run(320)
    e.setw(OPT1, SJ)
    e.setw(OPT2, NJ)
    e.setw(OPTPEN, 2)
    e.setw(PERLEN, 0)
    r.press("DOWN", 30); r.press("UP", 60)
    r.capture("setup")
    seen = set()
    for k in range(30):                                   # START through the screens before the faceoff
        if e.b(SCREEN) == 0:
            c = e.w(CLOCK)
            e.run(60)
            if e.b(SCREEN) == 0 and e.w(CLOCK) != c:
                break
        img = grab(e)
        h = hash(img[::4, ::4].tobytes())
        if h not in seen:
            seen.add(h)
            r.capture(f"pre_{len(seen):02d}")
        r.press("START", 90)
    e.run(240)
    r.capture("play")
    play = e.serialize()
    r.press("START", 120)
    r.capture("pause")
    paused = e.serialize()
    for item in range(1, 9):
        e.unserialize(paused)
        for _ in range(30):
            if e.w(MENUITEM) == item:
                break
            r.press("DOWN")
        r.press("C", 300)
        r.capture(f"pause_item{item}")
        if item == 1:                                      # the instant replay's panel
            r.press("START", 120)
            r.capture("pause_item1_panel")
    # a penalty: the computer on both sides, the visitors' aggression held up, until the horizontal rink
    e.unserialize(play)
    got = False
    for f in range(0, 60 * 60 * 12, 2):
        if f % 60 == 0:
            e.setw(CONT1, 0)
            e.setw(CONT2, 0)
            for k in range(12):
                e.setb(BASE + SZ * k + 0x62, e.b(BASE + SZ * k + 0x62) & ~8)
            if f % 3600 == 0:
                lowload.breathe()
        for k in range(12):
            if 1 <= e.b(BASE + SZ * k + 0x35) <= 6:
                e.setb(BASE + SZ * k + 0x73, 38)
        e.run(2)
        if e.b(SFLAGS) & 0x80 and not e.b(SFLAGS) & 1:
            e.run(90)
            r.capture("penalty_box")
            got = True
            break
    r.report["penalty_found"] = got
    # the first intermission: every screen from the horn to period 2's play, START every 2 s (the period count goes up
    # at the horn, so play is only "back" once the clock runs again in period 2)
    e.unserialize(play)
    e.setw(CLOCK, 2)
    seen, last = set(), None
    for k in range(60):
        e.run(120)
        c = e.w(CLOCK)
        if e.b(SCREEN) == 0 and e.w(GSP) == 1 and last is not None and c != last and not e.b(SFLAGS) & 0x81:
            break
        last = c
        img = grab(e)
        h = hash(img[::4, ::4].tobytes())
        if h not in seen:
            seen.add(h)
            r.capture(f"break_{len(seen):02d}")
        if k % 2:
            r.press("START", 30)
    # the energy bars: line changes on, the line-change box (A while pad 1's team has the puck)
    e.unserialize(play)
    e.setw(OPTLINE, 0)
    r.report["linechange_found"] = False
    for f in range(6000):
        k = e.b(PUCK + 0x61)
        if e.b(PUCK + 0x60) == 0 and k < 12 and e.b(BASE + SZ * k + 0x62) & 8:
            e.run(30, hold=["A"])
            e.run(20)
            r.capture("linechange_box")
            r.report["linechange_found"] = True
            break
        e.run(1)
    r.save()
    return r.report


def playoff_route(rom, out):
    r = Route(rom, out)
    e = r.e
    G.to_setup(e, out)
    e.setw(PLAYMODE, 1)
    r.press("DOWN", 30); r.press("UP", 30)
    e.setb(POTREE, SJ)                                     # San Jose in Buffalo's place (the bracket's first team)
    r.capture("playoff_setup")
    e.run(4, hold=["START"])
    for _ in range(60):
        e.setb(POTREE, SJ)
        e.run(1)
    seen = set()
    for k in range(16):
        e.run(400)
        img = grab(e)
        h = hash(img[::4, ::4].tobytes())
        if h not in seen:
            seen.add(h)
            r.capture(f"playoff_{len(seen):02d}")
    r.save()
    return r.report


def main():
    lowload.gentle()
    orig, build, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    if len(sys.argv) > 4 and sys.argv[4] == "game":
        for tag, rom in (("orig", orig), ("build", build)):
            rep = game_route(rom, out / f"{tag}_game2")
            for n, v in sorted(rep.items()):
                print(tag, n, v if not isinstance(v, dict) else (v["entry"], v["pixels"], v["boxes"][:4]))
        return
    if len(sys.argv) > 4 and sys.argv[4] == "playoff":
        for tag, rom in (("orig", orig), ("build", build)):
            rep = playoff_route(rom, out / f"{tag}_playoff")
            for n, v in sorted(rep.items()):
                print(tag, n, v["entry"], v["pixels"], v["boxes"][:4])
        return
    res = {}
    for tag, rom in (("orig", orig), ("build", build)):
        res[tag] = game_route(rom, out / tag)
        res[tag].update(playoff_route(rom, out / tag))
        print(tag, "done", flush=True)
    names = sorted(set(res["orig"]) & set(res["build"]) - {"penalty_found"})
    for n in names:
        a, b = res["orig"][n], res["build"][n]
        if not isinstance(a, dict):
            continue
        ia = np.array(Image.open(out / "orig" / f"{n}.png").convert("RGB"))
        ib = np.array(Image.open(out / "build" / f"{n}.png").convert("RGB"))
        diff = int(np.any(ia != ib, axis=2).sum()) if ia.shape == ib.shape else -1
        print(f"{n:20} entry 27 orig {a['entry']} build {b['entry']}; pixels using it orig {a['pixels']} build {b['pixels']};"
              f" pixels differing {diff}; build boxes {b['boxes'][:5]}")
    print("penalty found:", res["orig"].get("penalty_found"), res["build"].get("penalty_found"))
    (out / "report.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
