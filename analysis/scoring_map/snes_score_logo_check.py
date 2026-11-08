"""For NOSE4Web's port of McMarkis's score-box logos to the original SNES game (2026-11-08): what the retail game does
with the video memory, palettes and palbuffer rows the 32-team build uses for them, through a whole game.

A game on the ROM (penalties on, every period cut to a minute by the clock, pad 1 on the home team doing nothing):
the 12 tiles from ExtraChars (setupice: the first tile after TeamBlocksTiles; VRAM word ExtraChars x 16 + $1000) are
filled with a marker once play starts, and every frame checks whether the game wrote over them; when it did, the
state is logged with a screenshot, and the marker goes back as play resumes (as the port's reload would put the
logos back). palbuffer's rows 4 and 7 ($7E35F4 + row x $20) are watched for any write. In play (vertical and
horizontal rink) every 10 frames both background maps are scanned: BG1 (the text layer: score box, clock box; map at
word 0, 32 x 32, tiles from word $2000, printed tile numbers are global - 256) and BG2 (the rink; map at word $400,
64 x 32, tiles from $1000): which palettes each uses, which colour numbers palette 4's tiles use, and whether any entry
points at the marked tiles. Along the way: a pause into every safe pause-menu item (each screen left with START), an
instant replay, a power play shown by making the two tmap words differ, and the intermissions between periods.

python snes_score_logo_check.py ROM OUT_DIR"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

import menu_shots as M

SFLAGS, SFHOR, GSP, CLOCK, PSITEM, TMAP, EXTRA, PALBUF = 0x15D8, 0x15DA, 0x1630, 0x1632, 0x0D15, 0x17A6, 0x35C2, 0x35F4
PAUSE_ITEMS = [2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 1]      # stats screens ... player cards, other scores, crowd, replay
MARK = bytes((0xA5, 0x5A) * 192)                          # 12 tiles x 32 bytes


class Check:
    def __init__(self, rom, out):
        import ctypes as C
        self.e = e = M.emulator(rom)
        self.vram = (C.c_ubyte * e.lib.retro_get_memory_size(3)).from_address(e.lib.retro_get_memory_data(3))
        self.out = out
        self.log = []
        self.frame = 0
        self.region = None
        self.pal = None
        self.uses = defaultdict(Counter)         # (mode, layer) -> palette counts
        self.p4colours = defaultdict(Counter)    # (mode, layer) -> colour numbers palette 4 tiles use
        self.refs = Counter()
        self.shots = 0

    def vr(self, a, n):
        return bytes(self.vram[a:a + n])

    def state(self):
        w = self.e.w
        s = w(SFLAGS)
        return dict(period=w(GSP), clock=w(CLOCK), paused=bool(s & 1), replay=bool(s & 0x0800), hor=w(SFHOR) != 0)

    def in_play(self):
        st = self.state()
        return not st["paused"] and not st["replay"]

    def note(self, what):
        st = self.state()
        name = f"{len(self.log):02d}"
        self.log.append((self.frame, what, st, name))
        if self.shots < 40:
            self.e.screenshot(self.out / f"{name}.png")
            self.shots += 1

    def mark(self):
        x = self.e.w(EXTRA)
        a = (x * 16 + 0x1000) * 2
        for i, b in enumerate(MARK):
            self.vram[a + i] = b
        self.region = (x, a)

    def palrows(self):
        return bytes(self.e.ram[PALBUF + 4 * 32:PALBUF + 5 * 32]) + bytes(self.e.ram[PALBUF + 7 * 32:PALBUF + 8 * 32])

    def scan(self):
        mode = "horizontal" if self.state()["hor"] else "vertical"
        x = self.region[0]
        for layer, base, size, tiles, off in (("BG1", 0x0000, 1024, 0x2000, 256), ("BG2", 0x0800, 2048, 0x1000, 0)):
            raw = self.vr(base, size * 2)
            for i in range(size):
                e = raw[2 * i] | raw[2 * i + 1] << 8
                t, p = e & 0x3FF, (e >> 10) & 7
                self.uses[(mode, layer)][p] += 1
                if layer == "BG1" and x - off <= t < x - off + 12:
                    self.refs[(mode, t)] += 1
                if True:                                  # every palette: which colour numbers its tiles use
                    ta = (tiles + 16 * t) * 2
                    d = self.vr(ta, 32)
                    for row in range(8):
                        b0, b1, b2, b3 = d[2 * row], d[2 * row + 1], d[16 + 2 * row], d[17 + 2 * row]
                        for bit in range(8):
                            c = (b0 >> bit & 1) | (b1 >> bit & 1) << 1 | (b2 >> bit & 1) << 2 | (b3 >> bit & 1) << 3
                            self.p4colours[(mode, layer, p)][c] += 1

    def step(self, n=1, hold=()):
        e = self.e
        for _ in range(n):
            e.run(1, hold=hold)
            self.frame += 1
            if self.region is None:
                continue
            x, a = self.region
            if e.w(EXTRA) != x:
                self.note(f"ExtraChars changed {x:#x} -> {e.w(EXTRA):#x}")
                self.region = (e.w(EXTRA), (e.w(EXTRA) * 16 + 0x1000) * 2)
            if not getattr(self, "wait_marker", False) and self.vr(a, len(MARK)) != MARK:
                self.note("marked tiles written over")
                self.wait_marker = True                 # put back when play resumes
            pr = self.palrows()
            if pr != self.pal:
                self.note("palbuffer rows 4 / 7 changed")
                self.pal = pr
            if getattr(self, "wait_marker", False) and self.in_play() and e.w(0x0AD3) == 15:
                self.mark()
                self.wait_marker = False
                self.note("in play again: marker put back")
            if self.frame % 10 == 0 and self.in_play() and not getattr(self, "wait_marker", False) and e.w(0x0AD3) == 15:
                self.scan()

    def press(self, b, after=26):
        self.step(4, hold=[b])
        self.step(after)

    def top(self):
        """A fingerprint of the screen's top rows (the arena scoreboard on the pause menu)."""
        import hashlib
        self.e.screenshot(self.out / "_top.png")
        self.frame += 1
        from PIL import Image
        return hashlib.md5(Image.open(self.out / "_top.png").convert("RGB").crop((0, 0, 256, 24)).tobytes()).hexdigest()

    def pause_item(self, item):
        e = self.e
        self.press("START", 90)
        menu_top = self.top()
        for _ in range(40):
            if e.w(PSITEM) == item:
                break
            self.press("DOWN")
        self.note(f"pause menu item {item}")
        self.press("A", 300)
        self.note(f"in item {item}")
        if item == 1:                             # the replay: let it run a while
            self.step(300)
        for k in range(8):                        # leave: START, then A (Edit Lines' "Return to Game"), until the
            self.press("START" if k % 2 == 0 else "A", 240)    # pause menu's scoreboard is back
            if self.top() == menu_top and self.state()["paused"]:
                break
        self.note(f"left item {item}")
        for _ in range(40):
            if e.w(PSITEM) == 0:
                break
            self.press("UP")
        self.press("START", 240)
        self.note(f"resumed after item {item}")

    def through_break(self, per):
        """Period per (0-based) is over: press START through the intermission screens until play runs in the next."""
        e = self.e
        for k in range(60):
            for _ in range(30):
                self.step(10)
                if e.w(GSP) == per + 1 and self.in_play() and not self.state()["hor"] and e.w(0x0AD3) == 15                         and e.w(CLOCK) < 600 and e.w(CLOCK) > 0:
                    self.note(f"period {per + 2} under way")
                    return True
            if k % 3 == 0:
                self.note(f"between periods ({k})")
            self.press("START", 30)
        return False

def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    c = Check(rom, out)
    e = c.e
    M.play(e, "w1500 START w240 START w240 DOWN*4 RIGHT DOWN RIGHT w60", out)   # penalties on, line changes on
    M.play(e, "S:setup START w240 START w120 w2400 START w300 START w600", out)
    for _ in range(600):                                                     # play running
        c.step()
        if c.in_play() and e.w(0x0AD3) == 15:
            break
    c.mark()
    c.pal = c.palrows()
    c.note("game on: marker placed")
    plan = {0: [2, 3, 4, 5], 1: [6, 7, 8, 12, "pp"], 2: [13, 14, 1]}
    for per in range(3):
        for item in plan[per]:
            for _ in range(200):                  # wait for play (not on the scoreboard, not paused)
                if c.in_play() and not c.state()["hor"] and e.w(0x0AD3) == 15:
                    break
                c.step(10)
            if item == "pp":
                t1 = e.w(TMAP + 2)
                e.setw(TMAP + 2, t1 - 1)
                c.step(120)
                c.note("power play shown (tmap)")
                e.setw(TMAP + 2, t1)
                c.step(60)
            else:
                c.pause_item(item)
            c.step(300)
        e.setw(CLOCK, min(e.w(CLOCK), 20))        # then to the end of the period
        for _ in range(400):
            c.step(30)
            if e.w(CLOCK) == 0 and not c.in_play():
                break
        c.note(f"period {per + 1} over")
        if per < 2 and not c.through_break(per):
            c.note("stuck between periods")
            break
    c.note("end")
    lines = [f"{f:7d} {what:40s} {st}" for f, what, st, _ in c.log]
    lines.append("\npalettes used in play (mode, layer): counts of map entries by palette")
    for k, v in sorted(c.uses.items()):
        lines.append(f"  {k}: {dict(sorted(v.items()))}")
    lines.append("colour numbers the tiles use, by (mode, layer, palette): pixel counts")
    for k, v in sorted(c.p4colours.items()):
        lines.append(f"  {k}: {dict(sorted(v.items()))}")
    lines.append(f"map entries pointing at the marked tiles: {dict(c.refs)}")
    (out / "log.txt").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
