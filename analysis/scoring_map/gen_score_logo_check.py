"""For NOSE4Web's Genesis score-box logos (2026-11-08): what the original game does with the score box's corner, video
memory, palettes and priority through a whole game.

NOSE4Web's plan: printscores1's 8x5 score box at x $17, y $17 becomes 8x7 at y $15, each team two rows (a 24x16 logo
and its score, visitors above, home below), each logo in its own team's uniform palette line. A game on nhl94.bin
(penalties and line changes on, each period cut short by the clock, pad 1 on the home team), and every frame:
- the corner: map 1 (the text map, VmMAP1 $B004 / Map1col $B006) at columns $17-$1E, rows $15-$16: anything but the
  blank tile ($07FF) is logged with a screenshot and the state (pause, horizontal rink, the lower line-change box,
  sflags3 bit 0); also whenever the score box's own rows ($17-$1B) are covered by something else (the new rows
  above would then stay on screen);
- the palette lines (palfadenew $BD28: line 1 the score box's frame and fill, 2 home uniform, 3 visitors) changing.
Every 30 frames the video memory (from the core's saved state: Genesis Plus GX keeps it there, at offset VRAM_AT):
which 32-byte tiles any plane map (maps 1-3, the size from VDP register 16) or a sprite (the table at VSPRITES $B002)
uses during vertical play, and which tiles change at any time after the game starts. Along the way: line-change boxes
(A pressed while pad 1's team has the puck; lcfound by B a moment later) in two periods, so one is the lower box;
pause screens (Edit Lines, Game Stats, Player Cards, Other Scores, Crowd Meter, Instant Replay); the breaks between
periods. Gentle (idle priority).

python gen_score_logo_check.py ROM OUT"""
import hashlib
import sys
from collections import Counter, defaultdict
from pathlib import Path

import menu_shots as M
import lowload

VRAM_AT = 74789                       # Genesis Plus GX 1.7.6's state: header, work RAM, Z80 RAM ..., SAT, then VRAM
SCREEN, SFLAGS, SFLAGS3, MENUITEM, CLOCK, GSP = 0xFFF7, 0xC2EC, 0xC2F0, 0xCF20, 0xC468, 0xC466
VSPR, VMAP1, MAP1COL, VMAP2, MAP2COL, VMAP3, MAP3COL, PAL = 0xB002, 0xB004, 0xB006, 0xB008, 0xB00A, 0xB00C, 0xB00E, 0xBD28
PUCK = 0xB04A + 14 * 0x80
BLANK = 0x07FF


class Watch:
    def __init__(self, rom, out):
        self.e = M.emulator(rom)
        self.out = out
        self.frame = 0
        self.log = []
        self.shots = 0
        self.base = None                  # VRAM at the game's start
        self.changed = set()              # tiles changed since
        self.used = Counter()             # tiles a map or sprite used in vertical play (scans)
        self.used_by = defaultdict(set)
        self.pal = None
        self.corner_busy = False
        self.box_covered = False
        self.scans = 0

    def w(self, a):
        return self.e.w(0xFF0000 | a)

    def b(self, a):
        return self.e.b(0xFF0000 | a)

    def state(self):
        return dict(period=self.w(GSP), clock=self.w(CLOCK), screen=self.b(SCREEN), paused=bool(self.b(SFLAGS) & 1),
                    hor=bool(self.b(SFLAGS) & 0x80), lower_lc=bool(self.b(SFLAGS3) & 1))

    def note(self, what):
        name = f"{len(self.log):02d}"
        self.log.append((self.frame, what, self.state(), name))
        if self.shots < 60:
            self.e.screenshot(self.out / f"{name}.png")
            self.frame += 1
            self.shots += 1

    def vram(self):
        st = self.e.serialize()
        return st[VRAM_AT:VRAM_AT + 0x10000], st[VRAM_AT + 0x10000 + 0x100:VRAM_AT + 0x10000 + 0x120]

    def cell(self, vr, base, col, row, shift):
        a = (base + ((row << shift) + col) * 2) & 0xFFFF
        return vr[a] | vr[a + 1] << 8

    def in_play(self):
        s = self.state()
        return s["screen"] == 0 and not s["paused"] and not s["hor"]

    def check(self):
        """The corner, the score box rows and the palette lines (cheap: from the map words of the last VRAM read)."""
        pal = bytes(self.e.ram[(PAL & 0xFFFF):(PAL & 0xFFFF) + 0x80])
        if pal != self.pal:
            if self.pal is not None:
                lines = [k for k in range(4) if pal[32 * k:32 * k + 32] != self.pal[32 * k:32 * k + 32]]
                self.note(f"palette lines {lines} changed")
            self.pal = pal

    def scan(self):
        vr, reg = self.vram()
        if self.base is None:
            self.base = vr
        for t in range(2048):
            if t not in self.changed and vr[32 * t:32 * t + 32] != self.base[32 * t:32 * t + 32]:
                self.changed.add(t)
        size = reg[16]
        width = (32, 64, 32, 128)[size & 3]
        height = (32, 64, 32, 128)[(size >> 4) & 3]
        if self.in_play():
            self.scans += 1
            for name, (vb, vc) in (("map1", (VMAP1, MAP1COL)), ("map2", (VMAP2, MAP2COL)), ("map3", (VMAP3, MAP3COL))):
                base = self.w(vb)
                for i in range(width * height):
                    a = (base + 2 * i) & 0xFFFF
                    t = (vr[a] | vr[a + 1] << 8) & 0x7FF
                    self.used[t] += 1
                    self.used_by[t].add(name)
            sat = self.w(VSPR)
            k, seen = 0, 0
            while seen < 80:
                a = (sat + 8 * k) & 0xFFFF
                words = [vr[a + 2 * j] | vr[a + 2 * j + 1] << 8 for j in range(4)]
                size_b, link = words[1] >> 8, words[1] & 0x7F
                t0 = words[2] & 0x7FF
                n = (((size_b >> 2) & 3) + 1) * ((size_b & 3) + 1)
                for t in range(t0, t0 + n):
                    self.used[t & 0x7FF] += 1
                    self.used_by[t & 0x7FF].add("sprite")
                seen += 1
                if link == 0:
                    break
                k = link
            # the corner and the score box
            m1, sh = self.w(VMAP1), self.w(MAP1COL)
            corner = [self.cell(vr, m1, c, r, sh) for r in (0x15, 0x16) for c in range(0x17, 0x1F)]
            busy = any(v != BLANK for v in corner)
            if busy and not self.corner_busy:
                self.note("corner rows $15-$16 not blank: " + " ".join(f"{v:04x}" for v in corner))
            self.corner_busy = busy
            boxrow = [self.cell(vr, m1, c, 0x17, sh) for c in range(0x17, 0x1F)]
            covered = boxrow[0] & 0x7FF != 0x3FC            # the score box's top-left frame tile, as drawn
            if covered != self.box_covered:
                self.note("score box covered" if covered else "score box back")
            self.box_covered = covered

    def step(self, n=1, hold=()):
        for _ in range(n):
            self.e.run(1, hold=hold)
            self.frame += 1
            self.check()
            if self.frame % 30 == 0:
                self.scan()
                lowload.breathe()

    def press(self, b, after=26):
        self.step(4, hold=[b])
        self.step(after)

    def top(self):
        self.e.screenshot(self.out / "_top.png")
        self.frame += 1
        from PIL import Image
        return hashlib.md5(Image.open(self.out / "_top.png").convert("RGB").crop((0, 0, 320, 24)).tobytes()).hexdigest()

    def wait_play(self, frames=3000):
        for _ in range(frames // 30):
            c = self.w(CLOCK)
            self.step(30)
            if self.in_play() and self.w(CLOCK) != c:
                return True
        return False

    def pause_item(self, item):
        self.press("START", 90)
        menu_top = self.top()
        for _ in range(30):
            if self.w(MENUITEM) == item:
                break
            self.press("DOWN")
        self.note(f"pause item {item}")
        self.press("C", 300)
        self.note(f"in pause item {item}")
        if item == 1:
            self.step(400)
        for k in range(8):
            self.press(("START", "C", "B")[k % 3], 240)
            if self.top() == menu_top and self.state()["paused"]:
                break
        for _ in range(30):
            if self.w(MENUITEM) == 0:
                break
            self.press("UP")
        self.press("C", 240)
        self.note(f"resumed after pause item {item}")

    def line_change(self):
        """A pressed while pad 1's team has the puck: the line-change box; B a moment later picks a line."""
        for _ in range(1200):
            carried = self.b(PUCK + 0x60) == 0
            k = self.b(PUCK + 0x61)
            if carried and k < 6 and self.b(0xB04A + k * 0x80 + 0x62) & 8:
                self.press("A", 30)
                self.note("line-change box (A with the puck)")
                self.step(60)
                self.press("B", 60)
                self.note("line chosen (B)")
                return True
            self.step(1)
        return False


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    g = Watch(rom, out)
    e = g.e
    M.play(e, "w900 START w120 START w120 DOWN*7 RIGHT DOWN RIGHT w60 S:setup", out)   # penalties and line changes on
    for _ in range(40):                                  # through the matchups into play
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    g.scan()
    g.note("game on")
    plan = {0: ["lc", 3, 4], 1: ["lc", 12, 9], 2: ["lc", 10, 1]}
    for per in range(3):
        for item in plan[per]:
            g.wait_play()
            if item == "lc":
                g.line_change()
            else:
                g.pause_item(item)
            g.step(200)
        e.setw(CLOCK, min(e.w(CLOCK), 20))
        for _ in range(600):
            g.step(30)
            if g.w(GSP) > per and g.in_play():
                break
            if e.w(CLOCK) == 0 or not g.in_play():
                g.press("START", 30)
        g.note(f"period {per + 1} over")
    g.note("end")
    lines = [f"{f:7d} {what:60s} {st}" for f, what, st, _ in g.log]
    unused = [t for t in range(2048) if g.used[t] == 0]
    untouched = [t for t in unused if t not in g.changed]
    runs, run = [], []
    for t in range(2048):
        if t in set(untouched):
            run.append(t)
        else:
            if len(run) >= 12:
                runs.append((run[0], run[-1]))
            run = []
    if len(run) >= 12:
        runs.append((run[0], run[-1]))
    lines.append(f"\n{g.scans} scans in vertical play; tiles never used by a map or sprite in play: {len(unused)}; of "
                 f"those never changed all game: {len(untouched)}")
    lines.append("runs of 12+ such tiles (tile numbers, VRAM byte addresses): " + "; ".join(
        f"${a:03X}-${b:03X} ({b - a + 1}, VRAM ${32 * a:04X}-${32 * b + 31:04X})" for a, b in runs))
    used_runs, run = [], []
    for t in range(2048):
        if g.used[t] == 0:
            run.append(t)
        else:
            if len(run) >= 12:
                used_runs.append((run[0], run[-1]))
            run = []
    if len(run) >= 12:
        used_runs.append((run[0], run[-1]))
    lines.append("runs of 12+ tiles unused in play (written at some point): " + "; ".join(
        f"${a:03X}-${b:03X} ({b - a + 1})" for a, b in used_runs if not all(t in set(untouched) for t in range(a, b + 1))))
    for k in range(4):
        cols = [g.w(PAL + 32 * k + 2 * i) for i in range(16)]
        lines.append(f"palette line {k} (palfadenew, as the RAM holds it): " + " ".join(f"{c:04x}" for c in cols))
    (out / "log.txt").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
