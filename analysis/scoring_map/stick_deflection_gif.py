"""A GIF of a shot deflected off the goalie's stick, which the Genesis doesn't count as a shot on goal (2026-11-08, a
community member asked to see it; GENESIS_SHOOTING 4.7). There is no special animation: a low puck (height 5 or
under, not rising) reaching the goalie's stick blade faster than the catch limit (about 13,000) is sent off it with
the stick-deflection sound (puckstick .stdef), and only a catch or a body touch counts the shot.

The retail ROM in live play (bot_live states): the home centre at a spot with the puck, everyone else parked, a
slapshot (C held) with Down held (aimed along the ice) at the computer's goalie. Trials are searched for a low puck
that turns back at the goalie, isn't held, isn't a goal, and leaves Home's shots on goal ($C6CE) as they were; the
first is filmed frame by frame, the counter printed under each frame.

python stick_deflection_gif.py OUT.gif [ROM]"""
import random
import sys

from PIL import Image, ImageDraw

from blind_ring_test import park, SHOOTER, GOALIE
from bot import rec, PUCKC, pad
from bot_scenario import live_state
from emu import Emu
from paths import WORK

SHOTS, SCORE = 0xC6CE, 0xC6DA


class Film:
    def __init__(self, e):
        self.e, self.frames = e, []

    def step(self, hold=(), note=None, colour=(255, 255, 255)):
        e = self.e
        if note is None:
            e.run(1, hold=hold)
            return
        e.want_frame = True
        e.run(1, hold=hold)
        e.want_frame = False
        data, w, h, pitch = e.frame
        if getattr(e, "pixfmt", 0) == 2:
            im = Image.frombuffer("RGB", (w, h), data, "raw", "BGR;16", pitch, 1)
        else:
            im = Image.frombuffer("RGBX", (w, h), data, "raw", "BGRX", pitch, 1).convert("RGB")
        im = im.resize((w * 2, h * 2), Image.NEAREST)
        d = ImageDraw.Draw(im)
        d.rectangle((0, im.height - 24, im.width, im.height), fill=(0, 0, 0))
        d.text((8, im.height - 19), f"Home shots on goal: {e.w(SHOTS)}    {note}", fill=colour)
        self.frames.append(im)


def setup(e, base, rnd):
    x, y = rnd.choice((-50, -25, 0, 25, 50)), rnd.choice((120, 150, 180))
    hold = rnd.choice((6, 9, 12))
    e.unserialize(base)
    e.setw(0xC468, 250)
    e.setl(0xD066, rnd.getrandbits(32))
    for k in range(6):
        e.setb(rec(k) + 0x62, e.b(rec(k) + 0x62) & ~8)
    e.setb(rec(SHOOTER) + 0x62, e.b(rec(SHOOTER) + 0x62) | 8)
    e.setw(0xC320, SHOOTER)
    for _ in range(90):
        e.setw(rec(SHOOTER), x & 0xFFFF)
        e.setw(rec(SHOOTER) + 0x14, y & 0xFFFF)
        for off in (0x28, 0x2A, 0x2C):
            e.setw(rec(SHOOTER) + off, 0)
        park(e)
        e.setw(PUCKC, SHOOTER)
        e.run(1)
    return hold


def play(e, hold, film=None):
    """The shot. Returns whether it was a stick deflection that didn't count."""
    s0, g0 = e.w(SHOTS), e.w(SCORE)
    step = film.step if film else (lambda hold=(), note=None, colour=None: e.run(1, hold=hold))
    for f in range(80):
        park(e)
        step(hold=(["C"] if f < hold else []) + pad(4), note="slapshot, Down held: aimed along the ice")
        if e.w(PUCKC) >= 0x8000:
            break
    else:
        return False
    turned = held = False
    for f in range(50):
        park(e, keep_shooter=False)
        vy0 = e.sw(rec(14) + 0x2A)
        low = e.sw(rec(14) + 0x18) <= 5
        step(note="off the goalie's stick: not a shot on goal" if turned else "", colour=(255, 220, 120) if turned else (255, 255, 255))
        if not turned and vy0 > 0 >= e.sw(rec(14) + 0x2A) and low and e.w(PUCKC) >= 0x8000 and \
                abs(e.sw(rec(14) + 0x14) - e.sw(rec(GOALIE) + 0x14)) < 20:
            turned = True
        held = held or e.w(PUCKC) == GOALIE
    return turned and not held and e.w(SHOTS) == s0 and e.w(SCORE) == g0


def main():
    out = sys.argv[1]
    rom = sys.argv[2] if len(sys.argv) > 2 else str(WORK / "nhl94_retail.bin")
    e = Emu(rom)
    bases = [live_state(e, j) for j in range(4)]
    for trial in range(400):
        hold = setup(e, bases[trial % 4], random.Random(trial))
        start = e.serialize()
        if play(e, hold):
            e.unserialize(start)
            film = Film(e)
            play(e, hold, film)
            film.frames[0].save(out, save_all=True, append_images=film.frames[1:], duration=50, loop=0, optimize=True)
            print("trial", trial, "frames", len(film.frames))
            return
    print("none found")


if __name__ == "__main__":
    main()
