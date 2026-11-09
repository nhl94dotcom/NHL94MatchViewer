"""Which line slots the Genesis line editor's cursor can reach (2026-11-09, for NOSE4Web): retail nhl94.bin from power-on
to play, the pause menu's Edit Lines (item 3, C), then every slot reachable by up / down / left / right from the
first (each reached slot's state kept and all four directions tried from it), with OptLine ($D058) 0 and 1. The cursor
is TestList ($D5B8: line * 8 + slot, slots 0 G, 1 LD, 2 RD, 3 LW, 4 C, 5 RW, 6 extra attacker), found by its 1, 2, 3
under DOWN presses; the code's LineCursorTable (stats94.asm) is what the presses follow.

python gen_line_editor_cursor.py ROM OUT"""
import sys
from pathlib import Path

import menu_shots as M
from gen_score_logo_check import Watch, MENUITEM

TESTLIST, OPTLINE = 0xD5B8, 0xD058
NAMES = ["G", "LD", "RD", "LW", "C", "RW", "EA", "-"]


def main():
    rom, out = sys.argv[1], Path(sys.argv[2])
    g = Watch(rom, out)
    e = g.e
    M.play(e, "w900 START w120 START w120 w60", out)
    for _ in range(40):
        if e.b(0xFFF7) == 0:
            break
        e.run(4, hold=["START"])
        e.run(200)
    g.wait_play()
    play = e.serialize()
    for opt in (0, 1):
        e.unserialize(play)
        e.setw(OPTLINE, opt)
        g.press("START", 90)
        for _ in range(30):
            if e.w(MENUITEM) == 3:
                break
            g.press("DOWN")
        g.press("C", 240)
        start = e.w(TESTLIST)
        seen, todo = {start: e.serialize()}, [start]
        while todo:
            s = todo.pop()
            for d in ("UP", "DOWN", "LEFT", "RIGHT"):
                e.unserialize(seen[s])
                g.press(d, 40)
                t = e.w(TESTLIST)
                if t not in seen:
                    seen[t] = e.serialize()
                    todo.append(t)
        lines = {}
        for s in sorted(seen):
            lines.setdefault(s // 8, []).append(NAMES[s % 8])
        print(f"OptLine {opt}:", {f"line {k}": v for k, v in lines.items()})
        e.unserialize(seen[start])
        e.screenshot(out / f"editor_optline{opt}.png")


if __name__ == "__main__":
    main()
