"""Shots in the real game (SMAP test ROM). setup() puts the controlled home skater (pad 1) at a spot with the puck
for `settle` frames (the computer goalie sets himself), then shoot() winds up (C held `hold` frames), releases with
the d-pad held for the aim, and stops on the frame doshot runs. play_out() runs on with every skater kept away
until the shot is decided."""
import os

from emu import Emu
from paths import ROM, STATE_TOP

BASE, SZ = 0xB04A, 0x80                    # player records (SortCords): 0-5 home, 6-11 away, 14 the puck
PUCK = BASE + 14 * SZ
PUCKC = 0xB7AA                             # puckc: the carrier's record, $FFxx loose
SCORE_HOME = 0xC6DA
# the test ROM's hook RAM (patch_rom.py)
E = dict(ovr=0xE000, vx=0xE002, vy=0xE004, vz=0xE006, n=0xE010, seed=0xE012, pin=0xE016, dir=0xE018, px=0xE01A,
         py=0xE01C, gvx=0xE020, gvy=0xE022, gvz=0xE024, pout=0xE026, seed2=0xE028)


def rec(k):
    return BASE + k * SZ

DIRPAD = {0: ["UP"], 1: ["UP", "RIGHT"], 2: ["RIGHT"], 3: ["DOWN", "RIGHT"], 4: ["DOWN"], 5: ["DOWN", "LEFT"],
          6: ["LEFT"], 7: ["UP", "LEFT"], 8: []}
SHOTS_HOME = 0xC6CE
GOALIE = 11            # the away goalie's record (away attacks down in period 1, so he guards the top net)
SHOOTER = 2


class Harness:
    def __init__(self, rom=ROM, state=STATE_TOP, top=True, emu=None):
        """top: the state has home shooting at the top net (period 1, live.state) or the bottom (live_p2.state).
        emu: share one emulator (the core is one DLL per process: a second Emu would take over its callbacks)."""
        self.e = emu or Emu(rom)
        self.base = open(state, "rb").read()
        g = os.environ.get("NHL94_GOALIE")       # "agl,spd,dfa,pkc": the computer goalie's working ratings, 0-30
        if g:                                     # (the states' own: 13, 13, about 20, 18); Puck Control is the ShP slot
            e = self.e                            # +$6B holds aidef, not the rating: setplayer stores 15 - DfA / 4
            e.unserialize(self.base)              # (7-15; his reaction timer is aidef / 4 frames). Before 2026-10-25
            agl, spd, dfa, pkc = map(int, g.split(","))     # the value given was written there as it was
            aidef = (((dfa >> 1) ^ 0xF) + 0xF) >> 1
            for off, v in zip((0x68, 0x69, 0x6B, 0x6C), (agl, spd, aidef, pkc)):
                e.setb(rec(GOALIE) + off, v)
            self.base = e.serialize()
        self.top = top
        self.park_y = -230 if top else 230

    def park(self, keep_shooter=True):
        e = self.e
        for k in range(12):
            if k == GOALIE or (k == SHOOTER and keep_shooter):
                continue
            e.setw(rec(k), -100 + 18 * k)
            e.setw(rec(k) + 0x14, self.park_y)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(k) + off, 0)

    def setup(self, x, y, settle=90, clock=None):
        e = self.e
        e.unserialize(self.base)
        if clock is not None:
            e.setw(0xC468, clock)
        for _ in range(settle):
            e.setw(rec(SHOOTER), x)
            e.setw(rec(SHOOTER) + 2, 0)
            e.setw(rec(SHOOTER) + 0x14, y)
            e.setw(rec(SHOOTER) + 0x16, 0)
            for off in (0x28, 0x2A, 0x2C):
                e.setw(rec(SHOOTER) + off, 0)
            self.park()
            e.setw(PUCKC, SHOOTER)
            e.run(1)

    def shoot(self, aim=8, hold=3, maxf=120):
        """Wind up and release; returns the state just before the doshot frame and the frame count, or None."""
        e = self.e
        n0 = e.w(E["n"])
        pad = DIRPAD[aim]
        for f in range(maxf):
            pre = e.serialize()
            self.park()
            e.run(1, hold=(["C"] if f < hold else []) + pad)
            if e.w(E["n"]) != n0:
                return pre, f
        return None, None

    def entry(self):
        e = self.e
        return dict(px=e.sw(E["px"]), py=e.sw(E["py"]), dir=e.w(E["dir"]), pin=e.w(E["pin"]), pout=e.w(E["pout"]),
                    seed=e.l(E["seed"]), v=(e.sw(E["gvx"]), e.sw(E["gvy"]), e.sw(E["gvz"])),
                    sha=e.b(rec(SHOOTER) + 0x6D), shp=e.b(rec(SHOOTER) + 0x6C),
                    top=bool(e.b(rec(SHOOTER) + 0x62) & 0x80), gspa=e.w(0xE02E))

    def play_out(self, maxf=150):
        """After the release: keep every skater away (the shooter too), watch the puck. Returns 'goal' or a
        reason it isn't, and the frames taken."""
        e = self.e
        s0 = e.w(SCORE_HOME)
        for f in range(maxf):
            self.park(keep_shooter=False)
            e.run(1)
            if e.w(SCORE_HOME) != s0:
                return "goal", f
            if e.w(PUCKC) == GOALIE:
                return "held", f
        return "loose", maxf


def place_goalie(h, state):
    """Move the goalie off his set spot as a recorded goalie was at a shot's release: state = [dx, dy, vx, vy] from
    xg.goalie_states (units, units a frame, as if at the top net; mirrored here for the bottom net)."""
    e, g = h.e, rec(GOALIE)
    sg = 1 if h.top else -1
    dx, dy, vx, vy = (sg * v for v in state)
    e.setw(g, e.sw(g) + round(dx))
    e.setw(g + 0x14, e.sw(g + 0x14) + round(dy))
    e.setw(g + 0x28, max(-32768, min(32767, round(vx * 4096))))
    e.setw(g + 0x2A, max(-32768, min(32767, round(vy * 4096))))


def fire(h, pre, v, pad=(), post_seed=None, goalie=None):
    """From the state before the doshot frame, launch with velocity v instead of the game's. post_seed: the random
    generator's state after the release (what happens once the puck touches the goalie, hold or rebound (5.2), a
    stick deflection's direction, is random; in a game, other players' random calls make it independent of the
    shot's own draws). goalie: a recorded goalie state to put him in first (place_goalie)."""
    e = h.e
    e.unserialize(pre)
    if goalie is not None:
        place_goalie(h, goalie)
    e.setw(E["ovr"], 1)
    e.setw(E["vx"], v[0])
    e.setw(E["vy"], v[1])
    e.setw(E["vz"], v[2])
    h.park()
    e.run(1, hold=list(pad))
    e.setw(E["ovr"], 0)
    if post_seed is not None:
        e.setl(0xD066, post_seed)


def decide(h, top=None, maxf=150, fast=True):
    """Play out until decided. Fast stop: the goalie has held it 20 frames; or the puck has been moving away from the goal for 4
    frames in a row (it can't go in without touching something); or it's 12+ beyond the goal line. Goals show as the
    score going up."""
    e = h.e
    s0 = e.w(SCORE_HOME)
    away = held = 0
    top = h.top if top is None else top
    sign = 1 if top else -1
    for f in range(maxf):
        h.park(keep_shooter=False)
        e.run(1)
        if e.w(SCORE_HOME) != s0:
            return 1, f
        if not fast:
            continue
        held = held + 1 if e.w(PUCKC) == GOALIE else 0
        if held >= 20:                      # held 20 frames: past the top net's shoulder-save bobble (5.3)
            return 0, f
        vy = e.sw(PUCK + 0x2A) * sign
        away = away + 1 if vy < 0 else 0
        if away >= 4 or e.sw(PUCK + 0x14) * sign > 276:
            return 0, f
    return 0, maxf
