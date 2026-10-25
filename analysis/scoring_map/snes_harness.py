"""Shots in the real SNES game (the retail ROM, no hook). setup() puts the controlled home skater (pad 1) at a spot
with the puck for `settle` frames (the computer goalie sets himself), from a given random seed; shoot() winds up (A
held `hold` frames) with the d-pad held for the aim and stops just before the frame doshot runs (found by the puck
coming loose). fire() runs that frame from a fresh random seed (the shot's own draws: the perfect-shot roll and the
three scatter draws, and everything after: rebounds, holds, post deflections), and decide() plays it out.

With no hook the shot's draws aren't steered, so each (spot, aim) is sampled: phases (the goalie's state, from the
seed and the moment) times release seeds."""
import os

from paths import SNES_STATE_TOP
from snes_emu import SnesEmu

XPOS, YPOS, XFRAC, YFRAC, XVEL, YVEL = 0x0D55, 0x0DB7, 0x0D77, 0x0DD9, 0x0EC3, 0x0EE3
PUCK = 14
PUCKC = 0x0AD9                    # the carrier's object index (x 2), negative loose
SEED = 0x0792                     # RandomWord's two generators (words at $0792, $0794)
SCORE_HOME = 0x178E               # tmscore, home word
CLOCK = 0x1632
PUCKZ, PUCKVZ = 0x0DF9, 0x0E01
SPA, SHOTSPD, SHOTACC = 0x11A3, 0x1363, 0x1383
LEGSTR, LEGSPD, AIDEF = 0x12E3, 0x1303, 0x1343   # working Agility, Speed, aidef (word arrays, setplayer)
PASSDIR, PASSSPEED = 0x0D03, 0x0D05

SHOOTER = 2                       # home centre, pad 1
GOALIE = 11                       # Montreal's goalie: the top net in period 1, the bottom in period 2

# d-pad held -> passdir (screen directions, 0 = up, clockwise; 8 = none)
DIRPAD = {0: ["UP"], 1: ["UP", "RIGHT"], 2: ["RIGHT"], 3: ["DOWN", "RIGHT"], 4: ["DOWN"], 5: ["DOWN", "LEFT"],
          6: ["LEFT"], 7: ["UP", "LEFT"], 8: []}


def o(k):
    return 2 * k


class Harness:
    def __init__(self, state=SNES_STATE_TOP, top=True, emu=None):
        self.e = emu or SnesEmu()
        self.base = open(state, "rb").read()
        self.top = top
        self.park_y = -230 if top else 230
        g = os.environ.get("NHL94_SNES_GOALIE")  # "agl,spd,dfa,pkc": the computer goalie's working ratings, 0-15
        if g:                                     # (Puck Control in the shotspd slot); aidef is stored, not DfA:
            e = self.e                            # setplayer's goalie formula (15 - DfA + 15) / 2, 7-15
            e.unserialize(self.base)
            agl, spd, dfa, pkc = map(int, g.split(","))
            for a, v in ((LEGSTR, agl), (LEGSPD, spd), (AIDEF, (30 - dfa) // 2), (SHOTSPD, pkc)):
                e.setw(a + o(GOALIE), v)
            self.base = e.serialize()

    def sw(self, a):
        v = self.e.w(a)
        return v - 0x10000 if v & 0x8000 else v

    def put(self, k, x, y):
        e = self.e
        e.setw(XPOS + o(k), x)
        e.setw(XFRAC + o(k), 0)
        e.setw(YPOS + o(k), y)
        e.setw(YFRAC + o(k), 0)
        e.setw(XVEL + o(k), 0)
        e.setw(YVEL + o(k), 0)

    def park(self, keep_shooter=True):
        for k in range(12):
            if k == GOALIE or (k == SHOOTER and keep_shooter):
                continue
            self.put(k, -100 + 18 * k, self.park_y)

    def setup(self, x, y, settle=90, clock=None, seed=None):
        e = self.e
        e.unserialize(self.base)
        if clock is not None:
            e.setw(CLOCK, clock)
        if seed is not None:
            e.setw(SEED, seed >> 16 or 1)
            e.setw(SEED + 2, seed & 0xFFFF or 1)
        for _ in range(settle):
            self.put(SHOOTER, x, y)
            self.park()
            e.setw(PUCKC, o(SHOOTER))
            e.run(1)

    def shoot(self, aim=8, hold=3, maxf=90):
        """A pressed for `hold` frames with the aim's d-pad held throughout. Returns the state just before the doshot
        frame (the puck comes loose on it) and the frame count, or (None, None)."""
        e = self.e
        pad = DIRPAD[aim]
        for f in range(maxf):
            pre = e.serialize()
            self.park()
            e.run(1, hold=(["A"] if f < hold else []) + pad)
            if e.w(PUCKC) & 0x8000:
                return pre, f
        return None, None

    def fire(self, pre, aim, seed):
        e = self.e
        e.unserialize(pre)
        e.setw(SEED, seed >> 16 or 1)
        e.setw(SEED + 2, seed & 0xFFFF or 1)
        self.park()
        e.run(1, hold=DIRPAD[aim])

    def decide(self, maxf=150):
        """Play out until decided: a goal (the score goes up); held by the goalie 20 frames; the puck moving away from
        the goal 4 frames running; or 12+ beyond the goal line."""
        e = self.e
        s0 = e.w(SCORE_HOME)
        sign = 1 if self.top else -1
        away = held = 0
        for f in range(maxf):
            self.park(keep_shooter=False)
            e.run(1)
            if e.w(SCORE_HOME) != s0:
                return 1, f
            held = held + 1 if e.w(PUCKC) == o(GOALIE) else 0
            if held >= 20:
                return 0, f
            vy = self.sw(YVEL + o(PUCK)) * sign
            away = away + 1 if vy < 0 else 0
            if away >= 4 or self.sw(YPOS + o(PUCK)) * sign > 280:
                return 0, f
        return 0, maxf
