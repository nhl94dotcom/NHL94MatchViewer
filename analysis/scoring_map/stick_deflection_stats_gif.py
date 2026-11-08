"""The stick deflection with the game's own Game Stats before and after, in one continuous take (2026-11-08, for a
community member; stick_deflection_gif.py has the play itself). From the moment the shooter is set with the puck:
START, down to Game Stats, its screen (Shots for both teams), START back to the menu, Resume Game; then the slapshot
along the ice that comes off the goalie's stick; then START, Game Stats again: the shooter's team's Shots unchanged.
Trials are searched with the whole sequence played, so the clip is the game as it ran, frame by frame (menu frames
every other one at real speed, the play at a third of it).

python stick_deflection_stats_gif.py OUT.gif [ROM]   (NHL94_SDG_DOWN=1: the bottom net, period 2)"""
import random
import sys

from PIL import Image, ImageDraw

import stick_deflection_gif as D
from bot_scenario import live_state
from emu import Emu
from paths import WORK


class Film(D.Film):
    def __init__(self, e):
        super().__init__(e)
        self.durations, self.tick = [], 0

    def step(self, hold=(), note=None, colour=(255, 255, 255), every=1, ms=50):
        self.tick += 1
        if note is None or self.tick % every:
            self.e.run(1, hold=hold)
            return
        super().step(hold, note, colour)
        self.durations.append(ms)


def menu(e, film, buttons, note, settle=40):
    step = (lambda hold=(), **k: e.run(1, hold=hold)) if film is None else \
        (lambda hold=(), **k: film.step(hold, note, every=2, ms=33))
    for b in buttons:
        for _ in range(4):
            step(hold=[b])
        for _ in range(settle):
            step()


def take(e, base, rnd, film=None):
    hold = D.setup(e, base, rnd)
    menu(e, film, ["START"], "paused")
    menu(e, film, ["DOWN"] * 4, "paused: down to Game Stats", settle=12)
    menu(e, film, ["C"], "Game Stats before the shot", settle=120)
    if film:
        film.durations[-1] += 3000                       # time to read it
    menu(e, film, ["START"], "back to the menu")
    menu(e, film, ["UP"] * 4, "back to Resume Game", settle=12)
    menu(e, film, ["C"], "resume", settle=10)
    for _ in range(90):                                  # back in play (about 25 frames)
        if e.b(0xFFF7) == 0:
            break
        if film:
            film.step(note="resume", every=2, ms=33)
        else:
            e.run(1)
    else:
        return False
    for _ in range(40):                                  # the game ignores the pad for a moment after a pause
        D.park(e)
        if film:
            film.step(note="", every=1, ms=33)
        else:
            e.run(1)
    s0 = e.w(D.SHOTS)
    ok = D.play(e, hold, film)
    menu(e, film, ["START"], "paused after the shot")
    menu(e, film, ["DOWN"] * 4, "paused: down to Game Stats", settle=12)
    menu(e, film, ["C"], "Game Stats after the shot: Shots unchanged", settle=150)
    if film:
        film.durations[-1] += 4000
    return ok and e.w(D.SHOTS) == s0


def main():
    out = sys.argv[1]
    rom = sys.argv[2] if len(sys.argv) > 2 else str(WORK / "nhl94_retail.bin")
    e = Emu(rom)
    bs = D.bases(e)
    for trial in range(400):
        if take(e, bs[trial % 4], random.Random(trial)):
            film = Film(e)
            take(e, bs[trial % 4], random.Random(trial), film)
            film.frames[0].save(out, save_all=True, append_images=film.frames[1:], duration=film.durations, loop=0,
                                optimize=True)
            print("trial", trial, "frames", len(film.frames))
            return
    print("none found")


if __name__ == "__main__":
    main()
