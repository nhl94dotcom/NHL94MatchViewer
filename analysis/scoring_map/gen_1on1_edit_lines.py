"""Edit Lines and Team Rosters on the 1-on-1 ROM (2026-11-09, for NOSE4Web's "Edit Lines for fewer skaters"):
NHL941on1.bin (C only) against NOSE4Web's NHL941on1_edit_lines.bin. From power-on to play, line changes off
(OptLine $D058 = 1; 0 is on, LC=on), then the pause menu: Edit Lines (item 3) with every line stepped through (RIGHT moves the line,
DOWN the row; C on a row opens the roster list, B backs out), and Team Rosters. A screenshot at each step; a step that
leaves the frame counter or the screen unchanged for 600 frames of presses is reported as a hang.

python gen_1on1_edit_lines.py ROM OUT [explore]"""
import hashlib
import sys
from pathlib import Path

import lowload
import menu_shots as M

TESTLIST, OPTLINE, MENUITEM, SCREEN, SFLAGS = 0xD5B8, 0xD058, 0xCF20, 0xFFF7, 0xC2EC
VCOUNT = 0xB03E


class Run:
    def __init__(self, rom, out):
        self.e = M.emulator(rom)
        self.out = out
        out.mkdir(parents=True, exist_ok=True)
        self.n = 0
        self.log = []

    def step(self, n, hold=()):
        for k in range(n):
            self.e.run(1, hold=hold)
            if k % 60 == 59:
                lowload.breathe()

    def press(self, b, after=40):
        self.step(4, hold=[b])
        self.step(after)

    def shot(self, what):
        p = self.out / f"{self.n:02d}_{what}.png"
        self.e.screenshot(p)
        self.n += 1
        h = hashlib.md5(p.read_bytes()).hexdigest()
        self.log.append((p.name, what, hex(self.e.w(TESTLIST)), self.e.w(MENUITEM), self.e.w(VCOUNT)))
        print(p.name, what, "testlist", hex(self.e.w(TESTLIST)), "item", self.e.w(MENUITEM), "vcount",
              self.e.w(VCOUNT), flush=True)
        return h

    def to_play(self):
        M.play(self.e, "w900 START w120 START w120 w60", self.out / "_boot")
        for _ in range(60):
            if self.e.b(SCREEN) == 0:
                break
            self.step(4, hold=["START"])
            self.step(200)
        for _ in range(100):
            c = self.e.w(0xC468)
            self.step(30)
            if self.e.b(SCREEN) == 0 and self.e.w(0xC468) != c:
                return True
        return False

    def alive(self, presses=("B",)):
        """The game still answers: the screen changes, or the pause menu comes back, within some presses."""
        a = self.shot("check")
        for b in presses * 4:
            self.press(b, 120)
            if self.shot("check") != a:
                return True
        return False

    def menu(self, item):
        for _ in range(30):
            if self.e.w(MENUITEM) == item:
                break
            self.press("DOWN")
        self.press("C", 240)


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    explore = len(sys.argv) > 3
    r = Run(rom, out)
    print("in play:", r.to_play())
    import os
    print("OptLine as the game set it:", r.e.w(OPTLINE))
    r.e.setw(OPTLINE, 0 if os.environ.get("LC") == "on" else 1)     # OptLine: 0 on, 1 off, 2 auto (optsetup94)
    play = r.e.serialize()
    r.press("START", 90)
    r.shot("pause_menu")
    if explore:
        for i in range(8):
            r.press("DOWN")
            r.shot(f"menu_down{i + 1}")
        return
    # Edit Lines: every line, and the roster list from each line's first row
    r.menu(3)
    r.shot("edit_lines")
    for line in range(8 if not os.environ.get("QUICK") else 1):
        r.shot(f"line{line}")
        st = r.e.serialize()
        r.press("C", 120)
        r.shot(f"line{line}_C")
        r.press("DOWN", 60)
        r.shot(f"line{line}_C_down")
        r.press("B", 120)
        r.shot(f"line{line}_back")
        r.e.unserialize(st)
        r.press("RIGHT", 60)
    # Team Roster (item 8): its pages by RIGHT (and back by LEFT), each a screenshot; a page that never answers is a hang
    r.e.unserialize(play)
    r.press("START", 90)
    r.menu(8)
    last = r.shot("team_roster")
    for i in range(12):
        r.press("RIGHT", 150)
        h = r.shot(f"team_roster_right{i + 1}")
        if h == last:
            print("  (unchanged after RIGHT)")
        last = h
    for i in range(8):                                  # the line chooser: Scoring 1, 2, Checking, PP 1, 2, PK 1, 2
        r.press("DOWN", 150)
        r.shot(f"team_roster_down{i + 1}")
        r.press("RIGHT", 150)
        r.shot(f"team_roster_down{i + 1}_right")
    r.press("B", 200)
    r.shot("team_roster_B")
    r.press("START", 200)
    r.shot("team_roster_START")


if __name__ == "__main__":
    main()
