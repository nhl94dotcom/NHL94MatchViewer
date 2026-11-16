"""NHL '95 (Genesis): team banners (2026-11-16, for NOSE4Web 2ad82c0 / 62c8eba: the menu set TeamBitmaps, the in-game
set Teamblocksmap, the pause set PauseTeamBlocksMap). Screens, the same presses on two ROMs (an original and a
build), screenshotted and compared pixel by pixel:
  per team T (Team 1 = T, Team 2 = T + 1): Game Setup (menu set), Controller Setup (in-game set), the pause screen
  (pause set), Game Statistics (in-game set), the line editor (in-game set);
  once: New Playoffs' tree (in-game set), New Season's Games Today (in-game set), NHL Standings (in-game set; RIGHT the other conference, UP the
  divisions).
Printed per screen: pixels differing and their box. Screenshots in OUT/<tag>_<screen>.png.

python gen95_banner_check.py ORIGINAL BUILD OUT NTEAMS [TEAMS...]"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from emu import Emu
import gen95_fight_check as F
import lowload

ROW = 0xD282


def press(e, b, w=120):
    e.run(6, hold=[b]); e.run(w)


def team_route(rom, t, n, out, tag):
    e = Emu(rom)
    F.to_setup(e)
    e.setb(ROW + 1, t); e.setb(ROW + 2, (t + 1) % n)
    press(e, "DOWN", 30); press(e, "UP", 60)
    shots = {}

    def snap(name):
        p = out / f"{tag}_t{t:02d}_{name}.png"; e.screenshot(p); shots[name] = p
    snap("setup")
    press(e, "START", 300); snap("controller")
    last, f = None, 0
    while f < 60 * 120:                                   # START through the intro screens until the clock runs
        e.run(1, hold=["START"] if f % 240 == 0 else []); f += 1
        c = e.w(0xC022)
        if e.w(0xC020) == 0 and last is not None and 0 < c < last:
            break
        last = c
    e.run(300)
    press(e, "START", 150); snap("pause")
    press(e, "LEFT", 90); press(e, "DOWN", 30); press(e, "C", 300); snap("gamestats")
    press(e, "B", 200); press(e, "RIGHT", 90); press(e, "RIGHT", 90)
    press(e, "DOWN", 30); press(e, "DOWN", 30); press(e, "C", 300); snap("editlines")
    return shots


def once_route(rom, out, tag):
    shots = {}

    def snap(e, name):
        p = out / f"{tag}_{name}.png"; e.screenshot(p); shots[name] = p
    e = Emu(rom); F.to_setup(e)
    press(e, "RIGHT", 60); press(e, "RIGHT", 60)                     # Play Mode: New Playoffs
    snap(e, "setup_playoffs")
    press(e, "START", 400); press(e, "START", 400); snap(e, "playoffs")
    press(e, "START", 400); snap(e, "playoffs2")
    e = Emu(rom); F.to_setup(e)
    e.setb(ROW, 6); press(e, "DOWN", 30); press(e, "UP", 60)          # New Season
    press(e, "START", 400); press(e, "START", 400)
    for d in range(6):
        snap(e, f"today{d}")
        press(e, "RIGHT", 120)
    press(e, "START", 400); snap(e, "season_options")
    press(e, "DOWN", 30); press(e, "DOWN", 30); press(e, "C", 400); snap(e, "standings")
    press(e, "RIGHT", 200); snap(e, "standings2")
    press(e, "UP", 200); snap(e, "standings3")
    press(e, "UP", 200); snap(e, "standings4")
    return shots


def compare(a, b):
    x = np.asarray(Image.open(a).convert("RGB")); y = np.asarray(Image.open(b).convert("RGB"))
    d = np.any(x != y, axis=2); ys, xs = np.nonzero(d)
    return int(d.sum()), ((int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())) if len(xs) else None)


def main():
    orig, build, out, n = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4])
    teams = [int(a) for a in sys.argv[5:]] or list(range(n))
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    a, b = once_route(orig, out, "orig"), once_route(build, out, "build")
    for k in a:
        print(f"once {k}: {compare(a[k], b[k])}", flush=True)
    for t in teams:
        a, b = team_route(orig, t, n, out, "orig"), team_route(build, t, n, out, "build")
        print(f"team {t}: " + "; ".join(f"{k} {compare(a[k], b[k])}" for k in a), flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
