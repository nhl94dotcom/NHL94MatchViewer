"""NHL '95 (Genesis): centre-ice logos (2026-11-16, for NOSE4Web 62e10aa: TeamGfxList's $30A blocks, 24 tiles drawn 6 x 4
at centre ice in the home team's colours). For each team at home (Game Setup's Team 1; Team 2 the next team): into
the game, START through the screens, and a screenshot of the opening faceoff at centre ice (the state 40 frames before
the clock first runs), for the original and the build; the two compared pixel by pixel (the same presses give the same
game, so only the logo should differ). With --replay TEAM: that team's game paused 5 s after the drop, INSTANT REPLAY,
START (the replay banner), C (reverse angle), C (play), screenshots as it plays.

python gen95_rink_logo_check.py ORIGINAL BUILD OUT NTEAMS [--replay TEAM]"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from emu import Emu
import gen95_fight_check as F
import lowload

GSP, CLOCK, ROW = 0xC020, 0xC022, 0xD282


def opening(rom, home, away, base=None):
    e = Emu(rom)
    F.to_setup(e)
    e.setb(ROW + 1, home); e.setb(ROW + 2, away); e.run(30)
    states, last, f = [], None, 0
    while f < 60 * 120:
        if f % 20 == 0:
            states.append(e.serialize()); states = states[-4:]
        e.run(1, hold=["START"] if f % 240 == 0 else [])
        f += 1
        c = e.w(CLOCK)
        if e.w(GSP) == 0 and last is not None and 0 < c < last:
            e.unserialize(states[0])
            return e
        last = c
    return None


def shot(e, path):
    e.screenshot(path)
    return np.asarray(Image.open(path).convert("RGB"))


def main():
    orig, build, out, n = sys.argv[1], sys.argv[2], Path(sys.argv[3]), int(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    lowload.gentle()
    rep = [int(a) for a in sys.argv[5:] if a.isdigit()]
    if "--replay" in sys.argv:
        t = rep[0]
        for tag, rom in (("orig", orig), ("build", build)):
            e = opening(rom, t, (t + 1) % n)
            e.run(300)
            for b, w in (("START", 120), ("DOWN", 30), ("C", 300)):
                e.run(6, hold=[b]); e.run(w)
            e.run(6, hold=["START"]); e.run(60)       # the replay banner (B Options, C Rev. Angle)
            e.run(6, hold=["C"]); e.run(120)          # reverse angle (sflags4 $FFBEFA bit 4)
            print(f"{tag}: reverse angle flag {bool(e.b(0xBEFA) & 0x10)}")
            e.screenshot(out / f"replay_{tag}_0.png")
            e.run(6, hold=["C"]); e.run(10)           # play
            for k in range(1, 9):
                e.run(40); e.screenshot(out / f"replay_{tag}_{k}.png")
        return
    for t in range(n):
        imgs = []
        for tag, rom in (("orig", orig), ("build", build)):
            e = opening(rom, t, (t + 1) % n)
            if e is None:
                imgs.append(None); continue
            imgs.append(shot(e, out / f"team{t:02d}_{tag}.png"))
        if imgs[0] is None or imgs[1] is None:
            print(f"team {t}: no opening faceoff reached"); continue
        d = np.any(imgs[0] != imgs[1], axis=2)
        ys, xs = np.nonzero(d)
        box = f" in x {xs.min()}-{xs.max()}, y {ys.min()}-{ys.max()}" if len(xs) else ""
        print(f"team {t}: pixels differing {int(d.sum())}{box}", flush=True)
        lowload.breathe()


if __name__ == "__main__":
    main()
